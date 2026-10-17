// node render.mjs stills 6,18,30,42,66   → preview/fNN.png
// node render.mjs final                 → out/usd_rub.mp4 + out/usd_rub_alpha.mov
import {bundle} from '@remotion/bundler';
import {renderMedia, renderStill, selectComposition} from '@remotion/renderer';
import path from 'node:path';
import fs from 'node:fs';

const browserExecutable = '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';
const chromiumOptions = {gl: 'swangle'};
const [mode = 'stills', arg = '6,18,30,42,66'] = process.argv.slice(2);

const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
const comp = (id) => selectComposition({serveUrl, id, browserExecutable, chromiumOptions, timeoutInMilliseconds: 300000});

if (mode === 'stills') {
	fs.mkdirSync('preview', {recursive: true});
	const composition = await comp('UsdRubPreview');
	for (const f of arg.split(',').map(Number)) {
		await renderStill({composition, serveUrl, frame: f, output: `preview/f${String(f).padStart(2, '0')}.png`, browserExecutable, chromiumOptions});
		console.log('still', f);
	}
} else {
	fs.mkdirSync('out', {recursive: true});
	const main = await comp('UsdRub');
	await renderMedia({
		composition: main,
		serveUrl,
		codec: 'h264',
		videoBitrate: '40M',
		pixelFormat: 'yuv420p',
		x264Preset: 'slow',
		imageFormat: 'png',
		audioCodec: 'aac',
		audioBitrate: '320k',
		outputLocation: 'out/usd_rub.mp4',
		browserExecutable,
		chromiumOptions,
		concurrency: 4,
		timeoutInMilliseconds: 300000,
		onProgress: ({progress}) => process.stdout.write(`\rmp4 ${(progress * 100).toFixed(0)}%`),
	});
	console.log();
	const alpha = await comp('UsdRubAlpha');
	await renderMedia({
		composition: alpha,
		serveUrl,
		codec: 'prores',
		proResProfile: '4444',
		imageFormat: 'png',
		pixelFormat: 'yuva444p10le',
		muted: true,
		outputLocation: 'out/usd_rub_alpha.mov',
		browserExecutable,
		chromiumOptions,
		concurrency: 4,
		timeoutInMilliseconds: 300000,
		onProgress: ({progress}) => process.stdout.write(`\rmov ${(progress * 100).toFixed(0)}%`),
	});
	console.log('\ndone');
}
