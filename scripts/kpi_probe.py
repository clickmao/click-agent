#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kpi_probe.py —— 能力自检探针 (eval/probe) 的 KPI 打点 + 前后对比报告。

数据源 (两路, 缺一不可)
  * 运行摘要 `data/probe/probe-*.json` —— run_probe.py 产出: rate/passed/total/taxonomy/by_family/per_task/taskset_sha
  * 遥测 `data/telemetry/host.jsonl`   —— point=llm_call 的 kv.prompt_tokens / kv.completion_tokens,
    按 run 的**墙钟窗口 [ts - elapsed_s, ts]** join (run_probe 的 ts = 运行结束时刻; 窗口外一律不算)

产出
  * KPI 台账: `data/probe/kpi.jsonl`  (每个 run 一行; 以 (solver, taskset_sha, ts) 去重)
  * 对比报告: markdown (--report), 含 A→B 逐项 Δ / 按族分层 / 失败模式分布 / 诚实边界

可证伪性 (硬约束, 违反即 error+退出码 2, 绝不静默跳过)
  * run 摘要缺 rate/passed/total/taskset_sha/ts ⇒ error
  * n_tasks <= 0 或 total <= 0 ⇒ error (禁止用除零掩盖)
  * 遥测窗口内无 llm_call ⇒ tokens = null 并**显式标注**, 不得写成 0
  * 未知 taxonomy 键**保留并单列**, 不得丢弃
退出码: 0 = 跑通; 2 = 输入/标签错误。
"""
import argparse
import glob as _glob
import io
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

REQUIRED_RUN_FIELDS = ("ts", "solver", "rate", "passed", "total", "n_tasks",
                       "elapsed_s", "taxonomy", "taskset_sha")
KNOWN_MODES = ("ok", "no_code", "syntax_error", "runtime_error", "timeout",
               "wrong_output", "partial", "no_final", "wrong_final", "wrong_witness")

DEFAULT_GLOB = "data/probe/probe-*.json"


class InputError(Exception):
    pass


def resolve_paths(run_list, glob_list, default_glob=DEFAULT_GLOB):
    """把 `--run` 显式路径与 `--glob` (**可重复**) 解析成一条**保序去重**的路径表。

    旧语义 = `a.run or sorted(glob(a.glob))` ⇒ **显式路径与通配符互斥**: 只要给了
    `--run`, `--glob` 整条被丢弃 ⇒ 无法表达「固定基线 ∪ 一轮通配产物」这类集合
    (实测: `--run <基线> --glob '<轮产物>' --compare <基线> <产物>` ⇒ rc=2
    「匹配不到 run」, 即证据面命令**写不出来**)。

    新语义 = **并集**: 显式项在前 (决定报告 `#` 列顺序, 使冻结台账的既有序号可复现),
    通配符命中项按路径排序在后。`--glob` 显式给出时**不带**缺省模式 (防 argparse
    `default=[缺省]` + `action="append"` 的静默并集 ⇒ 越界吸run)。
    """
    pats = list(glob_list) if glob_list else [default_glob]
    hits = []
    for g in pats:
        hits.extend(_glob.glob(g))
    out, seen = [], set()
    for p in list(run_list or []) + sorted(hits):
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _parse_ts(s):
    """严格解析 ISO 时间戳。

    兼容两类真机格式:
      * 运行摘要: 2026-09-13T23:08:03+0800
      * 遥测:     2026-09-13T15:08:03.9531864Z   (7 位小数 —— fromisoformat 只认 3/6 位)
    解析失败 ⇒ 抛错(绝不返回 None 静默跳过, 否则 token 打点会静默变 None)。
    """
    if not s:
        raise ValueError("空时间戳")
    x = str(s).strip().replace("Z", "+00:00")
    fm = re.match(r"^(.*\.)(\d+)([+-]\d{2}:?\d{2})$", x)
    if fm:
        x = fm.group(1) + ((fm.group(2) + "000000")[:6]) + fm.group(3)
    try:
        dt = datetime.fromisoformat(x)
    except ValueError as e:
        raise ValueError("无法解析时间戳 %r: %s" % (s, e))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))   # 无时区视作本机 +0800
    return dt


def validate_run(d, name):
    for k in REQUIRED_RUN_FIELDS:
        if k not in d:
            raise InputError("%s: 缺字段 %s" % (name, k))
    if int(d["total"]) <= 0 or int(d["n_tasks"]) <= 0:
        raise InputError("%s: total/n_tasks 必须 > 0 (total=%r n_tasks=%r)"
                         % (name, d["total"], d["n_tasks"]))
    if not isinstance(d.get("taxonomy"), dict) or not d["taxonomy"]:
        raise InputError("%s: taxonomy 为空" % name)
    _parse_ts(d["ts"])
    return d


def load_runs(paths):
    out = []
    for p in paths:
        d = json.load(io.open(p, encoding="utf-8"))
        validate_run(d, os.path.basename(p))
        d["_file"] = os.path.basename(p)
        out.append(d)
    if not out:
        raise InputError("没有任何 run 摘要")
    return sorted(out, key=lambda d: _parse_ts(d["ts"]))


def load_telemetry(path):
    """返回 [(ts, kv), ...], 只取 point=llm_call。"""
    if not path or not os.path.exists(path):
        return []
    rows = []
    for i, line in enumerate(io.open(path, encoding="utf-8-sig", errors="replace"), 1):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except ValueError as e:
            # 坏行不得静默跳过: 遥测格式漂移必须炸出来, 否则 token 打点静默变 n/a
            raise SystemExit("telemetry 第 %d 行非法 JSON: %s" % (i, e))
        if o.get("point") != "llm_call":
            continue
        try:
            kv = o["kv"]
            ts = _parse_ts(o["ts"])
        except KeyError as e:
            raise SystemExit("telemetry 第 %d 行缺字段 %s" % (i, e))
        except ValueError as e:
            raise SystemExit("telemetry 第 %d 行时间戳不可解析: %s" % (i, e))
        rows.append((ts, kv or {}))
    return rows


def tokens_in_window(tel, t0, t1):
    """窗口内 llm_call 的 token 合计; 无调用 ⇒ None (不是 0)。"""
    if not tel:
        return None
    p = c = n = 0
    for ts, kv in tel:
        if t0 <= ts <= t1:
            n += 1
            p += int(kv.get("prompt_tokens") or 0)
            c += int(kv.get("completion_tokens") or 0)
    return None if n == 0 else {"prompt": p, "completion": c, "calls": n}


def metrics(run, tel):
    # run_probe.py:268 的 ts 与 elapsed_s 同时写入 ⇒ ts 是**结束**时刻
    # 窗口 = [ts - elapsed_s, ts]; 锚点写反 ⇒ 只捞到窗口外的调用 ⇒ 空心 token 指标
    t1 = _parse_ts(run["ts"])
    t0 = t1 - timedelta(seconds=float(run["elapsed_s"]))
    tk = tokens_in_window(tel, t0, t1)
    n_tasks, total, passed = int(run["n_tasks"]), int(run["total"]), int(run["passed"])
    chars = [int(t.get("reply_chars") or 0) for t in run.get("per_task") or []]
    pt = run.get("per_task") or []
    tasks_ok = sum(1 for x in pt if x.get("mode") == "ok")
    m = {
        "file": run.get("_file") or run.get("file") or "?",
        "ts": run["ts"], "solver": run["solver"],
        "solver_id": run.get("solver_id") or run["solver"], "oracle": bool(run.get("oracle")),
        "seed": run.get("seed"), "kind_arg": run.get("kind_arg"),
        "taskset_sha": run["taskset_sha"], "n_tasks": n_tasks,
        "passed": passed, "total": total, "rate": float(run["rate"]),
        "elapsed_s": float(run["elapsed_s"]),
        "s_per_task": float(run["elapsed_s"]) / n_tasks,
        "reply_chars_mean": (sum(chars) / len(chars)) if chars else None,
        "tasks_ok": tasks_ok, "task_rate": (tasks_ok / len(pt)) if pt else None,
        "taxonomy": dict(run["taxonomy"]),
        "by_kind": dict(run.get("by_kind") or {}),
        "by_family": dict(run.get("by_family") or {}),
        "tokens": tk,
    }
    m["tok_per_task"] = (tk["prompt"] + tk["completion"]) / n_tasks if tk else None
    m["tok_per_passed_case"] = ((tk["prompt"] + tk["completion"]) / passed) if (tk and passed) else None
    return m


def unknown_modes(tax):
    return {k: v for k, v in (tax or {}).items() if k not in KNOWN_MODES}


def ledger_key(m):
    return "|".join([str(m["solver"]), str(m["taskset_sha"]), str(m["ts"])])


def ledger_append(path, rows):
    seen = set()
    if os.path.exists(path):
        for line in io.open(path, encoding="utf-8", errors="replace"):
            line = line.strip()
            if line:
                seen.add(ledger_key(json.loads(line)))
    added = 0
    with io.open(path, "a", encoding="utf-8") as fh:
        for m in rows:
            if ledger_key(m) in seen:
                continue
            fh.write(json.dumps(m, ensure_ascii=False) + "\n")
            added += 1
    return added


def _delta(a, b, key, pct=False):
    x, y = a.get(key), b.get(key)
    if x is None or y is None:
        return "n/a"
    d = y - x
    if pct:
        return "%+.4f" % d
    if isinstance(x, int) and isinstance(y, int):
        return "%+d" % d
    return "%+.2f" % d


def _fmt(v, nd=4):
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return ("%%.%df" % nd) % v
    return str(v)


def render(ms, a=None, b=None, tel_path="", note=""):
    L = []
    L.append("# 能力自检探针 KPI 台账")
    L.append("")
    L.append("生成时间: %s · 遥测: `%s` · run 数: %d" % (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), tel_path or "(未提供)", len(ms)))
    L.append("")
    L.append("**口径**: 通过率 = 隐藏用例通过数 / 隐藏用例总数(**整题全对才算过**的等价读数见 四); "
             "token 取 run 墙钟窗口 `[ts-elapsed_s, ts]` 内的 `llm_call` 打点合计; "
             "窗口内无调用 ⇒ `n/a`(**不是 0**)")
    L.append("")
    L.append("## 一、总览")
    L.append("")
    L.append("| # | run | solver | 题集sha | 题数 | 用例 | 整题全对 | 通过率 | 耗时(s) | s/题 | tokens(p/c) | tok/题 |")
    L.append("|--|--|--|--|--|--|--|--|--|--|--|--|")
    for i, m in enumerate(ms):
        tk = m.get("tokens")
        tks = "n/a" if not tk else "%d/%d" % (tk["prompt"], tk["completion"])
        L.append("| %d | %s | %s | %s | %s | %s | %s/%s | %s | %s | %s | %s | %s |" % (
            i, m.get("file"), m.get("solver"), str(m.get("taskset_sha") or "")[:12],
            m.get("n_tasks"), m.get("total"),
            m.get("tasks_ok"), m.get("n_tasks"),
            _fmt(m.get("rate")), _fmt(m.get("elapsed_s"), 2), _fmt(m.get("s_per_task"), 2), tks,
            _fmt(m.get("tok_per_task"), 1)))
    L.append("")

    if a is not None and b is not None:
        L.append("## 二、对比 A → B")
        L.append("")
        L.append("A = `%s` (%s, 题集 %s) · B = `%s` (%s, 题集 %s)"
                 % (a.get("file"), a.get("solver"), str(a.get("taskset_sha") or "")[:12],
                    b.get("file"), b.get("solver"), str(b.get("taskset_sha") or "")[:12]))
        L.append("")
        same = (a.get("taskset_sha") == b.get("taskset_sha")) and bool(a.get("taskset_sha"))
        L.append("> 题集是否同一批: **%s** %s" % (
            "是" if same else "否",
            "(不同题集 ⇒ 通过率 Δ 不可直接解读为能力变化, 必须在同一题集上再比)" if not same else "(同批题集 ⇒ Δ 可比)"))
        L.append("")
        L.append("| 指标 | A | B | Δ |")
        L.append("|--|--|--|--|")
        rows = [("整题全对率", "task_rate", True), ("整题全对题数", "tasks_ok", False),
                ("通过率(用例级)", "rate", True), ("通过用例数", "passed", False),
                ("用例总数", "total", False), ("题数", "n_tasks", False),
                ("耗时(s)", "elapsed_s", False), ("s/题", "s_per_task", False),
                ("回复字符均值", "reply_chars_mean", False), ("tok/题", "tok_per_task", False),
                ("tok/通过用例", "tok_per_passed_case", False)]
        for label, key, pct in rows:
            L.append("| %s | %s | %s | %s |" % (label, _fmt(a.get(key)), _fmt(b.get(key)),
                                                _delta(a, b, key, pct)))
        L.append("")

    L.append("## 三、按族分层 (B 或最后一个 run 之前的最新 run)")
    L.append("")
    ref = b or ms[-1]
    L.append("run = `%s` · 题集 `%s`" % (ref.get("file"), str(ref.get("taskset_sha") or "")[:12]))
    L.append("")
    L.append("| 族 | 题数 | 通过率 | 用例 | 模式 |")
    L.append("|--|--|--|--|--|")
    for k, v in sorted((ref.get("by_family") or {}).items()):
        if isinstance(v, dict):
            modes = ", ".join("%s=%s" % (a, b) for a, b in sorted((v.get("modes") or {}).items()))
            L.append("| %s | %s | %.4f | %s/%s | %s |"
                     % (k, v.get("n"), float(v.get("rate") or 0.0), v.get("passed"), v.get("total"), modes or "-"))
        else:
            L.append("| %s | - | %s | - | - |" % (k, _fmt(v)))
    L.append("")

    L.append("## 四、失败模式分布 + 未知键审计")
    L.append("")
    L.append("| run | 模式 | 计数 |")
    L.append("|--|--|--|")
    for m in ms:
        for k, v in sorted((m.get("taxonomy") or {}).items()):
            L.append("| %s | %s | %d |" % (m.get("file"), k, v))
    unknown = {m.get("file"): unknown_modes(m.get("taxonomy")) for m in ms}
    unknown = {k: v for k, v in unknown.items() if v}
    L.append("")
    L.append("未知模式键(不得丢弃, 单列备查): %s" % (json.dumps(unknown, ensure_ascii=False) if unknown else "无"))
    L.append("")

    L.append("## 五、诚实边界")
    L.append("")
    no_tok = [m.get("file") for m in ms if not m.get("tokens")]
    L.append("- token 读数缺失(窗口内无 llm_call 打点)的 run: %s"
             % (", ".join(no_tok) if no_tok else "无"))
    L.append("- 通过率=用例级读数; **整题全对** 的题数见 run 摘要 `per_task[].mode==ok` 计数")
    L.append("- 判定口径 = 交付物真实形态(围栏 / 回复区裸代码 / 落盘产物)取最长可编译候选; "
             "口径错会造成**反向空心指标**(满分记 0 分), 已有永久负控")
    L.append("- 题集饱和(通过率 1.0)时该读数对能力提升不敏感 ⇒ 需看对抗族与作弊解负控")
    if note:
        L.append("- %s" % note)
    L.append("")
    return "\n".join(L)


def pick(ms, key):
    for i, m in enumerate(ms):
        if str(i) == str(key) or key in m["file"] or key == m["solver"]:
            return m
    raise InputError("匹配不到 run: %s" % key)


# ---------------------------------------------------------------- 负控

def selftest() -> int:
    import tempfile
    from datetime import timedelta
    ok, fails = 0, []

    def chk(name, cond, detail=""):
        nonlocal ok
        if cond:
            ok += 1
            print("  [PASS] %s %s" % (name, detail))
        else:
            fails.append(name)
            print("  [FAIL] %s %s" % (name, detail))

    print("selftest: KPI 打点负控")
    base = {"ts": "2026-09-13T23:00:00+0800", "solver": "agent", "rate": 0.5, "passed": 3,
            "total": 6, "n_tasks": 2, "elapsed_s": 60.0, "taxonomy": {"ok": 3, "wrong_output": 3},
            "taskset_sha": "abc123", "per_task": [{"reply_chars": 100}, {"reply_chars": 200}]}

    # 1. 缺字段必须 error
    for miss in ("rate", "taskset_sha", "ts", "taxonomy"):
        d = dict(base)
        d.pop(miss)
        try:
            validate_run(d, "t.json")
            chk("缺 %s 必须 error" % miss, False, "竟然通过")
        except InputError:
            chk("缺 %s 必须 error" % miss, True)

    # 2. 除零保护
    for bad in ({"total": 0}, {"n_tasks": 0}):
        d = dict(base)
        d.update(bad)
        try:
            validate_run(d, "t.json")
            chk("除零保护 %s" % list(bad)[0], False, "竟然通过")
        except InputError:
            chk("除零保护 %s" % list(bad)[0], True)

    d = dict(base)
    d.update({"passed": 0, "rate": 0.0})
    m0 = metrics(d, [])
    chk("passed=0 时 tok/通过用例 = n/a 不崩", m0["tok_per_passed_case"] is None and m0["tokens"] is None)

    # 3. 时间窗 (真语义: ts=结束时刻 ⇒ [ts-elapsed, ts])
    t_end = _parse_ts(base["ts"])
    t_beg = t_end - timedelta(seconds=float(base["elapsed_s"]))
    tel = [(t_beg + timedelta(seconds=5), {"prompt_tokens": 1000, "completion_tokens": 500}),
           (t_end + timedelta(seconds=400), {"prompt_tokens": 99, "completion_tokens": 99})]
    tk = tokens_in_window(tel, t_beg, t_end)
    chk("窗口 [ts-elapsed, ts] 取到窗内调用",
        tk == {"prompt": 1000, "completion": 500, "calls": 1}, repr(tk))
    rev = tokens_in_window(tel, t_end, t_end + timedelta(seconds=120))
    chk("锚点写反([ts, ts+elapsed]) ⇒ 读不到窗内调用",
        rev is None, repr(rev))
    mm = metrics(dict(base, elapsed_s=120.0), tel)
    chk("metrics 的 token 必须来自 [ts-elapsed, ts] 窗内",
        mm["tokens"] == {"prompt": 1000, "completion": 500, "calls": 1}, repr(mm["tokens"]))
    chk("窗口内无调用 ⇒ None(不是 0)",
        tokens_in_window(tel, t_end + timedelta(seconds=700), t_end + timedelta(seconds=800)) is None)
    chk("无遥测 ⇒ None(不是 0)", tokens_in_window([], t_beg, t_end) is None)

    # 4. 未知 taxonomy 键不得丢弃
    u = unknown_modes({"ok": 1, "weird_mode": 2})
    chk("未知模式键被单列而非丢弃", u == {"weird_mode": 2}, repr(u))

    # 5. Δ 计算正确
    A: dict = {"rate": 0.5, "passed": 3, "total": 6, "n_tasks": 2, "elapsed_s": 60.0,
               "s_per_task": 30.0, "reply_chars_mean": 150.0, "tok_per_task": None,
               "tok_per_passed_case": None}
    B: dict = dict(A, rate=1.0, passed=6)
    chk("Δ(通过率) 精确", _delta(A, B, "rate", True) == "+0.5000", _delta(A, B, "rate", True))
    d0 = dict(base, per_task=[{"mode": "ok"}, {"mode": "wrong_output"}], _file="z.json")
    mz = metrics(d0, [])
    chk("整题全对口径: 1/2 ⇒ task_rate=0.5(不放水)",
        mz["tasks_ok"] == 1 and mz["task_rate"] == 0.5 and mz["rate"] == 0.5,
        "tasks_ok=%s task_rate=%s" % (mz["tasks_ok"], mz["task_rate"]))
    chk("Δ(通过用例数)", _delta(A, B, "passed") == "+3", _delta(A, B, "passed"))
    chk("7 位小数遥测时间戳可解析(曾静默丢 ⇒ token 全 None)",
        _parse_ts("2026-09-13T15:08:03.9531864Z") == _parse_ts("2026-09-13T23:08:03.953186+0800"),
        repr(_parse_ts("2026-09-13T15:08:03.9531864Z")))
    chk("无时区时间戳按本机 +0800 解释",
        _parse_ts("2026-09-13T23:08:03").utcoffset() == timedelta(hours=8))
    try:
        _parse_ts("2026-09-13 23:08:03 ???")
        bad = None
    except ValueError as e:
        bad = str(e)
    chk("非法时间戳必须抛错(不得静默跳过)", bad is not None and "无法解析" in (bad or ""), bad)

    chk("Δ 遇 None 记 n/a", _delta(A, B, "tok_per_task") == "n/a")

    # 6. 台账去重
    with tempfile.TemporaryDirectory() as td:
        lp = os.path.join(td, "kpi.jsonl")
        rows = [metrics(dict(base, _file="a.json"), [])]
        n1 = ledger_append(lp, rows)
        n2 = ledger_append(lp, rows)
        lines = [l for l in io.open(lp, encoding="utf-8") if l.strip()]
        chk("台账同 run 不重复追加", (n1, n2, len(lines)) == (1, 0, 1), "%d/%d/%d" % (n1, n2, len(lines)))

        # 7. 报告渲染: 同题集/异题集标注 + 未知键出现
        A.update({"file": "x.json", "taxonomy": {"ok": 1}, "taskset_sha": "aaa", "by_family": {"f": 1.0}})
        B.update({"file": "x.json", "taxonomy": {"ok": 1, "odd": 2}, "taskset_sha": "bbb", "by_family": {"f": 1.0}})
        rp = render([A, B], a=A, b=B, tel_path="(n/a)")
        chk("异题集时报告显式标注不可比", "不同题集" in rp)
        chk("报告含未知模式键", "odd" in rp and "未知模式键" in rp)
        chk("报告含台账表头", "| # | run | solver |" in rp)

    # 8. 路径解析: `--run` 与 `--glob` 取**并集** (旧「或」语义写不出「固定基线 ∪ 轮产物」)
    with tempfile.TemporaryDirectory() as td2:
        for n in ("a.json", "b.json", "c.json"):
            io.open(os.path.join(td2, n), "w", encoding="utf-8").write("{}")
        g = os.path.join(td2, "*.json")
        a_p, c_p = os.path.join(td2, "a.json"), os.path.join(td2, "c.json")
        got = resolve_paths([a_p], [g])
        chk("并集: --run 与 --glob 共存得全量(含去重)", len(got) == 3 and len(set(got)) == 3, str(got))
        chk("并集: 显式项在前(决定报告 # 列序)", resolve_paths([c_p], [g])[0] == c_p)
        chk("负控: 显式 --glob 时不并入缺省模式(防越界吸run)",
            resolve_paths([], [g]) == sorted(os.path.join(td2, n) for n in ("a.json", "b.json", "c.json")))
        chk("负控: 未给 --glob 才用缺省模式", resolve_paths([], None) == sorted(_glob.glob(DEFAULT_GLOB)))

    print("selftest %d/%d" % (ok, ok + len(fails)))
    return 0 if not fails else 1


# ---------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", action="append", default=None,
                    help="run 摘要 glob, **可重复**; 与 --run 取并集 (缺省 %s)" % DEFAULT_GLOB)
    ap.add_argument("--run", action="append", default=[])
    ap.add_argument("--tel", default="data/telemetry/host.jsonl")
    ap.add_argument("--ledger", default="data/probe/kpi.jsonl")
    ap.add_argument("--report", default="")
    ap.add_argument("--compare", nargs=2, default=None, metavar=("A", "B"))
    ap.add_argument("--no-ledger", action="store_true")
    ap.add_argument("--note", default="")
    ap.add_argument("--json", dest="json_out", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    try:
        paths = resolve_paths(a.run, a.glob)
        runs = load_runs(paths)
        tel = load_telemetry(a.tel)
        ms = [metrics(r, tel) for r in runs]
        A = B = None
        if a.compare:
            A, B = pick(ms, a.compare[0]), pick(ms, a.compare[1])
        note = a.note or ("遥测文件缺失, 全部 token 记 n/a: %s" % a.tel if not tel else "")
        text = render(ms, A, B, a.tel, note)
        if a.report:
            os.makedirs(os.path.dirname(a.report) or ".", exist_ok=True)
            io.open(a.report, "w", encoding="utf-8").write(text + "\n")
            print("wrote %s" % a.report)
        else:
            print(text)
        added = 0 if a.no_ledger else ledger_append(a.ledger, ms)
        if not a.no_ledger:
            print("ledger %s: +%d 行 (共 %d run)" % (a.ledger, added, len(ms)))
        if a.json_out:
            io.open(a.json_out, "w", encoding="utf-8").write(
                json.dumps({"runs": ms}, ensure_ascii=False, indent=1))
    except InputError as e:
        print("kpi_probe error: %s" % e)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
