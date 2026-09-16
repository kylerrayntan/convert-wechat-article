import base64,hashlib,json,struct
from html.parser import HTMLParser
from pathlib import Path

def sha(b):return hashlib.sha256(b).hexdigest()
def styles(value):
    return dict(item.strip().split(':',1) for item in value.split(';') if ':' in item)
def canonical(events):
    out=[]
    for e in events:
        if e[0]=='text' and out and out[-1][0]=='text':out[-1][1]+=e[1]
        elif e[0]!='text' or e[1]:out.append(list(e))
    return out
class Reader(HTMLParser):
    def __init__(self,A):super().__init__(convert_charrefs=True);self.A=A;self.depth=0;self.events=[];self.p=-1;self.nimages=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='div' and a.get('id')=='article':self.depth=1;return
        if not self.depth:return
        if tag=='div':self.depth+=1
        if tag=='p':
            self.p+=1
            if self.p>=len(self.A['blocks']):raise ValueError('unexpected extra paragraph')
            block=self.A['blocks'][self.p];cfg=self.A['config'];style=styles(a.get('style',''))
            size=cfg['font_px']+(5 if block['paragraph']==0 else 2 if block['heading'] else 0)
            if style.get('font-size')!=str(size)+'px' or style.get('margin')!=f"0 0 {cfg['paragraph_after_px']}px":raise ValueError('paragraph layout mismatch')
        if tag=='br':self.events.append(['text','\n'])
        if tag=='img':
            typ=a['data-kind'];i=int(a['data-index'])
            if typ not in ('formula','original') or i<0:raise ValueError('invalid image kind/index')
            f=self.A['equations' if typ=='formula' else 'images'][i];data=base64.b64decode(a['src'].split(',',1)[1],validate=True)
            if sha(data)!=f['sha256']:raise ValueError('embedded image differs from asset')
            if typ=='formula':
                if struct.unpack('>II',data[16:24])!=(f['pixelWidth'],f['pixelHeight']):raise ValueError('formula pixel bounds mismatch')
                if (int(a['width']),int(a['height']))!=(f['width'],f['height']):raise ValueError('formula display bounds mismatch')
                style=styles(a.get('style',''))
                if style.get('width')!=str(f['width'])+'px' or style.get('height')!=str(f['height'])+'px' or style.get('vertical-align')!=f"-{f['descent']:.3f}px":raise ValueError('formula CSS dimensions/baseline mismatch')
                if (f['pixelWidth'],f['pixelHeight'])!=(f['width']*self.A['config']['scale'],f['height']*self.A['config']['scale']):raise ValueError('formula render scale mismatch')
                self.events.append(['math',i,f['text']])
            else:
                style=styles(a.get('style',''))
                if style.get('height')!='auto' or style.get('width')!='100%' or style.get('max-width')!=str(round(f['displayWidth']))+'px':raise ValueError('original image display style mismatch')
                self.events.append(['image',i,f['sha256']])
            self.nimages+=1
    def handle_data(self,data):
        if self.depth:self.events.append(['text',data])
    def handle_endtag(self,tag):
        if not self.depth:return
        if tag=='p':self.events.append(['paragraph_end',self.A['blocks'][self.p]['paragraph']])
        if tag=='div':self.depth-=1

def verify(folder):
    folder=Path(folder);A=json.loads((folder/'manifest.json').read_text())
    expected={'paragraphs':len(A['blocks']),'equations':len(A['equations']),'original_images':len(A['images'])}
    if A['counts']!=expected:raise ValueError('manifest counts mismatch')
    if (folder/'report.json').exists():
        saved=json.loads((folder/'report.json').read_text())
        if saved.get('article_sha256')!=sha((folder/'article.html').read_bytes()):raise ValueError('article changed since validation')
        if saved.get('manifest_sha256')!=sha((folder/'manifest.json').read_bytes()):raise ValueError('manifest changed since validation')
    for f in A['images']+A['equations']:
        target=(folder/f['file']).resolve()
        if not target.is_relative_to(folder.resolve()):raise ValueError('asset path outside result')
        if sha(target.read_bytes())!=f['sha256']:raise ValueError('asset integrity mismatch: '+f['file'])
    parser=Reader(A);parser.feed((folder/'article.html').read_text());parser.close()
    if canonical(parser.events)!=canonical(A['events']):raise ValueError('HTML content/order differs from source extraction')
    if parser.nimages!=len(A['equations'])+len(A['images']):raise ValueError('HTML image count mismatch')
    if parser.p+1!=len(A['blocks']):raise ValueError('HTML paragraph count mismatch')
    return {'status':'pass','schema':1,'counts':A['counts'],'source_sha256':A['source_sha256'],'config':A['config'],'runtime':A['runtime'],'manifest_sha256':sha((folder/'manifest.json').read_bytes()),'article_sha256':sha((folder/'article.html').read_bytes()),'checks':['source_text_order','paragraph_count','formula_count','image_count','embedded_asset_hashes','original_image_byte_preservation','formula_pixel_dimensions','formula_display_dimensions','formula_css_baseline','paragraph_font_and_spacing','artifact_hashes'],'limitations':['WeChat processing after paste is not verified by this local report.','Same-environment repeatability is tested; OS/font differences can change rendered pixels.']}
if __name__=='__main__':
    import sys
    try:print(json.dumps(verify(sys.argv[1]),ensure_ascii=False,indent=2))
    except Exception as e:print(str(e),file=sys.stderr);sys.exit(1)
