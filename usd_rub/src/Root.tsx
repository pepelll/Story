import React from 'react';
import {AbsoluteFill, Composition, Html5Audio, continueRender, delayRender, staticFile} from 'remotion';
import {CameraMotionBlur} from '@remotion/motion-blur';
import {CONFIG, FRAMES} from './config';
import {BackLayer, Grain, Scene} from './Scene';

const fontCss = `
@font-face{font-family:'Inter Display';font-weight:700;src:url(${staticFile('fonts/InterDisplay-Bold.otf')}) format('opentype');}
@font-face{font-family:'Inter Display';font-weight:600;src:url(${staticFile('fonts/InterDisplay-SemiBold.otf')}) format('opentype');}
@font-face{font-family:'Inter Display';font-weight:300;src:url(${staticFile('fonts/InterDisplay-Light.otf')}) format('opentype');}
`;

const Fonts: React.FC = () => {
	const [handle] = React.useState(() => delayRender('fonts'));
	React.useEffect(() => {
		Promise.all(['700', '600', '300'].map((w) => document.fonts.load(`${w} 100px 'Inter Display'`))).then(() =>
			continueRender(handle),
		);
	}, [handle]);
	return <style>{fontCss}</style>;
};

const Main: React.FC<{transparent: boolean; audio: boolean}> = ({transparent, audio}) => (
	<AbsoluteFill style={{backgroundColor: transparent ? 'transparent' : CONFIG.colors.bgTop}}>
		<Fonts />
		<BackLayer transparent={transparent} />
		<CameraMotionBlur samples={CONFIG.motionBlurSamples} shutterAngle={CONFIG.shutterAngle}>
			<Scene />
		</CameraMotionBlur>
		{transparent ? null : <Grain />}
		{audio ? <Html5Audio src={staticFile('sfx.wav')} /> : null}
	</AbsoluteFill>
);

export const Root: React.FC = () => (
	<>
		<Composition id="UsdRub" component={Main} durationInFrames={FRAMES} fps={CONFIG.fps} width={CONFIG.width} height={CONFIG.height} defaultProps={{transparent: false, audio: true}} />
		<Composition id="UsdRubAlpha" component={Main} durationInFrames={FRAMES} fps={CONFIG.fps} width={CONFIG.width} height={CONFIG.height} defaultProps={{transparent: true, audio: false}} />
		<Composition id="UsdRubPreview" component={Main} durationInFrames={FRAMES} fps={CONFIG.fps} width={CONFIG.width} height={CONFIG.height} defaultProps={{transparent: false, audio: false}} />
	</>
);
