#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q42 · 轮次看板补行 (锚点插入 + 幂等 + 读回)。"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
BL = ROOT / 'docs/plans/v0.22.0-longterm-backlog.md'
ROW = ("| EXP1-Q42 | 尾 LF 闸**转正**的副作用收口 + `exp1q41.*` 能力登记 + 登记表**形态反解** | "
       "E5 过期期望刷新 ⇒ **11/11**; 前态负控 **5/5**; 登记表 **214→217** 行 (`bind_evidence --check` rc=0); "
       "`bind_evidence` 形态反解修复 (**登记通路复活**, numstat 80/5 而非整份重排); "
       "形式门禁 Failed **0** / Passed **14**; 真提交面 (4e50ba8) 拦截 **0**; 证据: "
       "`docs/plans/v0.22.0-exp1-local-index-and-code-graph.md` AN.10/AN.11 ∧ `eval/capability/exp1-q42/` | "
       "**完成** (M5 现场事件诚实结转) |\n")


def main():
    raw = BL.read_text(encoding='utf-8')
    if 'EXP1-Q42' in raw:
        print('BACKLOG=IDEMPOTENT (EXP1-Q42 行已存在)')
        return 0
    anchor = '| R370 | 确定性召回实测'
    if anchor not in raw:
        print('BACKLOG=ANCHOR_MISSING ⇒ fail-closed')
        return 3
    # 插到该表最后一行之后 (R370 行结束处)
    i = raw.index(anchor)
    j = raw.index('\n', i) + 1
    BL.write_text(raw[:j] + ROW + raw[j:], encoding='utf-8', newline='')
    back = BL.read_text(encoding='utf-8')
    ok = ('EXP1-Q42' in back) and back.endswith('\n') and back.count('EXP1-Q42') == 1
    print('BACKLOG=INSERTED readback=%s rows=%d' % ('OK' if ok else 'FAIL', back.count('| R')))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
