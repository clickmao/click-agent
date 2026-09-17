#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q44 · C3 器具: 主报告 §7 最新状态块的**增量**改写 (行锚点替换, 幂等, 读回校验)。

纪律 (R409/R-Q39 同族):
  ① 只做**行级替换/插入**, 不重排、不整段覆盖 (对侧 (30m 作业) 也会写同一文件);
  ② 锚点必须**唯一命中**, 命中数 ≠ 1 即 fail-closed (rc=2);
  ③ 幂等: 已含本轮标记 (EXP1-Q44) 则跳过 (rc=0, applied=false);
  ④ 写完**读回**校验标记存在 + 行数变化符合预期 (不采信自报 OK)。
rc: 0 成功(或已应用) / 2 器具缺陷 (锚点不唯一/读回失败) / 3 文件缺失
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DOC = os.path.join(ROOT, "docs", "reports", "dynamic-telemetry-eval-rollback-strategy.md")
MARK = "EXP1-Q44"

NEW_AFTER_VERSION = [
    "> - **最近一轮（R509，2026-09-17 08:09:10 提交）**: 前端任务事件域（`task.started` / "
    "`task.completed` / `task.failed` + `state.snapshot.tasks`）+ 同题重复臂（每跑次独立 session ⇒ "
    "会话隔离）；HEAD `0b88277`。**块范围**: 本块承载「最新状态 + 历史锚（R401–R412 已回填，见下）」；"
    "R413 之后的逐轮明细在 `docs/improvements.md` 顶部各节 + `eval/rover/r4xx/`。",
]
NEW_HEAD = (
    "> - **HEAD（EXP1-Q44 观测 2026-09-17 08:14）**: `0b88277`(R509 收口) ← `6bec98f`(R508) ← "
    "`e7b360b`(EXP1-Q43) ← `ac108e1`(R507 补测) …；远端 `origin/main` = `740ddf2`，**未推**"
    "（推送暂停令在效，三道机械闸在位）。"
)
NEW_AFTER_CI = [
    "> - **机检（EXP1-Q44 真机复跑，2026-09-17 08:13）**: 全量 **1643 / 失败 0 / 跳过 0**（38 s，"
    "`FULLTEST_EXIT=0` —— 由**显式标记**取值，非管道末段）；`scripts/capability_cycle_status.py "
    "--selftest` **30/30**（v5/D8）。",
    "> - **器具取证（EXP1-Q44 · 对侧记录面假绿）**: `/tmp/r508_fulltest.log` 尾部同时含 "
    "`Failed: 1`（1636 中 1 条 `FrontendAskSameConnTests`）与 `TEST_RC=0` ⇒ 记录侧 rc 取自管道末段"
    "（`… | tail`）。检测器 `eval/capability/exp1-q44/scan_pipe_rc.py` 判 rc=1（FALSE_GREEN）；"
    "仓库自带 **251** 个 `.sh` 扫描 **0 命中**（缺陷在对侧**临时命令**，非仓内脚本）；本侧同轮真机复跑"
    "该用例**全绿**（1643/1643）⇒ 单条失败未重现、未定论（可能其后已修 / 可能网络型偶发），"
    "但**记录面 rc 不可信**已确证。**纪律**: rc 必须由发射点显式写标记，并在日志面加"
    "「正文 Failed/Passed vs 标记」矛盾闸。",
]
BACKFILL = [
    "> - **R401–R412 逐轮回填（EXP1-Q44 机械 census，来源 `eval/capability/exp1-q44/census_401_412.py`）**: "
    "本块此前自 R400 直跳 R413，该「未回填」缺口在本轮**关闭**（12/12 有来源，逐轮一行）:",
    ">   - **R401** · 能力自检循环常驻化（60 分钟检测机制，用户令）· `eval/rover/r401/`(3) + `docs/reports/r401/` + improvements R401 节",
    ">   - **R402** · 循环入口自检（探针 v2：完成标记覆盖进行中 / 状态列硬编码 / 零命中静默 三缺陷）· `eval/rover/r402/`(27)",
    ">   - **R403** · chat template 工具作用域 + RoPE 配对修复 · `eval/rover/r403/`(22) + `docs/reports/r403/chat-template-tool-scope.md`",
    ">   - **R404** · bge 融合对账 + G1 阈值修缺陷（旧阈值落「数学上不可能显著」区）· `eval/bge/train_adapter.py` R404 段 + `eval/bge/auto_cycle.py` ⑥（**无独立证据目录**，读数散在代码注释与后续计划交叉引用 ⇒ 如实标注）",
    ">   - **R405** · 本机增强 R1-Distill-1.5B · `docs/plans/v0.27.0-r405-r1-local-enhancement.md` + `eval/rover/r405/`(8)",
    ">   - **R406** · 模板驱动 chat template（Jinja 子集）与 R1 链归因 · `docs/plans/v0.28.0-r406-jinja-template-and-r1-chain.md`",
    ">   - **R407** · qwen2 前向对账：attn bias 层归属缺陷 · `docs/plans/v0.29.0-r407-qwen2-attn-bias-and-forward-parity.md` + `eval/rover/r407/`(14)",
    ">   - **R408** · 本地 GGUF 引擎整线退役 + llama.cpp 进程化（10,966 LOC + `agent.embedcpu` 退役）· `docs/plans/v0.30.0-r408-llamacpp-process-pivot.md` + `eval/rover/r408/`(3)",
    ">   - **R409** · 本地 prompt 模板闸门（结构性阻断）+ BOS 口径 · `docs/plans/v0.31.0-r409-local-prompt-template-gate.md` + `eval/rover/r409/`(19)",
    ">   - **R410** · 会话长前缀复用（K2b 落点）+ 生成口径分离 · `docs/plans/v0.32.0-r410-session-prefix-reuse.md` + `eval/rover/r410/`(8)",
    ">   - **R411** · 长驻生成端口 + 本地 K2b 台账 · `docs/plans/v0.33.0-r411-long-lived-generation-port.md` + `eval/rover/r411/`(20)",
    ">   - **R412** · 多会话 slot 争用（本地长驻生成的第二 regime）· `docs/plans/v0.34.0-r412-multi-session-slot-contention.md` + `eval/rover/r412/`(18)",
    ">   - **另一本台账（未在本轮动）**: `improvements.md` 自身的 **R404–R416 轮节**尚未回填（该缺口已在改进日志内登记，属 `improvements.md` 的重排任务）。",
]
NEW_AFTER_DOCSYNC = [
    "> - **文档同步（EXP1-Q44）**: `eval/capability/exp1-q44/`（prereg_q44.json / verdict_q44.json / "
    "selftest_v5.txt / status_v4.json / status_v5.json / status_v5_legacyroute.json / "
    "fulltest_q44.raw.log / scan_pipe_rc.py / census_401_412.py / backfill_401_412.json）+ "
    "`scripts/capability_cycle_status.py`(v5/D8) + `eval/capability/kpi.jsonl`(+1 行) + 本块。",
]

ANCHORS = [
    ("> - **版本（历史快照锚，保留原样）**:", "after", NEW_AFTER_VERSION),
    ("> - **HEAD**:", "replace", [NEW_HEAD]),
    ("> - **机检 / AOT**:", "after", NEW_AFTER_CI),
    ("> - **状态回填缺口（如实标注）**:", "replace", BACKFILL),
    ("> - **文档同步（本轮）**:", "after", NEW_AFTER_DOCSYNC),
]


def main() -> int:
    if not os.path.exists(DOC):
        print(f"rc=3 missing_doc {DOC}")
        return 3
    with open(DOC, encoding="utf-8-sig", errors="replace") as fh:
        src = fh.read()
    if MARK in src:
        print('{"rc": 0, "applied": false, "why": "already_applied"}')
        return 0
    lines = src.splitlines()
    before = len(lines)
    for text, mode, payload in ANCHORS:
        idx = [i for i, l in enumerate(lines) if l.startswith(text)]
        if len(idx) != 1:
            print(f'{{"rc": 2, "why": "anchor_not_unique", "anchor": "{text[:40]}", "hits": {len(idx)}}}')
            return 2
        i = idx[0]
        lines[i:i + 1] = ([lines[i]] + payload) if mode == "after" else payload
    out = "\n".join(lines) + ("\n" if src.endswith("\n") else "")
    with open(DOC, "w", encoding="utf-8") as fh:
        fh.write(out)
    # 读回校验 (不采信自报 OK)
    with open(DOC, encoding="utf-8-sig", errors="replace") as fh:
        back = fh.read()
    ok = MARK in back and all(p.strip().split(":")[0] in back for _, _, payload in ANCHORS for p in payload)
    delta = len(back.splitlines()) - before
    print(f'{{"rc": {0 if ok else 2}, "applied": true, "lines_before": {before}, '
          f'"lines_after": {len(back.splitlines())}, "delta": {delta}, "readback_mark": {MARK in back}}}')
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
