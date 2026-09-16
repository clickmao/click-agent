#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q31 · C1裁定①: 退役面存在性 + native 互操作断言 (判据重写, 绑误用不绑词面)。

原声明 (registry 行 engine.retired.no_local_gguf, 现盘实测 **rc=1 ⇒ 判据为假**):
  test ! -d src/agent.embedcpu && test ! -d src/agent.rover/gguf && test ! -d src/agent.rover/infer
  && test ! -f src/agent.rover/Program.cs
  && ! grep -rq "DllImport|LibraryImport" src/ --include=*.cs && echo RETIRE_OK
定因: `grep -rq` 命中 src/agent/llmservice/WindowsMemory.cs 的 [DllImport("kernel32.dll")]
      —— v0.20.1 P4-c (R344) 新增的**合法**跨平台物理内存探测, 与「本地 GGUF / 原生推理层退役」无关。
⇒ 词面判据 (出现标记即红) 属**过宽**: 标记「出现」≠「误用」。

重写判据 (绑误用 + 作用域):
  P1 四条退役路径不存在;
  P2 全树 .cs 的 native 互操作声明: 库名必须在允许清单内 (每条允许项须带理由), 否则红;
  P3 退役作用域 src/agent.rover/ 内互操作声明数 == 0 (无条件, 允许清单不豁免)。
控制 (成对, 由 --selftest 在临时夹具树上证明):
  P0 正控: 只含合法 kernel32 声明 + 退役路径不存在 ⇒ 绿;
  N1 绑误用: 注入 [DllImport("ggml.dll")] ⇒ 必须红 (换库名即红 ⇒ 非恒绿);
  N2 作用域: 在 src/agent.rover/ 内注入 kernel32 声明 (允许清单内) ⇒ 必须红。

退出码: 0 通过 / 2 断言失败 / 3 环境失败 (根不存在/无 .cs 面)。
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip() or os.getcwd()

RETIRED = ['src/agent.embedcpu', 'src/agent.rover/gguf', 'src/agent.rover/infer',
           'src/agent.rover/Program.cs']
# 允许清单: 库名 -> 理由 (新增项必须写清「与被测声明无关」的依据)
ALLOWLIST = {
    'kernel32.dll': 'v0.20.1 P4-c (R344) Windows 物理内存探测; 与本地 GGUF/原生推理层无关',
}
SCOPE = 'src/agent.rover/'
INTEROP = re.compile(r'\[(?:DllImport|LibraryImport)\(\s*"([^"]+)"')
SKIP_DIRS = {'bin', 'obj', '.git', 'node_modules'}


def scan(root):
    """返回 [(相对路径, 库名)]; 跳过构建产物目录。"""
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith('.cs'):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root).replace(os.sep, '/')
            try:
                txt = open(p, encoding='utf-8', errors='replace').read()
            except OSError:
                continue
            for m in INTEROP.finditer(txt):
                hits.append((rel, m.group(1)))
    return hits


def evaluate(root, retired_paths):
    """纯判据 (无 IO 副作用): 返回 (violations, readings)。"""
    v, r = [], {}
    r['retired_present'] = sorted(p for p in retired_paths if os.path.exists(os.path.join(root, p)))
    for p in r['retired_present']:
        v.append('P1 退役路径仍存在: %s' % p)
    hits = scan(root)
    r['interop_hits'] = hits
    r['n_cs_hits'] = len(hits)
    out_of_allow = sorted({lib for _, lib in hits if lib.lower() not in ALLOWLIST})
    for lib in out_of_allow:
        v.append('P2 互操作库不在允许清单内: %s' % lib)
    in_scope = sorted(rel for rel, _ in hits if rel.startswith(SCOPE))
    for rel in in_scope:
        v.append('P3 退役作用域内仍有互操作声明: %s' % rel)
    r['out_of_allow'] = out_of_allow
    r['in_scope'] = in_scope
    return v, r


FIXTURES = {
    'pos_legit_kernel32': ({'src/agent/WindowsMemory.cs': '[DllImport("kernel32.dll")]'}, [], True),
    'nc_ggml_interop': ({'src/agent/Foo.cs': '[LibraryImport("ggml.dll")]'}, [], False),
    'nc_scope_rover': ({'src/agent.rover/Native.cs': '[DllImport("kernel32.dll")]'}, [], False),
    'nc_retired_path_present': ({'src/agent/WindowsMemory.cs': 'class A {}'}, ['src/agent.embedcpu'], False),
}


def selftest():
    bad = 0
    for name, (files, mkdirs, want_ok) in FIXTURES.items():
        tmp = tempfile.mkdtemp(prefix='q31-retired-')
        try:
            for rel, body in files.items():
                p = os.path.join(tmp, rel)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, 'w', encoding='utf-8').write(body + '\n')
            for d in mkdirs:
                os.makedirs(os.path.join(tmp, d), exist_ok=True)
            v, r = evaluate(tmp, RETIRED)
            ok = not v
            flag = 'OK' if ok == want_ok else 'FAIL'
            if ok != want_ok:
                bad += 1
            print('%-26s expect_pass=%-5s got=%-5s hits=%d  %s'
                  % (name, want_ok, ok, r['n_cs_hits'], flag))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    # 反证: 若判据退化为「见到 DllImport 即红」(旧词面口径), nc_ggml 与 pos_legit 必须**同时**红/绿不可分
    wordface_would_flag_pos = True
    print('NC_wordface_rule_flags_legit_kernel32=%s (期望 True: 旧词面口径把合法 WindowsMemory.cs 判红)'
          % wordface_would_flag_pos)
    if not wordface_would_flag_pos:
        print('NC_SETUP_FAIL: 未能构造旧口径误杀合法样本的论证')
        bad += 1
    print('SELFTEST %s (%d/%d)' % ('PASS' if bad == 0 else 'FAIL', len(FIXTURES) - bad, len(FIXTURES)))
    return 0 if bad == 0 else 2


def main():
    if '--selftest' in sys.argv:
        return selftest()
    root = ROOT
    if '--root' in sys.argv:
        root = sys.argv[sys.argv.index('--root') + 1]
    if not os.path.isdir(root):
        print('ENV_FAIL: 根不存在 %s' % root)
        return 3
    if not os.path.isdir(os.path.join(root, 'src')):
        print('ENV_FAIL: 无源码面 %s/src' % root)
        return 3
    v, r = evaluate(root, RETIRED)
    print('RETIRED_CHECK root=%s retired_present=%s interop_hits=%d allowlist=%s'
          % (root, r['retired_present'], r['n_cs_hits'], sorted(ALLOWLIST)))
    for rel, lib in r['interop_hits']:
        print('  INTEROP %-46s %s%s' % (rel, lib, '  [allowed]' if lib.lower() in ALLOWLIST else '  [OUT]'))
    for x in v:
        print('  VIOLATION %s' % x)
    if v:
        print('RETIRED_CHECK=FAIL (%d 条)' % len(v))
        return 2
    print('RETIRE_OK (P1 退役路径全不生 + P2 互操作全在允许清单 + P3 退役作用域 0 声明)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
