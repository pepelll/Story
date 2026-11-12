const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1672,height:941},deviceScaleFactor:1});
await p.goto('file://'+process.cwd()+'/cards.html');await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(400);
console.log(await p.$$eval('.fit',e=>e.map(x=>x.textContent+':'+x.dataset.final)), await p.evaluate(()=>document.body.dataset.pr));
await p.screenshot({path:'cards.png',omitBackground:true});await b.close();})();
