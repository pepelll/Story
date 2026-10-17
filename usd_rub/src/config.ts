// ─────────────────────────────────────────────────────────────────────────────
//  Всё, что меняется от ролика к ролику, — здесь.
//  «EUR/USD»: parts = ['EUR', '/', 'USD'];  «BTC»: parts = ['BTC'];  «GOLD»: parts = ['GOLD'].
//  Акцентная часть — последняя (accentIndex = -1) или по индексу.
// ─────────────────────────────────────────────────────────────────────────────

export const CONFIG = {
	// Текст: части появляются по очереди. '/' и другие одиночные знаки рисуются как «разделитель».
	parts: ['USD', '/', 'RUB'],
	accentIndex: -1, // -1 = последняя часть

	// Видео
	width: 1920,
	height: 1080,
	fps: 60,
	durationSec: 1.2,

	// Типографика
	fontSize: 220,
	letterSpacing: -0.03, // em
	fontWeight: 700, // Inter Display Bold
	separatorWeight: 300, // «/» тоньше
	separatorOpacity: 0.55,
	textOffsetY: -20, // px, сдвиг текста от центра кадра (минус = выше)

	// Цвета
	colors: {
		bgTop: '#05070A',
		bgBottom: '#0B1418',
		blobGreen: '#2BD98A',
		blobBlue: '#4FB8FF',
		mainTop: '#FFFFFF', // «USD»: вертикальный градиент
		mainBottom: '#CFE9DD',
		accentFrom: '#3BF29A', // «RUB»: зелёный → бирюзовый
		accentTo: '#22D3D8',
		separator: '#E6F4EE',
		glow: '#2BD98A',
		money: '#9BE8C4', // доллары/купюры
		particle: '#BFFFE0',
		chart: '#2BD98A',
	},

	// Тайминги, секунды
	t: {
		bgIn: [0.0, 0.15], // раскрытие фона и блоба
		textStart: 0.08, // первая часть
		stagger: 0.07, // задержка между частями
		partDur: 0.4, // длительность появления одной части
		shine: [0.45, 0.75], // блик
		glowPeak: 0.52, // пик вспышки свечения
		glowEnd: 0.8,
		chart: [0.5, 1.0], // прорисовка линии-графика
		pushIn: [1.0, 1.06], // scale камеры за весь ролик
	},

	// Анимация появления части (по референсу)
	reveal: {
		blur: 20, // px → 0
		rise: 36, // px → 0
		scaleFrom: 0.92,
		separatorRotate: -20, // deg → 0
	},

	// Фон
	money: {count: 13, seed: 7},
	particles: {count: 42, seed: 3},
	showChart: true,
	grain: 0.028, // 2–3 %

	// Качество
	motionBlurSamples: 6,
	shutterAngle: 180,
} as const;

export const FRAMES = Math.round(CONFIG.durationSec * CONFIG.fps);
