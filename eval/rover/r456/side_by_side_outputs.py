#!/usr/bin/env python3
"""两侧「输出效果」原文对照（只读落盘证据）:
我方: /tmp/r456_env/{logs/agent-turns.jsonl, logs/audit/action_loop.jsonl, agent/work/*}
codex: /tmp/r455_env/logs/codex-t*.jsonl 事件流 + /tmp/r455_env/codex/work/*
"""
import glob, json, os

PROD = ['count.txt', 'merged.txt', 'stats.txt', 'first.txt']


def our_replies():
    p = '/tmp/r456_env/logs/agent-turns.jsonl'
    if not os.path.exists(p):
        return []
    d = json.load(open(p, encoding='utf-8'))
    ts = d['turns'] if isinstance(d, dict) and 'turns' in d else d
    out = []
    for i, t in enumerate(ts, 1):
        r = (t.get('reply') or t.get('content') or '').strip()
        out.append((i, t.get('ask') or t.get('input') or '', r))
    return out


def our_exec():
    p = '/tmp/r456_env/logs/audit/action_loop.jsonl'
    rows = []
    if os.path.exists(p):
        for ln in open(p, encoding='utf-8', errors='replace'):
            ln = ln.strip()
            if ln:
                try:
                    rows.append(json.loads(ln))
                except Exception:
                    pass
    return rows


def codex_events():
    msgs, cmds = [], []
    for p in sorted(glob.glob('/tmp/r455_env/logs/codex-t*.jsonl')):
        for ln in open(p, encoding='utf-8', errors='replace'):
            ln = ln.strip()
            if not ln:
                continue
            try:
                e = json.loads(ln)
            except Exception:
                continue
            it = e.get('item') or e
            t = it.get('type') or it.get('item_type') or ''
            if t == 'agent_message':
                msgs.append((os.path.basename(p), (it.get('text') or '').strip()))
            elif t == 'command_execution':
                cmds.append((os.path.basename(p), it.get('command'), it.get('exit_code'),
                             (it.get('aggregated_output') or '')[:110].replace('\n', ' | ')))
    return msgs, cmds


print('========== 我方 click-agent R456（动作环 on，9 次上游调用）==========')
rs = our_replies()
print(f'[A] 6 轮输入→我方回复原文（len / 问询? ）: {len(rs)} 轮')
for i, ask, r in rs:
    print(f"  T{i} <{ask[:26]}> len={len(r)} {'[含问号]' if ('?' in r or '？' in r) else ''}")
    print('     ' + (r[:300].replace('\n', ' ⏎ ') if r else '(空回复)'))
print()
ex = our_exec()
print(f'[B] 我方工具执行审计（真实落盘）: {len(ex)} 次')
for e in ex:
    print(f"  step={e.get('step')} tool={e.get('tool')} rc={e.get('rc')} ok={e.get('ok')} arg={str(e.get('arg') or e.get('path') or '')[:60]}")
    o = (e.get('stdout') or e.get('output') or '')
    if o:
        print('     out: ' + o[:110].replace('\n', ' | '))
print()
print('[C] 我方产物（磁盘原文）:')
for f in PROD:
    p = f'/tmp/r456_env/agent/work/{f}'
    v = open(p, encoding='utf-8', errors='replace').read() if os.path.exists(p) else None
    print(f"  {f:11s} = {v!r}")
print()
print('========== codex 0.154（同一适配器/同一模型/同一夹具；冻结）==========')
m, c = codex_events()
print(f'[A] codex agent_message: {len(m)} 条')
for f, t in m:
    print(f'  {f} len={len(t)}: ' + t[:200].replace('\n', ' ⏎ '))
print(f'[B] codex command_execution: {len(c)} 条')
for f, cmd, rc, o in c:
    print(f'  {f} rc={rc} cmd={str(cmd)[:70]}')
    if o:
        print('     out: ' + o)
print('[C] codex 产物（磁盘原文）:')
for f in PROD:
    p = f'/tmp/r455_env/codex/work/{f}'
    v = open(p, encoding='utf-8', errors='replace').read() if os.path.exists(p) else None
    print(f"  {f:11s} = {v!r}")
