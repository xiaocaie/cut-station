// Frame-driven Canvas implementation extracted from the CutStation motion preview.
const W = 960;
const H = 540;
const PI = Math.PI;
const sans = '"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",system-ui,sans-serif';
const palettes = {
  paper: {
    bg: '#eeece3', ground: '#e9e3d4', surface: '#fffdf7', edge: '#faf7ed',
    ink: '#292720', soft: '#646250', faint: '#a89e85',
    rule: '#ddd5c1', track: '#eee8da', line: '#398476', accent: '#24695d',
    tint: '#dceade', warm: '#b94d3c', warmSoft: '#f4ded1',
    shadow: 'rgba(101,80,44,.21)', light: 'rgba(255,255,248,.82)',
    spill: 'rgba(216,193,139,.20)', grid: 'rgba(115,86,54,.10)',
    gold: '#cf902e', goldSoft: '#dfb667',
    display: 'Baskerville,Georgia,serif', weight: 400, dark: false
  },
  stage: {
    bg: '#101217', ground: '#080a0d', surface: '#222734', edge: '#13161d',
    ink: '#f0f4fc', soft: '#b4c2d5', faint: '#8193aa',
    rule: '#353c4c', track: '#262a33', line: '#4a9cff', accent: '#86c5ff',
    tint: '#233c56', warm: '#ffae92', warmSoft: '#523d40',
    shadow: 'rgba(0,4,13,.55)', light: 'rgba(76,94,146,.19)',
    spill: 'rgba(34,60,115,.19)', grid: 'rgba(162,175,198,.19)',
    gold: '#5b7bff', goldSoft: '#6265a4',
    display: '"Space Grotesk","Avenir Next",system-ui,sans-serif', weight: 650, dark: true
  }
};

// Public effect IDs and default lengths are the same as the approved preview.
export const MG_EFFECTS = Object.freeze(Object.fromEntries([
  ['chapter-flip', '章节卡侧翻', 3.55, ['章节侧翻', '编号卡侧翻']],
  ['page-to-card', '网页缩入卡片／样片推入全屏', 5.60, ['网页缩入卡片', '样片推入全屏', '全屏网页缩入截图卡']],
  ['branch-cards', '主卡展开与分支连线', 4.30, ['主卡展开', '分支连线']],
  ['grid-roll-stamp', '填格、滚数与盖章', 5.35, ['填格滚数盖章', '方格累积', '数字滚动', '盖章反馈']],
  ['data-score', '数据生长与分数尺', 6.30, ['数据生长', '分数尺', '柱状生长']],
  ['gallery-2-5d', '2.5D 卡片展台', 7.10, ['2.5D 展台', '卡片展台', '暗场陈列']]
].map(([id, name, duration, aliases]) => [id, Object.freeze({name, duration, aliases: Object.freeze(aliases)})])));

export const MG_PRESETS = Object.freeze(Object.fromEntries(
  Object.entries(palettes).map(([id, tokens]) => [id, Object.freeze({
    ...tokens,
    id,
    name: id === 'paper' ? '暖白纸卡' : '暗场展台',
    sans
  })])
));

const normalize = value => value.normalize('NFKC').toLowerCase().replace(/[\s，、。；]+/gu, '');

/** Resolve a name or one shot description. Multiple matching motions defer to the shot planner. */
export function resolveMgEffect(request) {
  if (typeof request !== 'string') return null;
  const text = normalize(request);
  if (!text) return null;
  if (Object.hasOwn(MG_EFFECTS, text)) return text;

  const direct = Object.entries(MG_EFFECTS).filter(([, {name, aliases}]) =>
    [name, ...aliases].some(value => text.includes(normalize(value))));
  if (direct.length === 1) return direct[0][0];
  if (direct.length > 1) return null;

  const intents = [
    ['chapter-flip', /(?:章节|编号|目录).*(?:翻面|转窄|翻转|翻过去|翻开|侧翻)/u],
    ['page-to-card', /(?:网页|官网|页面|样片|缩略图|卡片).*(?:缩(?:进|成|到|向|回|入)|(?:推近|放大|推进|推入).*全屏)|(?:全屏|整屏|全貌).*(?:缩(?:进|成|到|向|回|入)|退到.*卡)/u],
    ['branch-cards', /(?:主卡|中心卡|总览|项目卡).*(?:展开|分出|连线|分支|接出)|(?:节点|模块卡).*(?:连线|接到)/u],
    ['grid-roll-stamp', /(?:色格|方格|小格|网格|逐格|格子).*(?:填|累积|填满|亮)|(?:滚数|滚到|数字.*(?:跳动|滚动|滚至|滚到)|盖章|落章)/u],
    ['data-score', /(?:柱子|柱形|柱状|条形).*(?:长出|生长|增长|抬高|上升|阈值|达标)|(?:光点|分数|评分).*(?:刻度|评分轴|从.*(?:移|滑|涨|升)到)/u],
    ['gallery-2-5d', /(?:卡片|样片|成品|三张).*(?:虚焦|失焦|倒影|错层|视差|阶梯状)|(?:虚焦|失焦|倒影|错层|视差).*(?:卡片|样片|成品|展板)/u]
  ];
  const matched = intents.filter(([, pattern]) => pattern.test(request));
  return matched.length === 1 ? matched[0][0] : null;
}

export function resolveMgPreset(value) {
  if (typeof value !== 'string') return null;
  const normalized = normalize(value);
  return Object.keys(MG_PRESETS).find(id => id === normalized ||
    normalize(MG_PRESETS[id].name) === normalized) ?? null;
}

const example = {
  cards: Array.from({length: 9}, (_, index) => index + 1),
  selectedCard: 0,
  flipDirection: 'right',
  projectName: 'Fieldwork',
  pageDirection: 'roundtrip',
  branchChips: ['资料分类', '交付顺序'],
  dockTitle: '项目方案',
  tiers: [
    {label: 'Basic', value: 29, filled: 3},
    {label: 'Plus', value: 89, filled: 8},
    {label: 'Studio', value: 189, filled: 20}
  ],
  prefix: '$',
  unit: '/ 月',
  gridUnit: ' 格',
  statusTitle: '费用对比',
  stamp: '预算偏高',
  statusMode: 'all',
  meter: {left: 4, right: 20, leftLabel: '起步', rightLabel: '上限', leftChip: '套餐', rightChip: '按量', label: '单次额度'},
  barValues: [10, 50, 14, 19, 24, 29, 35, 39, 40],
  barLabels: [],
  barsTitle: '阶段完成度',
  barMax: 50,
  barUnit: '%',
  threshold: 50,
  assessmentTitle: '阶段评估',
  scoreMode: 'both',
  railTitle: '版本评分',
  scoreRange: [5, 10],
  scoreFrom: 5.2,
  scoreTo: 7.8,
  scoreDecimals: 2,
  scoreResult: '达到展示标准',
  gallery: [],
  galleryLabels: ['卡片叙事', '节奏剪辑', '空间图形'],
  galleryHeading: '完整流程 + 视觉细节',
  galleryEmphasis: '逐个拆开看',
  galleryTitle: '三支样片，逐个展开',
  tilt: 1,
  blur: 8.4
};

function numberIn(value, minimum, maximum, label) {
  if (!Number.isFinite(value) || value < minimum || value > maximum) {
    throw new RangeError(label + ' must be between ' + minimum + ' and ' + maximum);
  }
  return value;
}

function integerIn(value, minimum, maximum, label) {
  if (!Number.isInteger(value)) throw new RangeError(label + ' must be an integer');
  return numberIn(value, minimum, maximum, label);
}

function gallerySources(images, optional = false) {
  if (!Array.isArray(images) || (images.length !== 3 && !(optional && images.length === 0)) ||
      images.some(image => !image)) {
    throw new RangeError('gallery requires exactly three loaded image sources');
  }
  return images.slice();
}

function settings(content) {
  const options = {...example, ...content};
  if (!Array.isArray(options.cards) || options.cards.length < 1 || options.cards.length > 9) {
    throw new RangeError('cards requires 1 to 9 labels');
  }
  options.cards = options.cards.map(String);
  integerIn(options.selectedCard, 0, options.cards.length - 1, 'selectedCard');
  if (!['left', 'right'].includes(options.flipDirection)) throw new RangeError('Invalid flipDirection');
  if (!['roundtrip', 'shrink', 'expand'].includes(options.pageDirection)) throw new RangeError('Invalid pageDirection');
  if (!Array.isArray(options.branchChips) || options.branchChips.length > 2) {
    throw new RangeError('branchChips accepts up to two labels');
  }
  options.branchChips = options.branchChips.slice();
  if (!Array.isArray(options.tiers) || options.tiers.length < 1 || options.tiers.length > 3) {
    throw new RangeError('tiers requires 1 to 3 entries');
  }
  options.tiers = options.tiers.map(({label, value, filled}) => ({
    label: String(label),
    value: integerIn(value, 0, 99999, 'tier value'),
    filled: integerIn(filled, 0, 20, 'tier filled')
  }));
  if (!['all', 'grid', 'roll', 'stamp'].includes(options.statusMode)) throw new RangeError('Invalid statusMode');
  options.highlightTier = content.highlightTier ?? Math.min(2, options.tiers.length - 1);
  integerIn(options.highlightTier, 0, options.tiers.length - 1, 'highlightTier');
  if (content.tiers && !Object.hasOwn(content, 'stamp')) options.stamp = false;
  if (content.tiers && !Object.hasOwn(content, 'meter')) options.meter = false;
  if (options.meter) {
    options.meter = {...example.meter, ...options.meter};
    integerIn(options.meter.left, 0, 999, 'meter.left');
    integerIn(options.meter.right, 0, 999, 'meter.right');
  }
  if (!Array.isArray(options.barValues) || options.barValues.length < 1 || options.barValues.length > 12) {
    throw new RangeError('barValues requires 1 to 12 entries');
  }
  if (content.barValues && !Object.hasOwn(content, 'threshold')) options.threshold = null;
  if (content.barValues && !Object.hasOwn(content, 'barMax')) {
    options.barMax = Math.max(1, options.threshold ?? 0, ...options.barValues);
  }
  numberIn(options.barMax, .000001, Number.MAX_SAFE_INTEGER, 'barMax');
  options.barValues = options.barValues.map(value => numberIn(value, 0, options.barMax, 'bar value'));
  options.barLabels = options.barLabels.slice();
  if (options.threshold !== null) numberIn(options.threshold, 0, options.barMax, 'threshold');
  const hasRail = Object.hasOwn(content, 'scoreFrom') || Object.hasOwn(content, 'scoreTo');
  if (hasRail && !Object.hasOwn(content, 'scoreResult')) options.scoreResult = '';
  if (!Object.hasOwn(content, 'scoreMode')) {
    if (content.barValues && !hasRail) options.scoreMode = 'bars';
    if (!content.barValues && hasRail) options.scoreMode = 'rail';
  }
  if (!['both', 'bars', 'rail'].includes(options.scoreMode)) throw new RangeError('Invalid scoreMode');
  if (!Array.isArray(options.scoreRange) || options.scoreRange.length !== 2 ||
      !options.scoreRange.every(Number.isFinite) || options.scoreRange[0] >= options.scoreRange[1]) {
    throw new RangeError('scoreRange must contain two increasing finite numbers');
  }
  options.scoreRange = options.scoreRange.slice();
  numberIn(options.scoreFrom, ...options.scoreRange, 'scoreFrom');
  numberIn(options.scoreTo, ...options.scoreRange, 'scoreTo');
  integerIn(options.scoreDecimals, 0, 3, 'scoreDecimals');
  options.gallery = gallerySources(options.gallery, true);
  options.galleryLabels = options.galleryLabels.slice(0, 3);
  numberIn(options.tilt, 0, 2, 'tilt');
  numberIn(options.blur, 0, 28, 'blur');
  if (options.reflectionOpacity !== undefined) numberIn(options.reflectionOpacity, 0, 1, 'reflectionOpacity');
  if (options.caption !== undefined && options.caption !== false && typeof options.caption !== 'string') {
    throw new TypeError('caption must be a string or false');
  }
  return options;
}

function defaultCanvas(width, height) {
  if (typeof document !== 'undefined') {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    return canvas;
  }
  if (typeof OffscreenCanvas !== 'undefined') return new OffscreenCanvas(width, height);
  throw new Error('Provide a canvasFactory in a non-browser renderer');
}

function mediaDimensions(image) {
  const width = image.naturalWidth || image.videoWidth || image.displayWidth || image.width;
  const height = image.naturalHeight || image.videoHeight || image.displayHeight || image.height;
  if (!(Number.isFinite(width) && Number.isFinite(height) && width > 0 && height > 0)) {
    throw new RangeError('Load or decode the canvas image source before drawing');
  }
  return {width, height};
}

function coverRect(width, height, boxWidth, boxHeight) {
  const ratio = Math.max(boxWidth / width, boxHeight / height);
  const cropWidth = boxWidth / ratio;
  const cropHeight = boxHeight / ratio;
  return {x: (width - cropWidth) / 2, y: (height - cropHeight) / 2, width: cropWidth, height: cropHeight};
}

/** Build a reusable painter. The input time is local seconds and may be sampled in any order. */
export function createMgMotion({id, preset = 'paper', duration, content = {}, style = {}, canvasFactory = defaultCanvas} = {}) {
  const effect = resolveMgEffect(id);
  const presetId = resolveMgPreset(preset);
  if (!effect || !presetId) throw new RangeError('Use a known CutStation MG effect and preset');
  const nominalDuration = MG_EFFECTS[effect].duration;
  const seconds = duration ?? nominalDuration;
  numberIn(seconds, .001, Number.MAX_SAFE_INTEGER, 'duration');
  if (typeof canvasFactory !== 'function') throw new TypeError('canvasFactory must be a function');

  const options = settings(content);
  const p = {...MG_PRESETS[presetId], ...style};
  const useExampleCaptions = Object.keys(content).length === 0;
  const hasGalleryLabels = Object.hasOwn(content, 'galleryLabels');
  const hasTiers = Object.hasOwn(content, 'tiers');
  let ctx;
  let frameMedia;
  function paintImage(image, x, y, width, height) {
    const source = mediaDimensions(image);
    const scale = Math.min(width / source.width, height / source.height);
    const w = source.width * scale;
    const h = source.height * scale;
    ctx.drawImage(image, x + (width - w) / 2, y + (height - h) / 2, w, h);
  }

  const clamp = (x, hi = 1) => Math.max(0, Math.min(hi, x));
  const mix = (a, b, x) => a + (b - a) * x;
  const out = x => 1 - (1 - x) ** 3;
  const smooth = x => x * x * (3 - 2 * x);
  const linear = x => x;
  const cue = (t, start, duration, ease = out) => ease(clamp((t - start) / duration));

  function rect(x, y, w, h, radius = 0) {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, radius);
  }

  function fill(x, y, w, h, color, radius = 0) {
    ctx.fillStyle = color;
    rect(x, y, w, h, radius);
    ctx.fill();
  }

  function line(x1, y1, x2, y2, color, width = 1) {
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.stroke();
  }

  function dot(x, y, r, color) {
    ctx.beginPath();
    ctx.arc(x, y, r, 0, PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
  }

  function text(value, x, y, size, options = {}) {
    const {color = p.ink, weight = 500, align = 'left', display = false, maxWidth, font} = options;
    ctx.fillStyle = color;
    ctx.font = weight + ' ' + size + 'px ' + (font ?? (display ? p.display : p.sans));
    ctx.textAlign = align;
    ctx.textBaseline = 'middle';
    if (maxWidth === undefined) ctx.fillText(value, x, y);
    else ctx.fillText(value, x, y, maxWidth);
  }

  function vertical(y, h, a, b) {
    const g = ctx.createLinearGradient(0, y, 0, y + h);
    g.addColorStop(0, a);
    g.addColorStop(1, b);
    return g;
  }

  function halo(x, y, radius, color) {
    const g = ctx.createRadialGradient(x, y, 0, x, y, radius);
    g.addColorStop(0, color);
    const clear = color.startsWith('rgba(') ? color.slice(0, color.lastIndexOf(',')) + ',0)' : 'transparent';
    g.addColorStop(1, clear);
    ctx.fillStyle = g;
    ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
  }

  function panel(x, y, w, h, radius = 20, selected = false, depth = 1) {
    const surface = vertical(y, h, p.surface, p.edge);
    ctx.save();
    ctx.shadowColor = p.shadow;
    ctx.shadowBlur = 21 * depth;
    ctx.shadowOffsetY = 12 * depth;
    fill(x, y, w, h, surface, radius);
    ctx.restore();
    rect(x + .5, y + .5, w - 1, h - 1, radius);
    ctx.strokeStyle = selected ? p.line : p.rule;
    ctx.lineWidth = selected ? 2.25 : 1;
    ctx.stroke();
    line(x + radius, y + 1, x + w - radius, y + 1, p.light, 1);
  }

  const tileSize = p.dark ? 24 : 96;
  const tile = newCanvas(tileSize, tileSize);
  const texturePainter = tile.getContext('2d');
  texturePainter.fillStyle = p.grid;
  if (p.dark) {
    texturePainter.beginPath();
    texturePainter.arc(12, 12, 1.06, 0, PI * 2);
    texturePainter.fill();
  } else {
    let seed = 17;
    for (let i = 0; i < 255; i++) {
      seed = (seed * 16807) % 2147483647;
      const x = seed % 96;
      seed = (seed * 16807) % 2147483647;
      texturePainter.fillRect(x, seed % 96, .8, .8);
    }
  }
  const patterns = new WeakMap();

  function background(drift = 0) {
    fill(0, 0, W, H, vertical(0, H, p.bg, p.ground));
    halo(390 + drift, 100, 465, p.light);
    halo(738 + drift * .35, 360, 370, p.spill);
    ctx.save();
    ctx.translate(drift * .25, 0);
    if (!patterns.has(ctx)) patterns.set(ctx, ctx.createPattern(tile, 'repeat'));
    fill(-70, 0, W + 140, H, patterns.get(ctx));
    ctx.restore();
  }

  function treeMark(x, y, size) {
    const s = size / 24;
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(s, s);
    ctx.lineCap = 'round';
    line(0, -6, 0, 5, p.accent, 1.8);
    line(-6, 1, 6, 1, p.accent, 1.8);
    dot(0, -7, 3, p.accent);
    [-7, 0, 7].forEach(u => dot(u, 6, 2.5, p.accent));
    ctx.restore();
  }

  function caption(example, opacity = 1) {
    const value = options.caption ?? (useExampleCaptions && !frameMedia ? example : '');
    if (!value) return;
    withOpacity(opacity, () => {
      ctx.font = (p.dark ? '500' : '660') + ' 24px ' + p.sans;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.strokeStyle = 'rgba(12,13,14,.88)';
      ctx.lineJoin = 'round';
      ctx.lineWidth = p.dark ? 2.4 : 4.5;
      ctx.strokeText(value, 480, 504, 878);
      ctx.fillStyle = '#fffdf5';
      ctx.fillText(value, 480, 504, 878);
    });
  }

  function chip(value, x, y, width, color = p.accent) {
    fill(x - width / 2, y - 13, width, 26, p.surface, 12);
    rect(x - width / 2 + .5, y - 12.5, width - 1, 25, 12);
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.stroke();
    text(value, x, y, 15, {color, align: 'center', weight: 650, maxWidth: width - 10});
  }

  function comparisonDock(label, result, status = 0) {
    const left = 185;
    const y = 423;
    panel(left, y, 590, 53, 11, false, .65);
    text(label, left + 17, y + 28, 18, {weight: 650, maxWidth: 135});
    for (const [i, heading] of ['规模', '完成度', '结果'].entries()) {
      const x = left + 175 + i * 137;
      const active = status === i;
      if (active) fill(x - 12, y + 5, 123, 43, i === 1 ? p.tint : p.warmSoft, 7);
      text(heading, x, y + 16, 13, { color: p.soft });
      if (active && result) text(result, x, y + 36, 17, { color: i === 1 ? p.accent : p.warm, weight: 680 });
      else line(x, y + 34, x + 95, y + 34, p.rule, 1.4);
    }
  }

  function withOpacity(alpha, paint) {
    if (alpha <= 0) return;
    ctx.save();
    ctx.globalAlpha *= alpha;
    paint();
    ctx.restore();
  }

  function chapterFace(value, x, y, w, h, depth = .70) {
    panel(x, y, w, h, 10, false, depth);
    rect(x + 6, y + 6, w - 12, h - 12, 7);
    ctx.strokeStyle = p.rule;
    ctx.lineWidth = 1.2;
    ctx.stroke();
    text(String(value), x + w / 2, y + h / 2 + 2, h * .49, {
      display: true, weight: p.weight, align: 'center', color: p.faint, maxWidth: w - 15
    });
  }

  function cardLayout() {
    const count = options.cards.length;
    const gap = count === 9 ? 12 : 17;
    const width = Math.min(count === 9 ? 83 : 132, (843 - gap * (count - 1)) / count);
    const total = count * width + (count - 1) * gap;
    return {width, start: count === 9 ? 59 : (W - total) / 2, step: width + gap};
  }

  function chapter(t) {
    if (t >= 1.82) {
      workspace(0, 0, W, 0, t - 1.82);
      caption('第一章，从项目主页开始', cue(t, 1.82, .20));
      return;
    }
    background();
    const raise = cue(t, .78, .43, smooth);
    const flip = cue(t, 1.25, .57, smooth);
    const {width, start, step} = cardLayout();
    const height = 115;
    const anchor = start + options.selectedCard * step;
    for (const [index, label] of options.cards.entries()) {
      if (index !== options.selectedCard) chapterFace(label, start + index * step, 192, width, height);
    }
    withOpacity(raise * .68, () => {
      rect(anchor, 192, width, height, 9);
      ctx.strokeStyle = p.faint;
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 6]);
      ctx.stroke();
    });
    const yaw = flip * PI / 2;
    const scale = mix(1, 1.62, raise);
    const center = anchor + width / 2;
    const lean = options.flipDirection === 'left' ? -1 : 1;
    const target = clamp(center + 31.5 * lean, W - width);
    ctx.save();
    ctx.translate(mix(center, target, raise), mix(249.5, 249, raise));
    ctx.scale(scale, scale);
    ctx.transform(Math.max(.012, Math.cos(yaw)), Math.sin(yaw) * .14 * lean, 0, 1, 0, 0);
    chapterFace(options.cards[options.selectedCard], -width / 2, -height / 2, width, height, 1.12);
    ctx.restore();
    caption('第一章，先看项目主页');
  }

  function workspace(x, y, width, radius, t) {
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(width / W, width / W);
    panel(0, 0, W, H, radius, false, .66);
    ctx.save();
    rect(1, 1, W - 2, H - 2, radius);
    ctx.clip();
    fill(0, 0, W, H, p.dark ? p.edge : '#fffdf8');
    const page = frameMedia?.page ?? options.page;
    if (page) {
      paintImage(page, 0, 0, W, H);
      ctx.restore();
      ctx.restore();
      return;
    }
    line(47, 67, 913, 67, p.rule, 1.15);
    text(options.projectName, 55, 38, 27, {display: true, weight: p.weight, maxWidth: 370});
    text('项目', 712, 38, 16, { color: p.soft });
    text('归档', 778, 38, 16, { color: p.soft });
    fill(844, 22, 67, 31, p.ink, 5);
    text('打开', 877.5, 38, 15, { color: p.surface, align: 'center' });
    text('Work takes', 258, 206, 59, { display: true, weight: p.weight, align: 'center' });
    text('shape.', 258, 266, 59, { display: true, weight: p.weight, align: 'center' });
    text('从第一份资料开始', 258, 324, 21, { color: p.soft, align: 'center' });
    fill(182, 361, 152, 38, p.ink, 5);
    text('查看项目资料', 258, 380, 17, { color: p.surface, align: 'center', weight: 650 });
    editorialBoard(471, 91, 433, 374, t);
    ctx.restore();
    ctx.restore();
  }

  function editorialBoard(x, y, width, height, t) {
    ctx.save();
    rect(x, y, width, height, 2);
    ctx.clip();
    fill(x, y, width, height, vertical(y, height, '#8ba9a1', '#3d6462'));
    const noteColors = ['#c7c9aa', '#efdbab', '#a9c6be', '#c7b8a2', '#d9d6bf'];
    for (let i = 0; i < 23; i++) {
      const sx = x + 9 + (i * 77) % 403;
      const sy = y + 8 + (i * 61) % 279;
      const w = 34 + i * 13 % 66;
      const h = 39 + i * 19 % 58;
      ctx.save();
      ctx.translate(sx, sy);
      ctx.rotate((i % 7 - 3) * .061);
      ctx.shadowColor = 'rgba(20,39,37,.28)';
      ctx.shadowBlur = 8;
      ctx.shadowOffsetY = 4;
      fill(0, 0, w, h, noteColors[i % noteColors.length]);
      ctx.shadowColor = 'transparent';
      for (let r = 0; r < 4; r++) {
        line(8, 13 + r * 7, w - 9 - r * (i % 3), 13 + r * 7, 'rgba(65,85,74,.42)', 1.3);
      }
      ctx.restore();
    }
    const tableY = y + height * .79;
    fill(x, tableY, width, height, vertical(tableY, 120, '#8a6d49', '#55472f'));
    ctx.save();
    ctx.translate(x + width * .67, tableY + 22);
    ctx.rotate(-.13);
    fill(-54, -23, 112, 61, '#d9d5b9', 2);
    for (let j = 0; j < 6; j++) line(-45, -15 + j * 7, 46, -15 + j * 7, '#a9a48e');
    ctx.restore();
    fill(x + 33, tableY - 44, 72, 61, '#1d3639', 4);
    fill(x + 40, tableY - 37, 58, 44, '#567971', 2);
    const glint = .55 + .45 * Math.sin(t * 1.7);
    halo(x + width * .79, y + height * .70, 260, 'rgba(255,229,161,' + (.28 + .09 * glint) + ')');
    fill(x, y, width, height, vertical(y, height, 'rgba(247,220,174,.04)', 'rgba(27,31,26,.12)'));
    ctx.restore();
  }

  function portal(t) {
    background();
    const shrink = options.pageDirection === 'expand' ? 1 : cue(t, .93, .87, smooth);
    const pushStart = options.pageDirection === 'expand' ? .93 : 3.99;
    const push = options.pageDirection === 'shrink' ? 0 : cue(t, pushStart, .85, smooth);
    const frame = shrink * (1 - push);
    const away = options.pageDirection === 'shrink' ? 1 : 1 - cue(t, pushStart - .34, .26, smooth);
    const showComparison = options.showComparison ?? (hasTiers || !(options.page || frameMedia?.page));
    if (showComparison) {
      for (const [i, {label, value, filled}] of options.tiers.entries()) {
        const entrance = options.pageDirection === 'expand' ? 1 : cue(t, 1.66 + i * .13, .43);
        withOpacity(entrance * away, () => {
          tierCard(420 + i * 163, 116 + (1 - entrance) * 22, 151, label, value, filled, .88);
        });
      }
      const dockArrival = options.pageDirection === 'expand' ? 1 : cue(t, 1.67, .38);
      withOpacity(dockArrival * away, () => comparisonDock(options.dockTitle, '', 0));
    }
    workspace(57 * frame, 135 * frame, mix(W, 325, frame), 25 * frame, t);
    caption(t < 1.03 ? '先看完整页面' : t < 3.83 ? '页面缩入版面，右侧展开对比' : '沿着同一张卡推回全屏');
  }

  function cable(x, target, fraction, y, endY) {
    if (fraction === 0) return;
    const c1 = [x, y + 13];
    const c2 = [target, endY - 23];
    ctx.beginPath();
    ctx.moveTo(x, y);
    const samples = 26;
    for (let step = 1; step <= samples; step++) {
      const u = step / samples * fraction;
      const v = 1 - u;
      const a = v ** 3;
      const b = 3 * v * v * u;
      const c = 3 * v * u * u;
      const d = u ** 3;
      ctx.lineTo(a * x + b * c1[0] + c * c2[0] + d * target,
        a * y + b * c1[1] + c * c2[1] + d * endY);
    }
    ctx.strokeStyle = p.line;
    ctx.lineWidth = 1.7;
    ctx.stroke();
    if (fraction > .96) dot(target, endY, 4.5, p.accent);
  }

  function branches(t) {
    background();
    const lift = cue(t, .66, .77, smooth);
    const cardW = mix(236, 154, lift);
    const cardH = mix(171, 108, lift);
    const x = 480 - cardW / 2;
    const y = mix(175, 38, lift);
    withOpacity(1 - lift, () => {
      fill(40, 352, 880, 4, p.rule, 2);
      withOpacity(.5, () => {
        ctx.filter = 'blur(3px)';
        chip('文档', 173, 240, 77);
        chip('归档', 783, 317, 78);
      });
    });
    const layout = cardLayout();
    const count = options.cards.length;
    for (let i = 0; i < count; i++) {
      const target = layout.start + layout.width / 2 + i * layout.step;
      cable(480 + (i - (count - 1) / 2) * 5, target, cue(t, 1.37 + i * .066, .63, smooth), y + cardH - 1, 192);
    }
    panel(x, y, cardW, cardH, 11, false, .9);
    treeMark(x + 21, y + 22, 17);
    text('项目', x + 38, y + 23, 15, { color: p.soft, weight: 650 });
    text(options.projectName, 480, y + cardH * .58, mix(53, 33, lift), {
      display: true, weight: p.weight, align: 'center',
      maxWidth: options.projectName === example.projectName ? undefined : cardW - 23
    });
    line(x + 13, y + cardH - 17, x + cardW - 13, y + cardH - 17, p.rule, 1.2);
    for (const [i, label] of options.cards.entries()) {
      const arrive = cue(t, 1.09 + i * .058, .34);
      withOpacity(arrive, () => chapterFace(label, layout.start + i * layout.step, 192 + (1 - arrive) * 20, layout.width, 115));
    }
    withOpacity(cue(t, 2.03, .4), () => {
      options.branchChips.forEach((label, i) => chip(label, 403 + i * 153, 372, 100));
    });
    caption('从一个项目展开九个章节');
  }

  function digitStrip(distance, x, y, size, color = p.ink) {
    const base = Math.floor(distance);
    const frac = distance - base;
    const stride = size * 1.12;
    ctx.save();
    rect(x - size * .32, y - stride / 2, size * .64, stride);
    ctx.clip();
    const style = { display: true, weight: p.weight, align: 'center', color };
    text(String(base % 10), x, y - frac * stride, size, style);
    text(String((base + 1) % 10), x, y + (1 - frac) * stride, size, style);
    ctx.restore();
  }

  function tierCard(x, y, width, label, price, slots, progress, highlighted = 0, gridProgress = progress) {
    const height = 243;
    const cell = (width - 38) / 5;
    panel(x, y, width, height, 10, highlighted > .65, .83);
    text(label, x + 15, y + 34, 27, {display: true, weight: p.weight, maxWidth: width - 30});
    text(options.prefix, x + 15, y + 70, 24, {display: true, weight: p.weight, maxWidth: 20});
    const digits = [...String(price)];
    const digitGap = digits.length > 4 ? 12 : 16;
    digits.forEach((digit, i) => {
      digitStrip(Number(digit) * progress, x + 36 + i * digitGap, y + 70, digits.length > 4 ? 22 : 27);
    });
    text(options.unit, x + Math.max(99, 39 + digitGap * digits.length), y + 73, 14,
      {color: p.soft, maxWidth: 27});
    line(x + 14, y + 91, x + width - 14, y + 91, p.rule, 1);
    for (let n = 0; n < 20; n++) {
      const px = x + 15 + n % 5 * (cell + 1.5);
      const py = y + 107 + Math.floor(n / 5) * 23;
      rect(px + .5, py + .5, cell - 4, 17, 2.3);
      ctx.strokeStyle = p.rule;
      ctx.lineWidth = 1;
      ctx.stroke();
      withOpacity(clamp((slots * gridProgress - n) * 1.7), () => fill(px, py, cell - 3, 18, p.dark ? p.line : '#d5725a', 2.3));
    }
    text(String(Math.floor(slots * gridProgress + .05)) + options.gridUnit, x + 16, y + 218, 17, {color: p.warm, weight: 700, maxWidth: width - 32});
  }

  function costStamp(t, x, y) {
    const fall = cue(t, 2.15, .20, linear);
    const bounce = fall < .58 ? mix(1.34, .94, out(fall / .58)) : mix(.94, 1, out((fall - .58) / .42));
    withOpacity(cue(t, 2.15, .095), () => {
      ctx.translate(x, y);
      ctx.rotate(.13);
      ctx.scale(bounce, bounce);
      fill(-51, -19, 102, 38, p.surface, 5);
      rect(-50, -18, 100, 36, 4);
      ctx.strokeStyle = p.warm;
      ctx.lineWidth = 2.5;
      ctx.stroke();
      text(options.stamp, 0, 0, 23, {color: p.warm, weight: 820, align: 'center', maxWidth: 92});
      const spark = cue(t, 2.19, .30);
      withOpacity((1 - spark) * cue(t, 2.19, .08), () => {
        for (let i = 0; i < 7; i++) {
          const angle = -.2 - i * .43;
          const start = 41 + spark * 13;
          line(Math.cos(angle) * start, Math.sin(angle) * start,
            Math.cos(angle) * (start + 10), Math.sin(angle) * (start + 10), p.gold, 2);
        }
      });
    });
  }

  function status(t) {
    background();
    const mode = options.statusMode;
    const showStamp = options.stamp && (mode === 'all' || mode === 'stamp');
    const showNumbers = mode === 'all' || mode === 'roll';
    const animateGrid = mode === 'all' || mode === 'grid';
    const useMeter = options.meter && mode === 'all';
    const fan = useMeter ? cue(t, 3.29, .64, smooth) : 0;
    const showWorkspace = !hasTiers || Boolean(options.page || frameMedia?.page);
    if (showWorkspace) withOpacity(1 - fan, () => workspace(58 - fan * 27, 143, 325, 25, t));
    const start = showWorkspace ? 419 : (W - (options.tiers.length * 171 - 20)) / 2;
    const gap = showWorkspace ? 163 : 171;
    const highlight = options.highlightTier;
    for (const [i, {label, value, filled}] of options.tiers.entries()) {
      const rise = cue(t, .15 + i * .095, .40);
      const increment = cue(t, .66 + i * .15, 1.09, smooth);
      const x = mix(start + i * gap, 188 + i * 52, fan);
      const y = mix(115, 153 + i * 8, fan) + (1 - rise) * 23;
      withOpacity(rise, () => {
        ctx.translate(x + 75, y + 119);
        ctx.rotate(fan * (i - 1) * .13);
        ctx.scale(mix(1, .83, fan), mix(1, .83, fan));
        tierCard(-75, -119, 151, label, value, filled, showNumbers ? increment : 1,
          i === highlight && showStamp ? cue(t, 2.16, .13) : 0, animateGrid ? increment : 1);
        if (i === highlight && showStamp) costStamp(t, 16, -120);
      });
    }
    const showMeter = useMeter ? cue(t, 3.67, .46) : 0;
    withOpacity(showMeter, () => {
      chip(options.meter.leftChip, 311, 120, 79);
      chip(options.meter.rightChip, 694, 120, 79);
      line(354, 120, 651, 120, p.line, 1.4);
      const y = 176 + (1 - showMeter) * 25;
      panel(519, y, 355, 164, 14, false, 1.1);
      fill(525, y + 6, 343, 152, vertical(y, 152, '#172747', '#111b35'), 11);
      line(696, y + 30, 696, y + 119, '#384e77', 1);
      text(options.meter.leftLabel, 612, y + 38, 19, {color: '#b3c2e2', align: 'center', maxWidth: 132});
      text(options.meter.rightLabel, 782, y + 38, 19, {color: '#b3c2e2', align: 'center', maxWidth: 132});
      const settle = cue(t, 3.94, .63, smooth);
      const cells = [[options.meter.left, 580, 615], [options.meter.right, 736, 776]];
      cells.forEach(([value, prefixX, digitsX]) => {
        text(options.prefix, prefixX, y + 94, 34, {color: '#ffc657', display: true, weight: p.weight, maxWidth: 26});
        const digits = [...String(value)];
        const gap = digits.length > 2 ? 23 : 32;
        digits.forEach((digit, i) => digitStrip(Number(digit) * settle, digitsX + gap * i,
          y + 91, digits.length > 2 ? 37 : 54, '#ffcc6a'));
      });
      text(options.meter.label, 697, y + 137, 15, {color: '#9cadcc', align: 'center', maxWidth: 290});
    });
    comparisonDock(options.statusTitle, t >= 2.31 && showStamp ? options.stamp : '', 0);
    const statusCaption = {
      grid: '色格按档位累积',
      roll: '数字依次滚到目标值',
      stamp: '重点档位落章',
      all: t < 2.15 ? '色格按档位累积' : t < 3.31 ? '重点档位落章' : '再把结果对到按量报价'
    };
    caption(statusCaption[mode]);
  }

  function scoreBars(t) {
    const values = options.barValues;
    const base = 358;
    const step = Math.min(110, 624 / Math.max(1, values.length - 1));
    const barWidth = Math.min(48, step * .65);
    const top = base - 149 * options.threshold / options.barMax;
    chip(options.barsTitle, 489, 65, 115);
    const legendColor = p.dark ? p.gold : p.goldSoft;
    fill(179, 100, 12, 12, legendColor, 2);
    text('各阶段', 200, 107, 16, { color: p.soft });
    line(153, base, 866, base, p.dark ? '#4d5567' : '#b8a98c', 1.3);
    values.forEach((value, i) => {
      const growth = cue(t, .27 + i * .145, .59, smooth);
      const x = 508 + (i - (values.length - 1) / 2) * step;
      const height = value / options.barMax * 149 * growth;
      if (height > 1) {
        const color = p.dark
          ? vertical(base - height, height, i === 1 ? '#9a79ff' : '#739dff', '#3152c7')
          : i < 2 ? p.gold : p.goldSoft;
        fill(x - barWidth / 2, base - height, barWidth, height, color, [5, 5, 0, 0]);
      }
      text(options.barLabels[i] ?? String(i + 1), x, base + 18, 15, {align: 'center', color: p.soft, maxWidth: step - 6});
      if (i < 2 || i === values.length - 1) {
        withOpacity(cue(growth, .84, .14), () => {
          text(value + options.barUnit, x, base - height - 15, 18, { align: 'center', color: p.dark ? p.accent : '#96651f', weight: 700 });
        });
      }
    });
    const threshold = options.threshold === null ? 0 : cue(t, 1.92, .38);
    withOpacity(threshold, () => {
      ctx.save();
      ctx.setLineDash([9, 5]);
      line(153, top, mix(153, 857, threshold), top, p.line, 2);
      ctx.restore();
      chip('目标 ' + options.threshold + options.barUnit, 851, top, 91);
    });

    const reached = options.barValues.some(value => value >= options.threshold);
    const result = t > 2.08 && options.threshold !== null
      ? options.threshold + options.barUnit + (reached ? ' 达标' : ' 目标')
      : '';
    comparisonDock(options.assessmentTitle, result, 1);
  }

  function scoreRail(t) {
    const start = 178;
    const width = 604;
    const y = 285;
    const [minimum, maximum] = options.scoreRange;
    const score = mix(options.scoreFrom, options.scoreTo, cue(t, .43, 1.05, smooth));
    const ratio = (score - minimum) / (maximum - minimum);
    const marker = start + width * ratio;
    text(options.railTitle, 403, 192, 20, { color: p.dark ? p.accent : p.soft, align: 'right' });
    text(score.toFixed(options.scoreDecimals), 510, 177, 85, {display: true, weight: p.weight, align: 'center', maxWidth: 205});
    fill(start, y, width, 20, p.track, 10);
    ctx.save();
    rect(start, y, width, 20, 10);
    ctx.clip();
    for (let i = 0; i < 64; i++) {
      const x = start + 14 + i * 10.5;
      line(x, y + 21, x + 20, y - 1, p.rule, 1.65);
    }
    const glow = ctx.createLinearGradient(start, y, marker, y);
    glow.addColorStop(0, p.dark ? '#144e88' : '#83ac9b');
    glow.addColorStop(.72, p.dark ? '#268ae6' : '#418673');
    glow.addColorStop(1, p.dark ? '#8de3ff' : '#206e63');
    fill(start, y, marker - start + 5, 20, glow, 10);
    ctx.restore();
    for (let i = 0; i <= 5; i++) {
      const x = start + width * i / 5;
      text(String(Number(mix(minimum, maximum, i / 5).toFixed(2))), x, y - 24, 18, {color: p.soft, align: 'center'});
    }
    halo(marker, y + 10, 30, p.dark ? 'rgba(93,201,255,.63)' : 'rgba(58,140,117,.23)');
    dot(marker, y + 10, 10.5, p.dark ? '#ecfcff' : '#f7fff9');
    dot(marker, y + 10, 5, p.dark ? '#2596f4' : p.accent);
    withOpacity(cue(t, 1.42, .44), () => {
      text(options.scoreResult, 480, 399, 29, {align: 'center', weight: 680, color: p.accent, maxWidth: 620});
    });
  }

  function score(t) {
    background();
    const transfer = options.scoreMode === 'bars' ? 0 : options.scoreMode === 'rail' ? 1 : cue(t, 2.92, .38, smooth);
    withOpacity(1 - transfer, () => scoreBars(t));
    withOpacity(transfer, () => scoreRail(options.scoreMode === 'rail' ? t : Math.max(0, t - 3.03)));
    caption(options.scoreMode === 'bars' || (options.scoreMode === 'both' && t < 3.07)
      ? '依次比较，再标出达标线' : '用一条分数尺看清变化');
  }

  function newCanvas(width, height) {
    return canvasFactory(width, height);
  }

  function polygon(points, color) {
    ctx.beginPath();
    points.forEach(([x, y], index) => index === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y));
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
  }

  function exhibit(kind, variant = 0) {
    const texture = newCanvas(480, 270);
    const previous = ctx;
    ctx = texture.getContext('2d');
    if (kind === 0) {
      fill(0, 0, 480, 270, vertical(0, 270, '#f9f3e6', '#e0d4b9'));
      for (let i = 0; i < 13; i++) {
        const angle = i * PI * 2 / 13;
        line(240 + Math.cos(angle) * 4, 86 + Math.sin(angle) * 4,
          240 + Math.cos(angle) * 24, 86 + Math.sin(angle) * 24, '#c97654', 2.8);
      }
      text('Fieldwork', 240, 144, 55, {font: palettes.paper.display, align: 'center', color: '#292821'});
      line(154, 195, 326, 195, '#bbae92', 1.1);
      text('项目档案', 240, 219, 17, { align: 'center', color: '#726b59' });
    } else if (kind === 1) {
      const color = ['#a9241f', '#235d7c', '#bc8d2c'][variant];
      fill(0, 0, 480, 270, vertical(0, 270, '#262629', '#08090d'));
      polygon([[167, 0], [480, 0], [480, 164], [114, 249]], color);
      polygon([[115, 215], [269, 0], [377, 0], [214, 244]], '#0d1016');
      polygon([[220, 64], [301, 12], [405, 73], [387, 178], [329, 225], [248, 192]], '#e6e6df');
      polygon([[220, 64], [263, 51], [278, 119], [390, 145], [329, 225], [248, 192]], '#73909d');
      polygon([[263, 51], [301, 12], [405, 73], [278, 119]], '#f8f7ef');
      polygon([[278, 119], [405, 73], [387, 178], [390, 145]], '#303b46');
      polygon([[0, 177], [225, 158], [218, 221], [0, 235]], '#f7f4e9');
      polygon([[0, 228], [215, 210], [211, 227], [0, 249]], color);
      text('FRAME STUDY', 22, 198, 25, { color: '#131419', weight: 850 });
    } else {
      fill(0, 0, 480, 270, '#272733');
      fill(20, 23, 298, 223, '#e4e0fa', 5);
      const tile = (i, j, height) => [167 + (i - j) * 12, 65 + (i + j) * 6.8 - height];
      for (let i = 0; i < 11; i++) {
        for (let j = 0; j < 11; j++) {
          const raised = i > 2 && i < 8 && j > 2 && j < 8 && (i + j) % 3 === 0;
          const height = raised ? 16 : 0;
          const a = tile(i, j, height);
          const b = tile(i + 1, j, height);
          const c = tile(i + 1, j + 1, height);
          const d = tile(i, j + 1, height);
          polygon([b, c, tile(i + 1, j + 1, 0), tile(i + 1, j, 0)], '#746ca2');
          polygon([c, d, tile(i, j + 1, 0), tile(i + 1, j + 1, 0)], '#a598c2');
          polygon([a, b, c, d], raised ? '#fffcfa' : (i + j) % 2 ? '#b9afdb' : '#c7bfeb');
        }
      }
      text('MG 展示', 338, 61, 28, { color: '#faf7ff', weight: 700 });
      for (let i = 0; i < 6; i++) line(339, 105 + i * 17, 451 - (i % 3) * 12, 105 + i * 17, '#7d7a90', 1.4);
    }
    ctx = previous;
    return texture;
  }

  let exhibits;
  let galleryCanvas;
  let galleryCtx;
  let reflectionCanvas;
  let reflectionCtx;

  function prepareGallery() {
    if (galleryCanvas) return;
    const main = ctx;
    try {
      exhibits = [exhibit(0), exhibit(2), exhibit(1, 0), exhibit(1, 1), exhibit(1, 2)];
      galleryCanvas = newCanvas(W, H);
      galleryCtx = galleryCanvas.getContext('2d');
      reflectionCanvas = newCanvas(W, H);
      reflectionCtx = reflectionCanvas.getContext('2d');
    } finally {
      ctx = main;
    }
  }

  function galleryCard(item, mirrored = false) {
    const {x, y, width, yaw, alpha, texture} = item;
    const source = mediaDimensions(texture);
    const height = width * 9 / 16;
    const crop = coverRect(source.width, source.height, width, height);
    const amount = Math.sin(yaw);
    const face = Math.cos(yaw);
    const focalLength = 486;
    function project(s) {
      const offset = (s - .5) * width;
      const scale = focalLength / (focalLength + offset * amount);
      return { x: offset * face * scale, h: height * scale, base: offset * amount * .038 };
    }
    withOpacity(alpha, () => {
      ctx.translate(x, y);
      if (mirrored) ctx.scale(1, -1);
      const n = 30;
      for (let i = 0; i < n; i++) {
        const left = project(i / n);
        const right = project((i + 1) / n);
        ctx.drawImage(texture, crop.x + i * crop.width / n, crop.y, crop.width / n, crop.height,
          left.x, left.base - left.h, right.x - left.x + .43, left.h);
      }
    });
  }

  function galleryHeading(t, resolve) {
    const show = cue(t, .69, .30) * (1 - cue(t, 3.66, .45));
    const emphasis = cue(t, 1.06, .53, smooth);
    withOpacity(show, () => {
      const y = mix(257, 137, resolve);
      const scale = mix(1, .74, resolve);
      ctx.translate(480, y);
      ctx.scale(scale, scale);
      text(options.galleryHeading, 0, -18, 57, {align: 'center', weight: 830, color: p.dark ? '#fcfcfe' : p.ink, maxWidth: 840});
      withOpacity(emphasis, () => {
        const g = ctx.createLinearGradient(-185, 65, 186, 65);
        g.addColorStop(0, p.dark ? '#2d9eff' : '#338479');
        g.addColorStop(.5, p.dark ? '#7356ff' : '#855a91');
        g.addColorStop(1, p.dark ? '#ff744f' : '#d46046');
        text(options.galleryEmphasis, 0, 72, 78, {align: 'center', weight: 850, color: g, maxWidth: 770});
        if (options.galleryEmphasis) fill(-188, 126, 376 * emphasis, 4, g, 2);
      });
    });
  }

  function gallery(t) {
    prepareGallery();
    const opening = cue(t, 0, .67, smooth);
    const resolve = cue(t, 2.68, .91, smooth);
    const steps = cue(t, 3.66, 1.14, smooth);
    const travel = mix(-20, 22, cue(t, .17, 4.4, smooth));
    const floor = 317;
    background(travel);
    const sources = frameMedia?.gallery ?? options.gallery;
    const labels = sources.length && !hasGalleryLabels ? [] : options.galleryLabels;
    const middle = Math.floor(cue(t, 3.62, 2.12, linear) * 3.95) % 3;
    const items = [
      {texture: sources[0] ?? exhibits[0], x: 221, width: 268, yaw: -.27, stepX: 204, stepY: 387},
      {texture: sources[1] ?? exhibits[2 + middle], x: 480, width: 300, yaw: .035, stepX: 470, stepY: 315},
      {texture: sources[2] ?? exhibits[1], x: 739, width: 252, yaw: .26, stepX: 737, stepY: 249}
    ].map((item, i) => {
      const reveal = cue(t, i * .08, .56);
      return {
        ...item,
        alpha: mix(.58, 1, reveal),
        x: mix(item.x, item.stepX, steps) + travel * (i === 1 ? 1.05 : .59) * (1 - .55 * steps),
        y: mix(floor + (i - 1) * -7 + (1 - reveal) * 16, 390, resolve) + (item.stepY - 390) * steps,
        width: mix(item.width * (.92 + opening * .08), 222, resolve),
        yaw: item.yaw * options.tilt * (1 - .93 * resolve) + travel * .0012
      };
    });
    const main = ctx;
    ctx = reflectionCtx;
    ctx.clearRect(0, 0, W, H);
    items.forEach(item => galleryCard(item, true));
    ctx.save();
    ctx.globalCompositeOperation = 'destination-in';
    fill(0, 0, W, H, vertical(floor, 107, 'rgba(0,0,0,.92)', 'rgba(0,0,0,0)'));
    ctx.restore();
    ctx = galleryCtx;
    ctx.clearRect(0, 0, W, H);
    items.forEach(item => galleryCard(item));
    ctx = main;
    withOpacity((options.reflectionOpacity ?? (p.dark ? .36 : .25)) * (1 - resolve), () => {
      ctx.filter = 'blur(' + mix(6.2, 2.1, resolve).toFixed(2) + 'px)';
      ctx.drawImage(reflectionCanvas, 0, 0);
    });
    withOpacity(mix(.66, 1, resolve), () => {
      const blur = mix(options.blur, 0, resolve);
      if (blur > .08) ctx.filter = 'blur(' + blur.toFixed(2) + 'px)';
      ctx.drawImage(galleryCanvas, 0, 0);
    });
    if (p.dark) {
      withOpacity((1 - resolve) * .83, () => {
        fill(0, 377, W, 163, vertical(377, 163, 'rgba(8,10,13,0)', '#080a0d'));
      });
    }
    galleryHeading(t, resolve);

    withOpacity(cue(t, 3.68, .58), () => {
      text(options.galleryTitle, 55, 70, 28, {weight: 740, maxWidth: 825});
      line(106, 449, 868, 449, p.faint, 1);
      line(868, 449, 860, 445, p.faint);
      line(868, 449, 860, 453, p.faint);
      items.forEach((item, i) => {
        text(labels[i] ?? '', item.x, item.y + 22, 19, {align: 'center', weight: 690, maxWidth: 214});
        line(item.x, item.y + 38, item.x, 448, p.rule, 1);
        dot(item.x, 449, 3.9, p.line);
      });
    });
    caption(t < 3.68 ? '先看全貌，再把注意力转向样片' : '三张样片在同一空间里逐个展开');
  }

  const painters = {
    'chapter-flip': chapter,
    'page-to-card': portal,
    'branch-cards': branches,
    'grid-roll-stamp': status,
    'data-score': score,
    'gallery-2-5d': gallery
  };
  const paint = painters[effect];

  function draw(target, time, {
    x = 0, y = 0, width = target?.canvas?.width, height = target?.canvas?.height,
    fit = 'contain', media
  } = {}) {
    if (!target || typeof target.save !== 'function') throw new TypeError('Pass a CanvasRenderingContext2D');
    if (![time, x, y, width, height].every(Number.isFinite) || width <= 0 || height <= 0) {
      throw new RangeError('Use finite time and a positive drawing rectangle');
    }
    if (!['contain', 'cover'].includes(fit)) throw new RangeError('fit must be contain or cover');
    if (media?.gallery !== undefined) gallerySources(media.gallery);
    const scale = (fit === 'cover' ? Math.max : Math.min)(width / W, height / H);
    target.save();
    ctx = target;
    frameMedia = media;
    try {
      target.beginPath();
      target.rect(x, y, width, height);
      target.clip();
      target.translate(x + (width - W * scale) / 2, y + (height - H * scale) / 2);
      target.scale(scale, scale);
      paint(clamp(time / seconds) * nominalDuration);
    } finally {
      ctx = undefined;
      frameMedia = undefined;
      target.restore();
    }
  }

  return Object.freeze({id: effect, preset: presetId, duration: seconds, width: W, height: H, draw});
}
