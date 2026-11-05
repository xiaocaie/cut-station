"""Observable checks for bounded voice input and the distributable hook corpus."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import shutil
import subprocess
import unittest
from unittest.mock import patch

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
import prepare_voice_text as voice
import workflow_guard as guard
from fill_copywriting import fill_ellipses
from select_copywriting import select, PUBLIC


class BoundedVoiceTests(unittest.TestCase):
    def make_input(self, root, text=None):
        root=root.resolve()
        source=root/'script.json';evidence=root/'limit.txt';output=root/'voice.txt'
        source.write_text(json.dumps({'script_status':'final','narration_text':text or ('完整内容保留标点和术语。'*60)},ensure_ascii=False),encoding='utf-8')
        evidence.write_text('本项目当前所选音色单次最多500字符，请按上限拆开配音。',encoding='utf-8')
        with patch.object(sys,'argv',['prepare_voice_text',str(source),str(output),'--max-chars','500','--limit-source','user','--limit-evidence',str(evidence)]),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(voice.main(),0)
        manifest=output.with_suffix('.voice-input.json')
        return source,evidence,output,manifest,json.loads(manifest.read_text())

    def test_real_files_preserve_all_text_and_bound_each_chunk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source,evidence,output,manifest,data=self.make_input(root)
            self.assertEqual(data['mode'],'bounded_chunks')
            chunks=[Path(c['text_file']).read_text() for c in data['chunks']]
            self.assertEqual(''.join(chunks),output.read_text())
            self.assertTrue(all(voice.character_units(c)<=500 for c in chunks))
            state={'script_lock':{'path':str(source.resolve()),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}}
            guard.validate_artifact({'path':str(manifest),'role':'voice_input'},state)
            self.assertIn(evidence,voice.validate_input_files(data))
            self.assertIn(Path(data['chunks'][0]['text_file']),voice.validate_input_files(data))

    def test_missing_limit_authorization_cannot_enable_chunks(self):
        for source,evidence in [(None,None),('user',None),('self_approved','not-used')]:
            with self.assertRaises(ValueError):voice.prepare({'script_status':'final','narration_text':'甲'*600},500,evidence,source)

    def test_short_text_remains_single_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,_,_,_,data=self.make_input(Path(tmp),'短稿保留一次朗读。')
            self.assertEqual((data['mode'],data['text_object_count']),('whole_paragraph',1))
            self.assertNotIn('chunks',data)
            voice.validate_input_files(data)

    def test_utf16_limit_preserves_complete_non_bmp_characters(self):
        text='😀'*251+'结束。';parts=voice.split_bounded(text,500)
        self.assertEqual(''.join(parts),text)
        self.assertEqual(len(parts[0]),250)
        self.assertTrue(all(voice.character_units(p)<=500 for p in parts))

    def test_chunk_or_evidence_mutation_rejected(self):
        for changed in ['chunk','evidence','reorder','extra']:
            with self.subTest(changed=changed),tempfile.TemporaryDirectory() as tmp:
                _,evidence,_,_,data=self.make_input(Path(tmp))
                if changed=='chunk':Path(data['chunks'][0]['text_file']).write_text('偷改',encoding='utf-8')
                elif changed=='evidence':evidence.write_text('限制已改变',encoding='utf-8')
                elif changed=='reorder':data['chunks'].reverse()
                else:data['chunks'].append(data['chunks'][-1])
                with self.assertRaises(ValueError):voice.validate_input_files(data)

    def test_existing_part_file_prevents_all_new_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'script.json';evidence=root/'limit.txt';output=root/'voice.txt'
            source.write_text(json.dumps({'script_status':'final','narration_text':'甲'*600}),encoding='utf-8');evidence.write_text('用户要求按500上限拆分',encoding='utf-8')
            part=root/'voice.part-01.txt';part.write_text('keep',encoding='utf-8')
            with patch.object(sys,'argv',['prepare_voice_text',str(source),str(output),'--max-chars','500','--limit-source','user','--limit-evidence',str(evidence)]),contextlib.redirect_stderr(io.StringIO()):self.assertEqual(voice.main(),1)
            self.assertFalse(output.exists());self.assertEqual(part.read_text(),'keep')


class FontCheckoutTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('git'), 'Git is required for the actual checkout regression')
    def test_font_license_bytes_survive_windows_style_checkout(self):
        package=SCRIPTS.parent
        data=json.loads((package/'assets/fonts/manifest.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';dest=root/'checkout';source.mkdir();hooks=root/'empty-hooks';hooks.mkdir()
            (source/'.gitattributes').write_bytes((package/'.gitattributes').read_bytes())
            (source/'assets/fonts').mkdir(parents=True)
            names=[]
            for font in data['fonts']:
                name='assets/fonts/'+font['license_file'];names.append(name)
                shutil.copyfile(package/name,source/name)
            def git(*args):
                return subprocess.run(['git',*map(str,args)],cwd=source,check=True,capture_output=True)
            git('init','-q');git('config','core.autocrlf','true');git('config','core.hooksPath',hooks)
            git('add','--','.gitattributes',*names)
            git('-c','user.name=Synthetic Test','-c','user.email=synthetic@example.invalid','-c','commit.gpgsign=false','commit','-qm','Synthetic byte preservation')
            git('clone','-q','--no-local','--config','core.autocrlf=true',source,dest)
            for font in data['fonts']:
                name='assets/fonts/'+font['license_file'];actual=(dest/name).read_bytes()
                self.assertEqual(actual,(package/name).read_bytes(),name)
                self.assertEqual(hashlib.sha256(actual).hexdigest(),font['license_file_sha256'])


class PublicCopyTests(unittest.TestCase):
    def test_complete_corpus_has_consistent_counts_sources_and_ids(self):
        data=json.loads(PUBLIC.read_text(encoding='utf-8'));rows=data['entries'];ids=[x['id'] for x in rows]
        self.assertEqual(len(ids),len(set(ids)))
        for kind,key in [('template','templates'),('example','examples')]:self.assertEqual(sum(x['kind']==kind for x in rows),data['counts'][key])
        self.assertEqual(len(data['methods']),data['counts']['methods'])
        sources={x['file'] for x in data['sources']}
        self.assertTrue(all(row['source'] in sources and row['text'] for row in rows))
        self.assertTrue(all(row.get('duplicate_of') in ids for row in rows if row.get('duplicate_of')))
        self.assertTrue(all(len(x['sha256'])==64 and Path(x['file']).name==x['file'] for x in data['sources']))

    def test_public_selector_and_filler_work_without_personal_corpus(self):
        data=json.loads(PUBLIC.read_text(encoding='utf-8'));row=select(data,query='打破信息差',kind='template',limit=1)[0]
        self.assertIn('打破信息差',row['text'])
        result=fill_ellipses(row['text'],['具体任务'])
        self.assertEqual(result,row['text'].replace('……','具体任务'))

    def test_fixed_words_numbers_and_punctuation_do_not_change(self):
        self.assertEqual(fill_ellipses('只用了10分钟，……！……？',['完成甲','完成乙']),'只用了10分钟，完成甲！完成乙？')
        for fills in [[],['不够'],['甲','乙','丙']]:
            with self.assertRaises(ValueError):fill_ellipses('……！……？',fills)


if __name__=='__main__':unittest.main()
