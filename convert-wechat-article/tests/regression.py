#!/usr/bin/env python3
"""Test observable content preservation, determinism, tampering, and fail-closed behavior."""
import argparse,base64,hashlib,json,shutil,struct,subprocess,sys,zlib
from pathlib import Path
from zipfile import ZipFile
from xml.sax.saxutils import escape
SKILL=Path(__file__).resolve().parents[1];sys.path.insert(0,str(SKILL/'scripts'))
from verify import verify
NS='xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
def png():
    def c(t,b):return struct.pack('>I',len(b))+t+b+struct.pack('>I',zlib.crc32(t+b)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+c(b'IHDR',struct.pack('>IIBBBBB',2,2,8,2,0,0,0))+c(b'IDAT',zlib.compress((b'\0'+b'\xff\xff\xff'*2)*2))+c(b'IEND',b'')
def fixture(path,body,rels='',image=False,image_payload=None,image_name='test.png'):
    with ZipFile(path,'w') as z:
        z.writestr('word/document.xml',f'<w:document {NS}><w:body>{body}<w:sectPr/></w:body></w:document>')
        z.writestr('word/_rels/document.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+rels+'</Relationships>')
        if image:z.writestr('word/media/'+image_name,png() if image_payload is None else image_payload)
def tree(folder):return {str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}
def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,action='append',default=[]);p.add_argument('--workdir',type=Path,required=True);p.add_argument('--node',default='node');args=p.parse_args();root=args.workdir.resolve();root.mkdir(parents=True,exist_ok=False);checks=[]
    def run(src,label,good=True,extra=()):
        out=root/label;r=subprocess.run([sys.executable,str(SKILL/'scripts/convert.py'),str(src),'--output',str(out),'--node',args.node,*extra],capture_output=True,text=True)
        if good:
            assert r.returncode==0,(label,r.stderr);verify(out);assert (out/'report.json').exists();checks.append(label+':pass')
        else:
            assert r.returncode!=0,label;assert not (out/'article.html').exists(),label;assert (out/'failure.json').exists(),label;checks.append(label+':correctly_rejected')
        return out
    txt='<w:p><w:r><w:t>'+escape('中文 title __ARTICLE__ <script>literal</script>')+'</w:t></w:r></w:p><w:p><w:r><w:t>说明</w:t></w:r><m:oMath><m:sSub><m:e><m:r><m:t>X</m:t></m:r></m:e><m:sub><m:r><m:t>d</m:t></m:r></m:sub></m:sSub></m:oMath><w:r><w:t>结束</w:t></w:r></w:p>'
    drawing='<w:p><w:r><w:drawing><wp:inline><wp:extent cx="952500" cy="952500"/><a:graphic><a:blip r:embed="img1"/></a:graphic></wp:inline></w:drawing></w:r></w:p>'
    rel='<Relationship Id="img1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/test.png"/>'
    sample=root/'fixture.docx';fixture(sample,txt+drawing,rel,True);before=sample.read_bytes();a=run(sample,'synthetic-a');b=run(sample,'synthetic-b');assert tree(a)==tree(b);assert sample.read_bytes()==before;checks+=['synthetic:byte_identical_repeat','source_unchanged']
    # One-pass template expansion and escaped body text must remain literal.
    html=(a/'article.html').read_text();assert '&lt;script&gt;literal&lt;/script&gt;' in html;assert '__ARTICLE__' in html;checks.append('literal_document_text_not_executed')
    cases={
      'hidden-text':'<w:p><w:r><w:rPr><w:vanish/></w:rPr><w:t>隐藏内容</w:t></w:r></w:p>',
      'missing-denominator':'<w:p><m:oMath><m:f><m:num><m:r><m:t>1</m:t></m:r></m:num></m:f></m:oMath></w:p>',
      'unknown-math-child':'<w:p><m:oMath><m:f><m:num><m:r><m:t>1</m:t></m:r></m:num><m:den><m:r><m:t>2</m:t></m:r></m:den><m:rad/></m:f></m:oMath></w:p>',
      'table':txt+'<w:tbl/>',
      'unsupported-math':txt+'<w:p><m:oMath><m:rad><m:e><m:r><m:t>x</m:t></m:r></m:e></m:rad></m:oMath></w:p>',
      'revision':txt+'<w:p><w:del><w:r><w:delText>deleted</w:delText></w:r></w:del></w:p>',
      'missing-image':txt+drawing,
      'picture-transform':txt+drawing.replace('<a:blip r:embed="img1"/>','<a:blip r:embed="img1"><a:grayscl/></a:blip>'),
      'zero-picture-size':txt+drawing.replace('cx="952500"','cx="0"'),
      'cropped-image':txt+drawing.replace('<a:blip','<a:srcRect l="10000"/><a:blip'),
      'line-fraction':txt+'<w:p><m:oMath><m:f><m:fPr><m:type m:val="lin"/></m:fPr><m:num><m:r><m:t>a</m:t></m:r></m:num><m:den><m:r><m:t>b</m:t></m:r></m:den></m:f></m:oMath></w:p>',
      'wide-formula':txt+'<w:p><m:oMath><m:r><m:t>'+('A+'*100)+'B</m:t></m:r></m:oMath></w:p>'}
    for label,body in cases.items():
        f=root/(label+'.docx');fixture(f,body,rel,label in ('cropped-image','picture-transform','zero-picture-size'));run(f,label+'-result',False)
    bad=root/'bad-image';shutil.copytree(a,bad);asset=next((bad/'assets/originals').glob('*'));asset.write_bytes(b'corrupt')
    try:verify(bad);raise AssertionError('image tamper not detected')
    except ValueError:checks.append('image_tamper_detected')
    bad=root/'bad-text';shutil.copytree(a,bad);f=bad/'article.html';s=f.read_text().replace('说明','丢失',1);f.write_text(s)
    try:verify(bad);raise AssertionError('text tamper not detected')
    except ValueError:checks.append('text_tamper_detected')
    # Validate CSS independently, even without the saved report hash.
    for label,old,new in [('formula-css','vertical-align:-','vertical-align:0;unused:-'),('spacing-css','margin:0 0 24px','margin:0 0 0px')]:
        bad=root/label;shutil.copytree(a,bad);(bad/'report.json').unlink();f=bad/'article.html';f.write_text(f.read_text().replace(old,new,1))
        try:verify(bad);raise AssertionError('CSS tamper not detected')
        except ValueError:checks.append(label+':detected')
    from omml import convert,check_structure,M
    from xml.etree import ElementTree as ET
    for val in ['0','false','off']:
        n=ET.fromstring(f'<m:oMath xmlns:m="{M}"><m:r><m:rPr><m:nor m:val="{val}"/></m:rPr><m:t>x</m:t></m:r></m:oMath>');check_structure(n);assert convert(n)=='x'
    checks.append('math_boolean_false_preserved')
    # Non-default settings must change pixel/display dimensions consistently.
    run(sample,'custom-layout',extra=('--font-px','18','--paragraph-after-px','32','--scale','4'))
    jpeg=root/'jpeg.docx';jpeg_data=base64.b64decode('/9j/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAACAAIDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAj/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFAEBAAAAAAAAAAAAAAAAAAAAAP/EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAMAwEAAhEDEQA/AKpAB//Z');fixture(jpeg,txt+drawing,rel.replace('test.png','test.jpg'),True,jpeg_data,'test.jpg');jpeg_out=run(jpeg,'jpeg-result');assert next((jpeg_out/'assets/originals').glob('*.jpg')).read_bytes()==jpeg_data;checks.append('JPEG_original_bytes_preserved')
    corrupt=root/'corrupt-image.docx';fixture(corrupt,txt+drawing,rel,True,b'\x89PNG\r\n\x1a\ninvalid');run(corrupt,'corrupt-image-result',False)
    stress=root/'stress-200.docx';one='<w:p><w:r><w:t>正文</w:t></w:r><m:oMath><m:f><m:num><m:r><m:t>1</m:t></m:r></m:num><m:den><m:r><m:t>x</m:t></m:r></m:den></m:f></m:oMath></w:p>'
    fixture(stress,one*200+drawing*3,rel,True);stress_out=run(stress,'stress-200-result');assert json.loads((stress_out/'report.json').read_text())['counts']=={'paragraphs':203,'equations':200,'original_images':3};checks.append('200_equations_3_images_complete')
    for i,src in enumerate(args.source):
        digest=hashlib.sha256(src.read_bytes()).hexdigest();a=run(src,f'real-{i+1}-a');b=run(src,f'real-{i+1}-b');assert tree(a)==tree(b),f'non-deterministic output: {src.name}';assert hashlib.sha256(src.read_bytes()).hexdigest()==digest;checks.append(src.name+':byte_identical_repeat_and_source_unchanged')
    summary={'status':'pass','checks':checks};(root/'test-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
