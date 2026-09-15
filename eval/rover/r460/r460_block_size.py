#!/usr/bin/env python3
# 量: R458 承接块实发大小 + codex T5 对照
import json, io, glob, os

def walk(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, path + '/' + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, path + f'[{i}]')
    else:
        yield path, o

print('=== 适配器落盘文件 ===')
fs = sorted(glob.glob('/tmp/r458_env/logs/adapter/*.json'))
print([os.path.basename(f) for f in fs][:12])
print()
# 找含「承接状态」的文件与块长
for f in fs:
    try:
        d = json.load(io.open(f, encoding='utf-8'))
    except Exception as e:
        print('skip', os.path.basename(f), e); continue
    blk = None
    for path, v in walk(d):
        if isinstance(v, str) and '[承接状态' in v:
            i = v.find('[承接状态')
            j = v.find(']', i)
            blk = v[i:j+1]
            break
    if blk:
        print(f'{os.path.basename(f)}: 块长={len(blk)} 字符')
        print(blk.replace('\n', ' | ')[:600])
        break
else:
    print('未找到承接块字符串; 列出 side 文件顶层键以定位')
    for f in fs[:2]:
        d = json.load(io.open(f, encoding='utf-8'))
        print(os.path.basename(f), list(d.keys())[:12])
        print(json.dumps(d, ensure_ascii=False)[:400])
