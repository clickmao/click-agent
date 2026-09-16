#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q31 · C5: L2 器具面扩容 (21 → 27) —— 新器具行 + 被改器具行的 sha 重审。

行内纪律 (沿用 Q30 通路): 序列化器逐字节复现断言 → 只新增/只刷新三字段 (version/instrument_sha12/owner_round)
→ 幂等 → 读回 → 行数守恒 → numstat。
新增 6 行 (每条成对: 正控 expect_rc/expect_substr + 负控 nc_cmd/nc_expect):
  exp1q31.retired-interop / exp1q31.cleanup-ledger / exp1q31.dotnet-gate-classifier /
  exp1q31.cap-headroom / exp1q31.only-equivalence / exp1q31.stage-guard-hook
刷新 1 行: hooks.pre-commit (本轮接入了跨写者提交闸 ⇒ 器具字节已变, 声明 sha 必须重审, 否则面判 DRIFT)。
"""
import hashlib
import json
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=True).stdout.strip()
MAN = 'eval/capability/instruments.json'


def sha12(rel):
    return hashlib.sha256(open(os.path.join(ROOT, rel), 'rb').read()).hexdigest()[:12]


def row(rid, kind, cmd, substr, nc_cmd, nc_expect, evidence, surface, reason,
        unit, denom, truth, caliber, fingerprint=()):
    sha = sha12(evidence)
    return {
        'id': rid, 'kind': kind, 'cmd': cmd, 'expect_rc': 0, 'expect_substr': substr,
        'nc_cmd': nc_cmd, 'nc_expect': nc_expect,
        'kpi_quad': {'单位': unit, '分母': denom, '真值源': truth, '口径档': caliber},
        'owner_round': 'EXP1-Q31', 'evidence_path': evidence,
        'version': 'content-sha12:%s' % sha, 'version_source': 'content-sha12', 'instrument_sha12': sha,
        'input_fingerprint': list(fingerprint), 'input_surface': surface,
        'input_surface_source': 'audit_hook', 'input_surface_reason': reason,
    }


def main():
    dry = '--dry-run' in sys.argv
    man_abs = os.path.join(ROOT, MAN)
    raw = open(man_abs, encoding='utf-8', newline='').read()
    doc = json.loads(raw)
    ser = json.dumps(doc, indent=1, ensure_ascii=False)
    tail = '\n' if raw.endswith('\n') else ''
    if ser + tail != raw:
        print('SER_ASSERT=FAIL (禁改写)')
        return 3
    print('SER_ASSERT=OK (tail=%s)' % ('LF' if tail else 'NONE'))

    ledger_rel = 'eval/rover/r463/deletion-ledger.json'
    new_rows = [
        row('exp1q31.retired-interop', 'assertion-instrument',
            'python3 eval/capability/exp1-q31/instruments/retired_interop_absent.py', 'RETIRE_OK',
            'bash eval/capability/exp1-q31/_nc_retired_q31.sh', 'detect:NC_DETECTED',
            'eval/capability/exp1-q31/instruments/retired_interop_absent.py', 'dynamic_corpus',
            '输入 = 仓库源码树 .cs 互操作声明扫描结果 (随轮增删) ⇒ 不做字节指纹, 记扫描口径',
            'registry 行', '登记表覆盖行 (113)', '登记表 evidence_cmd + 源码树扫描', 'L1 断言', ()),
        row('exp1q31.cleanup-ledger', 'assertion-instrument',
            'python3 eval/capability/exp1-q31/instruments/cleanup_ledger_check.py',
            'CLEANUP_LEDGER_CHECK=OK',
            'python3 eval/capability/exp1-q31/instruments/cleanup_ledger_check.py '
            '--ledger /tmp/q31_absent_ledger.json', 'nonzero',
            'eval/capability/exp1-q31/instruments/cleanup_ledger_check.py', 'external_files',
            '输入 = 单份删除台账 (可冻结字节指纹)',
            '台账条目', '台账条数 (4)', 'eval/rover/r463/deletion-ledger.json', 'L1 断言',
            ({'path': ledger_rel, 'sha12': sha12(ledger_rel)},)),
        row('exp1q31.dotnet-gate-classifier', 'classifier-fixture',
            'python3 eval/capability/exp1-q31/instruments/dotnet_test_gate.py --selftest', 'SELFTEST PASS',
            'python3 eval/capability/exp1-q31/instruments/dotnet_test_gate.py', 'nonzero',
            'eval/capability/exp1-q31/instruments/dotnet_test_gate.py', 'self_contained',
            '输入 = 内建 6 例合成日志夹具 (三分类), 无仓库内输入文件',
            '分类分支', '夹具数 (6)', '合成日志夹具', '三态 (0/2/3)', ()),
        row('exp1q31.cap-headroom', 'threshold-ledger',
            'python3 eval/capability/exp1-q31/instruments/face_cap_headroom.py --check', 'CAP_HEADROOM=OK',
            'python3 eval/capability/exp1-q31/_nc_cap_capped_q31.py', 'detect:NC_DETECTED',
            'eval/capability/exp1-q31/instruments/face_cap_headroom.py', 'dynamic_corpus',
            '输入 = 全量面记录 (每轮重写) + 器具源码阈值常量 ⇒ 不冻结字节, 记余量比',
            '面', '器具面规模 (器具数/命令数)', 'eval/capability/instruments-check.json trace 段',
            'log_bytes/命令数', ()),
        row('exp1q31.only-equivalence', 'equivalence-guard',
            'python3 eval/capability/exp1-q31/instruments/only_equivalence_guard.py', 'verdict=PASS',
            'python3 eval/capability/exp1-q31/_nc_only_equivalence_q31.py', 'detect:NC_DETECTED',
            'eval/capability/exp1-q31/instruments/only_equivalence_guard.py', 'dynamic_corpus',
            '输入 = 真登记表 (每轮重写) + 现场派生夹具锚 (防旧轮 pin 字面量过期)',
            '写路径对', '等价判据检查项 (8)', '两条独立写路径产物 sha', '逐字节等价', ()),
        row('exp1q31.stage-guard-hook', 'arbitration',
            'python3 eval/capability/exp1-q31/verify_stage_guard_hook_q31.py', 'verdict=PASS',
            'python3 eval/capability/exp1-q31/_nc_stage_guard_hollow_q31.py', 'detect:NC_DETECTED',
            'eval/capability/exp1-q31/verify_stage_guard_hook_q31.py', 'dynamic_corpus',
            '输入 = 真仓钩子 + 一次性 git 夹具仓 (不接触真索引) ⇒ 不冻结字节',
            '提交', '夹具场景 (8)', 'git 夹具仓 rc + BLOCKED 文案', 'n/a', ()),
    ]
    by_id = {e['id']: e for e in doc['instruments']}
    changed, added = [], []
    for r in new_rows:
        if r['id'] in by_id:
            cur = by_id[r['id']]
            if cur != r:
                changed.append(r['id'])
                by_id[r['id']].update(r)
        else:
            doc['instruments'].append(r)
            added.append(r['id'])
    # 刷新被改器具行 (钩子): 只动 version/instrument_sha12/owner_round
    hook = by_id.get('hooks.pre-commit')
    hook_refresh = None
    if hook is not None:
        sha = sha12(hook['evidence_path'])
        want = {'version': 'content-sha12:%s' % sha, 'instrument_sha12': sha, 'owner_round': 'EXP1-Q31'}
        diff = {k: (hook.get(k), v) for k, v in want.items() if hook.get(k) != v}
        if diff:
            hook.update(want)
            hook_refresh = diff
    print('ADDED %d: %s' % (len(added), added))
    print('UPDATED %d: %s' % (len(changed), changed))
    print('HOOK_REFRESH %s' % (hook_refresh or 'none'))
    if not added and not changed and not hook_refresh:
        print('IDEMPOTENT=OK (无变化)')
        return 0
    if dry:
        print('DRY_RUN=OK (未写盘)')
        return 0
    out = json.dumps(doc, indent=1, ensure_ascii=False) + '\n'
    open(man_abs, 'w', encoding='utf-8', newline='').write(out)
    back = open(man_abs, encoding='utf-8', newline='').read()
    print('WRITE_READBACK=%s' % ('OK' if back == out else 'MISMATCH'))
    d2 = json.loads(back)
    print('MANIFEST_SIZE %d -> %d' % (len(json.loads(raw)['instruments']), len(d2['instruments'])))
    print(subprocess.run(['git', 'diff', '--numstat', '--', MAN], cwd=ROOT, capture_output=True,
                         text=True).stdout.strip())
    return 0 if back == out else 2


if __name__ == '__main__':
    sys.exit(main())
