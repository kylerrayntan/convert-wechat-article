#!/usr/bin/env python3
"""Deterministic local DOCX -> copyable HTML. Never edits the source."""
import argparse,json,shutil,subprocess,sys,tempfile
from pathlib import Path
from extract import extract
from build_page import build
from verify import verify

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--node',default='node');p.add_argument('--font-px',type=int,default=17);p.add_argument('--paragraph-after-px',type=int,default=24);p.add_argument('--scale',type=int,default=6);p.add_argument('--max-formula-width-px',type=int,default=351);args=p.parse_args()
    if not 12<=args.font_px<=24 or not 0<=args.paragraph_after_px<=64 or args.scale not in (3,4,6) or not 200<=args.max_formula_width_px<=1000:p.error('layout parameters out of supported range')
    source=args.input.resolve();out=args.output.resolve();skill=Path(__file__).resolve().parent.parent
    if source.suffix.lower()!='.docx' or not source.is_file():p.error('input must be an existing DOCX')
    if out.exists():p.error('output path already exists; choose a new output directory')
    out.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.wechat-build-',dir=out.parent))
    try:
        A=extract(source,stage);A['config']={'font_px':args.font_px,'paragraph_after_px':args.paragraph_after_px,'scale':args.scale,'max_formula_width_px':args.max_formula_width_px}
        (stage/'manifest.json').write_text(json.dumps(A,ensure_ascii=False,indent=2)+'\n')
        cmd=[args.node,str(skill/'scripts/render.cjs'),str(stage)]
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
        if r.returncode:raise RuntimeError('render failed: '+r.stderr.strip()[-3000:])
        A=json.loads((stage/'manifest.json').read_text());build(A,stage,skill/'assets/page.html');report=verify(stage)
        (stage/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        stage.rename(out);print(json.dumps({'status':'pass','output':str(out),'counts':A['counts']},ensure_ascii=False))
        return 0
    except Exception as e:
        shutil.rmtree(stage);out.mkdir();(out/'failure.json').write_text(json.dumps({'status':'failed','error':str(e)},ensure_ascii=False,indent=2)+'\n');print(str(e),file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
