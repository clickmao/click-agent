#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q19 · exp1q18.rebuild-constructor 的机械负控 (外部可调用的缺陷注入)。

注入缺陷: 把**源文件副本**的版本常量改成一个非预期值 ⇒ 重建器必须 FATAL (rc!=0) 且**不产出**目标。
纪律: 一切替换串**由源文件自身派生** (正则锚点定位 + 同形字面量), 不手打长字面量;
      全部动作发生在 mktemp 临时树内, 不触碰仓库语料 (可重复运行, 幂等)。

退出码语义 (与 registry 的 nc_expect='detect:NC_OK' 配套):
  0 = NC_OK   缺陷被抓 (重建器 fail-closed)
  1 = NC_FAIL 没抓到 ⇒ 器具空心, 该行不得进 L2
  2 = NC_INVALID 锚点失效 ⇒ 弃权 (仪器问题, 不是被测问题)
"""
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path('/home/agentuser/AgentFramework')
SRC = ROOT / 'eval/capability/exp1-q10/probe_v260.py'
BUILDER = ROOT / 'eval/capability/exp1-q18/build_q18_probe.py'


def main() -> int:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='q19nc_'))
    try:
        (tmp / 'eval/capability/exp1-q10').mkdir(parents=True, exist_ok=True)
        (tmp / 'eval/capability/exp1-q18').mkdir(parents=True, exist_ok=True)

        src = SRC.read_text(encoding='utf-8')
        m = re.search(r'^(PROBE_VERSION = )("[0-9.]+")$', src, re.M)
        if not m:
            print('NC_INVALID: version anchor not found')
            return 2
        old_lit = m.group(2)
        parts = old_lit.strip('"').split('.')
        new_lit = '"' + '.'.join('9' * len(p) for p in parts) + '"'   # 同形: 位数保持
        mut = src[:m.start(2)] + new_lit + src[m.end(2):]
        if mut.count(m.group(1) + new_lit) != 1 or mut == src:
            print('NC_INVALID: mutation not unique')
            return 2
        (tmp / 'eval/capability/exp1-q10/probe_v260.py').write_text(mut, encoding='utf-8')

        b = BUILDER.read_text(encoding='utf-8')
        b2, n = re.subn(re.escape(str(ROOT)), str(tmp), b)
        if n == 0:
            print('NC_INVALID: builder root literal not found')
            return 2
        (tmp / 'eval/capability/exp1-q18/build_q18_probe.py').write_text(b2, encoding='utf-8')

        p = subprocess.run([sys.executable, str(tmp / 'eval/capability/exp1-q18/build_q18_probe.py')],
                           capture_output=True, text=True, timeout=300)
        out = ((p.stdout or '') + (p.stderr or '')).strip()
        tail = out.splitlines()[-1][:140] if out else ''
        dst_exists = (tmp / 'eval/capability/exp1-q18/probe_v270.py').exists()
        caught = (p.returncode != 0) and ('FATAL' in out) and (not dst_exists)
        if caught:
            print(f'NC_OK: mutated source rejected rc={p.returncode} dst_written={dst_exists} | {tail}')
            return 0
        print(f'NC_FAIL: rc={p.returncode} dst_written={dst_exists} | {tail}')
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
