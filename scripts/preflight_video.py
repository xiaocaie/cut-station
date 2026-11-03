#!/usr/bin/env python3
"""Read-only checks of selected local video runtime and optional source media.

No installation, API calls, transcription, rendering, or application mutations.
Package metadata does not prove that a composition or renderer works.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys


def run(command):
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise ValueError(result.stderr.strip()[:1000] or f'exit {result.returncode}')
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', choices=['remotion', 'hyperframes'], required=True)
    parser.add_argument('--project', type=Path)
    parser.add_argument('--node', default='node')
    parser.add_argument('--ffmpeg', default='ffmpeg')
    parser.add_argument('--ffprobe', default='ffprobe')
    parser.add_argument('--media', type=Path, action='append', default=[])
    args = parser.parse_args()
    checks, media = [], []
    def record(name, status, detail):
        checks.append({'name': name, 'status': status, 'detail': detail})
    for name, command in [('node', args.node), ('ffmpeg', args.ffmpeg), ('ffprobe', args.ffprobe)]:
        executable = shutil.which(command)
        if not executable:
            record(name, 'missing', f'{command} not found; pass an installed executable path')
            continue
        try:
            version = run([executable, '--version' if name == 'node' else '-version']).splitlines()[0]
            record(name, 'verified', {'path': executable, 'version': version})
            if name == 'node' and args.engine == 'hyperframes':
                match = re.match(r'v(\d+)\.', version)
                record('hyperframes_node22', 'verified' if match and int(match[1]) >= 22 else 'missing',
                       'HyperFrames currently requires Node.js 22+; do not assume another shell uses it')
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            record(name, 'missing', str(exc))
    if args.project:
        project = args.project.resolve()
        try:
            package = json.loads((project / 'package.json').read_text(encoding="utf-8"))
            if not isinstance(package, dict):
                raise ValueError('Project package.json must be a JSON object')
            record('project', 'verified', {'path': str(project), 'name': package.get('name'),
                                          'engines': package.get('engines', {})})
            installed = project / 'node_modules' / args.engine / 'package.json'
            if installed.is_file():
                installed_data = json.loads(installed.read_text(encoding="utf-8"))
                if not isinstance(installed_data, dict):
                    raise ValueError('Installed package.json must be a JSON object')
                record('engine_package', 'verified', {'name': installed_data.get('name'),
                       'version': installed_data.get('version'), 'path': str(installed)})
            else:
                record('engine_package', 'unverified',
                       'No project-local package found; verify workspace or CLI resolution before use')
        except (OSError, ValueError) as exc:
            record('project', 'missing', str(exc))
    else:
        record('project', 'unverified', 'No project supplied; engine installation and composition not checked')
    probe = shutil.which(args.ffprobe)
    for path in args.media:
        try:
            if not probe:
                raise ValueError('ffprobe not found')
            data = json.loads(run([probe, '-v', 'error', '-show_streams', '-show_format',
                                   '-of', 'json', str(path.resolve())]))
            summary = {'path': str(path.resolve()), 'duration': data.get('format', {}).get('duration'),
                       'streams': [{key: stream.get(key) for key in (
                           'codec_type', 'codec_name', 'width', 'height', 'avg_frame_rate',
                           'r_frame_rate', 'sample_rate', 'channels')}
                           for stream in data.get('streams', [])]}
            if not summary['streams']:
                raise ValueError('No streams found')
            media.append(summary)
            record('media:' + path.name, 'verified', 'Metadata only; actual speech/content not checked')
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            record('media:' + path.name, 'missing', str(exc))
    ready = all(check['status'] == 'verified' for check in checks)
    report = {'engine': args.engine, 'ready_for_project_smoke_test': ready,
              'checks': checks, 'media': media,
              'not_checked': ['actual speech or silence', 'engine CLI/composition execution',
                              'render/decode/preview', 'Jianying UI', 'paid service credentials']}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ready else 1


if __name__ == '__main__':
    sys.exit(main())
