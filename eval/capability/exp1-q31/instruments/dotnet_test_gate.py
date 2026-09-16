#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q31 · C1裁定②: 外部测试面包装器 —— 把「dotnet test + 过滤表达式」变成仓库内可复现器具。

动机: 若干 L4 行的 evidence_cmd 是**裸 dotnet test 命令行** (无仓库内器具可派生), 且退出码语义混
      为一谈 —— `dotnet test` 对「测试红」与「编译/环境失败」都给 rc=1, 而「测量/环境失败不得冒充
      断言失败」是既有铁律 (跑测脚本结论须由显式标记决定, 分类退出码不同码)。

判据 (退出码分类, fail-closed):
  0 = 全绿 (Passed! / Failed: 0)
  2 = 断言失败 (存在 Failed: N>0 或测试结果区报红)
  3 = 环境/测量失败 (dotnet 缺失 / 构建错 (error CS*, Build FAILED) / 超时 / 日志为空 / 自相矛盾)
自相矛盾 (rc=0 而日志含 Failed: N>0) 判 2 (fail-closed, 不放行)。

用法:
  python3 eval/capability/exp1-q31/instruments/dotnet_test_gate.py --filter FQN~X --label r420
  python3 eval/capability/exp1-q31/instruments/dotnet_test_gate.py --filter ... --dry-run   # 只打印解析命令
  python3 eval/capability/exp1-q31/instruments/dotnet_test_gate.py --selftest               # 分类器夹具

纪律: 判定只读 `DOTNET_GATE_EXIT=<码>` 显式标记; 日志物理上限 8 MiB (管道截断, 防失控放大)。
"""
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip() or os.getcwd()
LOG_DIR = os.path.join(ROOT, 'eval/capability/exp1-q31/logs')
LOG_CAP = 8 * 1024 * 1024
PROJ = 'src/agent.tests/agentframework.tests.csproj'
UNSET = ['AGENTFRAMEWORK_PY_RUN', 'AGENTFRAMEWORK_ARTIFACT_REPAIR']


def classify(rc, log):
    """纯函数: (进程退出码, 日志文本) -> (分类, 退出码)。禁「末条命令退出码决定成败」。"""
    if rc is None:
        return 'timeout', 3
    if not (log or '').strip():
        return 'empty_log', 3
    m = re.search(r'Failed:\s*(\d+)', log)
    n_failed = int(m.group(1)) if m else None
    if re.search(r'error [A-Z]{2}\d+|Build FAILED|MSB\d{4}', log):
        return 'build_or_env_error', 3
    if n_failed is not None and n_failed > 0:
        return 'assert_fail', 2
    if rc != 0:
        return 'nonzero_unknown', 3
    if 'Passed!' in log or (n_failed == 0):
        return 'pass', 0
    return 'no_verdict_marker', 3


FIXTURES = [
    ('green', 0, 'Passed!  - Failed:     0, Passed:    14, Skipped:     0, Total:    14', 0),
    ('red_tests', 1, 'Failed!  - Failed:     2, Passed:    12, Skipped:     0, Total:    14', 2),
    ('build_error', 1, 'src/agent/x.cs(3,5): error CS1002: ; expected\nBuild FAILED.', 3),
    ('empty_log', 1, '', 3),
    ('timeout', None, 'partial...', 3),
    ('contradiction_rc0_but_failed', 0, 'Failed!  - Failed:     1, Passed:    13, Total: 14', 2),
]


def selftest():
    bad = 0
    for name, rc, log, want in FIXTURES:
        got_cls, got = classify(rc, log)
        ok = (got == want)
        if not ok:
            bad += 1
        print('%-30s rc=%-5s expect=%-4d got=%-4d (%-18s) %s' % (name, rc, want, got, got_cls, 'OK' if ok else 'FAIL'))
    # 反证: 朴素口径「末条命令退出码」会把 build_error 判成 1 (无分类) ⇒ 与「测试红」不可分
    naive = 1 if classify(1, 'error CS1002') is not None else None
    print('NC_naive_exitcode_rule_confuses_build_and_test=%s (期望 True: 两者退出码同为 1)'
          % (classify(1, 'error CS1002')[1] != classify(1, 'Failed: 1')[1]))
    if classify(1, 'error CS1002')[1] == classify(1, 'Failed: 1')[1]:
        print('NC_SETUP_FAIL: 分类未把编译错与测试红分开')
        bad += 1
    print('SELFTEST %s (%d/%d)' % ('PASS' if bad == 0 else 'FAIL', len(FIXTURES) - bad, len(FIXTURES)))
    return 0 if bad == 0 else 2


def argval(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def main():
    if '--selftest' in sys.argv:
        return selftest()
    flt = argval('--filter')
    if not flt:
        print('ENV_FAIL: 缺 --filter')
        return 3
    label = argval('--label', 'gate')
    cfg = argval('--config')
    timeout = int(argval('--timeout', '900'))
    log_path = argval('--log') or os.path.join(LOG_DIR, '%s.log' % label)
    cmd = ['dotnet', 'test', PROJ]
    if cfg:
        cmd += ['-c', cfg]
    cmd += ['--filter', flt, '--nologo', '-v', 'q']
    env_cmd = ['env'] + sum([['-u', v] for v in UNSET], []) + cmd if shutil.which('env') else cmd
    print('GATE_CMD %s' % ' '.join(env_cmd))
    if '--dry-run' in sys.argv:
        print('DRY_RUN=OK (未执行)')
        return 0
    if not shutil.which('dotnet'):
        print('DOTNET_GATE_EXIT=3\nGATE_CLASS=dotnet_missing')
        return 3
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    t0 = time.time()
    with open(log_path, 'wb') as lf:
        try:
            p = subprocess.run(env_cmd, cwd=ROOT, stdout=lf, stderr=subprocess.STDOUT,
                               timeout=timeout, check=False)
            rc = p.returncode
        except subprocess.TimeoutExpired:
            rc = None
    dur = time.time() - t0
    raw = open(log_path, 'rb').read()
    if len(raw) > LOG_CAP:
        raw = raw[:LOG_CAP]
        open(log_path, 'wb').write(raw)
        print('GATE_LOG_CAPPED (物理上限 %d B)' % LOG_CAP)
    log = raw.decode('utf-8', 'replace')
    cls, out = classify(rc, log)
    print('GATE label=%s rc=%s dur=%.1fs log_bytes=%d log=%s'
          % (label, rc, dur, len(raw), os.path.relpath(log_path, ROOT)))
    for line in [l for l in log.splitlines() if 'Failed:' in l or 'error CS' in l][:3]:
        print('  %s' % line.strip()[:160])
    print('GATE_CLASS=%s' % cls)
    print('DOTNET_GATE_EXIT=%d' % out)
    return out


if __name__ == '__main__':
    sys.exit(main())
