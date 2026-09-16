#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q41 · 提交面**报文**(非判红): 把冻结证据漂移 (`FROZEN_EVIDENCE_DRIFT`) 从
「只在失败分支里被 tail -5 带出」提升为**提交时可见**的一等信息。

读数依据 (EXP1-Q41 H6): 干净态下 bind_evidence --check 输出里
  `FROZEN_EVIDENCE_DRIFT=0` 汇总行**恒打**(1 行), 明细行 (`  FROZEN_DRIFT ...`) 只在漂移时出现。
⇒ 本件选择「**漂移为 0 时零输出**」: 干净提交**零噪声**, 漂移时逐条可见。

判据: 报文**永不**改变提交结论 (恒 exit 0); 汇总行缺失 ⇒ exit 3 (环境不可判, 调用方不得据此放行/拦截)。
"""
import argparse
import pathlib
import re
import sys

MARK = 'FROZEN_EVIDENCE_DRIFT='
DETAIL = 'FROZEN_DRIFT '


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--log', required=True)
    ap.add_argument('--max-detail', type=int, default=10)
    a = ap.parse_args()

    p = pathlib.Path(a.log)
    if not p.is_file():
        sys.stderr.write('NOTICE: 日志不可读 %s ⇒ 不可判\n' % a.log)
        return 3
    txt = p.read_text(encoding='utf-8', errors='replace')     # 遥测/日志按容错读 (真缺陷 70 同族)
    m = re.search(re.escape(MARK) + r'(\d+)', txt)
    if not m:
        sys.stderr.write('NOTICE: 日志内无 %s 汇总行 ⇒ 不可判 (不静默当 0)\n' % MARK)
        return 3
    n = int(m.group(1))
    if n == 0:
        return 0                                               # 干净态: 零输出 = 零噪声
    details = [ln.strip() for ln in txt.splitlines() if DETAIL in ln]
    sys.stderr.write('NOTICE(EXP1-Q41 冻结证据漂移): %s%d (归档自洽 ∧ 工作区漂移; 可见项, 不判红)\n'
                     % (MARK, n))
    for ln in details[:a.max_detail]:
        sys.stderr.write('  %s\n' % ln)
    return 0


if __name__ == '__main__':
    sys.exit(main())
