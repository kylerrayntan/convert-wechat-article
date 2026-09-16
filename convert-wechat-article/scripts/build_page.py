import base64,html,json,re
from pathlib import Path

def safe_json(v):return json.dumps(v,ensure_ascii=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
def build(A,stage,template):
    cfg=A['config'];paragraphs=[];plain=[]
    for b in A['blocks']:
        inner='';txt=''
        for p in b['parts']:
            if 'text'in p:
                t=html.escape(p['text']).replace('\n','<br/>');txt+=p['text']
                if p.get('italic'):t='<em>'+t+'</em>'
                if p.get('bold'):t='<strong>'+t+'</strong>'
                if p.get('vertical')=='superscript':t='<sup>'+t+'</sup>'
                if p.get('vertical')=='subscript':t='<sub>'+t+'</sub>'
                inner+=t
            elif 'math'in p:
                i=p['math'];f=A['equations'][i];data=base64.b64encode((stage/f['file']).read_bytes()).decode();txt+=f['text']
                inner+=f'<img data-kind="formula" data-index="{i}" src="data:image/png;base64,{data}" width="{f["width"]}" height="{f["height"]}" alt="{html.escape(f["text"],quote=True)}" style="display:inline-block;width:{f["width"]}px;height:{f["height"]}px;vertical-align:-{f["descent"]:.3f}px;max-width:100%;"/>'
            else:
                i=p['image'];f=A['images'][i];data=base64.b64encode((stage/f['file']).read_bytes()).decode();txt+=f'[原图{i+1}]'
                inner+=f'<img data-kind="original" data-index="{i}" src="data:{f["mime"]};base64,{data}" width="{round(f["displayWidth"])}" alt="原图{i+1}" style="display:block;width:100%;max-width:{round(f["displayWidth"])}px;height:auto;margin:0 auto;"/>'
        size=cfg['font_px']+(5 if b['paragraph']==0 else 2 if b['heading'] else 0)
        style=f'font-size:{size}px;line-height:1.8;margin:0 0 {cfg["paragraph_after_px"]}px;color:#111;text-align:{"center" if b["display"] else "left"};overflow-wrap:break-word;'
        if b['heading']:style+='font-weight:bold;'
        paragraphs.append('<p style="'+style+'">'+inner+'</p>');plain.append(txt)
    article='<section style="font-family:Arial,\'PingFang SC\',\'Microsoft YaHei\',sans-serif;font-size:'+str(cfg['font_px'])+'px;line-height:1.8;color:#111;">'+''.join(paragraphs)+'</section>'
    originals=''
    for i,f in enumerate(A['images']):
        data=base64.b64encode((stage/f['file']).read_bytes()).decode();ext=Path(f['file']).suffix
        originals+=f'<li>图{i+1}：{f["width"]} × {f["height"]} px，{f["bytes"]/1024:.0f} KB　<a download="原图{i+1}{ext}" href="data:{f["mime"]};base64,{data}">Download Original {i+1}</a></li>'
    counts=A['counts'];rep={'__TITLE__':html.escape(Path(A['source']).stem),'__COUNTS__':f'{counts["paragraphs"]} 段正文 · {counts["equations"]} 处公式 · {counts["original_images"]} 张原图','__PARAMS__':f'正文{cfg["font_px"]}px，段后{cfg["paragraph_after_px"]}px；公式{cfg["scale"]}倍分辨率','__IMAGE_COUNT__':str(len(A['equations'])+len(A['images'])),'__IMAGE_OPTIONS__':''.join(f'<option value="{i}">Original {i+1}</option>' for i in range(len(A['images']))),'__ARTICLE__':article,'__ORIGINALS__':originals or '<li>此文档没有原图。</li>','__META__':safe_json(A['images']),'__PLAIN__':safe_json('\n\n'.join(plain))}
    # One-pass substitution prevents document text being treated as template instructions.
    page=re.sub(r'__[A-Z_]+__',lambda m:rep[m.group(0)],template.read_text())
    (stage/'article.html').write_text(page,encoding='utf-8')
