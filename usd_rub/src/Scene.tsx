import React, {useLayoutEffect, useMemo, useRef, useState} from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import {CONFIG} from './config';

const C = CONFIG.colors;
const T = CONFIG.t;
const FONT = "'Inter Display', 'SF Pro Display', Inter, sans-serif";

// cubic-bezier(0.16, 1, 0.3, 1): мягкий выход с сильным замедлением, без перелёта
const easeOutExpo = Easing.bezier(0.16, 1, 0.3, 1);
const easeInOut = Easing.bezier(0.45, 0, 0.25, 1);
const pushEase = Easing.bezier(0.3, 0.1, 0.3, 1);

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const range = (t: number, a: number, b: number, ease = easeOutExpo) =>
	interpolate(t, [a, b], [0, 1], {...clamp, easing: ease});

// Детерминированный ГПСЧ, чтобы кадры не менялись между рендерами
const rng = (seed: number) => {
	let s = seed * 9301 + 49297;
	return () => {
		s = (s * 16807) % 2147483647;
		return (s - 1) / 2147483646;
	};
};

const accentIdx = CONFIG.accentIndex < 0 ? CONFIG.parts.length + CONFIG.accentIndex : CONFIG.accentIndex;
const isSeparator = (p: string) => p.length === 1 && !/[A-Za-z0-9]/.test(p);

type PartState = {opacity: number; blur: number; y: number; scale: number; rot: number; tint: number};

const partState = (t: number, i: number, sep: boolean): PartState => {
	const start = T.textStart + i * T.stagger;
	const p = range(t, start, start + T.partDur);
	const fade = range(t, start, start + T.partDur * 0.55, Easing.bezier(0.33, 0, 0.2, 1));
	const R = CONFIG.reveal;
	return {
		opacity: fade,
		blur: R.blur * (1 - p),
		y: R.rise * (1 - p),
		scale: R.scaleFrom + (1 - R.scaleFrom) * p,
		rot: sep ? R.separatorRotate * (1 - p) : 0,
		// по референсу: слово входит с цветным оттенком и «остывает» к своему цвету
		tint: 1 - range(t, start, start + T.partDur * 0.9),
	};
};

// ── Текст ────────────────────────────────────────────────────────────────────
type Layer = 'fill' | 'glow' | 'shine';

const TextRow: React.FC<{
	t: number;
	layer: Layer;
	offsets?: number[];
	rowWidth?: number;
	measureRef?: React.Ref<HTMLDivElement>;
	style?: React.CSSProperties;
}> = ({t, layer, offsets, rowWidth, measureRef, style}) => {
	// блик: диагональная полоса под 20°, едет слева направо
	const sp = range(t, T.shine[0], T.shine[1], easeInOut);
	const band = 0.16;
	const shinePos = -band + sp * (1 + 2 * band); // доля ширины строки
	return (
		<div
			ref={measureRef}
			style={{
				position: 'absolute',
				left: 0,
				right: 0,
				top: '50%',
				display: 'flex',
				justifyContent: 'center',
				alignItems: 'baseline',
				transform: `translateY(calc(-50% + ${CONFIG.textOffsetY}px))`,
				fontFamily: FONT,
				fontSize: CONFIG.fontSize,
				lineHeight: 1,
				letterSpacing: `${CONFIG.letterSpacing}em`,
				whiteSpace: 'pre',
				...style,
			}}
		>
			{CONFIG.parts.map((part, i) => {
				const sep = isSeparator(part);
				const s = partState(t, i, sep);
				const accent = i === accentIdx;
				let paint: React.CSSProperties;
				if (layer === 'fill') {
					const tint = `rgba(43,217,138,${0.55 * s.tint})`;
					const grad = sep
						? `linear-gradient(180deg, ${C.separator}, ${C.separator})`
						: accent
						? `linear-gradient(100deg, ${C.accentFrom} 0%, ${C.accentTo} 100%)`
						: `linear-gradient(180deg, ${C.mainTop} 18%, ${C.mainBottom} 92%)`;
					paint = {
						backgroundImage: accent || sep ? grad : `linear-gradient(${tint}, ${tint}), ${grad}`,
						WebkitBackgroundClip: 'text',
						backgroundClip: 'text',
						color: 'transparent',
						opacity: s.opacity * (sep ? CONFIG.separatorOpacity : 1),
						filter: s.blur > 0.05 ? `blur(${s.blur}px)` : undefined,
					};
				} else if (layer === 'glow') {
					paint = {
						color: accent ? C.accentFrom : C.glow,
						opacity: s.opacity * (sep ? 0.4 : 1),
						filter: `blur(${42 + s.blur}px)`,
					};
				} else {
					const W = rowWidth ?? 1;
					const off = offsets?.[i] ?? 0;
					const a = 'rgba(255,255,255,0)';
					paint = {
						backgroundImage: `linear-gradient(110deg, ${a} ${(shinePos - band) * 100}%, rgba(255,255,255,0.55) ${(shinePos - band * 0.35) * 100}%, rgba(255,255,255,0.95) ${shinePos * 100}%, rgba(255,255,255,0.55) ${(shinePos + band * 0.35) * 100}%, ${a} ${(shinePos + band) * 100}%)`,
						backgroundSize: `${W}px 100%`,
						backgroundPosition: `${-off}px 0`,
						backgroundRepeat: 'no-repeat',
						WebkitBackgroundClip: 'text',
						backgroundClip: 'text',
						color: 'transparent',
						opacity: s.opacity * (sep ? 0.5 : 1),
					};
				}
				return (
					<span
						key={i}
						style={{
							display: 'inline-block',
							fontWeight: sep ? CONFIG.separatorWeight : CONFIG.fontWeight,
							margin: sep ? '0 0.015em' : undefined,
							padding: '0.12em 0.02em', // запас под блюр, чтобы не обрезался
							transform: `translateY(${s.y}px) scale(${s.scale}) rotate(${s.rot}deg)`,
							transformOrigin: '50% 60%',
							...paint,
						}}
					>
						{part}
					</span>
				);
			})}
		</div>
	);
};

const Title: React.FC<{t: number}> = ({t}) => {
	const ref = useRef<HTMLDivElement>(null);
	const [m, setM] = useState<{offsets: number[]; width: number} | null>(null);
	useLayoutEffect(() => {
		const row = ref.current;
		if (!row) return;
		const spans = Array.from(row.children) as HTMLElement[];
		const first = spans[0].offsetLeft;
		const last = spans[spans.length - 1];
		const width = last.offsetLeft + last.offsetWidth - first;
		const offsets = spans.map((s) => s.offsetLeft - first);
		setM((prev) =>
			prev && prev.width === width && prev.offsets.join() === offsets.join() ? prev : {offsets, width},
		);
	});

	return (
		<AbsoluteFill>
			<TextRow t={t} layer="fill" measureRef={ref} />
			{m && t > T.shine[0] - 0.02 && t < T.shine[1] + 0.02 ? (
				<TextRow t={t} layer="shine" offsets={m.offsets} rowWidth={m.width} style={{mixBlendMode: 'plus-lighter'}} />
			) : null}
		</AbsoluteFill>
	);
};

// Ореол вокруг текста: вынесен из motion blur (он и так размыт, а сэмплы дают ступеньки)
const TextGlow: React.FC<{t: number}> = ({t}) => {
	// свечение: короткая вспышка в момент блика, затем мягкий остаточный ореол
	const flash =
		interpolate(t, [T.shine[0] - 0.05, T.glowPeak], [0, 1], {...clamp, easing: Easing.bezier(0.4, 0, 0.6, 1)}) *
		(1 - range(t, T.glowPeak, T.glowEnd, Easing.bezier(0.25, 0.1, 0.25, 1)));
	const glowOpacity = 0.18 + 0.5 * flash;

	return <TextRow t={t} layer="glow" style={{opacity: glowOpacity}} />;
};

// ── Фон ──────────────────────────────────────────────────────────────────────
const Background: React.FC<{t: number}> = ({t}) => {
	const open = range(t, T.bgIn[0], T.bgIn[1] + 0.1, Easing.bezier(0.33, 0, 0.2, 1));
	return (
		<AbsoluteFill style={{background: `linear-gradient(180deg, ${C.bgTop} 0%, ${C.bgBottom} 100%)`}}>
			<AbsoluteFill
				style={{
					background: 'radial-gradient(ellipse 70% 70% at 50% 50%, rgba(0,0,0,0) 40%, rgba(0,0,0,0.65) 100%)',
				}}
			/>
			<AbsoluteFill style={{background: '#000', opacity: 1 - open}} />
		</AbsoluteFill>
	);
};

// Световой блоб за текстом (входит и в альфа-версию как «свечение»)
const Blob: React.FC<{t: number; strength: number}> = ({t, strength}) => {
	const grow = range(t, T.bgIn[0], T.bgIn[1] + 0.25);
	const flash = Math.exp(-(((t - T.glowPeak) / 0.12) ** 2));
	const breathe = 1 + 0.02 * Math.sin(t * 4);
	const o = strength * grow * (0.85 + 0.25 * flash);
	return (
		<AbsoluteFill style={{transform: `scale(${(0.7 + 0.3 * grow) * breathe})`}}>
			<AbsoluteFill
				style={{
					background: `radial-gradient(ellipse 34% 30% at 50% 50%, ${C.blobGreen}80 0%, ${C.blobGreen}2a 45%, ${C.blobGreen}00 100%)`,
					opacity: o,
				}}
			/>
			<AbsoluteFill
				style={{
					background: `radial-gradient(ellipse 26% 24% at 60% 40%, ${C.blobBlue}44 0%, ${C.blobBlue}14 50%, ${C.blobBlue}00 100%)`,
					opacity: o,
				}}
			/>
			<AbsoluteFill
				style={{
					background: `radial-gradient(ellipse 22% 18% at 42% 60%, #1FB5A033 0%, #1FB5A000 100%)`,
					opacity: o,
				}}
			/>
		</AbsoluteFill>
	);
};

// ── Доллары и купюры ─────────────────────────────────────────────────────────
const DollarGlyph: React.FC<{size: number; outline: boolean}> = ({size, outline}) => (
	<svg width={size} height={size} viewBox="0 0 100 100" style={{overflow: 'visible'}}>
		<text
			x="50"
			y="50"
			textAnchor="middle"
			dominantBaseline="central"
			fontFamily={FONT}
			fontWeight={600}
			fontSize={92}
			fill={outline ? 'none' : C.money}
			stroke={outline ? C.money : 'none'}
			strokeWidth={outline ? 2.2 : 0}
		>
			$
		</text>
	</svg>
);

const Bill: React.FC<{size: number}> = ({size}) => (
	<svg width={size} height={size * 0.46} viewBox="0 0 220 100" style={{overflow: 'visible'}}>
		<rect x="1" y="1" width="218" height="98" rx="10" fill={`${C.money}14`} stroke={C.money} strokeWidth="2" />
		<rect x="11" y="11" width="198" height="78" rx="5" fill="none" stroke={C.money} strokeWidth="1" opacity="0.6" />
		<circle cx="110" cy="50" r="26" fill="none" stroke={C.money} strokeWidth="1.6" />
		<text x="110" y="51" textAnchor="middle" dominantBaseline="central" fontFamily={FONT} fontWeight={600} fontSize="34" fill={C.money}>
			$
		</text>
		<circle cx="38" cy="50" r="7" fill="none" stroke={C.money} strokeWidth="1.2" opacity="0.7" />
		<circle cx="182" cy="50" r="7" fill="none" stroke={C.money} strokeWidth="1.2" opacity="0.7" />
		<line x1="150" y1="30" x2="196" y2="30" stroke={C.money} strokeWidth="1" opacity="0.5" />
		<line x1="24" y1="72" x2="70" y2="72" stroke={C.money} strokeWidth="1" opacity="0.5" />
	</svg>
);

type MoneyItem = {
	kind: 'dollar' | 'dollarOutline' | 'bill';
	layer: 0 | 1 | 2; // 0 дальний, 2 ближний
	x: number;
	y: number;
	size: number;
	rot0: number;
	rotV: number;
	vy: number;
	sway: number;
	phase: number;
};

const LAYERS = [
	{size: [44, 70], blur: 4.5, opacity: 0.16, speed: 45, parallax: 0.02},
	{size: [80, 130], blur: 1.6, opacity: 0.22, speed: 75, parallax: 0.05},
	{size: [170, 250], blur: 0, opacity: 0.27, speed: 120, parallax: 0.1},
];

const makeMoney = (): MoneyItem[] => {
	const r = rng(CONFIG.money.seed);
	const items: MoneyItem[] = [];
	const W = CONFIG.width;
	const H = CONFIG.height;
	// зона текста (+запас), где ближние/средние предметы не ставим
	const safe = {x0: W * 0.2, x1: W * 0.8, y0: H * 0.3, y1: H * 0.72};
	const plan: (0 | 1 | 2)[] = [0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2];
	for (let k = 0; k < CONFIG.money.count; k++) {
		const layer = plan[k % plan.length];
		const L = LAYERS[layer];
		let x = 0;
		let y = 0;
		for (let tries = 0; tries < 200; tries++) {
			x = r() * W;
			y = r() * H * 1.05;
			const inSafe = x > safe.x0 && x < safe.x1 && y > safe.y0 && y < safe.y1;
			const tooClose = items.some((o) => Math.hypot(o.x - x, o.y - y) < (layer === 2 ? 420 : 230));
			if ((layer === 0 || !inSafe) && !tooClose) break;
		}
		const roll = r();
		items.push({
			kind: roll < 0.4 ? 'bill' : roll < 0.7 ? 'dollar' : 'dollarOutline',
			layer,
			x,
			y,
			size: L.size[0] + r() * (L.size[1] - L.size[0]),
			rot0: (r() - 0.5) * 60,
			rotV: (r() - 0.5) * 40,
			vy: L.speed * (0.75 + r() * 0.5),
			sway: 6 + r() * 12,
			phase: r() * Math.PI * 2,
		});
	}
	return items;
};

const Money: React.FC<{t: number}> = ({t}) => {
	const items = useMemo(makeMoney, []);
	const appear = range(t, 0.02, 0.4, Easing.bezier(0.33, 0, 0.2, 1));
	return (
		<AbsoluteFill>
			{[0, 1, 2].map((layer) => {
				const L = LAYERS[layer];
				// параллакс: ближние слои «подъезжают» к камере сильнее
				const par = 1 + L.parallax * pushEase(Math.min(1, t / CONFIG.durationSec));
				return (
					<AbsoluteFill key={layer} style={{transform: `scale(${par})`, filter: L.blur ? `blur(${L.blur}px)` : undefined}}>
						{items
							.filter((m) => m.layer === layer)
							.map((m, i) => {
								const y = m.y - m.vy * t;
								const x = m.x + m.sway * Math.sin(m.phase + t * 2.2);
								const rot = m.rot0 + m.rotV * t;
								const isBill = m.kind === 'bill';
								const w = isBill ? m.size * 1.15 : m.size;
								const h = isBill ? w * 0.46 : m.size;
								return (
									<div
										key={i}
										style={{
											position: 'absolute',
											left: x - w / 2,
											top: y - h / 2,
											width: w,
											height: h,
											opacity: L.opacity * appear,
											transform: `rotate(${rot}deg) ${isBill ? `rotateX(${18 * Math.sin(m.phase + t * 1.5)}deg)` : ''}`,
										}}
									>
										{isBill ? <Bill size={w} /> : <DollarGlyph size={m.size} outline={m.kind === 'dollarOutline'} />}
									</div>
								);
							})}
					</AbsoluteFill>
				);
			})}
		</AbsoluteFill>
	);
};

// ── Боке-пылинки ─────────────────────────────────────────────────────────────
const Particles: React.FC<{t: number}> = ({t}) => {
	const ps = useMemo(() => {
		const r = rng(CONFIG.particles.seed);
		return new Array(CONFIG.particles.count).fill(0).map(() => {
			const big = r() < 0.18;
			return {
				x: r() * CONFIG.width,
				y: r() * CONFIG.height,
				rad: big ? 10 + r() * 14 : 1.5 + r() * 3.5,
				blur: big ? 6 + r() * 6 : r() * 1.5,
				o: big ? 0.08 + r() * 0.1 : 0.35 + r() * 0.5,
				vy: 15 + r() * 50,
				vx: (r() - 0.5) * 20,
				tw: r() * Math.PI * 2,
				twS: 3 + r() * 6,
			};
		});
	}, []);
	const appear = range(t, 0.05, 0.45, Easing.bezier(0.33, 0, 0.2, 1));
	return (
		<AbsoluteFill>
			{ps.map((p, i) => {
				const tw = 0.65 + 0.35 * Math.sin(p.tw + t * p.twS);
				return (
					<div
						key={i}
						style={{
							position: 'absolute',
							left: p.x + p.vx * t - p.rad,
							top: p.y - p.vy * t - p.rad,
							width: p.rad * 2,
							height: p.rad * 2,
							borderRadius: '50%',
							background: `radial-gradient(circle, ${C.particle} 0%, ${C.particle}88 40%, ${C.particle}00 72%)`,
							filter: p.blur > 0.3 ? `blur(${p.blur}px)` : undefined,
							opacity: p.o * tw * appear,
						}}
					/>
				);
			})}
		</AbsoluteFill>
	);
};

// ── Линия-график ─────────────────────────────────────────────────────────────
const Chart: React.FC<{t: number}> = ({t}) => {
	const pts = useMemo(() => {
		const r = rng(11);
		const n = 140;
		const w = 1240;
		const ph = [r() * 6, r() * 6, r() * 6];
		return new Array(n).fill(0).map((_, i) => {
			const u = i / (n - 1);
			const trend = -u * 70 - Math.pow(u, 3) * 40;
			const wig = 16 * Math.sin(u * 13 + ph[0]) + 9 * Math.sin(u * 29 + ph[1]) + 4 * Math.sin(u * 61 + ph[2]);
			return [u * w, trend + wig * (0.4 + 0.6 * u)] as [number, number];
		});
	}, []);
	const cum = useMemo(() => {
		const c = [0];
		for (let i = 1; i < pts.length; i++) c.push(c[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
		return c;
	}, [pts]);
	const total = cum[cum.length - 1];
	const p = range(t, T.chart[0], T.chart[1], Easing.bezier(0.45, 0.05, 0.2, 1));
	if (p <= 0) return null;
	const len = p * total;
	let k = cum.findIndex((c) => c >= len);
	if (k < 1) k = 1;
	const f = (len - cum[k - 1]) / (cum[k] - cum[k - 1] || 1);
	const tip = [pts[k - 1][0] + (pts[k][0] - pts[k - 1][0]) * f, pts[k - 1][1] + (pts[k][1] - pts[k - 1][1]) * f];
	const d = pts.map((q, i) => `${i ? 'L' : 'M'}${q[0].toFixed(1)},${q[1].toFixed(1)}`).join(' ');
	const ox = (CONFIG.width - 1240) / 2;
	const oy = CONFIG.height / 2 + CONFIG.textOffsetY + 190;
	return (
		<AbsoluteFill>
			<svg width={CONFIG.width} height={CONFIG.height} style={{position: 'absolute', overflow: 'visible'}}>
				<defs>
					<linearGradient id="cg" x1="0" x2="1" y1="0" y2="0">
						<stop offset="0" stopColor={C.chart} stopOpacity="0" />
						<stop offset="0.35" stopColor={C.chart} stopOpacity="0.35" />
						<stop offset="1" stopColor={C.accentTo} stopOpacity="0.6" />
					</linearGradient>
					<filter id="cglow" x="-20%" y="-200%" width="140%" height="500%">
						<feGaussianBlur stdDeviation="6" />
					</filter>
				</defs>
				<g transform={`translate(${ox},${oy})`}>
					<path d={d} fill="none" stroke="url(#cg)" strokeWidth="6" strokeDasharray={`${len} ${total}`} filter="url(#cglow)" opacity="0.6" />
					<path d={d} fill="none" stroke="url(#cg)" strokeWidth="2.2" strokeLinecap="round" strokeDasharray={`${len} ${total}`} />
					<circle cx={tip[0]} cy={tip[1]} r="16" fill={C.accentTo} opacity={0.35 * Math.min(1, p * 4)} filter="url(#cglow)" />
					<path d={d} fill="none" stroke="#E9FFF6" strokeWidth="3.4" strokeLinecap="round" strokeDasharray={`0 ${Math.max(0, len - 70)} ${Math.min(len, 70)} ${total}`} opacity={0.85} />
					<circle cx={tip[0]} cy={tip[1]} r="3.4" fill="#F4FFFA" opacity={0.9 * Math.min(1, p * 4)} />
				</g>
			</svg>
		</AbsoluteFill>
	);
};

// ── Зерно ────────────────────────────────────────────────────────────────────
export const Grain: React.FC = () => {
	const frame = useCurrentFrame();
	return (
		<AbsoluteFill style={{mixBlendMode: 'overlay', opacity: CONFIG.grain * 12, pointerEvents: 'none'}}>
			<svg width="100%" height="100%">
				<filter id="grain">
					<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed={Math.floor(frame) % 97} stitchTiles="stitch" />
					<feColorMatrix type="matrix" values="1 0 0 0 0  1 0 0 0 0  1 0 0 0 0  0 0 0 0 1" />
				</filter>
				<rect width="100%" height="100%" filter="url(#grain)" fill="#808080" />
			</svg>
		</AbsoluteFill>
	);
};

// ── Сцена ────────────────────────────────────────────────────────────────────
const useCam = () => {
	const frame = useCurrentFrame();
	const t = frame / CONFIG.fps;
	const [s0, s1] = T.pushIn;
	return {t, cam: s0 + (s1 - s0) * pushEase(Math.min(1, Math.max(0, t / CONFIG.durationSec)))};
};

// Медленные слои (фон и блоб) — вне motion blur: усреднение сэмплов в 8 бит даёт бандинг
export const BackLayer: React.FC<{transparent: boolean}> = ({transparent}) => {
	const {t, cam} = useCam();
	return (
		<AbsoluteFill>
			{transparent ? null : <Background t={t} />}
			<AbsoluteFill style={{transform: `scale(${cam})`}}>
				<Blob t={t} strength={transparent ? 0.6 : 1} />
				<TextGlow t={t} />
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

// Движущиеся слои — внутри motion blur
export const Scene: React.FC = () => {
	const {t, cam} = useCam();
	return (
		<AbsoluteFill style={{transform: `scale(${cam})`}}>
			<Money t={t} />
			<Particles t={t} />
			{CONFIG.showChart ? <Chart t={t} /> : null}
			<Title t={t} />
		</AbsoluteFill>
	);
};
