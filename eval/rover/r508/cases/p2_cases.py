#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R508 P2 隐藏用例 (逐条机械判对) —— 在**产物目录**内以 `python3 -I -B` 运行。

判据: 真实调用 CLI 产 report.json, 校验其内容; 期望值在**本文件内用独立朴素路径**
(Counter + 手写排序/分位) 现算 —— 不从被测产物内部读。
"""
from __future__ import annotations
import json, math, os, subprocess, sys, tempfile
from collections import Counter

ENTRY = "logpipe.py"
TMP = tempfile.mkdtemp(prefix="p2case-")
IP = "127.0.0.1"
IP2 = "10.0.0.2"
IP3 = "192.168.1.9"


def line(ip, path, code, size, req="GET"):
    return '%s - - [10/Oct/2000:13:55:36 -0700] "%s %s HTTP/1.0" %s %s' % (ip, req, path, code, size)


FIX = "\n".join([
    line(IP, "/a", 200, "100"),
    line(IP, "/b", 200, "200"),
    line(IP2, "/c", 404, "0"),
    "this line is garbage",
    line(IP2, "/d", 500, "300"),
    line(IP3, "/e", 200, "-"),
]) + "\n"


def _p95(vals):
    if not vals:
        return 0
    s = sorted(vals)
    return s[max(0, min(int(math.ceil(0.95 * len(s))) - 1, len(s) - 1))]


def _parse_naive(text):
    """独立朴素路径: 按引号切结构, 不用完整行正则 (与被测实现不同源)。"""
    parsed, bad = [], 0
    for r in text.splitlines():
        if not r.strip():
            bad += 1
            continue
        q = r.split('"')
        if len(q) != 3:
            bad += 1
            continue
        ip_tok = q[0].split()
        tail = q[2].split()
        if not ip_tok or len(tail) != 2 or not tail[0].isdigit() or not (tail[1].isdigit() or tail[1] == "-"):
            bad += 1
            continue
        parsed.append((ip_tok[0], tail[0], 0 if tail[1] == "-" else int(tail[1])))
    return parsed, bad


def _expect(text, top=3):
    parsed, bad = _parse_naive(text)
    st = Counter(p[1] for p in parsed)
    ipc = Counter(p[0] for p in parsed)
    tops = sorted(ipc.items(), key=lambda kv: (-kv[1], kv[0]))[:top]
    return {
        "total": len(parsed),
        "skipped": bad,
        "status_counts": {k: st[k] for k in sorted(st, key=int)},
        "top_ips": [{"ip": k, "count": v} for k, v in tops],
        "p95_bytes": _p95([p[2] for p in parsed]),
    }


def run(text, top=None, name="log"):
    inp = os.path.join(TMP, name + ".log")
    out = os.path.join(TMP, name + ".json")
    with open(inp, "w", encoding="utf-8") as fh:
        fh.write(text)
    argv = [sys.executable, "-I", "-B", ENTRY, "--in", inp, "--out", out]
    if top is not None:
        argv += ["--top", str(top)]
    p = subprocess.run(argv, cwd=os.getcwd(), capture_output=True, text=True, timeout=60)
    rep = None
    if os.path.exists(out):
        with open(out, "rb") as fh:
            blob = fh.read()
        try:
            rep = json.loads(blob.decode("utf-8"))
        except Exception:
            rep = None
    else:
        blob = b""
    return p.returncode, rep, blob


def cases():
    yield "basic_counts_and_p95", c_basic
    yield "top_n_limit", c_top
    yield "top_tie_break_ip_asc", c_tie
    yield "status_keys_sorted", c_status
    yield "all_bad_lines", c_allbad
    yield "empty_file", c_empty
    yield "utf8_no_bom", c_bom
    yield "dash_size_is_zero", c_dash
    yield "p95_nearest_rank_20", c_p95_20
    yield "exit_code_zero", c_rc


def need(c, m):
    if not c:
        raise AssertionError(m)


def _get(text, top=None, name="log"):
    rc, rep, blob = run(text, top, name)
    need(rc == 0, "rc=%s" % rc)
    need(isinstance(rep, dict), "report 缺失/不可解析 (rc=%s)" % rc)
    return rep, blob


def c_basic():
    rep, _ = _get(FIX, None, "basic")
    want = _expect(FIX, 3)
    need(rep == want, "got=%s want=%s" % (json.dumps(rep, ensure_ascii=False), json.dumps(want, ensure_ascii=False)))
    need(rep["total"] == 5 and rep["skipped"] == 1, "total/skipped=%s/%s" % (rep["total"], rep["skipped"]))


def c_top():
    rep, _ = _get(FIX, 1, "top1")
    want1 = _expect(FIX, 1)["top_ips"]
    need(rep["top_ips"] == want1 and len(rep["top_ips"]) == 1, "top1 got=%r want=%r" % (rep["top_ips"], want1))
    rep2, _ = _get(FIX, 99, "top99")
    want = _expect(FIX, 99)
    need(rep2["top_ips"] == want["top_ips"], "got=%r" % (rep2["top_ips"],))


def c_tie():
    txt = "\n".join([line(IP, "/x", 200, "10"), line(IP2, "/y", 200, "10"), line(IP, "/z", 200, "10")]) + "\n"
    rep, _ = _get(txt, 3, "tie")
    want = _expect(txt, 3)["top_ips"]
    need(rep["top_ips"] == want, "got=%r want=%r" % (rep["top_ips"], want))
    txt2 = "\n".join([line(IP2, "/x", 200, "10"), line(IP, "/y", 200, "10")]) + "\n"
    rep2, _ = _get(txt2, 3, "tie2")
    want2 = sorted([(IP, 1), (IP2, 1)], key=lambda kv: (-kv[1], kv[0]))
    need(rep2["top_ips"] == [{"ip": k, "count": v} for k, v in want2],
         "同数按 ip 字符串升序: got=%r want=%r" % (rep2["top_ips"], want2))


def c_status():
    rep, _ = _get(FIX, None, "status")
    keys = list(rep["status_counts"].keys())
    need(keys == ["200", "404", "500"], "keys=%r (须按状态码升序)" % (keys,))
    need(rep["status_counts"] == {"200": 3, "404": 1, "500": 1}, "counts=%r" % (rep["status_counts"],))


def c_allbad():
    txt = "garbage\n\nmore garbage\n"
    rep, _ = _get(txt, None, "allbad")
    need(rep == {"total": 0, "skipped": 3, "status_counts": {}, "top_ips": [], "p95_bytes": 0},
         "got=%s (空行计入 skipped)" % json.dumps(rep))


def c_empty():
    rep, blob = _get("", None, "empty")
    need(rep == {"total": 0, "skipped": 0, "status_counts": {}, "top_ips": [], "p95_bytes": 0}, "got=%s" % json.dumps(rep))
    need(os.path.exists(os.path.join(TMP, "empty.json")), "空输入也必须写出文件")


def c_bom():
    rep, blob = _get(FIX, None, "bom")
    need(blob[:1] == b"{", "文件首字节=%r (禁 BOM)" % blob[:1])
    try:
        blob.decode("utf-8")
    except Exception as e:
        raise AssertionError("非 UTF-8: %s" % e)


def c_dash():
    txt = "\n".join([line(IP, "/a", 200, "-"), line(IP, "/b", 200, "-"), line(IP, "/c", 200, "400")]) + "\n"
    rep, _ = _get(txt, None, "dash")
    need(rep["p95_bytes"] == 400, "p95=%s (期望 400: 两行 0 + 一行 400)" % rep["p95_bytes"])


def c_p95_20():
    txt = "\n".join([line(IP, "/p%d" % i, 200, str(i)) for i in range(1, 21)]) + "\n"
    rep, _ = _get(txt, None, "p95")
    vals = list(range(1, 21))
    want = sorted(vals)[int(math.ceil(0.95 * len(vals))) - 1]
    need(rep["p95_bytes"] == want, "p95=%s want=%s (最近秩法)" % (rep["p95_bytes"], want))


def c_rc():
    rc, rep, _ = run(FIX, None, "rc")
    need(rc == 0, "退出码=%s" % rc)
    need(isinstance(rep, dict), "report 不可解析")


def main():
    if not os.path.exists(ENTRY):
        print("CASE entry_exists FAIL 缺 %s" % ENTRY)
        return 1
    code = 0
    for name, fn in cases():
        try:
            fn()
            print("CASE %s PASS" % name)
        except Exception as e:
            code = 1
            print("CASE %s FAIL %s: %s" % (name, type(e).__name__, str(e)[:300]))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
