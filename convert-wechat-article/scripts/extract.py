"""Read-only DOCX extraction with explicit completeness checks."""
import base64,hashlib,io,posixpath,re,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
from omml import M,W,NS,Unsupported,convert,check_structure,local
A='http://schemas.openxmlformats.org/drawingml/2006/main';R='http://schemas.openxmlformats.org/officeDocument/2006/relationships';WP='http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
NS.update(a=A,r=R,wp=WP)
def digest(data):return hashlib.sha256(data).hexdigest()
def xml(data):
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise Unsupported('XML entity declarations are not supported')
    return ET.fromstring(data)
def extract(source,stage):
    raw=source.read_bytes()
    if len(raw)>100*1024*1024:raise Unsupported('DOCX exceeds 100MB input limit')
    z=zipfile.ZipFile(io.BytesIO(raw));infos=z.infolist()
    if len(infos)>5000 or sum(i.file_size for i in infos)>250*1024*1024:raise Unsupported('DOCX expanded size exceeds limit')
    if len({i.filename for i in infos})!=len(infos):raise Unsupported('duplicate ZIP entries')
    root=xml(z.read('word/document.xml'));body=root.find('w:body',NS)
    if body is None:raise Unsupported('missing document body')
    forbidden={'tbl','pict','object','txbxContent','altChunk','ins','del','moveFrom','moveTo','footnoteReference','endnoteReference','commentReference','fldSimple','fldChar','instrText','sym','sdt','AlternateContent','hyperlink','numPr','rPrChange','pPrChange','sectPrChange'}
    for n in body.iter():
        if local(n) in forbidden:raise Unsupported('unsupported document structure: '+local(n))
    for name in z.namelist():
        if re.match(r'word/(header|footer)\d+\.xml$',name):
            h=xml(z.read(name))
            if any((x.text or '').strip() for x in h.findall('.//w:t',NS)) or h.findall('.//w:drawing',NS) or h.findall('.//m:oMath',NS) or h.findall('.//w:pict',NS):raise Unsupported('non-empty header/footer requires explicit handling')
    rels_xml=xml(z.read('word/_rels/document.xml.rels')) if 'word/_rels/document.xml.rels' in z.namelist() else []
    rels={n.get('Id'):n for n in rels_xml}
    if len(rels)!=len(rels_xml):raise Unsupported('duplicate relationship ids')
    # A hidden style may be inherited; fail conservatively rather than expose hidden content.
    for part in ['word/document.xml','word/styles.xml']:
        if part not in z.namelist():continue
        for n in xml(z.read(part)).iter():
            if local(n) in ('vanish','webHidden','specVanish') and n.get('{'+W+'}val','1') not in ('0','false','off'):raise Unsupported('hidden text/style requires explicit handling')
    out_images=stage/'assets'/'originals';out_images.mkdir(parents=True)
    blocks=[];equations=[];images=[];events=[];written=[]
    ignorable={'pPr','rPr','bookmarkStart','bookmarkEnd','proofErr','lastRenderedPageBreak','sectPr','oMathParaPr'}
    def image(n,pi):
        blips=n.findall('.//a:blip',NS)
        if len(blips)!=1 or n.find('.//wp:anchor',NS) is not None:raise Unsupported('only single inline pictures are supported')
        if n.find('.//a:srcRect',NS) is not None:raise Unsupported('cropped picture needs explicit handling')
        if list(blips[0]):raise Unsupported('picture color/alpha transforms need explicit handling')
        if n.find('.//a:effectLst',NS) is not None:raise Unsupported('picture effects are not supported')
        for trans in n.findall('.//a:xfrm',NS):
            if any(trans.get(k)not in (None,'0','false') for k in ['rot','flipH','flipV']):raise Unsupported('rotated/flipped picture')
        rel=rels.get(blips[0].get('{'+R+'}embed'))
        if rel is None or rel.get('TargetMode')=='External':raise Unsupported('external or missing image relationship')
        target=rel.get('Target','');target=posixpath.normpath(target.lstrip('/') if target.startswith('/') else posixpath.join('word',target))
        if not target.startswith('word/media/'):raise Unsupported('image outside word/media')
        data=z.read(target)
        if data.startswith(b'\x89PNG\r\n\x1a\n'):ext='png';mime='image/png'
        elif data.startswith(b'\xff\xd8\xff'):ext='jpg';mime='image/jpeg'
        else:raise Unsupported('only PNG/JPEG original images are supported')
        i=len(images);path=f'assets/originals/image-{i+1:03}.{ext}';(stage/path).write_bytes(data)
        extent=n.find('.//wp:extent',NS)
        if extent is None:raise Unsupported('missing picture size')
        if int(extent.get('cx','0'))<=0 or int(extent.get('cy','0'))<=0:raise Unsupported('invalid picture display size')
        images.append({'file':path,'mime':mime,'sha256':digest(data),'bytes':len(data),'displayWidth':int(extent.get('cx'))/9525,'displayHeight':int(extent.get('cy'))/9525,'paragraph':pi,'sourcePart':target})
        return i
    for pi,p in enumerate(body):
        if local(p)=='sectPr':continue
        if local(p)!='p':raise Unsupported('unsupported body element '+local(p))
        parts=[]
        def walk(n,style=None):
            style=style or {};k=local(n)
            if k=='oMath':
                check_structure(n);idx=len(equations);t=''.join(x.text or '' for x in n.findall('.//m:t',NS));equations.append({'tex':convert(n),'text':t,'paragraph':pi});parts.append({'math':idx});events.append(['math',idx,t]);return
            if k=='drawing':idx=image(n,pi);parts.append({'image':idx});events.append(['image',idx,images[idx]['sha256']]);return
            if k in ignorable:return
            if n.tag=='{'+W+'}r':
                style={}
                for prop,key in [('b','bold'),('i','italic')]:
                    e=n.find('w:rPr/w:'+prop,NS);style[key]=e is not None and e.get('{'+W+'}val')not in ('0','false','off')
                e=n.find('w:rPr/w:vertAlign',NS)
                if e is not None:
                    v=e.get('{'+W+'}val')
                    if v not in ('baseline','superscript','subscript'):raise Unsupported('unsupported text vertical alignment')
                    style['vertical']=v
            if n.tag=='{'+W+'}t':
                t=n.text or '';parts.append({'text':t,**style});events.append(['text',t]);written.append(t);return
            if n.tag=='{'+W+'}tab':parts.append({'text':'\t'});events.append(['text','\t']);return
            if n.tag=='{'+W+'}br':
                if n.get('{'+W+'}type') not in (None,'textWrapping'):raise Unsupported('explicit page/column break')
                parts.append({'text':'\n'});events.append(['text','\n']);return
            if k not in ('p','r','oMathPara'):raise Unsupported('unsupported paragraph element '+k)
            for x in n:walk(x,style)
        walk(p)
        display=any('math'in x for x in parts) and not any(x.get('text','').strip() or 'image'in x for x in parts)
        for x in parts:
            if 'math'in x:equations[x['math']]['display']=display
        text=''.join(x.get('text','') for x in parts)
        heading=pi==0 or bool(re.match(r'^\d+、',text))
        blocks.append({'parts':parts,'display':display,'heading':heading,'paragraph':pi});events.append(['paragraph_end',pi])
    expected_text=''.join(x.text or '' for x in body.findall('.//w:t',NS))
    if ''.join(written)!=expected_text:raise ValueError('source text completeness mismatch')
    counts={'paragraphs':len(body.findall('w:p',NS)),'equations':len(body.findall('.//m:oMath',NS)),'original_images':len(body.findall('.//w:drawing',NS))}
    if (len(blocks),len(equations),len(images))!=tuple(counts.values()):raise ValueError('source count mismatch')
    return {'schema':1,'source':source.name,'source_sha256':digest(raw),'counts':counts,'blocks':blocks,'equations':equations,'images':images,'events':events}
