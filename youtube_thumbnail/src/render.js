const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1672,height:941},deviceScaleFactor:1});
await p.goto('file://'+process.cwd()+'/cards.html');await p.waitForTimeout(400);
console.log(await p.$$eval('.fit',e=>e.map(x=>x.textContent+':'+x.dataset.final)));
await p.screenshot({path:'cards.png',omitBackground:true});await b.close();})();
