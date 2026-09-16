#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q30 · 候选③: 未派生器具行的 `evidence_cmd` 指向**仓库内可复现的生产者脚本**。

缺陷: 9 行 `instrument == null` (evidence_cmd 里没有可派生的仓库内源文件):
  · 3 行把器具写在 **/tmp 一次性脚本**上 (`bash /tmp/r462_e2e.sh`, `/tmp/r462_w_bench.py`, `/tmp/r468_tests_x3.log`)
    ⇒ 声明的复现命令**今天已不可执行** (证据不可复现, 属 L1 级缺口);
  · 其余为 shell 断言链 / 文档证据 / 目录证据 (无单一器具)。
本步只做**有仓库内真实生产者**的行, 逐行先用 grep 机检「该脚本确实写这个产物」才改, 不猜。

纪律: 序列化器逐字节复现断言 → 只改 evidence_cmd 一个键 → 幂等 → 写后读回 → 打印 numstat。
pins 不在本步改动 (由接下来的 `bind_evidence --only ... --apply --round EXP1-Q30` 定向重审)。
"""
import hashlib
import json
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=True).stdout.strip()
REG = 'docs/verification-registry.json'
ROUND = 'EXP1-Q30'

# 逐条: (row_id, 新 evidence_cmd, 生产者脚本, 产物, 机检依据行)
FIXES = [
    ('r445.prev-reply-face-indicative',
     'python3 eval/rover/r445/judge_prefilter_precheck.py --out eval/rover/r445/precheck-judge-prefilter.json',
     'eval/rover/r445/judge_prefilter_precheck.py',
     'eval/rover/r445/precheck-judge-prefilter.json',
     'ap.add_argument("--out", default=os.path.join(HERE, "precheck-judge-prefilter.json"))'),
    ('r462.recall-reality-gate',
     'python3 eval/rover/r462/judge_r462.py   # verdict-r462.json 写入者 (R462_OUT 或默认 eval/rover/r462/); '
     '编排器 = eval/rover/r462/r462_run.sh (原声明 bash /tmp/r462_e2e.sh 已不存在)',
     'eval/rover/r462/judge_r462.py',
     'eval/rover/r462/verdict-r462.json',
     'os.environ.get("R462_OUT") or os.path.join(A, "eval", "rover", "r462", "verdict-r462.json")'),
    ('r464.settle-sentinel-and-cross-round-determinism',
     'python3 eval/rover/r464/settle_r464.py <run_root> <arm>   # verdict-r464.json 写入者 (逐臂累加)',
     'eval/rover/r464/settle_r464.py',
     'eval/rover/r464/verdict-r464.json',
     "p = os.path.join(ROOT, 'verdict-r464.json')"),
    ('r468.gate-rules-port-diff',
     'python3 eval/rover/r468/settle_r468.py   # difftest_r468.log 写入者 (日志由本脚本第 58 行落盘)',
     'eval/rover/r468/settle_r468.py',
     'eval/rover/r468/difftest_r468.log',
     'dt_path = os.path.join(HERE, "difftest_r468.log")'),
]


def sha12(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12]


def main():
    dry = '--dry-run' in sys.argv
    reg_abs = os.path.join(ROOT, REG)
    raw = open(reg_abs, encoding='utf-8', newline='').read()
    doc = json.loads(raw)
    ser = json.dumps(doc, indent=1, ensure_ascii=False)
    tail = '\n' if raw.endswith('\n') else ''
    if ser + tail != raw:
        print('SER_ASSERT=FAIL (禁改写)')
        return 3
    print('SER_ASSERT=OK (tail=%s)' % ('LF' if tail else 'NONE'))

    # --- grep 机检: 生产者脚本确实提及该产物 ---
    for rid, cmd, prod, art, ev in FIXES:
        blob = open(os.path.join(ROOT, prod), encoding='utf-8', errors='replace').read()
        base = os.path.basename(art)
        hit = (ev and ev in blob) or (base in blob)
        if not hit:
            print('GREP_CHECK=FAIL %s: %s 未提及产物 %s ⇒ 拒改 (不猜器具)' % (rid, prod, art))
            return 3
        print('GREP_CHECK=OK   %-46s %s ← %s' % (rid, base, prod))

    by_id = {r.get('id'): r for r in doc['rows']}
    changed = []
    for rid, cmd, prod, art, ev in FIXES:
        r = by_id[rid]
        if r.get('evidence_cmd') == cmd:
            continue
        changed.append(rid)
        r['evidence_cmd'] = cmd
    print('CMD_REWRITTEN %d: %s' % (len(changed), changed))
    if not changed:
        print('IDEMPOTENT=OK (无变化)')
        return 0
    if dry:
        print('DRY_RUN=OK (未写盘)')
        return 0
    out = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'
    open(reg_abs, 'w', encoding='utf-8', newline='').write(out)
    back = open(reg_abs, encoding='utf-8', newline='').read()
    ok = (back == out)
    print('WRITE_READBACK=%s' % ('OK' if ok else 'MISMATCH'))
    d2 = json.loads(back)
    # 结构不变式: 行数不变 ∧ 只有这些行的 evidence_cmd 变
    assert len(d2['rows']) == len(doc['rows'])
    b2 = {r.get('id'): r for r in d2['rows']}
    diff_rows = [i for i in b2 if b2[i] != by_id.get(i)]
    print('CHANGED_ROWS=%s' % sorted(diff_rows))
    print(subprocess.run(['git', 'diff', '--numstat', '--', REG], cwd=ROOT, capture_output=True,
                         text=True).stdout.strip())
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
