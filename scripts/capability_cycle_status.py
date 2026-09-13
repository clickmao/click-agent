#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""能力自检循环 · 状态探针 v2 (用户令 2026-09-14: 每 60 分钟检查「还有任务吗」)。

判据全部机械可复核 (不靠感觉):
  ① 计划看板 `docs/plans/v0.22.0-longterm-backlog.md` 中**状态列**含「进行中/未开始/待定/部分」的行 ⇒ 未完成计划项;
  ② 主报告 §7 最新状态块中的「下轮候选 / 待确认 / 进行中」条目 ⇒ 未完成事项;
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
OPEN_MARKERS = ("进行中", "未开始", "待定", "部分", "计划中")
ROW_KEY = re.compile(r"^R\d+")
SEP_CELL = re.compile(r":?-{2,}:?")
MASTER_PAT = re.compile(
    r"^\s*>?\s*[-*]?\s*\*\*(下轮候选|待确认|本轮待办|进行中)\*\*[:：]?\s*(.{0,120})", re.M
)


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
    diag = {"rows_scanned": 0, "closed": 0, "unmarked": 0, "tables": 0, "state_col": {}}
    for header, rows in iter_tables(read_text(path)):
        idx = None if legacy else state_index(header)
        diag["tables"] += 1
        for cells in rows:
            if not cells or not ROW_KEY.match(cells[0]):
                continue
            diag["rows_scanned"] += 1
            col = idx if (idx is not None and idx < len(cells)) else (2 if len(cells) > 2 else None)
            status = cells[col] if col is not None else ""
            diag["state_col"][cells[0]] = col
            if legacy:
                # v1: 完成标记先过滤, 再看开放标记; 状态列恒为 cells[2]
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
                               "table": " | ".join(header)[:80]})
            elif verdict == "closed":
                diag["closed"] += 1
            else:
                diag["unmarked"] += 1
    return items, detail, diag


def master_opens(path: str, legacy: bool = False):
    if not os.path.exists(path):
        return None, None
    txt = read_text(path)
    head = txt.split("## 7.")[-1][:4000]
    hits = [f"{m.group(1)}: {m.group(2).strip()}" for m in MASTER_PAT.finditer(head)]
    diag = {"hits": len(hits), "format_matched": bool(hits),
            "note": "" if hits else "该来源对当前报告版式零命中 ⇒ 视作「缺失」而非「无未完成事项」(v2 显式化)"}
    return hits[:8], diag


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


def build_report(backlog_path: str, master_path: str, legacy: bool = False) -> tuple[dict, int]:
    b, bdetail, bdiag = backlog_scan(backlog_path, legacy=legacy)
    m, mdiag = master_opens(master_path, legacy=legacy)
    if b is None or m is None:
        return {"error": "docs 缺失", "backlog": backlog_path, "master": master_path}, 2
    items = b + m
    out = {
        "mode": "tasks" if items else "selfcheck",
        "open_count": len(items),
        "open_items": items,
        "open_items_detail": bdetail,
        "backlog_open": len(b),
        "master_open": len(m),
        "sources": {"backlog": bdiag, "master": mdiag, "legacy_logic": legacy},
        "kpi_lines": 0,
        "skills_count": 0,
        "rule": "mode=tasks ⇒ 推进计划项一步; mode=selfcheck ⇒ 跑 py 随机程序+随机数学题能力自检并沉淀通用性 skill",
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
"""

FIXTURE_MASTER = """# fixture · 主报告

## 7. 迭代状态快照

> 本轮无任何 `**下轮候选**` 形式条目 (来源②应显式报 format_matched=false)。
"""


def selftest() -> int:
    """7 例判定 + 2 例负控 (v1 逻辑必须判错, 否则用例无判别力)。"""
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

    for name, ok, got in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}  got={json.dumps(got, ensure_ascii=False)[:160]}")
    print(f"selftest: {len(checks) - fails}/{len(checks)} passed "
          f"(new_open={new['open_items']} legacy_open={old['open_items']})")
    return 0 if fails == 0 else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="能力自检循环 · 状态探针")
    ap.add_argument("--selftest", action="store_true", help="判定器自检 (夹具 + 负控)")
    ap.add_argument("--legacy", action="store_true", help="复现 v1 逻辑 (仅用于 A/B 与负控)")
    ap.add_argument("--backlog", default=BACKLOG)
    ap.add_argument("--master", default=MASTER)
    ap.add_argument("--kpi", default=KPI)
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()

    out, code = build_report(a.backlog, a.master, legacy=a.legacy)
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
