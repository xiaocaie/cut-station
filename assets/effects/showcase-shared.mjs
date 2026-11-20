import {createElement as h} from 'react';
import {AbsoluteFill, Easing, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

export const showcaseEase = Easing.bezier(0.25, 0.72, 0.24, 1);
export const mix = (a, b, progress) => a + (b - a) * progress;

export function progress(time, start, end, easing = showcaseEase) {
  return interpolate(time, [start, end], [0, 1], {
    easing, extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
}

export function useShowcaseFrame() {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  return {time: frame / fps, width, height};
}

export function cardPose(x, y, width, roll = 0, yaw = 0, tilt = 0, radius = 0) {
  return {x, y, width, roll, yaw, tilt, radius};
}

export function blendCard(from, to, amount) {
  return cardPose(
    mix(from.x, to.x, amount), mix(from.y, to.y, amount),
    mix(from.width, to.width, amount), mix(from.roll, to.roll, amount),
    mix(from.yaw, to.yaw, amount), mix(from.tilt, to.tilt, amount),
    mix(from.radius, to.radius, amount),
  );
}

export function Screenshot({source}) {
  const {src, crop, fit = 'cover'} = typeof source === 'string' ? {src: source} : source;
  return h(Img, {
    src,
    style: {
      display: 'block', width: '100%', height: '100%', objectFit: fit,
      objectPosition: crop?.position, transform: crop?.scale ? `scale(${crop.scale})` : undefined,
      transformOrigin: crop?.origin,
    },
  });
}

export function ShowcaseCard({
  pose, aspect, children, source, dim = 0, shadow = 1, outline = 0, surface = '#f5efe4',
}) {
  const scale = pose.width / 600;
  return h('div', {style: {
    position: 'absolute', width: pose.width, aspectRatio: aspect,
    left: pose.x, top: pose.y, overflow: 'hidden', borderRadius: pose.radius,
    transform: `translate(-50%, -50%) perspective(${3.7 * pose.width}px) rotateZ(${pose.roll}deg) rotateY(${pose.yaw}deg) rotateX(${pose.tilt}deg)`,
    background: surface,
    boxShadow: shadow > 0 ? `0 ${15 * scale}px ${42 * scale}px rgba(26,21,16,${0.24 * shadow})` : undefined,
    outline: outline > 0 ? `1px solid rgba(255,255,255,${0.52 * outline})` : undefined,
    outlineOffset: -1,
  }},
  source && h(Screenshot, {source}),
  children,
  dim > 0 && h(AbsoluteFill, {style: {background: `rgba(17,14,11,${dim})`, pointerEvents: 'none'}}));
}
