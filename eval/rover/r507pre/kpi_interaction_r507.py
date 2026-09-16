#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R508 · 交互/人性化 KPI 对照（提问数量 · 精炼 · menu · 面板泄漏）

用户 2026-09-17 问：「有对比过提问数量，人性化，等其他 kpi 么」

背景：R502–R504 的 codex 对照只覆盖 整题全对 / tokens / 调用数 / 墙钟；
`eval/probe/process_metrics.py` 另可给 轮数 / 首次通过率 / 修复率，
但**交互面与输出面**（提问数量、回复精炼度、menu 选项、面板/协议帧泄漏）**两侧均未对照**。

本器具从**已落盘的两侧回复正文**（data/probe/replies/*.txt，外部真值，非重跑）
机械计算可判分列，禁止模型裁判、禁止事后补记：

  提问数量  : prose 内问号数 / asks_user（是否存在面向用户的反问或索要输入）
  人性化代理: prose 字数（去掉代码与框架面板后的自然语言量）、menu 选项数
  面板泄漏  : chrome 行数 / @chatbox 协议帧 / 产物路径泄漏  —— 本侧特有，codex 侧必须为 0（对照控制）

形态纪律：chrome 规则**源码派生**（src/agent.host/Program.cs:473 banner、:562 step），
非手工臆造；负控证明「代码围栏内的 ? 不计入问号」与「codex 侧 chrome 必须为 0」。

用法：
  python3 eval/rover/r507pre/kpi_interaction_r507.py --round r504            # 单轮
  python3 eval/rover/r507pre/kpi_interaction_r507.py --round r502 r503 r504  # 多轮
  python3 eval/rover/r507pre/kpi_interaction_r507.py --selftest              # 负控
"""
import argparse, glob, io, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
REPLIES = os.path.join(REPO, "data/probe/replies")
PROBE = os.path.join(REPO, "data/probe")

# ---- chrome（框架面板/遥测）规则：源码派生 ----
# Program.cs:473  sink.Write(CliRenderer.Bold("AgentFramework CLI"))
# Program.cs:562  sink.Step(step, $"意图分析: ...")      ->  "  [NN] 标题…"
CHROME_PATTERNS = [
    ("banner",      re.compile(r"^AgentFramework CLI$")),                       # Program.cs:473
    ("cmd_menu",    re.compile(r"^/[a-z_]+(\s|$)")),                            # /status /session ...
    ("turn_header", re.compile(r"^──.*──$")),                                   # 执行中 (turn N)
    ("step_line",   re.compile(r"^\[\d{2}\]\s")),                               # Program.cs:562 sink.Step
    ("log_line",    re.compile(r"^\[\d{4}-\d{2}-\d{2}T[\d:.]+Z?\]\s")),         # 遥测 log
    ("chatbox",     re.compile(r"^@chatbox:")),                                 # 前端协议帧
    ("artifact",    re.compile(r"^·\s")),                                       # 产物落盘 bullet
    ("fence",       re.compile(r"^```")),
]
ASK_WORDS = ("请提供", "需要我", "是否要", "要不要", "请问", "要我", "你希望", "确认一下")
MENU_RE = re.compile(r"^(\[\d+\]|\d+[.、)]|[（(]\d+[)）]|[-*]\s)")


def _norm_line(line):
    return line.strip().lstrip('"').strip()


def split_reply(text):
    """⇒ (prose, code_chars, chrome_lines, frames, artifact_leaks)"""
    code_chars, chrome_lines, frames, leaks = 0, 0, 0, 0
    prose, in_code = [], False
    for raw in text.splitlines():
        s = _norm_line(raw)
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            code_chars += len(raw)
            continue
        tag = None
        for name, rx in CHROME_PATTERNS:
            if rx.search(s):
                tag = name
                break
        if tag:
            chrome_lines += 1
            if tag == "chatbox":
                frames += 1
            if tag == "artifact":
                leaks += 1
            continue
        prose.append(s)
    return prose, code_chars, chrome_lines, frames, leaks


def measure_reply(text):
    prose, code_chars, chrome, frames, leaks = split_reply(text)
    joined = "\n".join(prose)
    marks = joined.count("?") + joined.count("？")
    asks = 1 if (marks > 0 or any(w in joined for w in ASK_WORDS)) else 0
    menu = sum(1 for ln in prose if MENU_RE.match(ln))
    return {
        "raw_chars": len(text), "code_chars": code_chars, "chrome_lines": chrome,
        "protocol_frames": frames, "artifact_leaks": leaks,
        "prose_chars": len(joined), "ask_marks": marks, "asks_user": asks, "menu_items": menu,
    }


def _sum(rows, key):
    return sum(r[key] for r in rows)


def side_report(probe_path):
    d = json.load(io.open(probe_path, encoding="utf-8-sig"))
    rows, missing = [], []
    seen_art, abytes = set(), 0
    for t in d.get("per_task", []):
        for p in (t.get("artifacts") or []):
            if p not in seen_art and os.path.isfile(p):
                seen_art.add(p); abytes += os.path.getsize(p)
        paths = t.get("reply_paths") or []
        p = os.path.join(REPO, paths[0]) if paths else None
        if not p or not os.path.isfile(p):
            missing.append(t.get("tid")); continue
        m = measure_reply(io.open(p, encoding="utf-8", errors="replace").read())
        m["tid"] = t.get("tid"); m["kind"] = t.get("kind")
        m["whole_ok"] = 1 if t.get("passed") == t.get("total") else 0
        rows.append(m)
    n = len(rows)
    return {
        "probe": os.path.relpath(probe_path, REPO), "tasks": n, "missing": missing,
        "artifact_files": len(seen_art), "artifact_bytes": abytes,
        "delivered_code_chars": _sum(rows, "code_chars") + abytes,
        "panel_lines_per_task": round(_sum(rows, "chrome_lines") / n, 1) if n else None,
        "human_chars_per_task": round(_sum(rows, "prose_chars") / n, 1) if n else None,
        "reply_chars_sum": _sum(rows, "raw_chars"),
        "prose_chars_sum": _sum(rows, "prose_chars"),
        "prose_chars_avg": round(_sum(rows, "prose_chars") / n, 1) if n else None,
        "code_chars_sum": _sum(rows, "code_chars"),
        "ask_marks_sum": _sum(rows, "ask_marks"),
        "asks_user_tasks": _sum(rows, "asks_user"),
        "ask_rate": round(_sum(rows, "asks_user") / n, 4) if n else None,
        "menu_items_sum": _sum(rows, "menu_items"),
        "menu_tasks": sum(1 for r in rows if r["menu_items"] > 0),
        "menu_rate": round(sum(1 for r in rows if r["menu_items"] > 0) / n, 4) if n else None,
        "chrome_lines_sum": _sum(rows, "chrome_lines"),
        "protocol_frames_sum": _sum(rows, "protocol_frames"),
        "artifact_leaks_sum": _sum(rows, "artifact_leaks"),
        "rows": rows,
    }


def discover(round_id):
    """两侧落盘摘要：本侧 probe-agent-*<r>*.json / codex probe-cmd:*codex-<r>*.json"""
    a = [p for p in glob.glob(os.path.join(PROBE, "probe-agent-*%s.json" % round_id))
         if "vmrun" not in os.path.basename(p)]
    c = [p for p in glob.glob(os.path.join(PROBE, "probe-cmd:*codex-%s.json" % round_id))]
    key = lambda ps: max(ps, key=os.path.getmtime) if ps else None
    return {"agent": key(a), "codex": key(c)}


def internal_ask_report(dirs):
    """内部问询（`[微步骤隔离问询]` / `[一次性隔离子任务]`）—— 来自**冻结适配器快照**的调用面。
    说明: 该标记是**本仓插桩**产物（src/agent.modelqueue/ToolDeclGate.cs:24 注释处记载的通道轴），
    外部真值(codex)自带循环不落此标记 ⇒ **结构不可对照**，只给本侧内部构成（禁按 0 冒充可比）。"""
    MARK = ("微步骤隔离问询", "一次性隔离子任务")
    tot = dict(calls=0, ask_calls=0, ask_mark=0, ptok=0, ptok_ask=0, hit=0, miss=0, dirs=0)
    for d in dirs:
        files = sorted(glob.glob(os.path.join(d, "side-*.json")))
        if not files:
            continue
        tot["dirs"] += 1
        for fp in files:
            try:
                x = json.load(io.open(fp, encoding="utf-8-sig"))
            except Exception:
                continue
            s = json.dumps(x.get("request", {}), ensure_ascii=False)
            u = (x.get("response") or {}).get("usage") or {}
            n = sum(s.count(m) for m in MARK)
            tot["calls"] += 1
            tot["ask_mark"] += n
            tot["ptok"] += u.get("prompt_tokens") or 0
            tot["hit"] += u.get("prompt_cache_hit_tokens") or 0
            tot["miss"] += u.get("prompt_cache_miss_tokens") or 0
            if n:
                tot["ask_calls"] += 1
                tot["ptok_ask"] += u.get("prompt_tokens") or 0
    tot["ask_share"] = round(tot["ask_calls"] / tot["calls"], 4) if tot["calls"] else None
    tot["ptok_ask_share"] = round(tot["ptok_ask"] / tot["ptok"], 4) if tot["ptok"] else None
    return tot


def _selftest(evidence=None):
    cases = [
        ("正控: 反问+menu+无代码", "我可以继续。\n1. 先跑公开用例\n2. 再补边界\n请问用哪个输入?\n", 1, 1, 2, 0, 0),
        ("负控: ? 在代码围栏内 ⇒ 不计问号", "```python\nq = 'a?b'\nprint(q)\n```\n", 0, 0, 0, 0, 0),
        ("负控: 纯代码 ⇒ prose 为空", "```python\nprint(1)\n```\n", 0, 0, 0, 0, 0),
        ("正控: 本侧面板 ⇒ chrome>0 且不计 prose/问号", "AgentFramework CLI\n  /status [agent_uid]\n  [01] 意图分析: x\n@chatbox:{\"Type\":\"x\"}\n  · ./data/artifacts/a.py (1B) ✓\n完成。\n", 0, 0, 0, 1, 1),
    ]
    ok = True
    rec = []
    for name, text, exp_ask, exp_marks, exp_menu, exp_frames, exp_leaks in cases:
        m = measure_reply(text)
        good = (m["asks_user"] == exp_ask and m["ask_marks"] == exp_marks
                and m["menu_items"] == exp_menu and m["protocol_frames"] == exp_frames
                and m["artifact_leaks"] == exp_leaks)
        ok = ok and good
        rec.append({"case": name, "expected": [exp_ask, exp_marks, exp_menu, exp_frames, exp_leaks],
                    "measured": [m["asks_user"], m["ask_marks"], m["menu_items"], m["protocol_frames"],
                                 m["artifact_leaks"]], "verdict": "PASS" if good else "FAIL"})
        print("%-6s %-42s ask=%d marks=%d menu=%d frames=%d leaks=%d prose=%d chrome=%d"
              % ("PASS" if good else "FAIL", name, m["asks_user"], m["ask_marks"], m["menu_items"],
                 m["protocol_frames"], m["artifact_leaks"], m["prose_chars"], m["chrome_lines"]))
    # 控制: codex 侧 chrome 必须为 0
    cx = discover("r504")["codex"]
    if cx:
        rep = side_report(cx)
        good = rep["chrome_lines_sum"] == 0 and rep["protocol_frames_sum"] == 0
        ok = ok and good
        rec.append({"case": "控制: codex 侧 chrome/协议帧必须为 0",
                    "expected": [0, 0], "measured": [rep["chrome_lines_sum"], rep["protocol_frames_sum"]],
                    "verdict": "PASS" if good else "FAIL"})
        print("%-6s 控制: codex 侧 chrome/协议帧必须为 0 (实测 chrome=%d frames=%d)"
              % ("PASS" if good else "FAIL", rep["chrome_lines_sum"], rep["protocol_frames_sum"]))
    print("SELFTEST=%s" % ("OK" if ok else "FAIL"))
    if evidence:
        io.open(evidence, "w", encoding="utf-8", newline="\n").write(json.dumps(
            {"instrument": "eval/rover/r507pre/kpi_interaction_r507.py", "cases": rec,
             "verdict": "OK" if ok else "FAIL"}, ensure_ascii=False, indent=2) + "\n")
        print("→ %s" % os.path.relpath(evidence, REPO))
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", nargs="*", default=["r504"])
    ap.add_argument("--adapter-dir", nargs="*", default=[])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--evidence", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest(a.evidence)
    if a.adapter_dir:
        rep = internal_ask_report(a.adapter_dir)
        print("| 快照目录 | 调用 | 含内部问询调用(率) | 标记数 | prompt tok(问询占比) | cache 命中/未命中 |")
        print("|---|---|---|---|---|---|")
        print("| %d 个 (本侧) | %d | %d(%s) | %d | %d(%s) | %d/%d |"
              % (rep["dirs"], rep["calls"], rep["ask_calls"],
                 ("%.1f%%" % (100 * rep["ask_share"])) if rep["ask_share"] is not None else "n/a",
                 rep["ask_mark"], rep["ptok"],
                 ("%.1f%%" % (100 * rep["ptok_ask_share"])) if rep["ptok_ask_share"] is not None else "n/a",
                 rep["hit"], rep["miss"]))
        print("注: 外部真值(codex)自带 agentic 循环不落此标记 ⇒ 内部问询**结构不可对照**（只给本侧构成，禁按 0 冒充可比）")
        return 0
    res = {}
    for r in a.round:
        d = discover(r)
        res[r] = {side: (side_report(p) if p else None) for side, p in d.items()}
    out = a.out or os.path.join(REPO, "eval/rover/r507pre/kpi-interaction.json")
    io.open(out, "w", encoding="utf-8", newline="\n").write(
        json.dumps(res, ensure_ascii=False, indent=2) + "\n")
    print("| 轮 | 侧 | 题数 | 整题全对 | 提问题数(率) | 问号数 | menu题数(率) | 人话字/题 | 代码字 | 产物(件/B) | 面板行/题 | 协议帧 | 产物泄漏 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in a.round:
        for side in ("agent", "codex"):
            s = res[r][side]
            if not s:
                print("| %s | %s | — | 未落盘 | | | | | | | | | |" % (r, side)); continue
            w = sum(x["whole_ok"] for x in s["rows"])
            print("| %s | %s | %d | %d/%d | %d(%.1f%%) | %d | %d(%.1f%%) | %s | %d | %d/%d | %s | %d | %d |"
                  % (r, side, s["tasks"], w, s["tasks"], s["asks_user_tasks"], 100 * s["ask_rate"],
                     s["ask_marks_sum"], s["menu_tasks"], 100 * s["menu_rate"], s["prose_chars_avg"],
                     s["code_chars_sum"], s["artifact_files"], s["artifact_bytes"],
                     s["panel_lines_per_task"], s["protocol_frames_sum"], s["artifact_leaks_sum"]))
    print()
    print("| 轮 | 侧 | 交付代码字(归一: 回复内代码+产物字节) | 人话字/题 | 面板行/题 |")
    print("|---|---|---|---|---|")
    for r in a.round:
        for side in ("agent", "codex"):
            s = res[r][side]
            if not s:
                continue
            print("| %s | %s | %d | %s | %s |"
                  % (r, side, s["delivered_code_chars"], s["human_chars_per_task"], s["panel_lines_per_task"]))
    print("→ %s" % os.path.relpath(out, REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
