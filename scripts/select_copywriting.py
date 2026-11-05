#!/usr/bin/env python3
"""Retrieve local copy patterns without treating source claims as verified facts."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PERSONAL = ROOT / 'private/copywriting-library/library.json'
PUBLIC = ROOT / 'assets/copywriting/library.json'
DEFAULT = PERSONAL if PERSONAL.is_file() else PUBLIC


def select(data, query='', categories=(), kind='all', ids=(), limit=6):
    terms=re.findall(r'[\w\u4e00-\u9fff]+',query.lower())
    requested=set(ids)
    rows=[]
    seen=set()
    for index,row in enumerate(data['entries']):
        if requested:
            if row['id'] not in requested:continue
        else:
            if categories and row['category'] not in categories:continue
            if kind!='all' and row['kind']!=kind:continue
            if row.get('duplicate_of'):continue
        normalized=re.sub(r'[\W_]+','',row['text']).lower()
        if not requested and normalized in seen:continue
        seen.add(normalized)
        haystack=(row['text']+' '+row['category']+' '+row['kind']).lower()
        score=sum(3+haystack.count(term) for term in terms if term in haystack)
        # Stable tie order; a query with no matching text still returns category candidates.
        rows.append((score,index,row))
    if requested:
        found={row[2]['id'] for row in rows}
        missing=requested-found
        if missing:raise ValueError('未知条目ID：'+', '.join(sorted(missing)))
        order={key:i for i,key in enumerate(ids)}
        rows.sort(key=lambda x:order[x[2]['id']])
    else:rows.sort(key=lambda x:(-x[0],x[1]))
    selected=rows if requested else rows[:limit]
    return [{**row,'query_score':score} for score,_,row in selected]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library',type=Path,default=DEFAULT)
    parser.add_argument('--query',default='')
    parser.add_argument('--category',action='append',default=[])
    parser.add_argument('--kind',choices=['all','template','example'],default='all')
    parser.add_argument('--id',action='append',default=[])
    parser.add_argument('--limit',type=int,default=6)
    args=parser.parse_args()
    if args.limit<1:parser.error('--limit 必须大于0')
    if not args.library.is_file():
        print(json.dumps({'available':False,'candidates':[],'fallback':'未找到原句库；可使用用户明确提供的原句，不声称已从库中选句'},ensure_ascii=False))
        return 0 if args.library==DEFAULT else 1
    try:
        data=json.loads(args.library.read_text(encoding='utf-8'))
        result=select(data,args.query,args.category,args.kind,args.id,args.limit)
    except (OSError,ValueError,KeyError,TypeError) as error:
        parser.error(str(error))
    print(json.dumps({'available':True,'source_notice':data.get('provenance'),'counts':data.get('counts'),
                      'query':args.query,'categories':args.category,'candidates':result},ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':sys.exit(main())
