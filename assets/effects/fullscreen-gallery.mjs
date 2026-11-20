import {createElement as h} from 'react';
import {AbsoluteFill, Easing} from 'remotion';
import {blendCard, cardPose, progress, Screenshot, ShowcaseCard, useShowcaseFrame} from './showcase-shared.mjs';

const zoomEase = Easing.bezier(0.54, 0.04, 0.23, 1);
const slideEase = Easing.bezier(0.45, 0, 0.25, 1);

export function gallerySeconds(pageCount, {
  zoomAt = 2.37, zoomDuration = 1.23, hold = 0.92, interval = 1.34, slideDuration = 0.38, finalHold = 1.44,
} = {}) {
  if (!Number.isInteger(pageCount) || pageCount < 2 ||
      ![zoomAt, zoomDuration, hold, interval, slideDuration, finalHold].every(Number.isFinite) ||
      zoomAt < 0.65 || zoomDuration <= 0 || slideDuration <= 0 ||
      hold < 0.5 || interval < slideDuration + 0.5 || finalHold < 0.5) {
    throw new Error('Gallery needs multiple pages and a full-screen reading hold before each turn.');
  }
  return zoomAt + zoomDuration + hold + (pageCount - 2) * interval + slideDuration + finalHold;
}

function Track({sources, time, width, height, y, size, speed, offset, tileAspect, dim}) {
  const cardWidth = width * size;
  const step = cardWidth + width * 0.0115;
  const travel = width * (offset + time * speed);
  // Recycle card slots entirely outside the canvas. Both tracks travel left to right.
  const first = Math.floor((-travel - cardWidth) / step);
  const count = Math.ceil((width + cardWidth * 2) / step) + 1;
  return Array.from({length: count}, (_, i) => {
    const slot = first + i;
    const source = sources[((slot % sources.length) + sources.length) % sources.length];
    return h(ShowcaseCard, {
      key: slot, source, aspect: tileAspect, dim, shadow: 0.65,
      pose: cardPose(slot * step + travel, height * y, cardWidth, 0, 0, 0, cardWidth * 0.023),
    });
  });
}

/** pages supply the hero and subsequent full-bleed pages in the editorial order. */
export function FullscreenPageGallery({
  pages, tracks, zoomAt = 2.37, zoomDuration = 1.23, hold = 0.92, interval = 1.34,
  slideDuration = 0.38, finalHold = 1.44, tileAspect = 16 / 9,
  background = 'radial-gradient(ellipse at 50% 30%,#fffefa,#eee4d7)',
}) {
  const {time, width, height} = useShowcaseFrame();
  gallerySeconds(pages.length, {zoomAt, zoomDuration, hold, interval, slideDuration, finalHold});
  if (!Array.isArray(tracks) || tracks.length !== 2 || tracks.some((row) => row.length === 0)) {
    throw new Error('FullscreenPageGallery needs two nonempty background tracks.');
  }
  const zoom = progress(time, zoomAt, zoomAt + zoomDuration, zoomEase);
  const centerIn = progress(time, 0, 0.65);
  const center = blendCard(
    blendCard(cardPose(width * 0.5, height * 0.51, width * 0.45, 0, 3, 0, width * 0.01),
      cardPose(width * 0.5, height * 0.49, width * 0.54, 0, 0, 0, width * 0.01), centerIn),
    cardPose(width * 0.5, height * 0.5, width), zoom,
  );

  const firstTurn = zoomAt + zoomDuration + hold;
  let pagePosition = 0;
  if (time >= firstTurn) {
    const turns = Math.min(Math.floor((time - firstTurn) / interval), pages.length - 2);
    const at = firstTurn + turns * interval;
    pagePosition = turns + progress(time, at, at + slideDuration, slideEase);
  }
  // Reversed source order moves right as progress increases. Full-sized frames
  // share an edge throughout the turn and are clipped to the viewport.
  const strip = h(AbsoluteFill, {style: {flexDirection: 'row-reverse', transform: `translateX(${pagePosition * 100}%)`}},
    pages.map((page, i) => h('div', {key: i, style: {flex: '0 0 100%', height: '100%', overflow: 'hidden'}},
      h(Screenshot, {source: page}))),
  );

  return h(AbsoluteFill, {style: {overflow: 'hidden', background}},
    zoom < 1 && h(AbsoluteFill, {style: {opacity: 0.92 - 0.38 * zoom}},
      h(Track, {sources: tracks[0], time, width, height, tileAspect, y: 0.286, size: 0.289, speed: 0.121, offset: 0.102, dim: 0.10}),
      h(Track, {sources: tracks[1], time, width, height, tileAspect, y: 0.697, size: 0.336, speed: 0.178, offset: 0.216, dim: 0.07})),
    h(ShowcaseCard, {pose: center, aspect: width / height, outline: 1 - zoom, shadow: 1 - zoom}, strip),
  );
}
