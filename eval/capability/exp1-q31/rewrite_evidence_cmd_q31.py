#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q31 · C1: 残留 5 行的 `evidence_cmd` → 仓库内可复现器具 (裁定表落地)。

裁定依据 (逐行, 见 residual_disposition_q31.py 的机检分布):
  · 2 行 doc_evidence + 1 行 directory_evidence: 证据本体是文档/目录, 但**命令**本可机跑 ⇒
    改证据面形态为仓库内器具 (断言器 / 测试面包装器), 文档/目录仍是 artifact (不动 evidence_path);
  · 1 行 tmp_instrument (r462.weight-probe): 归档**已存在且逐位相同** ⇒ 缺口在声明层, 改指归档入口;
  · 1 行 manual_read (r463.model-cleanup): `python3 -c` 一次性读取 ⇒ 变成带控制的器具。
纪律 (沿用 Q30 已证通路): 序列化器逐字节复现断言 → 逐行 grep/同一性机检 → 只改 evidence_cmd 一个键 →
  幂等 → 写后读回 → numstat。pins 由随后的 `bind_evidence --apply --only ... --round EXP1-Q31` 定向重审。
"""
import hashlib
import json
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=True).stdout.strip()
REG = 'docs/verification-registry.json'
ROUND = 'EXP1-Q31'

# (row_id, 新 evidence_cmd, 机检探针文件, 探针字面, 说明)
FIXES = [
    ('engine.retired.no_local_gguf',
     'python3 eval/capability/exp1-q31/instruments/retired_interop_absent.py   '
     '# 器具重写 (EXP1-Q31): 原声明为全树词面 grep (现盘为假 —— 合法 kernel32 声明被误杀); '
     '新判据绑子系统作用域 + 互操作库允许清单',
     'eval/capability/exp1-q31/instruments/retired_interop_absent.py', 'src/agent.embedcpu',
     '词面判据被合法用例命中 ⇒ 绑误用重写'),
    ('llamacpp.prompt.template_gate',
     'python3 eval/capability/exp1-q31/instruments/dotnet_test_gate.py '
     '--filter FullyQualifiedName~LlamaCppPromptGateTests --config Release --label template-gate '
     '&& agenthost --llamacpp --model <r1-q4km.gguf> --verify-template '
     '--chat-text "What is 12*12? Answer with the number." '
     '--prompt-file eval/rover/r409/prompt.txt --json eval/rover/r409/verify-template.json   '
     '# 外部测试面包装器: 退出码三分类 (0 绿 / 2 测试红 / 3 环境失败)',
     'eval/capability/exp1-q31/instruments/dotnet_test_gate.py',
     'src/agent.tests/agentframework.tests.csproj', '裸 dotnet test ⇒ 包装器'),
    ('r420.recall-command-wiring',
     'python3 eval/capability/exp1-q31/instruments/dotnet_test_gate.py '
     '--filter "FullyQualifiedName~SessionHistorySearchTests|FullyQualifiedName~CommandRouteConsistencyTests" '
     '--label r420-recall-wiring   # 退出码三分类: 0 绿 / 2 测试红 / 3 环境失败',
     'eval/capability/exp1-q31/instruments/dotnet_test_gate.py',
     'src/agent.tests/agentframework.tests.csproj', '裸 dotnet test ⇒ 包装器'),
    ('r462.weight-probe',
     'python3 eval/capability/exp1-q31/instruments/r462_w_probe_wrapper.py --check   '
     '# 归档入口: 器具/语料与 /tmp 原件逐位相同 (sha256); 真跑配方 = --run --gguf <gguf> (本轮 execution_blocked)',
     'eval/capability/exp1-q31/instruments/r462_w_probe_wrapper.py',
     'eval/rover/r462/bench_r462_w.py', '归档已在仓库内 ⇒ 改指自足入口'),
    ('r463.model-cleanup',
     'python3 eval/capability/exp1-q31/instruments/cleanup_ledger_check.py   '
     '# 原声明为 python3 -c 一次性读取; 新器具核字段完整性 + 逐条现盘不存在 + 与保留面无交集',
     'eval/capability/exp1-q31/instruments/cleanup_ledger_check.py',
     'eval/rover/r463/deletion-ledger.json', '一次性读取 ⇒ 带控制的器具'),
]


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

    for rid, cmd, probe_file, probe_lit, why in FIXES:
        p = os.path.join(ROOT, probe_file)
        if not os.path.isfile(p):
            print('PROBE_CHECK=FAIL %s: 探针文件不存在 %s ⇒ 拒改' % (rid, probe_file))
            return 3
        blob = open(p, encoding='utf-8', errors='replace').read()
        if probe_lit not in blob:
            print('PROBE_CHECK=FAIL %s: %s 未提及 %s ⇒ 拒改 (不猜器具)' % (rid, probe_file, probe_lit))
            return 3
        print('PROBE_CHECK=OK   %-34s %s ⊃ %s' % (rid, os.path.basename(probe_file), probe_lit[:34]))

    by_id = {r.get('id'): r for r in doc['rows']}
    missing = [f[0] for f in FIXES if f[0] not in by_id]
    if missing:
        print('ROWS_MISSING=%s ⇒ 拒改' % missing)
        return 3
    before = {f[0]: by_id[f[0]].get('evidence_cmd') for f in FIXES}
    changed = []
    for rid, cmd, *_ in FIXES:
        if by_id[rid].get('evidence_cmd') != cmd:
            by_id[rid]['evidence_cmd'] = cmd
            changed.append(rid)
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
    if len(d2['rows']) != len(doc['rows']):
        print('ROW_CONSERVATION=FAIL')
        return 2
    b2 = {r.get('id'): r for r in d2['rows']}
    diff_rows = sorted(i for i in b2 if b2[i] != by_id.get(i))
    print('ROW_CONSERVATION=OK (%d 行不变)' % len(d2['rows']))
    print('CHANGED_ROWS=%s' % diff_rows)
    print('SHA_BEFORE_AFTER=%s' % {k: (v[:40] if v else v) for k, v in before.items()})
    print(subprocess.run(['git', 'diff', '--numstat', '--', REG], cwd=ROOT, capture_output=True,
                         text=True).stdout.strip())
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
