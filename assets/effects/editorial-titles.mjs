import {createElement as h} from 'react';
import {AbsoluteFill, Easing} from 'remotion';
import {blendCard, cardPose, mix, progress, ShowcaseCard, useShowcaseFrame} from './showcase-shared.mjs';

const frontFont = '"Noto Sans SC", "PingFang SC", sans-serif';
const exitEase = Easing.bezier(0.55, 0, 0.74, 0.4);

export function SemanticHeadline({
  beats, color = '#fff8ec', accent = '#f5c68b', fontFamily = frontFont, fontScale = 0.06, vertical = 0.5,
}) {
  const {time, width, height} = useShowcaseFrame();
  const beat = beats.find(({start, end}) => time >= start && time < end);
  if (!beat) return null;
  const {start, end, enter = 0.38, exit = 0.22, pieces} = beat;
  if (enter <= 0 || exit <= 0 || end - start < enter + exit + 0.5) {
    throw new Error('Leave at least 0.5 seconds for the settled headline between entry and exit.');
  }
  const opening = progress(time, start, start + enter);
  const leaving = progress(time, end - exit, end, exitEase);
  const size = width * fontScale;
  return h(AbsoluteFill, {style: {alignItems: 'center', pointerEvents: 'none', justifyContent: 'center'}},
    h('div', {style: {
      maxWidth: '90%', padding: `${size * 0.08}px ${size * 0.28}px`, overflow: 'hidden',
      color, fontFamily, fontWeight: 900, fontSize: size, lineHeight: 1.13, textAlign: 'center',
      transform: `translateY(${height * (vertical - 0.5)}px)`,
    }},
    h('div', {style: {
      transform: `translateY(${size * (0.83 * (1 - opening) - 0.59 * leaving)}px) scale(${mix(0.985, 1, opening)})`,
      opacity: opening * (1 - leaving), textShadow: `0 ${size * 0.07}px ${size * 0.32}px #150f09b3`,
    }}, pieces.map(({text, emphasis}, i) => h('span', {key: i, style: {color: emphasis ? accent : undefined}}, text)))),
  );
}

/** A readable number and title on a card, optionally rising out of a montage. */
export function NumberedChapter({
  number, title, liftAt, landAt, slot = [0.56, 0.72, 0.36, 4, -5, -3],
  background = 'linear-gradient(125deg,#26221e,#141310 68%)',
  color = '#fff8ec', accent = '#f5c68b', fontFamily = frontFont, numeralFont = fontFamily,
}) {
  const {time, width, height} = useShowcaseFrame();
  if ((liftAt !== undefined || landAt !== undefined) && !(0 <= liftAt && liftAt < landAt)) {
    throw new Error('Use increasing liftAt and landAt times for a rising chapter card.');
  }
  const amount = liftAt === undefined ? 1 : progress(time, liftAt, landAt);
  const [x, y, size, roll, yaw, tilt] = slot;
  const card = blendCard(cardPose(x * width, y * height, size * width, roll, yaw, tilt, width * 0.009),
    cardPose(width / 2, height / 2, width), amount);
  return h(ShowcaseCard, {pose: card, aspect: width / height, outline: 0.45 * (1 - amount), shadow: 1 - amount},
    h(AbsoluteFill, {style: {
      background, color, fontFamily, flexDirection: 'row', justifyContent: 'center',
      alignItems: 'center', gap: card.width * 0.028, padding: '0 9%', boxSizing: 'border-box',
    }},
    h('span', {style: {
      color: accent, fontFamily: numeralFont, fontSize: card.width * 0.142,
      fontWeight: 700, lineHeight: 0.94, fontVariantNumeric: 'lining-nums tabular-nums',
    }}, number),
    h('span', {style: {
      minWidth: 0, fontSize: card.width * 0.052, fontWeight: 900, lineHeight: 1.12,
      borderLeft: `1px solid ${accent}`, paddingLeft: card.width * 0.028,
    }}, title)),
  );
}
