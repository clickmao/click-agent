#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q32 · KPI 台账追加 (幂等; 键集与既有行对齐; 写后读回逐行可解析)。"""
import json
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip() or os.getcwd()
SINK = 'eval/capability/kpi.jsonl'


def main():
    raw = open(os.path.join(ROOT, SINK), encoding='utf-8-sig', newline='').read()
    lines = [x for x in raw.split('\n') if x.strip()]
    rows = [json.loads(x) for x in lines]
    keyset = tuple(rows[-1].keys())
    if any(r.get('round') == 'EXP1-Q32' for r in rows):
        print('IDEMPOTENT=OK (已有 EXP1-Q32 行)')
        return 0
    ts = subprocess.run(['date', '+%Y-%m-%dT%H:%M%z'], capture_output=True, text=True).stdout.strip()
    row = {
        'round': 'EXP1-Q32',
        'ts': ts,
        'kind': 'self-check / /tmp 单副本逐行核查+归档自足化 + 面扩容阈值复测(N_MAX=0) + 器具 pin 重审闸入提交钩子 + 口径判据否证 (60m 自检作业, 不占主线轮号)',
        'artifact': 'eval/capability/exp1-q32/{prereg_q32.json,archived_tmp/**,archive_tmp_q32.py,tmp_path_census{,2,3}_q32.json,instruments/*.py,rewrite_tmp_refs_q32.py,repin_face_q32.py,face_cap_recheck_q32.json,verdict_q32_hook_gate.json,independent_recompute_q32.json,caliber_void_audit_q32{,_strict}.json,reaudit_guard_q32.json}; tools/hooks/pre-commit; eval/capability/{instruments.json,instruments-check.json,face-scale-ledger.jsonl}; docs/verification-registry.json; docs/plans/v0.22.0-exp1-local-index-and-code-graph.md (附录 AG)',
        'change': '① /tmp 依赖逐行核查: 三代口径红 11→1→0; 11 件单副本逐字归档 (sha256 记录) + 归档还原入口 (selftest 3/3, 真机 11/11 no-op) + 15 处改指 (含 3 处仓库内逐位相同副本); ② 面扩容阈值复测: 27/59, log_bytes 33,388,397, 余量 2.01 (K_MIN 2.0), m_hist 588,422.8 B/器具, allowance 166,035 B ⇒ N_MAX=0 ⇒ 不扩面, 重开条件=soft_cap 72 MiB; ③ 器具/记录 pin 重审闸入 pre-commit (env 门控默认关; selftest 8/8; 钩子机检 5/5 含零回归逐字节 + 两类负控 + 空心钩子反证): 修前命中 2 条 (含 hooks.pre-commit 面 pin DRIFT, 原需跑完全量面才可见) ⇒ 处置后 0 违例; ④ r444.instrument-acceptance 定向重审 (--apply --only, R2E_R2F_EXIT=0); ⑤ 独立视角复算 10/10; 形式门禁 14/14',
        'readings': {'tmp_reds': {'v1': 11, 'v2': 1, 'v3': 0}, 'archived_files': 11, 'restore_selftest': '3/3',
                     'rewrite_sites': 15, 'face': {'n_instruments': 27, 'n_commands': 59, 'log_bytes': 33388397,
                                                   'headroom': 2.01, 'k_min': 2.0, 'allowance_bytes': 166035,
                                                   'n_max_expandable': 0},
                     'guard': {'selftest': '8/8', 'violations_before_fix': 2, 'violations_after_fix': 0,
                               'face_pins_ok': '27/27'},
                     'hook_gate': '5/5', 'independent_recompute': '10/10',
                     'face_full_pass': '26/27 → 27/27 (重审 pin 后)', 'formal_gate': 'Failed 0 / Passed 14'},
        'honest_boundaries': ['C4 口径判据被实测否证 (三口径误红 83/21/14) ⇒ 红绿撤回, 只留 14 项候选清单',
                              'r444 pin = 提交时点快照语义 (面记录含 window ts + 随机 trace_dir ⇒ 非逐字节确定, 每次重跑必漂移)',
                              '全量面两次读数 MemAvailable 2546/2605 MB < 2650 MB 闸值 ⇒ 记指示性, 本侧未起手拦停',
                              '未扩 L2 面 (N_MAX=0); reaudit_guard 登记为证据面器具 (面别分区)',
                              '外部资产 (gguf/发布物/venv/scratch) 未入库 = 设计边界; 归档 ripple (deps_tmp_refs) 只登记未收口',
                              '推送暂停令在效: 仅本地提交'],
        'next': ['口径判据结构化重做 (绑字段而非词面) + 14 项候选复核',
                 '归档 ripple 逐条裁定', '面记录确定化 (掐 window ts/trace_dir) 摆脱提交时点快照语义',
                 '面扩容按 reopen_condition 字面执行 (禁先扩后测)', '外部资产显式字段'],
        'owner_round': 'EXP1-Q32',
    }
    if tuple(row.keys()) != keyset:
        print('KEYSET_ASSERT=FAIL: %s vs %s' % (tuple(row.keys()), keyset))
        return 3
    out = raw.rstrip('\n') + '\n' + json.dumps(row, ensure_ascii=False) + '\n'
    open(os.path.join(ROOT, SINK), 'w', encoding='utf-8', newline='').write(out)
    back = open(os.path.join(ROOT, SINK), encoding='utf-8-sig', newline='').read()
    print('WRITE_READBACK=%s' % ('OK' if back == out else 'MISMATCH'))
    if back != out:
        return 2
    n = len([x for x in back.strip().split('\n') if x.strip()])
    ok = all(isinstance(json.loads(x), dict) for x in back.strip().split('\n') if x.strip())
    print('READBACK_PARSE=%s (%d 行)' % ('OK' if ok else 'FAIL', n))
    print('APPENDED round=EXP1-Q32 ts=%s' % ts)
    return 0


if __name__ == '__main__':
    sys.exit(main())
