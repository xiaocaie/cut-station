#!/usr/bin/env python3
"""Fill only ellipsis runs, preserving every other original character."""
import argparse
import json
import re
import sys
from pathlib import Path
from select_copywriting import DEFAULT, select

ELLIPSIS=re.compile(r'…+|⋯+|\.{3,}')


def fill_ellipses(pattern, values):
    matches=list(ELLIPSIS.finditer(pattern))
    if len(matches)!=len(values):
        raise ValueError(f'原句有{len(matches)}组省略号，收到{len(values)}个填值；仅允许逐组填入')
    pieces=[];last=0
    for match,value in zip(matches,values):
        pieces.extend((pattern[last:match.start()],value))
        last=match.end()
    pieces.append(pattern[last:])
    return ''.join(pieces)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--id');g.add_argument('--pattern')
    p.add_argument('--library',type=Path,default=DEFAULT)
    p.add_argument('--fill',action='append',default=[])
    args=p.parse_args()
    try:
        pattern=args.pattern
        if args.id:
            data=json.loads(args.library.read_text(encoding='utf-8'))
            pattern=select(data,ids=[args.id])[0]['text']
        result=fill_ellipses(pattern,args.fill)
    except (OSError,ValueError,KeyError,TypeError) as error:p.error(str(error))
    print(json.dumps({'library_id':args.id,'source_pattern':pattern,'ellipsis_fills':args.fill,
                      'final_hook':result,'non_ellipsis_characters':'unchanged'},ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':sys.exit(main())
