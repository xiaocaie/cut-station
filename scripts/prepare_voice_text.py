#!/usr/bin/env python3
"""Prepare approved narration; split only for an explicitly evidenced text limit."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def character_units(text):
    # Conservative for UI limits whose treatment of supplementary characters is unknown.
    return len(text.encode('utf-16-le')) // 2


def split_bounded(text, maximum):
    if type(maximum) is not int or maximum < 1:
        raise ValueError('字数上限必须是正整数')
    chunks, start = [], 0
    while start < len(text):
        end, count = start, 0
        while end < len(text) and count + character_units(text[end]) <= maximum:
            count += character_units(text[end]); end += 1
        if end == start:
            raise ValueError('上限无法容纳一个完整Unicode字符')
        if end < len(text):
            part = text[start:end]
            # Prefer late semantic boundaries, not sentence-by-sentence caption cuts.
            for pattern in (r'[。！？!?；;][”’」』）)]? *', r'[，,、：:] *', r' +'):
                candidates = [m.end() for m in re.finditer(pattern, part)
                              if character_units(part[:m.end()]) >= maximum * .5]
                if candidates:
                    end = start + candidates[-1]; break
        chunks.append(text[start:end]); start = end
    return chunks


def prepare(document, max_chars=None, limit_evidence=None, limit_source=None):
    if not isinstance(document, dict) or document.get('script_status') != 'final':
        raise ValueError('先冻结定稿：script_status 必须为 final')
    text = document.get('narration_text')
    if not isinstance(text, str) or not text.strip():
        raise ValueError('缺少 narration_text：提供保留自然标点的完整定稿，不从碎字幕猜回口播')
    if re.search(r'\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->', text):
        raise ValueError('配音输入不得包含 SRT 时间码')
    paragraph = re.sub(r'\s+', ' ', text).strip()
    manifest = {'schema_version':1, 'script_status':'final', 'revision':document.get('revision'),
                'mode':'whole_paragraph', 'text_object_count':1, 'planned_generation_count':1,
                'text':paragraph, 'text_sha256':sha256(paragraph.encode()),
                'character_count':len(paragraph), 'normalization':'collapse whitespace only; preserve words and punctuation',
                'not_proven':['UI text/voice matches manifest', 'TTS generation succeeded', 'complete listening review']}
    if max_chars is not None:
        if type(max_chars) is not int or max_chars < 1:
            raise ValueError('字数上限必须是正整数')
        if limit_source not in ('user', 'observed_ui') or not limit_evidence:
            raise ValueError('限定拆分须提供user/observed_ui来源和实际限制依据文件')
        evidence = Path(limit_evidence).resolve()
        if not evidence.is_file() or not evidence.stat().st_size:
            raise ValueError('限制依据文件不存在或为空')
        limit = {'max_characters':max_chars, 'counting':'utf16_code_units', 'source':limit_source,
                 'evidence':str(evidence), 'evidence_sha256':sha256(evidence.read_bytes())}
        parts = split_bounded(paragraph, max_chars)
        if len(parts) > 1:
            manifest.update(schema_version=2, mode='bounded_chunks', limit=limit,
                            text_object_count=len(parts), planned_generation_count=len(parts),
                            chunks=[{'index':i+1, 'text':part, 'text_sha256':sha256(part.encode()),
                                     'character_units':character_units(part)} for i,part in enumerate(parts)])
    return paragraph, manifest


def validate_input_files(data):
    """Validate actual input files and return every file the gate must fingerprint."""
    counts = (data.get('text_object_count'), data.get('planned_generation_count'))
    if any(type(x) is not int for x in counts):
        raise ValueError('文本对象数与生成次数必须是整数，不能用布尔值代替')
    mode = data.get('mode')
    if mode not in ('whole_paragraph', 'bounded_chunks'):
        raise ValueError('不能把逐句字幕TTS当作整段或按已证实限制拆分的配音')
    source, text_file = Path(data['source']), Path(data['text_file'])
    text = text_file.read_text(encoding='utf-8')
    expected, _ = prepare(json.loads(source.read_text(encoding='utf-8-sig')))
    if ('\n' in text or '\r' in text or text != expected or text != data.get('text')
            or sha256(text.encode()) != data['text_sha256'] or sha256(source.read_bytes()) != data['source_sha256']):
        raise ValueError('配音输入文件、清单与当前完整定稿不一致')
    paths = [source, text_file]
    if mode == 'whole_paragraph':
        if counts != (1, 1) or data.get('chunks'):
            raise ValueError('未遇已证实上限时只允许一个文本对象、一次生成')
        return paths
    limit = data.get('limit', {})
    if limit.get('source') not in ('user', 'observed_ui') or limit.get('counting') != 'utf16_code_units':
        raise ValueError('分块缺少实际字数限制来源')
    evidence = Path(limit['evidence'])
    if not evidence.is_file() or not evidence.stat().st_size or sha256(evidence.read_bytes()) != limit['evidence_sha256']:
        raise ValueError('字数限制依据已经变化或不存在')
    parts = split_bounded(text, limit['max_characters'])
    chunks = data.get('chunks', [])
    if len(parts) < 2 or counts != (len(parts), len(parts)) or len(chunks) != len(parts):
        raise ValueError('分块次数必须对应完整稿按已证实上限的语义分块')
    for i,(part,chunk) in enumerate(zip(parts, chunks), 1):
        path = Path(chunk['text_file'])
        if (chunk.get('index') != i or chunk.get('text') != part or path.read_text(encoding='utf-8') != part
                or chunk.get('text_sha256') != sha256(part.encode())
                or chunk.get('character_units') != character_units(part)):
            raise ValueError('分块顺序、原文、字数或文件不一致')
        paths.append(path)
    paths.append(evidence)
    return paths


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('output', type=Path, help='完整稿TXT；有明确上限才另写part-NN.txt')
    p.add_argument('--max-chars', type=int)
    p.add_argument('--limit-source', choices=['user','observed_ui'])
    p.add_argument('--limit-evidence', type=Path)
    a = p.parse_args()
    try:
        source, output = a.input.resolve(), a.output.resolve()
        manifest_path = output.with_suffix('.voice-input.json')
        if output.suffix.lower() != '.txt': raise ValueError('输出必须为 .txt')
        if a.max_chars is None and (a.limit_source or a.limit_evidence): raise ValueError('限制依据必须与--max-chars同时使用')
        paragraph, manifest = prepare(json.loads(source.read_text(encoding='utf-8-sig')),a.max_chars,a.limit_evidence,a.limit_source)
        writes = [(output, paragraph)]
        for chunk in manifest.get('chunks', []):
            path = output.with_name(output.stem + '.part-%02d.txt' % chunk['index'])
            chunk['text_file'] = str(path); writes.append((path, chunk['text']))
        targets = [path for path,_ in writes] + [manifest_path]
        if any(path.exists() or path == source for path in targets):
            raise ValueError('使用新版本文件名；不覆盖源稿或已有完整稿/分块/清单')
        manifest.update(source=str(source),source_sha256=sha256(source.read_bytes()),text_file=str(output))
        output.parent.mkdir(parents=True,exist_ok=True)
        for path,content in writes: path.write_text(content,encoding='utf-8')
        manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'text_file':str(output),'manifest':str(manifest_path),'mode':manifest['mode'],
                          'text_object_count':manifest['text_object_count'],'character_count':len(paragraph)},ensure_ascii=False,indent=2))
        return 0
    except (OSError,UnicodeError,ValueError) as exc:
        print(str(exc),file=sys.stderr); return 1


if __name__ == '__main__':
    sys.exit(main())
