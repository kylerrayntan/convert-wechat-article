'use strict';
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {mathjax}=require('mathjax-full/js/mathjax.js'),{TeX}=require('mathjax-full/js/input/tex.js'),{SVG}=require('mathjax-full/js/output/svg.js'),{liteAdaptor}=require('mathjax-full/js/adaptors/liteAdaptor.js'),{RegisterHTMLHandler}=require('mathjax-full/js/handlers/html.js'),{AllPackages}=require('mathjax-full/js/input/tex/AllPackages.js');
const sharp=require('sharp');
const root=path.resolve(process.argv[2]);
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
async function run(){
 const A=JSON.parse(fs.readFileSync(path.join(root,'manifest.json'),'utf8')),cfg=A.config;
 const expected=require('../package.json').dependencies;
 for(const name of ['mathjax-full','sharp'])if(require(name+'/package.json').version!==expected[name])throw Error('Dependency version mismatch: '+name);
 const adaptor=liteAdaptor();RegisterHTMLHandler(adaptor);const doc=mathjax.document('',{InputJax:new TeX({packages:AllPackages}),OutputJax:new SVG({fontCache:'none'})});
 const dir=path.join(root,'assets/formulas');fs.mkdirSync(dir,{recursive:true});
 for(const [i,f] of A.equations.entries()){
  let svg=adaptor.outerHTML(adaptor.firstChild(doc.convert(f.tex,{display:f.display})));
  if(/data-mml-node="merror"|data-mjx-error/.test(svg))throw Error('Formula '+(i+1)+' rendering error');
  // MathJax fallback text for CJK punctuation relies on system fonts: record environment.
  const match=svg.match(/viewBox="([^"]+)"/);if(!match)throw Error('Missing SVG bounds '+i);
  const vb=match[1].split(' ').map(Number),unit=cfg.font_px/1000,pad=2;
  f.width=Math.ceil(vb[2]*unit+2*pad);f.height=Math.ceil(vb[3]*unit+2*pad);f.descent=Math.max(0,(vb[1]+vb[3])*unit)+pad;
  if(![...vb,f.width,f.height].every(Number.isFinite)||f.width<=0||f.height<=0||f.height>1000||f.width>cfg.max_formula_width_px)throw Error('Formula '+(i+1)+' is too wide ('+f.width+'px); split at a reviewed mathematical boundary, do not shrink it automatically.');
  const view=[vb[0]-pad/unit,vb[1]-pad/unit,f.width/unit,f.height/unit];
  svg=svg.replace(/viewBox="[^"]+"/,`viewBox="${view.join(' ')}"`).replace(/width="[^"]+"/,`width="${f.width}px"`).replace(/height="[^"]+"/,`height="${f.height}px"`).replace(/currentColor/g,'#000000');
  const file=`assets/formulas/formula-${String(i+1).padStart(3,'0')}.png`,buf=await sharp(Buffer.from(svg)).resize(f.width*cfg.scale,f.height*cfg.scale).flatten({background:'#ffffff'}).png({compressionLevel:9,adaptiveFiltering:false}).toBuffer();
  const meta=await sharp(buf).metadata();if(meta.width!==f.width*cfg.scale||meta.height!==f.height*cfg.scale)throw Error('Formula size mismatch');
  fs.writeFileSync(path.join(root,file),buf);Object.assign(f,{file,sha256:hash(buf),bytes:buf.length,pixelWidth:meta.width,pixelHeight:meta.height});
 }
 for(const f of A.images){
  const buf=fs.readFileSync(path.join(root,f.file));if(hash(buf)!==f.sha256)throw Error('Original image mutated');
  const image=sharp(buf,{limitInputPixels:80000000});const m=await image.metadata();if((m.pages||1)!==1||(m.orientation&&m.orientation!==1))throw Error('Animated/oriented picture needs explicit handling');
  await image.stats();Object.assign(f,{width:m.width,height:m.height});
  if(!Number.isFinite(f.displayWidth)||!Number.isFinite(f.displayHeight)||f.displayWidth<=0||f.displayHeight<=0)throw Error('Invalid original display size');
  const ratio=f.displayWidth/f.displayHeight,actual=m.width/m.height;if(Math.abs(ratio/actual-1)>.02)throw Error('Stretched original picture: explicit handling required');
 }
 A.runtime={node:process.version,platform:process.platform,arch:process.arch,mathjax:require('mathjax-full/package.json').version,sharp:require('sharp/package.json').version,vips:sharp.versions.vips};
 fs.writeFileSync(path.join(root,'manifest.json'),JSON.stringify(A,null,2)+'\n');
}
run().catch(e=>{console.error(e.message);process.exit(1)});
