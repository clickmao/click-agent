#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q40 · 候选④ 成对控制: 「尾 LF 契约纳入提交面自检, 默认关 (opt-in)」。

判据 (预注册见 eval/capability/exp1-q40/prereg_q40.json H8)：
  E1 合规件 ⇒ rc=0 (且源字段为 index/head/worktree 之一 —— 提交面取值方式可解释)。
  E2 违规件 ⇒ rc=2 且**逐件点名** ∧ 三型原因码各自出现 (tail 缺 LF / CRLF / BOM)。
  E3 不可解析的件 ⇒ rc=2 ∧ UNRESOLVED 计数 (不可判 = 拦, 不判绿)。
  E4 清单文件缺失 ⇒ rc=3 (环境不可判)。
  E5 提交面钩子 **默认关**: 同坏清单 ⇒ 放行 (rc=0, 零回归)。
  E6 打开 ⇒ 同态拦下 (rc=1 ∧ 报文含闸名)。
  E7 打开 + 合规清单 ⇒ rc=0。
  E8 真仓默认作用面 ⇒ rc=0 (零回归)。
  E9 代价实测: 闸单次耗时 (ms) + 钩子「开 − 关」增量 (ms)。

夹具纪律: 只读 + 只写 /tmp 与本件目录下的夹具; **不动 index** (不清空/不 add), 不跑真提交。
退出码: 0 全绿 / 2 判据红 / 3 弃权。
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True,
                                   text=True, check=True).stdout.strip())
GUARD = 'eval/capability/exp1-q31/instruments/tail_lf_guard.py'
HOOK = 'tools/hooks/pre-commit'
HERE = pathlib.Path(__file__).resolve().parent
FIX = HERE / 'fixtures'
SCRATCH = pathlib.Path('/tmp/q40_tail')


def sh(env_extra=None, argv=None, cwd=None, timeout=180):
    e = dict(os.environ)
    e.update(env_extra or {})
    t0 = time.perf_counter()
    p = subprocess.run(argv, cwd=str(cwd or ROOT), capture_output=True, text=True, env=e,
                       timeout=timeout)
    return p.returncode, (p.stdout or '') + (p.stderr or ''), (time.perf_counter() - t0) * 1000.0


def guard(targets=None):
    argv = ['python3', GUARD]
    if targets:
        argv += ['--targets', str(targets)]
    return sh(argv=argv)


def main():
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir(parents=True)
    FIX.mkdir(parents=True, exist_ok=True)

    rel = lambda p: str(p.relative_to(ROOT))
    good = FIX / 'tail_ok.txt';            good.write_bytes(b'canonical line\n')
    bad_lf = FIX / 'tail_missing.txt';     bad_lf.write_bytes(b'no trailing newline')
    bad_crlf = FIX / 'tail_crlf.txt';      bad_crlf.write_bytes(b'windows line\r\n')
    bad_bom = FIX / 'tail_bom.txt';        bad_bom.write_bytes(b'\xef\xbb\xbfbom body\n')
    missing = FIX / 'tail_absent.txt'
    if missing.exists():
        missing.unlink()

    list_ok = SCRATCH / 'list_ok.txt';  list_ok.write_text(rel(good) + '\n', encoding='utf-8')
    list_bad = SCRATCH / 'list_bad.txt'
    list_bad.write_text('\n'.join([rel(good), rel(bad_lf), rel(bad_crlf), rel(bad_bom)]) + '\n',
                        encoding='utf-8')
    list_unres = SCRATCH / 'list_unres.txt'; list_unres.write_text(rel(missing) + '\n', encoding='utf-8')

    checks, detail = {}, {}

    # E1 / E2 / E3 / E4
    rc1, o1, ms1 = guard(list_ok)
    detail['E1'] = {'rc': rc1, 'line': [l for l in o1.splitlines() if l.startswith('TAIL_LF_GUARD ')],
                    'ms': round(ms1, 1)}
    checks['E1_canonical_passes'] = (rc1 == 0 and 'TAIL_LF_GUARD=OK' in o1)

    rc2, o2, _ = guard(list_bad)
    detail['E2'] = {'rc': rc2, 'violations': [l.strip() for l in o2.splitlines()
                                              if l.strip().startswith('VIOLATION')]}
    reasons = {l.split('why=')[1].split()[0] for l in o2.splitlines() if 'why=' in l}
    checks['E2_three_defect_kinds_named'] = (rc2 == 2 and {'tail_lf_missing', 'crlf_present',
                                                           'bom_present'} <= reasons
                                             and sum(1 for l in o2.splitlines()
                                                     if l.strip().startswith('VIOLATION')) == 3)
    checks['E2_canonical_file_not_named'] = (rel(good) not in o2)

    rc3, o3, _ = guard(list_unres)
    detail['E3'] = {'rc': rc3, 'line': [l for l in o3.splitlines() if 'UNRESOLVED' in l]}
    checks['E3_unresolved_is_blocked_not_green'] = (rc3 == 2 and 'TAIL_LF_GUARD_UNRESOLVED=1' in o3)

    rc4, o4, _ = guard(SCRATCH / 'no_such_list.txt')
    detail['E4'] = {'rc': rc4}
    checks['E4_missing_list_abstains'] = (rc4 == 3)

    # E5 / E6 / E7 提交面钩子 (只读闸; 其余闸关掉以免混入无关因)
    base = {'AGENTFRAMEWORK_DECL_SWEEP': '0', 'AGENTFRAMEWORK_EVIDENCE_CHECK': '0'}
    rc5, o5, ms5 = sh({**base, 'AGENTFRAMEWORK_TAIL_LF_TARGETS': str(list_bad)},
                      argv=['bash', HOOK])
    detail['E5'] = {'rc': rc5, 'tail': o5.strip().splitlines()[-2:], 'ms': round(ms5, 1)}
    checks['E5_hook_default_off_passes_bad_list'] = (rc5 == 0
                                                     and 'BLOCKED(EXP1-Q40' not in o5)
    rc6, o6, ms6 = sh({**base, 'AGENTFRAMEWORK_TAIL_LF_GUARD': '1',
                       'AGENTFRAMEWORK_TAIL_LF_TARGETS': str(list_bad)}, argv=['bash', HOOK])
    detail['E6'] = {'rc': rc6, 'blocked': 'BLOCKED(EXP1-Q40 尾 LF 契约闸)' in o6, 'ms': round(ms6, 1)}
    checks['E6_hook_opt_in_blocks_bad_list'] = (rc6 == 1
                                                and 'BLOCKED(EXP1-Q40 尾 LF 契约闸)' in o6)
    rc7, o7, ms7 = sh({**base, 'AGENTFRAMEWORK_TAIL_LF_GUARD': '1',
                       'AGENTFRAMEWORK_TAIL_LF_TARGETS': str(list_ok)}, argv=['bash', HOOK])
    detail['E7'] = {'rc': rc7, 'ms': round(ms7, 1)}
    checks['E7_hook_opt_in_passes_canonical'] = (rc7 == 0)

    # E8 真仓默认作用面
    rc8, o8, ms8 = guard(None)
    detail['E8'] = {'rc': rc8, 'line': [l for l in o8.splitlines() if l.startswith('TAIL_LF_GUARD ')],
                    'ms': round(ms8, 1)}
    checks['E8_real_repo_default_scope_green'] = (rc8 == 0 and 'violations=0' in o8)

    # E9 代价: 闸本身 (3 次中位) 与钩子增量
    samples = sorted(guard(None)[2] for _ in range(3))
    detail['E9'] = {'guard_ms_median': round(samples[1], 1), 'guard_ms_samples': [round(x, 1) for x in samples],
                    'hook_off_ms': round(ms5, 1), 'hook_on_ms': round(ms6, 1),
                    'hook_delta_ms': round(ms6 - ms5, 1),
                    'note': ('「提交时修」的成本 = 0 (闸只读); 「拦下」的代价 = 一次重提交。'
                             '闸本身耗时见 guard_ms_median')}
    checks['E9_cost_measured'] = (samples[1] < 5000 and ms6 - ms5 < 8000)

    ok = all(checks.values())
    payload = {'round': 'EXP1-Q40', 'schema': 'selftest-q40-taillf/1',
               'prereg': 'eval/capability/exp1-q40/prereg_q40.json',
               'fixtures': [rel(good), rel(bad_lf), rel(bad_crlf), rel(bad_bom), rel(missing)],
               'checks': checks, 'detail': detail, 'verdict': 'PASS' if ok else 'FAIL'}
    out = HERE / 'selftest_q40_taillf.json'
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for k in sorted(checks):
        print('%-52s %s' % (k, 'PASS' if checks[k] else 'FAIL'))
    print('VERDICT=%s out=%s' % (payload['verdict'], out))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
