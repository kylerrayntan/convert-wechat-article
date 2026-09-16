'use strict';
// Unit-test generated page event handlers in a mock DOM. This is not a browser/WeChat integration test.
const fs=require('fs'),vm=require('vm');
async function main(){
 const html=fs.readFileSync(process.argv[2],'utf8'),source=html.match(/<script>([\s\S]*)<\/script>/)[1],article=html.match(/<div id="article" tabindex="0">([\s\S]*?)<\/div>/)[1];
 const count=(article.match(/<img /g)||[]).length;
 const els={},listeners={},clipboard={};let mode='ok';
 const get=id=>els[id]||(els[id]={value:'375',style:{},files:[],disabled:true,innerHTML:id==='article'?article:'',focus(){},querySelectorAll(){return Array.from({length:count},()=>({complete:true,naturalWidth:1}));}});
 const ctx={document:{getElementById:get,createRange(){return {selectNodeContents(){}};},addEventListener(t,f){listeners[t]=f;},removeEventListener(t,f){if(listeners[t]===f)delete listeners[t];},execCommand(){if(mode==='throw')throw Error('clipboard unavailable');if(mode==='false')return false;listeners.copy({preventDefault(){},clipboardData:{setData(k,v){clipboard[k]=v;}}});return true;}},getSelection(){return {removeAllRanges(){},addRange(){}};},console};
 vm.createContext(ctx);vm.runInContext(source,ctx);await new Promise(r=>setImmediate(r));
 if(get('copy').disabled)throw Error('button not enabled after images ready');
 get('copy').onclick();if(clipboard['text/html']!==article)throw Error('HTML clipboard payload differs from article');
 if((clipboard['text/html'].match(/<img /g)||[]).length!==count)throw Error('clipboard lost images');
 if(!clipboard['text/plain'])throw Error('plain text fallback missing');
 for(const failure of ['false','throw']){mode=failure;get('copy').onclick();if(listeners.copy)throw Error('copy event listener leaked');if(!get('status').textContent.includes('未完成'))throw Error('failed copy reported success');}
 get('select').onclick();if(!get('status').textContent.includes('⌘C'))throw Error('native selection fallback missing');
 console.log(JSON.stringify({status:'pass',images:count,checks:['whole_article_clipboard_payload','copy_false_fallback','copy_exception_fallback','event_listener_cleanup','native_selection'],scope:'mock DOM only; no real clipboard or WeChat access'}));
}
main().catch(e=>{console.error(e);process.exit(1)});
