#!/usr/bin/env python3
"""Inspect actual media, optionally verify decoded display timestamps and fully decode."""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys


def positive_float(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError('value must be positive and finite')
    return number


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError('value must be positive')
    return number


def positive_rate(value):
    try:
        return positive_float(float(Fraction(value)))
    except (ValueError, ZeroDivisionError):
        raise argparse.ArgumentTypeError('fps must be positive, for example 60 or 60000/1001')


def rate(value):
    try:
        result = float(Fraction(value))
        return result if math.isfinite(result) and result > 0 else None
    except (ValueError, TypeError, ZeroDivisionError):
        return None


def inspect_cadence(frames, time_base, expected_fps, expected_count):
    """Use decoded display order, not reordered H.264 packet PTS/DTS."""
    errors = []
    tb = Fraction(time_base)
    if tb <= 0:
        raise ValueError('Video time_base must be positive')
    step = 1 / (Fraction(str(expected_fps)) * tb)
    ticks = []
    for index, frame in enumerate(frames):
        value = frame.get('best_effort_timestamp')
        if value is None:
            value = frame.get('pts')
        try:
            ticks.append(int(value))
        except (ValueError, TypeError):
            errors.append(f'Decoded frame {index} has no valid display timestamp')
    if len(frames) != expected_count:
        errors.append(f'Actual decoded frame count {len(frames)} != expected {expected_count}')
    if not ticks:
        errors.append('No decoded display timestamps found')
    non_monotonic, irregular = [], []
    if len(ticks) == len(frames) and ticks:
        if abs(ticks[0]) > 1:
            errors.append('Delivered video does not start at display timestamp zero')
        for index, (previous, current) in enumerate(zip(ticks, ticks[1:]), 1):
            if current <= previous:
                non_monotonic.append(index)
            # One tick accommodates non-integer frame periods such as 30000/1001.
            if abs((current - previous) - step) > 1:
                irregular.append(index)
        drift = [i for i, tick in enumerate(ticks)
                 if abs((tick-ticks[0])-i*step) > 1]
        if non_monotonic:
            errors.append('Non-monotonic/duplicate display PTS at frames: ' + str(non_monotonic[:20]))
        if irregular or drift:
            errors.append('Irregular display cadence/gap/drift at frames: ' + str(sorted(set(irregular+drift))[:20]))
    return {'status': 'failed' if errors else 'passed',
            'decoded_frames': len(frames), 'time_base': str(tb),
            'expected_step_ticks': str(step), 'tolerance_ticks': 1,
            'non_monotonic_steps': len(non_monotonic), 'irregular_steps': len(irregular),
            'errors': errors,
            'not_proven': 'No missing display timestamps does not prove no visual freeze, slow source or playback stutter'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    parser.add_argument('--width', type=positive_int, required=True)
    parser.add_argument('--height', type=positive_int, required=True)
    parser.add_argument('--fps', type=positive_rate, required=True)
    parser.add_argument('--duration-seconds', type=positive_float, required=True)
    parser.add_argument('--frames', type=positive_int)
    parser.add_argument('--container', choices=['mov', 'mp4'],
                        help='Check suffix and actual ISO media major_brand, not filename alone')
    parser.add_argument('--no-audio', action='store_true', help='Permit a silent deliverable')
    parser.add_argument('--decode', action='store_true', help='Fully decode video and audio')
    parser.add_argument('--check-cadence', action='store_true',
                        help='Decode all video frame timestamps and verify CFR/count; required for formal export QA')
    parser.add_argument('--ffprobe', default='ffprobe')
    parser.add_argument('--ffmpeg', default='ffmpeg')
    args = parser.parse_args()
    report = {'file': str(args.file.resolve()), 'errors': [], 'warnings': [],
              'full_decode': 'not_requested', 'cadence': {'status': 'not_requested'},
              'not_checked': ['visual clarity/semantics/privacy', 'voice identity/pitch',
                              'continuous listening', 'motion continuity/freezes and source-speed audit',
                              'actual 1x playback experience']}
    errors, warnings = report['errors'], report['warnings']
    try:
        if not args.file.is_file() or args.file.stat().st_size == 0:
            raise ValueError('Delivered file is missing or empty')
        probe_tool = shutil.which(args.ffprobe)
        if not probe_tool:
            raise ValueError('ffprobe not found; pass --ffprobe /absolute/path')
        probe = subprocess.run([probe_tool, '-v', 'error', '-show_streams',
                                '-show_format', '-of', 'json', str(args.file)],
                               capture_output=True, text=True, check=True)
        data = json.loads(probe.stdout)
        media_format = data.get('format', {})
        major_brand = media_format.get('tags', {}).get('major_brand', '').strip()
        report['container'] = {'format_name': media_format.get('format_name'),
                               'major_brand': major_brand,
                               'suffix': args.file.suffix.lower()}
        if args.container:
            if args.file.suffix.lower() != '.' + args.container:
                errors.append('Output suffix does not match requested container')
            if 'mov' not in media_format.get('format_name', '').split(','):
                errors.append('Actual container is not in the MOV/MP4 media family')
            if args.container == 'mov' and major_brand != 'qt':
                errors.append('Expected actual QuickTime MOV major_brand=qt; renaming MP4 is insufficient')
            if args.container == 'mp4' and (not major_brand or major_brand == 'qt'):
                errors.append('Expected an MP4 major_brand rather than QuickTime MOV')
        videos = [s for s in data.get('streams', []) if s.get('codec_type') == 'video']
        audios = [s for s in data.get('streams', []) if s.get('codec_type') == 'audio']
        if len(videos) != 1:
            raise ValueError(f'Expected one video stream, found {len(videos)}')
        video = videos[0]
        duration = float(video.get('duration', data['format'].get('duration', 'nan')))
        average, nominal = rate(video.get('avg_frame_rate')), rate(video.get('r_frame_rate'))
        frame_count = int(video['nb_frames']) if str(video.get('nb_frames', '')).isdigit() else None
        report.update({'bytes': args.file.stat().st_size,
                       'video': {'codec': video.get('codec_name'), 'width': video.get('width'),
                                 'height': video.get('height'), 'average_fps': average,
                                 'nominal_fps': nominal, 'frames': frame_count,
                                 'duration_seconds': duration if math.isfinite(duration) else None},
                       'audio': [{'codec': s.get('codec_name'), 'sample_rate': s.get('sample_rate'),
                                  'channels': s.get('channels'), 'duration': s.get('duration')}
                                 for s in audios]})
        if (video.get('width'), video.get('height')) != (args.width, args.height):
            errors.append('Output dimensions do not match the requested dimensions')
        if average is None or abs(average - args.fps) > 1e-3:
            errors.append('Average fps does not match the requested fps')
        if nominal is None or abs(nominal - args.fps) > 1e-3:
            errors.append('Nominal fps does not match the requested fps')
        tolerance = max(1 / args.fps, 0.05)
        if not math.isfinite(duration) or abs(duration - args.duration_seconds) > tolerance:
            errors.append('Video duration does not match the requested duration')
        if args.frames is not None:
            if frame_count is None and not args.check_cadence:
                warnings.append('Container does not report frame count; exact count was not verified')
            elif frame_count is not None and frame_count != args.frames:
                errors.append('Frame count does not match the requested frame count')
        if not audios and not args.no_audio:
            errors.append('Expected an audio stream')
        for stream in audios:
            if stream.get('duration'):
                delta = abs(float(stream['duration']) - args.duration_seconds)
                if delta > max(tolerance, 0.1):
                    errors.append('Audio duration differs from the requested duration')
        if args.check_cadence:
            frame_probe = subprocess.run([probe_tool, '-v', 'error', '-select_streams', 'v:0',
                '-show_frames', '-show_entries', 'frame=pts,best_effort_timestamp',
                '-of', 'json', str(args.file)], capture_output=True, text=True, check=True)
            expected_count = args.frames if args.frames is not None else round(args.duration_seconds*args.fps)
            report['cadence'] = inspect_cadence(json.loads(frame_probe.stdout).get('frames', []),
                video['time_base'], args.fps, expected_count)
            errors.extend(report['cadence']['errors'])
            report['video']['decoded_frames'] = report['cadence']['decoded_frames']
        if args.decode:
            decode_tool = shutil.which(args.ffmpeg)
            if not decode_tool:
                raise ValueError('ffmpeg not found; pass --ffmpeg /absolute/path')
            command = [decode_tool, '-v', 'error', '-xerror', '-err_detect', 'explode',
                       '-i', str(args.file), '-map', '0:v:0', '-map', '0:a?', '-f', 'null', '-']
            result = subprocess.run(command, capture_output=True, text=True)
            report['full_decode'] = 'passed' if result.returncode == 0 and not result.stderr.strip() else 'failed'
            if report['full_decode'] == 'failed':
                errors.append('Full decode failed: ' + result.stderr[-3000:])
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        errors.append(str(exc))
    report['passed'] = not errors
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
