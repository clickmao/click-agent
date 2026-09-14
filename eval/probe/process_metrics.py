#!/usr/bin/env python3
"""探针过程 / 成本维度 KPI 提取器 (R418)。

口径（写死，勿凭字段名推断）:
- 质量: `data/probe/probe-*.json` 的 `per_task`（mode / passed / total）= **判定器产物**，外部真值。
- 过程: `data/probe/replies/<solver><tag>-<tid>.txt` 归档回复原文里的指标行 —— 这是**被测链自报**，
        只作过程旁读；质量一律以判定器为准。
        可用字段：`promptTokens=` `llmModel=` `contextSnippets=` `(NNNNms, intent=)` `── 执行中 (turn N) ──`。
- **缺字段记 n/a，绝不记 0**；n/a 从均值分母剔除并单列计数（把未上报当 0 与冒充上报同属数据造假）。
- 本口径**只有 prompt 侧 + 墙钟**（链不落 completionTokens）⇒ 报告显式标注，不得当总量读。

用法:
    python3 eval/probe/process_metrics.py --selftest
    python3 eval/probe/process_metrics.py                     # 全量归档 → data/probe/process-metrics.json
    python3 eval/probe/process_metrics.py --report            # 附人读表格
"""

import argparse
import datetime
import glob
import json
import os
import re
import sys

WIN_PRE_SLACK = 5.0      # 求解开始前容差(秒)
WIN_POST_SLACK = 60.0    # 运行结束后容差(秒)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "probe")
REPLIES = os.path.join(DATA, "replies")

RE_PROMPT = re.compile("promptTokens=([0-9]+)")
RE_WALL = re.compile("\\(([0-9]+)ms, intent=([a-z_]+)\\)")
RE_TURN = re.compile("执行中 \\(turn ([0-9]+)\\)")
RE_SNIP = re.compile("contextSnippets=([0-9]+)")
RE_MODEL = re.compile("llmModel=([A-Za-z0-9._-]+)")
RE_PROMPT_BAD = re.compile("promptTokens=([^0-9 \t][^ \t]*)")
RE_WALL_ANY = re.compile("\\(([^)]{0,20})ms,")


def parse_metrics(text):
    """从回复原文抽过程指标。缺失 ⇒ None；畸形 ⇒ 计入 malformed（不静默）。"""
    text = text or ""
    out = {"prompt_tokens": None, "wall_ms": None, "intent": None, "turns": None,
           "context_snippets": None, "llm_model": None, "malformed": []}
    m = RE_PROMPT.search(text)
    if m:
        out["prompt_tokens"] = int(m.group(1))
    elif RE_PROMPT_BAD.search(text):
        out["malformed"].append("promptTokens")
    m = RE_WALL.search(text)
    if m:
        out["wall_ms"] = int(m.group(1))
        out["intent"] = m.group(2)
    else:
        m2 = RE_WALL_ANY.search(text)
        if m2 and not m2.group(1).strip().isdigit():
            out["malformed"].append("wall_ms")
    ms = RE_TURN.findall(text)
    if ms:
        out["turns"] = len(ms)
        out["turn_max"] = max(int(x) for x in ms)
    m = RE_SNIP.search(text)
    if m:
        out["context_snippets"] = int(m.group(1))
    m = RE_MODEL.search(text)
    if m:
        out["llm_model"] = m.group(1)
    return out


def _window(ts_text, elapsed_s):
    """该 run 的可归属时间窗 (epoch 秒)。ts 解析失败 ⇒ None (不猜)。"""
    if not ts_text:
        return None
    t = str(ts_text).strip().replace("Z", "+00:00")
    try:
        end = datetime.datetime.fromisoformat(t).timestamp()
    except Exception:
        return None
    start = end - float(elapsed_s or 0.0) - WIN_PRE_SLACK
    return (start, end + WIN_POST_SLACK)


def find_replies(solver_id, tag, tid, window=None, ns=None):
    """定位该题归档回复。返回 (paths, attribution)。

    归属铁律 (R418): 归档回复**无命名空间**时会张冠李戴（同名文件被后一臂覆盖）。
    因此除文件名匹配外，必须用 run 的时间窗 (ts-elapsed ~ ts+slack) 核对回复文件 mtime；
    窗外的同名文件**不得**当本次读数（判 `reply_out_of_window`），否则跨轮指标静默错配。
    """
    safe = solver_id.replace(":", "_").replace("/", "_")
    if ns:                      # 新归档: 显式命名空间 ⇒ 精确解析, 无需时间窗
        exact = os.path.join(REPLIES, "%s%s-%s.txt" % (safe, ns, tid))
        return ([exact], "ns_exact") if os.path.exists(exact) else ([], "ns_missing")
    exact = os.path.join(REPLIES, "%s%s-%s.txt" % (safe, tag, tid))
    cands = ([exact] if os.path.exists(exact) else []) + \
            [p for p in sorted(glob.glob(os.path.join(REPLIES, "*-%s.txt" % tid))) if p != exact]
    if not cands:
        return [], "missing"
    if window is None:
        if len(cands) == 1:
            return cands, "exact_no_window"
        return cands, "ambiguous_no_window"
    lo, hi = window
    inside = [p for p in cands if lo <= os.path.getmtime(p) <= hi]
    if len(inside) == 1:
        return inside, ("exact_in_window" if inside[0] == exact else "glob_in_window")
    if len(inside) > 1:
        return inside, "ambiguous_in_window"
    return [], "reply_out_of_window"


def _avg(vals):
    vals = [v for v in vals if v is not None]
    return (sum(vals) / len(vals)) if vals else None


def analyse(probe_path):
    """单份 probe 摘要 → 过程/成本读数。"""
    with open(probe_path, encoding="utf-8", errors="replace") as fh:
        d = json.load(fh)
    solver = d.get("solver", "")
    tag = d.get("tag", "") or ""
    win = _window(d.get("ts"), d.get("elapsed_s"))
    rows, na, amb, mal = [], 0, 0, 0
    for t in d.get("per_task", []):
        tid = t.get("tid", "")
        paths, attrib = find_replies(solver, tag, tid, win, d.get("reply_ns") or None)
        if not paths:
            r = {"prompt_tokens": None, "wall_ms": None, "intent": None, "turns": None,
                 "context_snippets": None, "llm_model": None, "malformed": [],
                 "source": None, "note": attrib}
            na += 1
            rows.append((t, r))
            continue
        if attrib.startswith("ambiguous"):
            amb += 1
            r = {"prompt_tokens": None, "wall_ms": None, "intent": None, "turns": None,
                 "context_snippets": None, "llm_model": None, "malformed": [],
                 "source": None, "note": attrib + "(%d)" % len(paths)}
            na += 1                      # ★歧义 ⇒ 不猜(不取 paths[0]), 记 n/a
            rows.append((t, r))
            continue
        with open(paths[0], encoding="utf-8", errors="replace") as fh:
            mt = parse_metrics(fh.read())
        mt["source"] = os.path.relpath(paths[0], ROOT)
        mt["note"] = attrib
        if mt["prompt_tokens"] is None:
            na += 1
        mal += len(mt["malformed"])
        rows.append((t, mt))

    ok_tasks = [t for t, _ in rows if t.get("mode") == "ok"]
    tok_all = [m["prompt_tokens"] for _, m in rows]
    tok_ok = [m["prompt_tokens"] for t, m in rows if t.get("mode") == "ok"]
    n_total = len(rows)
    n_ok = len(ok_tasks)
    tok_sum = sum(v for v in tok_all if v is not None)
    tok_ok_sum = sum(v for v in tok_ok if v is not None)
    return {
        "probe_file": os.path.basename(probe_path),
        "solver": solver,
        "tag": tag,
        "n_tasks": n_total,
        "whole_ok": n_ok,
        "whole_rate": (n_ok / n_total) if n_total else None,
        "case_rate": d.get("rate"),
        "prompt_tokens_sum": tok_sum if any(v is not None for v in tok_all) else None,
        "tokens_per_task": _avg(tok_all),
        "tokens_per_whole_ok_task": (tok_ok_sum / len([v for v in tok_ok if v is not None]))
        if any(v is not None for v in tok_ok) else None,
        "first_try_ok": sum(1 for t, m in rows if t.get("mode") == "ok" and m.get("turns") == 1),
        "first_try_unknown": sum(1 for t, m in rows if t.get("mode") == "ok" and m.get("turns") is None),
        "first_try_rate": (sum(1 for t, m in rows if t.get("mode") == "ok" and m.get("turns") == 1) / n_total)
        if n_total else None,
        "wall_ms_avg": _avg([m["wall_ms"] for _, m in rows]),
        "wall_ms_sum": sum(v for _, m in rows for v in [m["wall_ms"]] if v is not None),
        "turns_max": max([m["turns"] for _, m in rows if m["turns"] is not None], default=None),
        "llm_model": next((m["llm_model"] for _, m in rows if m["llm_model"]), None),
        "na_count": na,
        "ambiguous_replies": amb,
        "malformed_fields": mal,
        "tasks": [{"tid": t.get("tid"), "family": t.get("family"), "mode": t.get("mode"),
                   "passed": t.get("passed"), "total": t.get("total"),
                   "prompt_tokens": m["prompt_tokens"], "wall_ms": m["wall_ms"],
                   "turns": m["turns"], "source": m["source"], "note": m["note"]}
                  for t, m in rows],
    }


def _fmt(v, nd=1):
    return "n/a" if v is None else ("%.*f" % (nd, v))


def report(rows):
    """人读表: 质量与成本**同一行**(这是本轮的关键口径 —— 只看质量会被饱和骗, 只看成本会被空心骗)。"""
    lines = ["| 题集(solver/tag) | 题数 | 整题全对 | 用例级 | 首次通过率 | tokens/题 | tokens/满分题 | 墙钟均(ms) | turn≤ | n/a | 畸形 |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        ft = ("%d/%d=%.4f" % (r["first_try_ok"], r["n_tasks"], r["first_try_rate"])
              if r["first_try_rate"] is not None else "n/a")
        cells = ["`%s` (%s/%s)" % (r["probe_file"], r["solver"], r["tag"]),
                 str(r["n_tasks"]),
                 "%d/%d=%.4f" % (r["whole_ok"], r["n_tasks"], r["whole_rate"] or 0.0),
                 _fmt(r["case_rate"], 4), ft, _fmt(r["tokens_per_task"]),
                 _fmt(r["tokens_per_whole_ok_task"]), _fmt(r["wall_ms_avg"], 0),
                 "-" if r["turns_max"] is None else str(r["turns_max"]),
                 str(r["na_count"]), str(r["malformed_fields"])]
        lines.append("| " + " | ".join(cells) + " |")
    return chr(10).join(lines)


def selftest():
    ok, fails = 0, []

    def chk(name, cond, detail=""):
        nonlocal ok
        if cond:
            ok += 1
            print("  [PASS] %s %s" % (name, detail))
        else:
            fails.append(name)
            print("  [FAIL] %s %s" % (name, detail))

    nl = chr(10)
    good = ("── 执行中 (turn 1) ──" + nl + "[03] 管线执行…" + nl + "promptTokens=9261  contextSnippets=8  llmModel=deepseek-flash" + nl
            + "── 回复 ──" + nl + "print(1)" + nl + "(122495ms, intent=code_generation)" + nl)
    m = parse_metrics(good)
    chk("正控: 单轮指标解析", m["prompt_tokens"] == 9261 and m["wall_ms"] == 122495
        and m["turns"] == 1 and m["context_snippets"] == 8 and m["llm_model"] == "deepseek-flash"
        and m["intent"] == "code_generation" and not m["malformed"], str(m))

    two = good + "── 执行中 (turn 2) ──" + nl
    chk("负控: 两轮 ⇒ turns=2 (异常可见)", parse_metrics(two)["turns"] == 2)

    miss = "── 回复 ──" + nl + "print(1)" + nl + "(9000ms, intent=general)" + nl
    m = parse_metrics(miss)
    chk("负控: 缺 promptTokens ⇒ None 而非 0", m["prompt_tokens"] is None, str(m["prompt_tokens"]))

    bad = "promptTokens=abc" + nl + "(12xms, intent=code_generation)" + nl
    m = parse_metrics(bad)
    chk("负控: 畸形字段计入 malformed (不静默)",
        m["prompt_tokens"] is None and "promptTokens" in m["malformed"] and "wall_ms" in m["malformed"],
        str(m["malformed"]))

    # 同 tid 多文件 ⇒ 判歧义不猜
    import tempfile
    tmp = tempfile.mkdtemp(prefix="pm_")
    global REPLIES
    keep = REPLIES
    try:
        REPLIES = tmp
        p1 = os.path.join(tmp, "agent-p001.txt")
        p2 = os.path.join(tmp, "agentm6-p001.txt")
        p3 = os.path.join(tmp, "agent-p003.txt")
        p4 = os.path.join(tmp, "agentm6-p004.txt")
        for p, tok in ((p1, 111), (p2, 222), (p3, 777), (p4, 888)):
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("promptTokens=%d%s" % (tok, nl))
        now = __import__("time").time()
        w_now = (now - 3600, now + 60)
        paths, at = find_replies("agent", "", "p003", w_now)
        chk("正控: 精确名唯一 + 时间窗内 ⇒ exact_in_window", at == "exact_in_window" and len(paths) == 1
            and os.path.basename(paths[0]) == "agent-p003.txt", at)
        paths, at = find_replies("agent", "", "p001", None)
        chk("负控: 无时间窗且多候选 ⇒ 判歧义(不猜)", at == "ambiguous_no_window" and len(paths) == 2, at)
        for nm, tok in (("agentm6-p002.txt", 333), ("agentr417-p002.txt", 444)):
            with open(os.path.join(tmp, nm), "w", encoding="utf-8") as fh:
                fh.write("promptTokens=%d%s" % (tok, nl))
        paths, at = find_replies("agent", "", "p002", w_now)
        chk("负控: 窗内多候选(无精确名) ⇒ 判歧义(不猜)", at == "ambiguous_in_window" and len(paths) == 2, at)
        paths, at = find_replies("agent", "", "p002", (1.0, 2.0))
        chk("★负控: 同名文件在窗外 ⇒ 判 reply_out_of_window, 不归属(防跨轮张冠李戴)",
            paths == [] and at == "reply_out_of_window", at)
        paths, at = find_replies("agent", "m6", "p004", w_now)
        chk("正控: 带 tag 精确命中单文件", at == "exact_in_window" and len(paths) == 1
            and os.path.basename(paths[0]) == "agentm6-p004.txt", at)
        w = _window("2026-09-14T13:00:00+08:00", 60)
        chk("正控: _window 由 ts/elapsed 算出时间窗", w is not None and abs((w[1] - w[0]) - 125.0) < 0.01, str(w))
        chk("负控: ts 不可解析 ⇒ window=None(不猜)", _window("not-a-time", 60) is None)
    finally:
        REPLIES = keep

    # n/a 从均值分母剔除
    probe = {"solver": "agent", "tag": "", "rate": 0.5,
             "per_task": [{"tid": "p001", "mode": "ok", "passed": 2, "total": 2},
                          {"tid": "p002", "mode": "partial", "passed": 1, "total": 2},
                          {"tid": "p003", "mode": "ok", "passed": 2, "total": 2}]}
    tmp2 = tempfile.mkdtemp(prefix="pm2_")
    pj = os.path.join(tmp2, "probe-agent-seed1.json")
    with open(pj, "w", encoding="utf-8") as fh:
        json.dump(probe, fh)
    try:
        REPLIES = tmp2
        with open(os.path.join(tmp2, "agent-p001.txt"), "w", encoding="utf-8") as fh:
            fh.write("── 执行中 (turn 1) ──" + nl + "promptTokens=1000" + nl + "(10ms, intent=code_generation)" + nl)
        with open(os.path.join(tmp2, "agent-p003.txt"), "w", encoding="utf-8") as fh:
            fh.write("promptTokens=2000" + nl + "(20ms, intent=code_generation)" + nl)   # 无 turn 标记 ⇒ 未知
        r = analyse(pj)
        chk("正控: n/a 从均值分母剔除(不按 0 摊)",
            r["n_tasks"] == 3 and r["whole_ok"] == 2 and r["na_count"] == 1
            and r["tokens_per_task"] == 1500.0 and r["tokens_per_task"] != 1000.0
            and r["tokens_per_whole_ok_task"] == 1500.0,
            "tpt=%s tok_ok=%s na=%d" % (r["tokens_per_task"], r["tokens_per_whole_ok_task"], r["na_count"]))
        chk("负控: 缺回复不改判质量为过", r["whole_ok"] == 2 and r["case_rate"] == 0.5)
        chk("正控: 首次通过率只数 turns=1 的满分题; turn 未知 ⇒ 不数且标注",
            r["first_try_ok"] == 1 and r["first_try_unknown"] == 1
            and abs(r["first_try_rate"] - 1 / 3.0) < 1e-9,
            "ok=%d rate=%s unk=%d" % (r["first_try_ok"], r["first_try_rate"], r["first_try_unknown"]))
    finally:
        REPLIES = keep

    print("selftest %d/%d" % (ok, ok + len(fails)))
    return 0 if not fails else 1


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--glob", default=os.path.join(DATA, "probe-*.json"))
    ap.add_argument("--out", default=os.path.join(DATA, "process-metrics.json"))
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    files = sorted(glob.glob(a.glob))
    rows = []
    for p in files:
        try:
            rows.append(analyse(p))
        except Exception as e:                      # 解析失败必须出声, 不静默跳过
            rows.append({"probe_file": os.path.basename(p), "error": "%s: %s" % (type(e).__name__, e)})
    by_file = {r["probe_file"]: r for r in rows}
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump({"note": "prompt 侧 only（无 completionTokens）; n/a 不计入均值分母",
                   "generated_from": os.path.relpath(a.glob, ROOT), "runs": by_file}, fh,
                  ensure_ascii=False, indent=2)
    good = [r for r in rows if "error" not in r]
    print("runs=%d ok=%d err=%d → %s" % (len(rows), len(good), len(rows) - len(good), os.path.relpath(a.out, ROOT)))
    print("na_sum=%d ambiguous=%d malformed=%d" % (sum(r["na_count"] for r in good),
                                                   sum(r["ambiguous_replies"] for r in good),
                                                   sum(r["malformed_fields"] for r in good)))
    if a.report:
        print(report(good))
    return 0


if __name__ == "__main__":
    sys.exit(main())
