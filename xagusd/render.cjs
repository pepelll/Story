// node render.cjs stills 0.5,1.3,2.0,2.9,3.45   → preview/*.png
// node render.cjs final                          → out/xagusd_silent.mp4 (60 fps, 210 кадров)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const W = 1440, H = 1080, FPS = 60, DUR = 3.5;
const mode = process.argv[2] || 'stills';

(async () => {
  const browser = await chromium.launch({ args: ['--disable-gpu-vsync'] });
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'scene.html'));
  await page.evaluate(() => window.ready);
  const shot = async t => {
    await page.evaluate(t => window.renderFrame(t), t);
    return page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: W, height: H } });
  };
  if (mode === 'stills') {
    fs.mkdirSync(path.join(__dirname, 'preview'), { recursive: true });
    const times = (process.argv[3] || '0.5,1.3,2.0,2.9,3.45').split(',').map(Number);
    for (const t of times) fs.writeFileSync(path.join(__dirname, 'preview', `t${t.toFixed(2)}.png`), await shot(t));
  } else {
    fs.mkdirSync(path.join(__dirname, 'out'), { recursive: true });
    const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
      '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
      path.join(__dirname, 'out', 'xagusd_silent.mp4')], { stdio: ['pipe', 'inherit', 'inherit'] });
    const N = Math.round(DUR * FPS);
    for (let i = 0; i < N; i++) {
      const buf = await shot(i / FPS);
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (i % 30 === 0) process.stdout.write(`frame ${i}/${N}\n`);
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
  }
  await browser.close();
})();
