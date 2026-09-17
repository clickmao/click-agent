#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""能力自检循环 · 状态探针 v3 (用户令 2026-09-14: 每 60 分钟检查「还有任务吗」)。

判据全部机械可复核 (不靠感觉):
  ① 计划看板 `docs/plans/v0.22.0-longterm-backlog.md` 中**状态列**含「进行中/未开始/待定/部分/欠」的行
     (轮次行 `R\d+` 与**计划项行** `exp\d+` 同等入账) ⇒ 未完成计划项; 每项附**其余格原文**供读者判沉积;
  ② 主报告 §7 **最新状态块**（`## 7.` 后第一段 `>` 引用块, 遇第二个块内标题即止）的全部 `**字段**` 原文
     ⇒ 逐条机械 hint（复用 OPEN_MARKERS + 缺口/未回填/未同步/待补/待裁决）+ **全字段原文入账由读者判**
     （与来源① other_cells 同口径; v4/D7 换口径: 旧版四条固定词面对当前版式零命中 ⇒ 主线最新状态不可见）;
  ③ 若 ① ② 皆空 ⇒ 输出 mode=selfcheck (运行「py 随机程序 + 随机数学难题」能力自检循环)。

输出: 单行 JSON (cron 注入用), 字段: mode / open_count / open_items / open_items_detail / sources / last_probe
退出码: 0 正常; 1 自检失败; 2 读取失败 (不静默)。

═══ v2 修复记录 (R402 步2 并行窗口 · 循环入口自检) ═══
本轮在「活跃用户会话占用 R402 步2」窗口内做**零冲突**推进: 只改本探针 (纯 stdlib, 不触发 dotnet build)。

D1 **(v1 主缺陷) 完成标记覆盖进行中标记**: v1 先按 `DONE_MARKERS` 过滤整行, 再看开放标记 ⇒
   状态列写成「接线已交付(R400)；解法级对比**进行中**」的行被当成已完成丢弃。实测后果: L8 表中
   R401/R402 两行 (均含「已交付」字样) 从 open_items 中消失, 探针只剩最后一行 R403 ⇒
   **循环会把「最前未完成项」判成最后一行**, 与计划文档自身路线 (R400→R401→R402→R403) 相反。
   修法: 开放标记优先于完成标记 (同格并存 ⇒ open), 且 `open_count==0` 与「行被完成标记吞掉」不再可混淆。
D2 **状态列位置硬编码 cells[2]**: 「轮次看板」表的状态列在第 4 格 (index 3) ⇒ 该表行全被读成非状态文本,
   永远不进 open_items。修法: 由**表头**定位「状态」列 (无表头则退回 cells[2] 并在 sources 里标注来源)。
D3 **零命中来源静默**: 来源② (主报告 §7 正则) 在当前报告版式下 0 命中, v1 无声无息 ⇒ 读者会以为
   「主报告没有未完成事项」。修法: `sources.master.format_matched=false` 显式入输出 (缺失≠为空)。
D4 **无自检**: v1 无 `--selftest` ⇒ 判定器自身不可信 (判定力未量化)。修法: `--selftest` 注入 7 例夹具 +
   **负控**: 同一夹具上跑 `--legacy` (v1 逻辑) 必须**判错** D1/D2 两例, 否则说明用例没有判别力。

═══ v3 修复记录 (R428-hold · 活跃体占用窗口内的零冲突推进, 2026-09-14) ═══
窗口: 30 分钟节拍作业 (9a97763d5fcd) 正于同一工作树内实现 R428 (未提交: `SessionHistorySearch.cs` +
      `SessionHistorySearchTests.cs`, mtime 18:14) ⇒ 本 tick **不碰产品源码 / 不跑 dotnet / 不占轮号**。
D5 **(结构性漏读) 计划项行不可见**: 行键硬编码 `^R\d+` ⇒ L3 表 (用户钦定「之前的 5 个开发计划的实施」)
   的行 (exp1/exp2/exp3/exp4/exp5/exp8) **永远读不到** ⇒ 探针只会报轮次看板里的历史轮行, 而轮次行
   标注的是「轮历史」不是「计划项」 ⇒ 「最前的未完成计划项」在机制上不可能被列出。实测 v2 输出:
   `open_items=[R371(进行中), R370(进行中)]` 两条**沉积行**, 而 6 条真计划项 0 条入账。
   修法: 行键扩为 `^(?:R\d+|exp\d+)`; 旧键保留为 `ROW_KEY_LEGACY` 供负控 A/B (旧键一并换 ⇒ 负控失去判别力)。
D6 **「核心已交付 + 自陈欠项」被判 closed**: exp5 行状态列 =「**核心已交付(R370)**：…；欠 域登记/前端通路」
   ⇒ 完成标记命中即 closed, 真实欠项被吞。修法: `欠` 入 `OPEN_MARKERS`, 并配**反面对照**用例
   (「已交付且无欠项」的计划行必须仍判 closed ⇒ 防「计划项一律 open」的空心判据)。

═══ v4 修复记录 (EXP1-Q43 · R508 活跃会话窗口内的零冲突推进, 2026-09-17) ═══
窗口: 同工作树内 R508 会话正跑全量 `dotnet test`(07:12 起, VBCSCompiler + MSBuild 节点在飞) ⇒ 本 tick
      不碰产品源码 / 不跑 dotnet / 不占主线轮号(R508)。
D7 **(来源②输入面覆盖 = 0: 主线最新状态对循环不可见)**: v3 的 MASTER_PAT 是四条**固定词面**(下轮候选/待确认/
   本轮待办/进行中), 而主报告 §7 的最新块早已换成另一种版式(`> ### ⏱ 最新状态` + `**主线**` / `**状态回填缺口**` /
   `**诚实边界**` 字段列表) ⇒ 真机 `sources.master = {hits:0, format_matched:false}` —— **来源②一个字符都没进输出**
   ⇒ mode 完全由来源①(v0.22.0 沉积行 R370/R371 + exp1..exp8) 决定, 与宪法级主线定义(铁律 10)方向错位。
   修法换**口径**而非再加词面: ① 块级定位(不依赖任何专有词面: `## 7.` 后第一段 `>` 引用块, 遇第二个块内标题即止);
   ② 块内**全部 `**字段**` 原文**入 `block_field_texts`, 由读者判(与来源① other_cells 同口径);
   ③ 机械 hint = 复用 OPEN_MARKERS + 缺口/未回填/未同步/待补/待裁决, 并加**否定围栏**(命中处前 20 字符含
   无/没有/不存在/未设/禁止/非 ⇒ 记 `neg_fenced` 不判 open —— 与 R299/R308b 同族, 防「凡含词面即 open」);
   ④ `block_found` / `block_fields` / `neg_fenced` / `legacy_form_hits` 入 diag ⇒ 「空」与「缺失」双向可区分。
   保留: `hits` / `format_matched` 字段语义不变(≥1 机械命中); 旧四条词面降为 `MASTER_PAT_LEGACY`, 仅用于负控 A/B。
   **预注册 P5 初版被实测否证**: 「legacy 在 T12 夹具上命中数 == 0」不成立 —— v3 实测形态是「漏真项(缺口)
   ∧ 错命中历史段(R900)」(假阴性 + 假阳性并存, 比零命中更坏)。处置 = N5 改判为**更强的成对陈述**
   (两条同时成立才算有判别力), 预注册原陈述与实测值单列 `checks_posthoc`(eval/capability/exp1-q43/
   verdict_q43.json); **未放宽任何既有断言**(T1–T11 / N1–N4 逐条原样)。

═══ v5 修复记录 (EXP1-Q44 · 主线 R509 提交后空闲窗口, 2026-09-17) ═══
窗口: 30m 节拍作业 (9a97763d5fcd) 于 08:09:10 提交 R509 后**空闲** ⇒ 本 tick 起手核过
      (无 .git/*.lock / 无 dotnet|run_*.sh 活体 / /tmp 最新非本侧产物 08:09) 后才跑真机全量测试。
D8 **(路由口径与权威源错位: 推进对象取自「看板沉积面」而非「最新状态块」)**: v4/D7 已让 §7 最新块的
   开放项**可见**(`open_items` 尾部), 但 `open_items[0]`(循环实际推进的第一项) 仍恒为看板行 ——
   实测: 看板首项 = `exp1`(计划项, 表内状态列写法早已沉积), 而权威恢复入口(主报告 §7「恢复迭代从
   这里开始」)在 v4 输出里**排在最后** ⇒ 「最前的未完成项」≠「当前主线的未完成项」, 循环每 tick 都
   先去推**沉积行**, 与宪法级主线定义(铁律 10)方向错位。
   修法(**纯增量, 不动既有字段**): 新增 `route = {primary, first, priority, rule, comparable_from}`
   —— `priority` = 权威源优先序 (`master:` 项在前, `backlog:` 项在后), `primary ∈ {master-block,
   backlog, selfcheck}`, 并写明该判决的**规则原文**。`mode`/`open_count`/`open_items` **逐字不变**
   (真机 A/B 机检, 见 eval/capability/exp1-q44/verdict_q44.json)。
   负控: `--legacy-route` 复现 v4 优先序(看板优先) ⇒ 同夹具上 primary 必为 `backlog`, 证明新优先序
   **有判别力**(不是「怎么改都绿」)。**可比性断点**: v5 起 `route.primary` 语义变更, 与 v4 及以前
   轮次的「推进对象」读数**不可直接相减**(`route.comparable_from` 字段显式登记)。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKLOG = os.path.join(ROOT, "docs", "plans", "v0.22.0-longterm-backlog.md")
MASTER = os.path.join(ROOT, "docs", "reports", "dynamic-telemetry-eval-rollback-strategy.md")
KPI = os.path.join(ROOT, "data", "probe", "kpi.jsonl")
SKILLS = os.path.join(ROOT, "skills")

DONE_MARKERS = ("已交付", "已完成", "已收口", "done", "DONE")
# v3/D6: 「欠」= 行内自陈的剩余项 (核心已交付 + 欠 X ⇒ 该行仍是 open)
OPEN_MARKERS = ("进行中", "未开始", "待定", "部分", "计划中", "欠")
ROW_KEY_LEGACY = re.compile(r"^R\d+")           # v2 及以前: 只认轮次行 (仅用于负控 A/B)
ROW_KEY = re.compile(r"^(?:R\d+|exp\d+)")       # v3/D5: 计划项行 (expN) 同等入账
PLAN_KEY = re.compile(r"^exp\d+")
SEP_CELL = re.compile(r":?-{2,}:?")
MASTER_PAT = re.compile(
    r"^\s*>?\s*[-*]?\s*\*\*(下轮候选|待确认|本轮待办|进行中)\*\*[:：]?\s*(.{0,120})", re.M
)
# v4/D7: 旧四条固定词面降为**负控专用**(证明新用例有判别力), 不再单独驱动来源②
MASTER_PAT_LEGACY = MASTER_PAT
# v4/D7: 机械 hint 词表 = 既有 OPEN_MARKERS + 状态块里实际使用的「欠项」类措辞
HINT_MARKERS = OPEN_MARKERS + ("缺口", "未回填", "未同步", "待补", "待裁决")
# v4/D7: 否定围栏 (R299/R308b 同族) —— 命中处前窗含否定标记 ⇒ 记 fenced, 不判 open
NEG_MARKERS = ("无任何", "不存在", "没有", "未设", "禁止", "无", "非")
NEG_WINDOW = 20
BLOCK_FIELD_MAX = 12


def _status_block(txt: str):
    """§7 内**最新状态块** = `## 7.` 之后第一段 `>` 引用块; 遇**第二个**块内标题即止(其后是历史快照)。

    块定位**不依赖任何专有词面** ⇒ 报告版式演进时不会静默失配(v4/D7 根因正是「靠固定词面找条目」)。
    """
    if "## 7." not in txt:
        return [], {"block_found": False, "block_why": "文档内无 `## 7.` 节"}
    lines = txt.split("## 7.", 1)[1].splitlines()
    start = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith(">"):
            start = i
            break
    if start is None:
        return [], {"block_found": False, "block_why": "§7 内无 `>` 引用块"}
    block, headings = [], 0
    for ln in lines[start:]:
        s = ln.strip()
        if not s:
            if block:
                break
            continue
        if not s.startswith(">"):
            break
        body = s.lstrip(">").strip()
        if body.startswith("#"):
            headings += 1
            if headings > 1:      # 第二个块内标题 ⇒ 历史快照段开始, 不含
                break
            block.append(body)
            continue
        block.append(body)
    fields = [b for b in block if "**" in b]
    return fields, {"block_found": bool(block), "block_lines": len(block), "block_fields": len(fields),
                    "block_why": ""}


def _negated(text: str, pos: int) -> bool:
    return any(m in text[max(0, pos - NEG_WINDOW):pos] for m in NEG_MARKERS)


def read_text(path: str) -> str:
    # 遥测/文档可能混入非 UTF-8 字节 (真缺陷 70) ⇒ 读端容错, 不让 decode 杀整轮
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        return fh.read()


def is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(SEP_CELL.fullmatch(c) or not c for c in cells)


def state_index(cells: list[str]):
    """表头里定位状态列; 返回 None 表示该表无状态列 (调用方退回 cells[2])。"""
    for i, c in enumerate(cells):
        if re.search(r"状态|进度", c):
            return i
    return None


def iter_tables(text: str):
    """把 markdown 拆成 (表头, 行) —— 空行/非表行结束当前表 (防跨表串读)。"""
    header: list[str] | None = None
    rows: list[list[str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            if header is not None:
                yield header, rows
                header, rows = None, []
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if is_separator(cells):
            continue
        if header is None:
            header = cells
            rows = []
        else:
            rows.append(cells)
    if header is not None:
        yield header, rows


def classify(status: str) -> str:
    """open 优先于 closed: 「进行中…已交付(R400)」是**未完成**, 不是已完成。"""
    opens = any(m in status for m in OPEN_MARKERS)
    dones = any(m in status for m in DONE_MARKERS)
    if opens:
        return "open"
    if dones:
        return "closed"
    return "unmarked"


def backlog_scan(path: str, legacy: bool = False):
    """→ (open_items, detail, diag)。legacy=True 复现 v1 逻辑 (仅用于负控 A/B)。"""
    if not os.path.exists(path):
        return None, None, None
    items, detail = [], []
    diag = {"rows_scanned": 0, "closed": 0, "unmarked": 0, "tables": 0, "state_col": {},
            "plan_rows_scanned": 0}
    key = ROW_KEY_LEGACY if legacy else ROW_KEY     # v3/D5: 负控跑旧键, 否则负控无判别力
    for header, rows in iter_tables(read_text(path)):
        idx = None if legacy else state_index(header)
        diag["tables"] += 1
        for cells in rows:
            if not cells or not key.match(cells[0]):
                continue
            diag["rows_scanned"] += 1
            if PLAN_KEY.match(cells[0]):
                diag["plan_rows_scanned"] += 1
            col = idx if (idx is not None and idx < len(cells)) else (2 if len(cells) > 2 else None)
            status = cells[col] if col is not None else ""
            diag["state_col"][cells[0]] = col
            if legacy:
                # v1/v2: 完成标记先过滤, 再看开放标记; 状态列恒为 cells[2]
                if any(m in status for m in DONE_MARKERS):
                    diag["closed"] += 1
                    continue
                if any(m in status for m in OPEN_MARKERS):
                    items.append(f"{cells[0]}: {status[:60]}")
                continue
            verdict = classify(status)
            if verdict == "open":
                items.append(f"{cells[0]}: {status[:60]}")
                detail.append({"item": cells[0], "status": status[:120], "state_col": col,
                               "kind": "plan-item" if PLAN_KEY.match(cells[0]) else "round",
                               "table": " | ".join(header)[:80],
                               # v3: 其余格原文 ⇒ 读者可自行判断「状态列说 open 是否沉积」。
                               # 不做机械裁定: 反例 R370 行产出格全 ✅ 但其 L4 是真实持续线 (机械判沉积会误杀)。
                               "other_cells": " | ".join(c for i, c in enumerate(cells) if i != col)[:220]})
            elif verdict == "closed":
                diag["closed"] += 1
            else:
                diag["unmarked"] += 1
    return items, detail, diag


def master_opens(path: str, legacy: bool = False):
    if not os.path.exists(path):
        return None, None
    txt = read_text(path)
    if legacy:
        # v3 逻辑**原样保留**: 仅用于负控 A/B (证明新增用例有判别力, 不是「怎么改都绿」)
        head = txt.split("## 7.")[-1][:4000]
        hits = [f"{m.group(1)}: {m.group(2).strip()}" for m in MASTER_PAT_LEGACY.finditer(head)]
        diag = {"hits": len(hits), "format_matched": bool(hits),
                "note": "" if hits else "该来源对当前报告版式零命中 ⇒ 视作「缺失」而非「无未完成事项」(v2 显式化)"}
        return hits[:8], diag

    fields, bdiag = _status_block(txt)
    hits, fenced = [], 0
    for f in fields:
        for marker in HINT_MARKERS:
            pos = f.find(marker)
            if pos < 0:
                continue
            if _negated(f, pos):          # 「说到但否定」⇒ 记 fenced, 不判 open (防凡含词面即 open)
                fenced += 1
                break
            hits.append(f[:160])
            break
    # 后向兼容: **最新块内**若仍用历史版式(`**下轮候选**:` 类)则入账; 同样过否定围栏。
    # 作用域=最新块(非 §7 全文) ⇒ 历史快照段的条目永不冒充「本轮未完成项」(与来源②块级口径一致)。
    block_text = "\n".join(fields)
    legacy_hits = []
    for m in MASTER_PAT_LEGACY.finditer(block_text):
        if _negated(block_text, m.start()):
            fenced += 1
            continue
        legacy_hits.append(f"{m.group(1)}: {m.group(2).strip()}")
    for h in legacy_hits:
        if h not in hits:
            hits.append(h)

    if hits:
        note = ""
    elif bdiag.get("block_found"):
        note = ("状态块已定位(block_fields=%d) 但机械词表零命中 ⇒ 「空」≠「缺失」可区分: 字段原文随 "
                "block_field_texts 入账, 由读者判 (与来源① other_cells 同口径)" % len(fields))
    else:
        note = "§7 内未定位到状态块 ⇒ 视作「缺失」而非「无未完成事项」(v2 显式化; v4 换口径)"

    diag = dict(bdiag)
    diag.update({
        "hits": len(hits),
        "open_matched": len(hits),
        "neg_fenced": fenced,
        "legacy_form_hits": len(legacy_hits),
        "block_field_texts": [f[:200] for f in fields[:BLOCK_FIELD_MAX]],
        "format_matched": bool(hits),     # 字段语义不变 (v2/D3: ≥1 机械命中)
        "note": note,
    })
    return hits[:8], diag


ROUTE_RULE = {
    "master-block": "推进主报告 §7 **最新块**的点名未完成项 (权威恢复入口; v5/D8 起优先)",
    "backlog": "推进计划看板最前未完成计划项 (块内无开放项时的回退)",
    "selfcheck": "两侧皆空 ⇒ 跑「py 随机程序 + 随机数学题」能力自检循环",
}
ROUTE_EPOCH = "v5/D8 (2026-09-17, EXP1-Q44)"


def decide_route(backlog_items: list[str], master_items: list[str], legacy_route: bool = False) -> dict:
    """v5/D8: 推进对象的优先序 = **权威源优先**。

    权威源 = 主报告 §7 最新状态块(其自述为「恢复迭代从这里开始」)= 「当前主线在做什么」;
    计划看板行是**沉积面**(状态列写法可长期不改)。v4 及以前按「看板在前」拼 items ⇒ 每 tick
    先去推沉积行, 与主线定义错位。`legacy_route=True` 复现 v4 优先序, 仅用于负控 A/B。
    """
    pairs = ([("master", i) for i in master_items] + [("backlog", i) for i in backlog_items]
             if not legacy_route else
             [("backlog", i) for i in backlog_items] + [("master", i) for i in master_items])
    primary = pairs[0][0] if pairs else "selfcheck"
    return {
        "primary": {"master": "master-block", "backlog": "backlog"}.get(primary, "selfcheck"),
        "first": pairs[0][1] if pairs else None,
        "priority": [f"{k}: {v}" for k, v in pairs],
        "rule": ROUTE_RULE[{"master": "master-block", "backlog": "backlog"}.get(primary, "selfcheck")],
        "legacy_route": legacy_route,
        "comparable_from": ROUTE_EPOCH,
    }


def last_probe(kpi_path: str):
    info = {"kpi_lines": 0, "last": None}
    if os.path.exists(kpi_path):
        lines = [l for l in read_text(kpi_path).splitlines() if l.strip()]
        info["kpi_lines"] = len(lines)
        if lines:
            try:
                info["last"] = json.loads(lines[-1])
            except Exception:  # noqa: BLE001  解析失败**可见**, 不静默
                info["last"] = {"parse_error": True}
    return info


def skills_count(path: str = SKILLS) -> int:
    if not os.path.isdir(path):
        return 0
    return sum(1 for d in os.listdir(path) if os.path.exists(os.path.join(path, d, "SKILL.md")))


def build_report(backlog_path: str, master_path: str, legacy: bool = False,
                 legacy_route: bool = False) -> tuple[dict, int]:
    b, bdetail, bdiag = backlog_scan(backlog_path, legacy=legacy)
    m, mdiag = master_opens(master_path, legacy=legacy)
    if b is None or m is None:
        return {"error": "docs 缺失", "backlog": backlog_path, "master": master_path}, 2
    items = b + m
    route = decide_route(b, m, legacy_route=legacy_route)
    out = {
        "mode": "tasks" if items else "selfcheck",
        "open_count": len(items),
        "open_items": items,
        "open_items_detail": bdetail,
        "route": route,
        "backlog_open": len(b),
        "master_open": len(m),
        "sources": {"backlog": bdiag, "master": mdiag, "legacy_logic": legacy},
        "kpi_lines": 0,
        "skills_count": 0,
        "rule": "mode=tasks ⇒ 推进计划项一步; mode=selfcheck ⇒ 跑 py 随机程序+随机数学题能力自检并沉淀通用性 skill",
        "rule_v5": "推进对象以 route.first 为准 (权威源优先: §7 最新块 > 计划看板); open_items 保留旧口径供对比",
    }
    return out, 0


# ─────────────────────────── 自检 (判定器必须自证可信) ───────────────────────────

FIXTURE_BACKLOG = """# fixture · 计划看板

| 阶段 | 内容 | 状态 | 证据指针 |
|---|---|---|---|
| R900 | 已完成项 | **已交付(R900)** | docs/x.md |
| R901 | 完成字样 + 进行中 (v1 主缺陷用例) | 接线已交付(R900)；解法级对比进行中 | docs/y.md |
| R902 | 全新项 | 未开始 | 待定 |
| R903 | 状态列无任何标记 | 。 | — |

## 轮次看板

| 轮 | 主题 | 产出 | 状态 |
|---|---|---|---|
| R910 | 状态列在第 4 格 (v1 硬编码缺陷用例) | 产出入账 + **已交付** | 进行中 |
| R911 | 该行真的完了 | 收尾 | **已交付** |

## fixture · L3 计划表 (v3/D5 用例: 计划项行 expN)

| 计划 | 文档 | 实施要点 | 状态 |
|---|---|---|---|
| exp1 夹具计划项 (未开始) | `x.md` | 待实施 | 未开始 |
| exp2 夹具计划项 (已交付, 无欠项) | `y.md` | 收尾 | **已交付(R1)** |
| exp3 夹具计划项 (核心已交付 + 自陈欠项) | `z.md` | 核心齐；欠 前端通路 | **核心已交付(R1)**：核心齐；欠 前端通路 |
"""

# ── v5/D8 夹具: 看板全闭合 (用于「块闭合 ⇒ route 回退」的成对判据) ──
FIXTURE_BACKLOG_CLOSED = """# fixture · 计划看板 (全闭合)

| 阶段 | 内容 | 状态 | 证据指针 |
|---|---|---|---|
| R900 | 已完成项 | **已交付(R900)** | docs/x.md |

| 计划 | 文档 | 实施要点 | 状态 |
|---|---|---|---|
| exp2 夹具计划项 (已交付, 无欠项) | `y.md` | 收尾 | **已交付(R1)** |
"""

FIXTURE_MASTER = """# fixture · 主报告

## 7. 迭代状态快照

> 本轮无任何 `**下轮候选**` 形式条目 (来源②应显式报 format_matched=false)。
"""

# ── v4/D7 夹具: 新形态状态块 (`> ### ⏱ 最新状态` + `**字段**` 列表) = 真机版式 ──
FIXTURE_MASTER_NEW_OPEN = """# fixture · 主报告

## 7. 迭代状态快照

> ### ⏱ 最新状态（先读这里）
>
> - **主线**: 外部真值对照自检（宪法级）。
> - **状态回填缺口（如实标注）**: R401–R412 逐轮条目未回填；补齐属文档轮任务。
> - **机检**: 全绿。
>
> ### 🗂 历史快照（保留以追溯）
>
> - **下轮候选**: R900 旧形态候选（属历史快照段, 不得混入最新块）
"""

FIXTURE_MASTER_NEW_CLOSED = """# fixture · 主报告

## 7. 迭代状态快照

> ### ⏱ 最新状态
>
> - **版本**: v9.9.9 · 全部已交付。
> - **机检**: 全绿, 零残留。
"""

FIXTURE_MASTER_NEW_NEG = """# fixture · 主报告

## 7. 迭代状态快照

> ### ⏱ 最新状态
>
> - **本轮无任何**「进行中」条目, 也不存在「待定」项。
"""

FIXTURE_MASTER_NO_BLOCK = """# fixture · 主报告

## 7. 迭代状态快照

最新状态：纯文本形态（本 fixture 无 `>` 引用块）。
"""

FIXTURE_MASTER_LEGACY_FORM = """# fixture · 主报告

## 7. 迭代状态快照

> - **下轮候选**: R901 历史版式仍须入账（后向兼容用例）。
"""


def selftest() -> int:
    """判定器自检 (夹具 + 负控; 旧逻辑必须判错, 否则用例无判别力)。

    v1–v4: T1–T11 + N1–N4; v4/D7: T12–T17 + N5–N7; v5/D8: T18–T22 + N8 —— 共 30 条断言。
    """
    tmp = tempfile.mkdtemp(prefix="ccstatus-selftest-")
    bl = os.path.join(tmp, "backlog.md")
    ms = os.path.join(tmp, "master.md")
    with open(bl, "w", encoding="utf-8") as fh:
        fh.write(FIXTURE_BACKLOG)
    with open(ms, "w", encoding="utf-8") as fh:
        fh.write(FIXTURE_MASTER)

    new, code = build_report(bl, ms)
    old, _ = build_report(bl, ms, legacy=True)
    checks, fails = [], 0

    def chk(name, cond, got):
        nonlocal fails
        checks.append((name, bool(cond), got))
        if not cond:
            fails += 1

    chk("T1 完成项判 closed", not any(i.startswith("R900") for i in new["open_items"]), new["open_items"])
    chk("T2 完成字样+进行中 ⇒ open (D1 修)",
        any(i.startswith("R901") for i in new["open_items"]), new["open_items"])
    chk("T3 未开始 ⇒ open", any(i.startswith("R902") for i in new["open_items"]), new["open_items"])
    chk("T4 无标记行计入 unmarked 可见 (非静默丢弃)",
        new["sources"]["backlog"]["unmarked"] == 1, new["sources"]["backlog"])
    chk("T5 状态列由表头定位 ⇒ 第 4 格行被读出 (D2 修)",
        any(i.startswith("R910") for i in new["open_items"]), new["open_items"])
    chk("T6 零命中来源显式报 format_matched=false (D3 修)",
        new["sources"]["master"]["format_matched"] is False, new["sources"]["master"])
    # ── 负控: v1 逻辑必须在这两例上判错, 证明用例有判别力 (不是「怎么改都绿」)
    chk("N1 负控: v1 逻辑漏掉 R901 (证明 T2 有判别力)",
        not any(i.startswith("R901") for i in old["open_items"]), old["open_items"])
    chk("N2 负控: v1 逻辑漏掉 R910 (证明 T5 有判别力)",
        not any(i.startswith("R910") for i in old["open_items"]), old["open_items"])
    # ── v3/D5/D6 用例 + 负控 (旧键 `^R\d+` 与旧分类都必须判错, 否则用例无判别力)
    chk("T7 计划项行 (expN) 入账 (D5 修)",
        any(i.startswith("exp1") for i in new["open_items"]), new["open_items"])
    chk("T8 kind 判别: 轮次行不得被标成计划项",
        all(d.get("kind") == "round" for d in new["open_items_detail"]
            if re.match(r"^R\d+", d["item"])), [d.get("kind") for d in new["open_items_detail"]])
    chk("T9 「核心已交付 + 自陈欠项」计划行仍判 open (D6 修)",
        any(i.startswith("exp3") for i in new["open_items"]), new["open_items"])
    chk("T10 反面对照: 「已交付且无欠项」的计划行必须 closed (防「计划项一律 open」空心判据)",
        not any(i.startswith("exp2") for i in new["open_items"]), new["open_items"])
    chk("T11 其余格原文随 open 项入账 (沉积由读者判, 不做机械裁定)",
        bool(new["open_items_detail"]) and all(
            d.get("other_cells") is not None for d in new["open_items_detail"]),
        {d["item"]: (d.get("other_cells") or "")[:36] for d in new["open_items_detail"]})
    chk("N3 负控: 旧行键漏掉 exp1 (证明 T7 有判别力)",
        not any(i.startswith("exp1") for i in old["open_items"]), old["open_items"])
    chk("N4 负控: 旧分类把 exp3 判 closed (证明 T9 有判别力)",
        not any(i.startswith("exp3") for i in old["open_items"]), old["open_items"])

    # ── v4/D7 用例: 新形态状态块 (旧四条词面对当前版式零命中 = 真机 D7 复现; R508 窗口内零冲突) ──
    def _w(name, text):
        p = os.path.join(tmp, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return p

    bl2 = _w("bl2.md", FIXTURE_BACKLOG)
    mp_new = _w("m_new_open.md", FIXTURE_MASTER_NEW_OPEN)
    o_new, _ = build_report(bl2, mp_new)
    o_new_legacy, _ = build_report(bl2, mp_new, legacy=True)
    o_closed, _ = build_report(bl2, _w("m_new_closed.md", FIXTURE_MASTER_NEW_CLOSED))
    o_neg, _ = build_report(bl2, _w("m_new_neg.md", FIXTURE_MASTER_NEW_NEG))
    o_noblock, _ = build_report(bl2, _w("m_noblock.md", FIXTURE_MASTER_NO_BLOCK))
    o_legacyform, _ = build_report(bl2, _w("m_legacy_form.md", FIXTURE_MASTER_LEGACY_FORM))

    def m_items(r):
        return [i for i in r["open_items"] if not re.match(r"^(?:R\d+|exp\d+)", i)]

    chk("T12 新形态状态块内的开放项被机械捕获 (D7 修)",
        any("缺口" in i for i in m_items(o_new)), m_items(o_new))
    chk("T13 「块在 + 全闭合」⇒ 0 开放项 ∧ block_found=true (「空」≠「缺失」)",
        (not m_items(o_closed)) and o_closed["sources"]["master"]["block_found"] is True,
        o_closed["sources"]["master"])
    chk("T14 「§7 内无 `>` 块」⇒ block_found=false ∧ format_matched=false (缺失)",
        o_noblock["sources"]["master"]["block_found"] is False
        and o_noblock["sources"]["master"]["format_matched"] is False,
        o_noblock["sources"]["master"])
    chk("T15 块边界: 历史快照段条目不得混入最新块",
        not any("R900" in t for t in o_new["sources"]["master"]["block_field_texts"]),
        o_new["sources"]["master"]["block_field_texts"])
    chk("T16 历史版式(`**下轮候选**:`)后向兼容仍入账 (作用域=最新块)",
        any("R901" in i for i in m_items(o_legacyform)), m_items(o_legacyform))
    chk("T17 全字段原文入账 (读数可见, 不靠词面) ≥3 条",
        len(o_new["sources"]["master"]["block_field_texts"]) >= 3,
        o_new["sources"]["master"]["block_field_texts"])
    # ── v4 负控 (旧逻辑必须判错; 反空心必须不误判)
    # 预注册 P5 初版陈述「legacy 在 T12 夹具上命中数 == 0」被**实测否证**: v3 的真实形态是
    # 「漏真项(缺口) ∧ 错命中历史段(R900)」——比「零命中」更坏(既是假阴性又是假阳性)。
    # 修正为**更强**的成对陈述(不是放宽断言); 预注册原陈述作 checks_posthoc 单列见 verdict_q43.json。
    chk("N5 负控: v3 在 T12 夹具上既漏真项(缺口)又错命中历史段(R900) ⇒ 证明 T12 有判别力",
        (not any("缺口" in i for i in m_items(o_new_legacy)))
        and any("R900" in i for i in m_items(o_new_legacy)),
        m_items(o_new_legacy))
    chk("N6 负控: 「说到但否定」不得判 open (防块内一律 open 的空心判据)",
        not m_items(o_neg), (m_items(o_neg), o_neg["sources"]["master"]["neg_fenced"]))
    chk("N7 否定围栏计数可见 (fenced>=1, 非静默丢弃)",
        o_neg["sources"]["master"]["neg_fenced"] >= 1, o_neg["sources"]["master"]["neg_fenced"])

    # ── v5/D8 用例: 推进对象优先序 = 权威源优先 (纯增量; 负控 N8 成对) ──
    bl_closed = _w("bl_closed.md", FIXTURE_BACKLOG_CLOSED)
    mp_closed = _w("m_new_closed2.md", FIXTURE_MASTER_NEW_CLOSED)
    o_new_lr, _ = build_report(bl2, mp_new, legacy_route=True)
    o_closed_bl, _ = build_report(bl2, mp_closed)          # 看板开放 + 块闭合 ⇒ 应回退 backlog
    o_all_closed, _ = build_report(bl_closed, mp_closed)   # 两侧皆闭合 ⇒ selfcheck
    o_all_lr, _ = build_report(bl_closed, mp_closed, legacy_route=True)

    chk("T18 权威源优先: 块有开放项 ⇒ route.primary=master-block ∧ priority[0] 为 master:",
        o_new["route"]["primary"] == "master-block"
        and o_new["route"]["priority"][0].startswith("master:"),
        o_new["route"])
    chk("T19 纯增量: route 变更不动 open_items/mode/open_count (逐字相同)",
        o_new["open_items"] == o_new_lr["open_items"] and o_new["mode"] == o_new_lr["mode"]
        and o_new["open_count"] == o_new_lr["open_count"],
        (o_new["open_items"], o_new_lr["open_items"]))
    chk("T20 回退正确: 块全闭合 + 看板有开放项 ⇒ primary=backlog (不是 master 恒赢)",
        o_closed_bl["route"]["primary"] == "backlog", o_closed_bl["route"])
    chk("T21 两侧皆空 ⇒ primary=selfcheck (且 mode=selfcheck 一致)",
        o_all_closed["route"]["primary"] == "selfcheck" and o_all_closed["mode"] == "selfcheck",
        (o_all_closed["route"]["primary"], o_all_closed["mode"]))
    chk("T22 route 判决附带 rule 原文与可比性断点 (读者可判, 不靠猜)",
        bool(o_new["route"]["rule"]) and bool(o_new["route"]["comparable_from"]),
        {k: o_new["route"][k] for k in ("rule", "comparable_from")})
    chk("N8 负控: --legacy-route 复现 v4 优先序 ⇒ 同夹具 primary=backlog (证明 T18 有判别力)",
        o_new_lr["route"]["primary"] == "backlog"
        and o_all_lr["route"]["primary"] == "selfcheck",
        (o_new_lr["route"]["primary"], o_all_lr["route"]["primary"]))

    for name, ok, got in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}  got={json.dumps(got, ensure_ascii=False)[:160]}")
    print(f"selftest: {len(checks) - fails}/{len(checks)} passed "
          f"(new_open={new['open_items']} legacy_open={old['open_items']})")
    return 0 if fails == 0 else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="能力自检循环 · 状态探针")
    ap.add_argument("--selftest", action="store_true", help="判定器自检 (夹具 + 负控)")
    ap.add_argument("--legacy", action="store_true", help="复现 v1 逻辑 (仅用于 A/B 与负控)")
    ap.add_argument("--legacy-route", action="store_true",
                    help="v5/D8 负控: 复现 v4 推进优先序 (看板优先), 仅用于 A/B")
    ap.add_argument("--backlog", default=BACKLOG)
    ap.add_argument("--master", default=MASTER)
    ap.add_argument("--kpi", default=KPI)
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()

    out, code = build_report(a.backlog, a.master, legacy=a.legacy, legacy_route=a.legacy_route)
    if code:
        print(json.dumps(out, ensure_ascii=False))
        return code
    info = last_probe(a.kpi)
    out["kpi_lines"] = info["kpi_lines"]
    out["last_probe"] = info["last"]
    out["skills_count"] = skills_count()
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
