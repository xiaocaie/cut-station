import {createElement as h} from 'react';
import {AbsoluteFill, Easing} from 'remotion';
import {blendCard, cardPose, progress, ShowcaseCard, useShowcaseFrame} from './showcase-shared.mjs';

const sweepEase = Easing.bezier(0.62, 0.035, 0.29, 1);
const wrap = (value, width) => ((value % width) + width) % width;

// Normalized x/y/width followed by restrained rotation on each axis.
const paperLayout = [
  [0.34, 0.02, 0.34, -10, 7, 7],
  [0.11, 0.24, 0.36, -10, 8, 5],
  [0.79, 0.08, 0.38, 12, -6, 7],
  [0.10, 0.77, 0.42, -8, 13, 4],
  [0.97, 0.46, 0.51, 12, -11, 3],
  [0.37, 0.33, 0.48, -2, 2, 0],
  [0.94, 0.96, 0.40, 12, -10, 0],
];

/** Use a level wall alone, or let a real wall tile occlude a change to a layered scene. */
export function ScreenshotWallSweep({
  sources, tileAspect = 16 / 9, leadSlot, darkBackground = '#141311',
  brightBackground = 'radial-gradient(ellipse at 48% 35%, #fffdf8 18%, #e9e0d3 115%)',
  drift = -0.046, sweep, brightSources = sources, brightLayout = paperLayout, brightFront, children,
}) {
  const {time, width, height} = useShowcaseFrame();
  if (!sources.length || !brightSources.length) throw new Error('ScreenshotWallSweep needs real screenshot sources.');
  if (sweep && !(0 <= sweep.lift && sweep.lift < sweep.cover && sweep.cover < sweep.exit)) {
    throw new Error('Use increasing lift, cover and exit times for the sweep.');
  }
  const columns = width >= height ? 5 : 3;
  const tileWidth = width * (1.32 / columns);
  const rowStep = tileWidth / tileAspect + width * 0.014;
  const rows = Math.ceil(height / rowStep);
  const columnStep = tileWidth + width * 0.012;
  const margin = columnStep / 2;
  const slot = leadSlot ?? Math.floor(rows / 2) * columns + Math.floor(columns / 2) + 1;
  if (slot < 0 || slot >= columns * rows || !Number.isInteger(slot)) throw new Error('Invalid leadSlot.');
  const wallPose = (i, at) => cardPose(
    wrap(width * 0.56 + (i % columns - (columns - 1) / 2) * columnStep + at * width * drift + margin,
      columns * columnStep) - margin,
    height * 0.5 + (Math.floor(i / columns) - (rows - 1) / 2) * rowStep,
    tileWidth, 0, 0, 0, tileWidth * 0.026,
  );
  const bright = sweep && time >= sweep.cover;
  const lifted = sweep && time >= sweep.lift;
  let sweepCard;
  if (lifted && time < sweep.exit) {
    const start = wallPose(slot, sweep.lift);
    const pullAt = sweep.lift + (sweep.cover - sweep.lift) * 0.32;
    const pull = cardPose(start.x + width * 0.049, start.y + height * 0.044, width * 0.41, -15, 6, 5, width * 0.01);
    const coverWidth = Math.max(width, height * tileAspect) * 1.43;
    const cover = cardPose(width * 0.52, height * 0.51, coverWidth, -2, 0, 0, width * 0.012);
    const exit = cardPose(-coverWidth * 0.61, height * 0.66, coverWidth * 0.81, 9, -6, -5, width * 0.013);
    if (time < pullAt) {
      sweepCard = blendCard(start, pull, progress(time, sweep.lift, pullAt));
    } else if (!bright) {
      sweepCard = blendCard(pull, cover, progress(time, pullAt, sweep.cover, sweepEase));
    } else {
      const occludedUntil = sweep.cover + Math.min(0.08, (sweep.exit - sweep.cover) * 0.2);
      sweepCard = blendCard(cover, exit, progress(time, occludedUntil, sweep.exit, sweepEase));
    }
  }
  const wallDim = 0.28;
  const settle = bright ? progress(time, sweep.cover, sweep.cover + 2.4) : 0;
  return h(AbsoluteFill, {style: {overflow: 'hidden', background: bright ? brightBackground : darkBackground}},
    bright
      ? brightLayout.map(([x, y, size, roll, yaw, tilt], i) => h(ShowcaseCard, {
          key: i, aspect: tileAspect, source: brightSources[i % brightSources.length],
          pose: cardPose((x + (x - 0.5) * settle * 0.13) * width,
            (y + (y - 0.5) * settle * 0.09) * height, size * width * (0.94 + 0.06 * settle),
            roll, yaw, tilt, size * width * 0.023),
        }))
      : Array.from({length: columns * rows}, (_, i) => i === slot && lifted ? null : h(ShowcaseCard, {
          key: i, pose: wallPose(i, time), aspect: tileAspect, source: sources[i % sources.length],
          dim: wallDim, outline: 0.36, shadow: 0.7,
        })),
    !bright && h(AbsoluteFill, {style: {background: 'radial-gradient(ellipse, #100d09ba, #14100c40 70%, #0c0b0a85)'}}),
    bright ? brightFront : children,
    sweepCard && h(ShowcaseCard, {
      pose: sweepCard, aspect: tileAspect, source: sources[slot % sources.length],
      dim: wallDim * (1 - progress(time, sweep.lift, sweep.cover)), outline: 0.36,
    }));
}
