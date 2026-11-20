import {createElement, useEffect, useLayoutEffect, useMemo, useRef, useState} from 'react';
import {cancelRender, continueRender, delayRender, useCurrentFrame, useVideoConfig} from 'remotion';
import {createMgMotion} from './mg-motion.mjs';

const empty = Object.freeze({});

async function loadImage(url) {
  const image = new Image();
  image.src = url;
  await image.decode();
  return image;
}

function validateSources(sources) {
  const page = sources?.page;
  const gallery = sources?.gallery;
  if (page !== undefined && (typeof page !== 'string' || !page)) {
    throw new TypeError('sources.page must be an image URL');
  }
  if (gallery !== undefined && (!Array.isArray(gallery) || gallery.length !== 3 ||
      gallery.some(url => typeof url !== 'string' || !url))) {
    throw new TypeError('sources.gallery must contain three image URLs');
  }
  return [page ?? null, gallery ?? []];
}

function MgLayer({sourceKey, id, preset, duration, content = empty, style = empty, fit = 'contain'}) {
  const canvas = useRef(null);
  const {width, height, fps} = useVideoConfig();
  const time = useCurrentFrame() / fps;
  const motion = useMemo(
    () => createMgMotion({id, preset, duration, content, style}),
    [id, preset, duration, content, style],
  );

  const [handle] = useState(() =>
    sourceKey === '[null,[]]' ? null : delayRender('CutStation MG image sources'));
  const pending = useRef(handle);
  const [media, setMedia] = useState(handle === null ? empty : null);

  function release() {
    if (pending.current === null) return;
    continueRender(pending.current);
    pending.current = null;
  }

  useEffect(() => {
    if (handle === null) return;
    const [page, gallery] = JSON.parse(sourceKey);
    let active = true;
    Promise.all([page ? loadImage(page) : null, Promise.all(gallery.map(loadImage))])
      .then(([pageImage, galleryImages]) => {
        if (active) setMedia({
          ...(pageImage ? {page: pageImage} : {}),
          ...(galleryImages.length ? {gallery: galleryImages} : {}),
        });
      })
      .catch(error => { if (active) cancelRender(error); });
    return () => {
      active = false;
      // React re-runs effects in development Strict Mode. Give a new effect
      // a chance to claim the same handle before releasing an unmounted layer.
      queueMicrotask(() => {
        if (canvas.current === null) release();
      });
    };
  }, [handle, sourceKey]);

  useLayoutEffect(() => {
    if (!media) return;
    const target = canvas.current.getContext('2d');
    try {
      target.clearRect(0, 0, width, height);
      motion.draw(target, time, {width, height, fit, media: media === empty ? undefined : media});
      release();
    } catch (error) {
      cancelRender(error);
    }
  }, [media, motion, time, width, height, fit]);

  return createElement('canvas', {
    ref: canvas,
    width,
    height,
    'aria-hidden': true,
    style: {position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none'},
  });
}

/** Place inside a Remotion Sequence. Pass staticFile(...) URLs for optional stills. */
export function CutStationMgMotion({sources, ...props}) {
  const sourceKey = JSON.stringify(validateSources(sources));
  return createElement(MgLayer, {...props, key: sourceKey, sourceKey});
}
