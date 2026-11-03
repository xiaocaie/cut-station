#!/usr/bin/env python3
"""Read-only validation of declared visual exposure/settled intervals, not actual visibility."""
import argparse
import json
import math
from pathlib import Path
import sys


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def frame_number(value):
    return finite_number(value) and value >= 0 and int(value) == value


def inspect(data, minimum_seconds=0.5):
    errors, warnings = [], []
    fps, total = data.get('fps'), data.get('total_frames', data.get('frames'))
    visuals = data.get('visuals')
    if not finite_number(fps) or fps <= 0:
        errors.append('fps必须为正有限数')
    if not frame_number(total) or total == 0:
        errors.append('total_frames必须为正整数')
    if not isinstance(visuals, list) or not visuals:
        errors.append('visuals必须为非空列表，每项声明可见和稳定可读区间')
    if not finite_number(minimum_seconds) or minimum_seconds <= 0:
        errors.append('minimum_seconds必须为正有限数')
    if errors:
        return {'structural_valid': False, 'errors': errors, 'warnings': warnings}
    minimum_frames = math.ceil(minimum_seconds * fps - 1e-9)
    effective_count, hold_count = 0, 0
    visible_lengths, settled_lengths, ids = [], [], set()
    for position, item in enumerate(visuals, 1):
        if not isinstance(item, dict):
            errors.append(f'visuals第{position}项不是对象')
            continue
        label = str(item.get('id', position))
        if label in ids:
            errors.append(f'{label}: ID重复')
        ids.add(label)
        start, end = item.get('start_frame'), item.get('end_frame')
        if not frame_number(start) or not frame_number(end) or end <= start or end > total:
            errors.append(f'{label}: 可见区间须为0<=start<end<=total的整数帧，end不含')
            continue
        if item.get('effective', True) is False:
            continue
        effective_count += 1
        visible_lengths.append(end - start)
        if end - start < minimum_frames:
            errors.append(f'{label}: 有效可见{end-start}帧，小于{minimum_frames}帧')
        if item.get('requires_hold', True) is False:
            continue
        settled_start, settled_end = item.get('settled_start_frame'), item.get('settled_end_frame')
        if settled_start is None or settled_end is None:
            warnings.append(f'{label}: 缺少稳定可读区间，不能证明落定阅读时长')
            continue
        if not frame_number(settled_start) or not frame_number(settled_end) or not start <= settled_start < settled_end <= end:
            errors.append(f'{label}: 稳定可读区间必须包含在有效可见区间内')
            continue
        hold_count += 1
        settled_lengths.append(settled_end - settled_start)
        if settled_end - settled_start < minimum_frames:
            errors.append(f'{label}: 稳定可读{settled_end-settled_start}帧，小于{minimum_frames}帧')
    return {
        'structural_valid': not errors,
        'fps': fps, 'total_frames': total,
        'minimum_seconds': minimum_seconds, 'minimum_frames': minimum_frames,
        'effective_visuals': effective_count, 'declared_hold_intervals': hold_count,
        'shortest_declared_visible_frames': min(visible_lengths, default=None),
        'shortest_declared_settled_frames': min(settled_lengths, default=None),
        'errors': errors, 'warnings': warnings,
        'basis': 'Declared frame intervals only; overlays may overlap intentionally',
        'not_checked': ['实际透明度/裁切/遮挡/页面进出视口', '实际字形/清晰度/对比/美观', '画面与旁白语义对应', '配音/音效/解码与连续播放'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--min-seconds', type=float, default=0.5)
    args = parser.parse_args()
    try:
        data = json.loads(args.manifest.read_text(encoding='utf-8-sig'))
        if not isinstance(data, dict):
            raise ValueError('根节点须为对象')
        report = inspect(data, args.min_seconds)
    except (OSError, UnicodeError, ValueError) as exc:
        report = {'structural_valid': False, 'errors': [str(exc)]}
    report['file'] = str(args.manifest.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['structural_valid'] else 1


if __name__ == '__main__':
    sys.exit(main())
