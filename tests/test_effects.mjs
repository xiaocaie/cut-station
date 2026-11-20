import assert from 'node:assert/strict';
import test from 'node:test';
import {getGreenDashedHighlight} from '../assets/effects/green-dashed-highlight.mjs';
import {getMarkerUnderline} from '../assets/effects/marker-underline.mjs';
import {createPromptTyping} from '../assets/effects/prompt-typing.mjs';
import {createMgMotion, MG_EFFECTS, MG_PRESETS, resolveMgEffect, resolveMgPreset} from '../assets/effects/mg-motion.mjs';

const box = {x: 100, y: 200, width: 400, height: 80};

test('highlight expands, holds, exits and keeps border/fill opacity independent', () => {
  const at = (time) => getGreenDashedHighlight({
    time, start: 1, end: 4, box,
    style: {stroke: '#6750A4', fill: '#B9A3E3', strokeOpacity: 0.7, fillOpacity: 0.15},
  });
  assert.equal(at(0), null);
  assert.equal(at(1).opacity, 0);
  assert.ok(at(1.1).width > 0 && at(1.1).width < box.width);
  assert.equal(at(2).width, box.width);
  assert.equal(at(2).height, box.height);
  assert.equal(at(2).stroke, '#6750A4');
  assert.equal(at(2).fill, '#B9A3E3');
  assert.equal(at(2).strokeOpacity, 0.7);
  assert.equal(at(2).fillOpacity, 0.15);
  assert.ok(at(3.95).opacity < 1);
  assert.equal(at(4), null);
  assert.deepEqual(at(60 / 30), at(120 / 60));
});

test('highlight supports optional marching dashes and validates alpha', () => {
  const config = {start: 0, end: 4, box, scale: 2};
  const still = getGreenDashedHighlight({...config, time: 1});
  assert.equal(still.strokeWidth, 4);
  assert.equal(still.strokeDasharray, '16 12');
  assert.equal(still.strokeDashoffset, getGreenDashedHighlight({...config, time: 2}).strokeDashoffset);
  const moving = (time) => getGreenDashedHighlight({...config, time, style: {dashSpeed: 16}});
  assert.notEqual(moving(1).strokeDashoffset, moving(1.1).strokeDashoffset);
  assert.throws(() => getGreenDashedHighlight({...config, time: 1, style: {fillOpacity: 1.1}}), RangeError);
  assert.throws(() => getGreenDashedHighlight({...config, time: 1, style: {strokeOpacity: -0.1}}), RangeError);
});

test('marker supports a left-to-right draw and whole-band fade with frame-independent seeking', () => {
  const config = {start: 1, end: 4, box, color: '#63D69B', fillOpacity: 0.85};
  const at = (time) => getMarkerUnderline({...config, time});
  assert.equal(at(0), null);
  assert.equal(at(1).width, 0);
  assert.ok(at(1.1).width > 0 && at(1.1).width < box.width);
  assert.equal(at(2).width, box.width);
  assert.equal(at(2).fillOpacity, 0.85);
  assert.equal(at(4), null);
  const settled = at(2);
  at(1.1);
  assert.deepEqual(at(2), settled);
  const fade = getMarkerUnderline({...config, time: 1, mode: 'fade'});
  assert.equal(fade.width, box.width);
  assert.equal(fade.opacity, 0);
  assert.equal(getMarkerUnderline({...config, time: 1.01, end: 1.02}).width, box.width);
});

test('prompt typing preserves graphemes, line breaks, spaces and exact final text', () => {
  const text = '中👨‍👩‍👧‍👦e\u0301\nA';
  const at = createPromptTyping({text, typingSeconds: 5, holdSeconds: 2});
  assert.equal(at(-1), null);
  assert.equal(at(0).text, '');
  assert.equal(at(1).text, '中');
  assert.equal(at(2).text, '中👨‍👩‍👧‍👦');
  assert.equal(at(3).text, '中👨‍👩‍👧‍👦e\u0301');
  assert.equal(at(4).text, '中👨‍👩‍👧‍👦e\u0301\n');
  assert.equal(at(5).text, text);
  assert.equal(at(5).sendEnabled, true);
  assert.equal(at(7), null);
  assert.deepEqual(at(60 / 30), at(120 / 60));
  const earlier = at(1);
  at(5);
  assert.deepEqual(at(1), earlier);
  const literal = '  请保留大小写\r\nhttps://example.test/A?q=1\\2  ';
  assert.equal(createPromptTyping({text: literal, typingSeconds: 0, holdSeconds: 1})(0).text, literal);
});

test('prompt cursor blinks after typing and handles empty/paste modes', () => {
  const at = createPromptTyping({text: '完成', typingSeconds: 1, holdSeconds: 2, cursorBlinkSeconds: 1});
  assert.equal(at(0.8).cursorVisible, true);
  assert.equal(at(1).cursorVisible, true);
  assert.equal(at(1.5).cursorVisible, false);
  assert.equal(createPromptTyping({text: '', holdSeconds: 1})(0).sendEnabled, false);
  assert.equal(createPromptTyping({text: '粘贴全文', typingSeconds: 0, holdSeconds: 1})(0).text, '粘贴全文');
  assert.throws(() => createPromptTyping({text: 'x', typingSeconds: -1}), RangeError);
});

test('MG effects resolve by name or by the requested motion', () => {
  const examples = [
    ['chapter-flip', '使编号卡转窄时切网页'],
    ['page-to-card', '完整官网的页面缩到左边'],
    ['branch-cards', '把中心卡分出四张模块卡并连线'],
    ['grid-roll-stamp', '让格子逐个填亮，给第三项盖章'],
    ['data-score', '柱子从零长出后显示达标线'],
    ['gallery-2-5d', '三张样片先虚焦再清晰并错层排开'],
  ];
  for (const [id, description] of examples) {
    assert.equal(resolveMgEffect(MG_EFFECTS[id].name), id);
    assert.equal(resolveMgEffect(description), id);
  }
  assert.equal(resolveMgEffect('保留原录屏供观众读菜单'), null);
  assert.equal(resolveMgEffect('章节卡侧翻和数据生长与分数尺'), null);
});

test('MG presets resolve independently and painters accept a supplied canvas factory', () => {
  assert.equal(resolveMgPreset('暖白纸卡'), 'paper');
  assert.equal(resolveMgPreset('暗场展台'), 'stage');
  assert.equal(resolveMgEffect('暖白纸卡'), null);
  assert.notEqual(MG_PRESETS.paper.bg, MG_PRESETS.stage.bg);

  const newCanvas = () => ({getContext: () => ({fillRect() {}, beginPath() {}, arc() {}, fill() {}})});
  for (const id of Object.keys(MG_EFFECTS)) {
    const motion = createMgMotion({id, preset: '暗场展台', canvasFactory: newCanvas});
    assert.equal(motion.preset, 'stage');
    assert.equal(motion.duration, MG_EFFECTS[id].duration);
    assert.equal(typeof motion.draw, 'function');
  }
  assert.equal(createMgMotion({id:'branch-cards', duration:8, canvasFactory:newCanvas}).duration, 8);
  assert.throws(() => createMgMotion({id:'branch-cards', duration:0, canvasFactory:newCanvas}), RangeError);
  assert.throws(() => createMgMotion({id:'chapter-flip', content:{cards:['章'], selectedCard:1}, canvasFactory:newCanvas}), RangeError);
});
