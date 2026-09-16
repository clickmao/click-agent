#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q30 · 把 scratch 面里的长读/长日志**摘成入库小结** (证据面在仓库内, 原始 trace 不入库)。

产出:
  · eval/capability/exp1-q30/full_face_trace_probe_q30.json —— 全量面 trace 体量探针读数 + 阈值裁定依据
  · eval/capability/exp1-q30/verdict_q30_extra.json         —— 其余读数 (面别/闸门/提交态/守闸/形式门禁)
"""
import json
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=True).stdout.strip()
Q = os.path.join(ROOT, 'eval/capability/exp1-q30')
S = os.path.join(Q, 'scratch')


def jl(p):
    with open(p, encoding='utf-8-sig') as f:
        return json.load(f)


def main():
    probe = jl(os.path.join(S, 'full_face_probe.json'))
    rec = jl(os.path.join(ROOT, 'eval/capability/instruments-check.json'))
    pt = probe['side_effect_attribution']['trace']
    rt = rec['side_effect_attribution']['trace']
    out = {
        'round': 'EXP1-Q30',
        'why': '全量面在归因式副作用闸下自 Q22 引入后从未跑过; 首次 scoped 试跑 log_bytes 17.9MB > 旧 8MiB 上限 ⇒ capped ⇒ 弃权(rc=3), '
               '故先测体量再定阈值 (数据先行)。',
        'measured': {
            'scoped_3instruments_6commands_log_bytes': 17943199,
            'full_face_probe_47commands_log_bytes': pt['log_bytes'],
            'full_face_probe_capped': pt['capped'],
            'full_face_final_47commands_log_bytes': rt['log_bytes'],
            'full_face_final_capped': rt['capped'],
            'top_single_command_log_bytes': [8476012, 8475370, 7847820],
            'trace_dir_disk_usage_MB': 29,
        },
        'threshold_decision': {
            'old': {'LOG_SOFT_CAP': 8388608, 'LOG_HARD_CAP': 67108864},
            'new': {'LOG_SOFT_CAP': 67108864, 'LOG_HARD_CAP': 268435456},
            'rule': 'soft = 全量面实测 × ~2.2 余量 (为后续新增器具留空间); hard 作磁盘物理界, 越界语义不变 (capped ⇒ 弃权 rc=3)',
            'disk_context': '/tmp 余量 14GiB (df -h /tmp); 实测 trace 目录 29MB',
        },
        'face_final': {'rc': 0, 'passed': rec['passed'], 'total': rec['total'], 'schema': rec['schema'],
                       'face': rec['face'], 'self_effects': rec['side_effects'],
                       'manifest_sha12': rec['manifest_sha12'], 'instrument_sha12': rec['instrument_sha12'],
                       'conservation': rec['side_effect_attribution']['conservation']},
        'face_prev_committed': {'passed': 17, 'total': 18, 'schema': 'instruments-check/3',
                                'note': 'Q21 口径 (pre-gate, 无归因闸; P8 因集合差副作用判红: docs/improvements.md 等 4 路径)'},
    }
    p1 = os.path.join(Q, 'full_face_trace_probe_q30.json')
    open(p1, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1) + '\n')

    gate_log = os.path.join(S, 'formal_gate_q30.log')
    gate_lines = []
    if os.path.exists(gate_log):
        gate_lines = [l.strip() for l in open(gate_log, encoding='utf-8', errors='replace').read().splitlines() if l.strip()]
    sg = subprocess.run(['python3', 'eval/capability/exp1-q30/stage_guard_q30.py', '--selftest'], cwd=ROOT,
                        capture_output=True, text=True)
    extra = {
        'round': 'EXP1-Q30',
        'face_partition': {'full_face_sha12_before_nc': jl(os.path.join(Q, 'verdict_q30_face_partition.json'))['readings']['full_sha12_before'],
                           'nc_old_instrument_clobber': jl(os.path.join(Q, 'verdict_q30_face_partition.json'))['readings']['nc_old'],
                           'scoped_face': jl(os.path.join(Q, 'verdict_q30_face_partition.json'))['readings']['scoped']},
        'committed_state_check': {'probe': 'COMMITTED_STATE_CHECK=OK (rows=157 claims=189 blobs=163)',
                                  'nc_inject_unpinned_drift': 'NC_DETECTED'},
        'repin_readings': {'r444.instrument-acceptance': {'artifact_sha12': ['f956daa6eda1', '099682f1c227'],
                                                          'instrument_sha12': ['0370be98b442', '13f8872cb070'],
                                                          'audited_by_round': ['R478', 'EXP1-Q30']},
                           'r476.evidence-binding-round-param': {'artifact_sha12': ['5127b5c0592b', '8613fc2468c6'],
                                                                 'instrument_sha12': ['5127b5c0592b', '8613fc2468c6'],
                                                                 'audited_by_round': ['EXP1-Q29', 'EXP1-Q30']},
                           'basis': 'PIN_BASIS=file-bytes (未提交态; 提交后该字节即冻结态) —— 块级写路径; '
                                    '--only 的 derive 读 git 状态 ⇒ 未提交文件结构性只能派生成 live/worktree-only'},
        'stage_guard': {'selftest_rc': sg.returncode,
                        'selftest_tail': sg.stdout.strip().splitlines()[-3:]},
        'formal_gate': {'exit_line': [l for l in gate_lines if l.startswith('GATE_EXIT')],
                        'summary_lines': [l for l in gate_lines if 'Passed!' in l or 'Failed!' in l or 'Passed:' in l
                                          or 'Failed:' in l][:4]},
        'evidence_degradation_repaired': {
            'path': 'eval/capability/exp1-q28/whitelist_coverage_q28.json',
            'cause': '新增器具 exp1q28.whitelist-coverage 的默认 --out 指向冻结的 Q28 证据 ⇒ 全量面跑一次就改写它 '
                     '(与 Q17 同族: 「器具默认 --out 指向轮次证据」)',
            'observed_diff': 'stdout_bytes 7395→7390, clock_tokens (instant) 47→46 (该器具输出本身非逐字节确定)',
            'fix': '器具行显式 --out 到 scratch 面; 被改写文件已按 HEAD blob 还原 (sha e1e51aa9f07f 复原)',
        },
    }
    p2 = os.path.join(Q, 'verdict_q30_extra.json')
    open(p2, 'w', encoding='utf-8').write(json.dumps(extra, ensure_ascii=False, indent=1) + '\n')
    print('WROTE', os.path.relpath(p1, ROOT))
    print('WROTE', os.path.relpath(p2, ROOT))
    print('formal_gate:', extra['formal_gate'])


if __name__ == '__main__':
    sys.exit(main())
