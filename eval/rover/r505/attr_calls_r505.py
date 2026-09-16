#!/usr/bin/env python3
"""R505 逐调用归因（判据② 的取证器）: adapter 落盘 side-*.json → 每题调用构成。

契约（机械面, 无模型裁判）:
  输入 = adapter 目录（side-codex-*.json / side-agent-*.json）, 冻结题集, 可选 manifest（逐文件 sha256）
  输出 = JSON: {side: {calls, by_task: [...], unmatched: [...], ambiguous: [...]}}

归因规则（确定性, fail-closed 不猜）:
  每条调用取 `request.upstream_request.tail_messages` 里**最后一条 role==user** 的 `head`（adapter 落盘=前 200 字符）;
  参考串两类: (a) 首轮 = task["prompt"][:200]; (b) 修正轮 = run_probe.correction_prompt(task)[:200];
  命中 = head 以参考串为前缀（逐位相同）且唯一; 多命中 ⇒ 取参考串最长者并记 ambiguous;
  零命中 ⇒ 退化为最长公共前缀 LCP >= 60 且领先第二名 >= 20 ⇒ 记 approx; 否则记 unmatched（禁归到"其它"）。
  修正轮命中 ⇒ kind="fix"（首轮 kind="first"）。

rc: 0 全覆盖（unmatched==0）; 2 有未归因/歧义调用; 3 fail-closed（缺输入/参考串不可派生）
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "eval", "probe"))


def load(p):
    return json.load(open(p, encoding="utf-8-sig"))


def head_of_user_msg(rec: dict) -> str | None:
    msgs = ((rec.get("request") or {}).get("upstream_request") or {}).get("tail_messages") or []
    for m in reversed(msgs):
        if m.get("role") == "user" and m.get("head"):
            return m["head"]
    return None


def lcp(a: str, b: str) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def _seq(p: str) -> int:
    """文件名尾号 = adapter 的**请求到达序**（进程内计数器）⇒ 归因第二阶段的「同一轮对话」判据。"""
    import re
    m = re.search(r"-(\d+)\.json$", os.path.basename(p))
    return int(m.group(1)) if m else 0


def build_refs(taskset: str):
    """每题两条参考串: 首轮题面 / 修正文案（后者由 probe 的确定性文案器派生）。"""
    import run_probe as rp  # noqa: E402
    ts = load(taskset)
    refs = []
    for t in ts:
        r_first = (t.get("prompt") or "")[:200]
        try:
            r_fix = (rp.correction_prompt(t) or "")[:200]
        except Exception:
            r_fix = ""
        refs.append({"tid": t["tid"], "family": t.get("family"), "kind": t.get("kind"),
                     "first": r_first, "fix": r_fix})
    return ts, refs


MARKER = re.compile(r"^\s*(?:\[[^\]]{2,24}\]|【[^】]{2,24}】)\s*")
TAIL_MARK = re.compile(r"\s*[（(](?:只回答本微问题|只依据本微问题)[^）)]*[）)]\s*$")


def strip_markers(head: str) -> str:
    """去掉管线在题面外包裹的标记（如 [微步骤隔离问询]）与尾注（如 (只回答本微问题, 不引申)）。

    这是**归因口径**的一部分, 不是内容改写: 原始 head 逐字留档于 rows[].resp/patched 字段。
    """
    s = head
    for _ in range(3):
        s2 = MARKER.sub("", s)
        if s2 == s:
            break
        s = s2
    for _ in range(2):
        s2 = TAIL_MARK.sub("", s)
        if s2 == s:
            break
        s = s2
    return s


def fragment_match(head_norm: str, refs: list, minlen: int = 40):
    """题面**片段**命中（微步骤问询会把题面切碎再问）: 取归一化 head 的最长前缀在题面里出现, 取唯一最长者。"""
    best = []
    for r in refs:
        for key in ("first", "fix"):
            ref = r.get(key) or ""
            if not ref:
                continue
            probe = head_norm[:200].strip()
            n = min(len(probe), 200)
            while n >= minlen:
                frag = probe[:n]
                if frag in ref:
                    best.append((n, r["tid"], r["family"], key))
                    break
                n -= 8
    if not best:
        return None
    best.sort(reverse=True)
    top = best[0]
    nxt = next((b for b in best[1:] if b[1] != top[1]), None)
    if nxt is None or top[0] - nxt[0] >= 20:
        return {"tid": top[1], "turn": "fix" if top[3] == "fix" else "first", "family": top[2],
                "match": "fragment", "score": top[0], "ambiguous": False}
    return {"tid": None, "turn": None, "family": None, "match": "unmatched",
            "score": top[0], "ambiguous": True}


def attribute(head: str, refs: list):
    got = _attribute_prefix(head, refs)
    if got and got.get("tid"):
        return got
    norm = strip_markers(head)
    if norm != head:
        got2 = _attribute_prefix(norm, refs)
        if got2 and got2.get("tid"):
            got2["match"] = "exact+marker_stripped" if got2["match"] == "exact" else "approx+marker_stripped"
            return got2
        frag = fragment_match(norm, refs)
        if frag and frag.get("tid"):
            return frag
    frag = fragment_match(norm, refs)
    if frag and frag.get("tid"):
        return frag
    if got and got.get("ambiguous"):
        return got
    return got or {"tid": None, "turn": None, "family": None, "match": "unmatched",
                   "score": 0, "ambiguous": False}


def _attribute_prefix(head: str, refs: list):
    exact = []
    for r in refs:
        for k in ("first", "fix"):
            ref = r[k]
            if not ref:
                continue
            if head.startswith(ref):
                exact.append((len(ref), r["tid"], "fix" if k == "fix" else "first", r["family"]))
            elif len(head) >= 60 and ref.startswith(head):
                # head 是被截断的变体（如去掉 [微步骤隔离问询] 标记后只剩 187 字符）: 反向包含同样成立
                exact.append((len(head), r["tid"], "fix" if k == "fix" else "first", r["family"]))
    if exact:
        exact.sort(reverse=True)
        best = exact[0]
        multi = [e for e in exact[1:] if e[0] == best[0] and e[1] != best[1]]
        if multi:
            # 同长度多题命中 ⇒ 参考串本身不可分辨（如通用修正文案）⇒ fail-closed 交第二阶段, 禁挑一个
            return {"tid": None, "turn": None, "family": None, "match": "ambiguous",
                    "score": best[0], "ambiguous": True}
        return {"tid": best[1], "turn": best[2], "family": best[3], "match": "exact",
                "score": best[0], "ambiguous": False}
    scored = []
    for r in refs:
        for k in ("first", "fix"):
            if r[k]:
                scored.append((lcp(head, r[k]), r["tid"], "fix" if k == "fix" else "first", r["family"]))
    if not scored:
        return None
    scored.sort(reverse=True)
    top = scored[0]
    second = next((s for s in scored[1:] if s[1] != top[1]), None)
    if top[0] >= 60 and (second is None or top[0] - second[0] >= 20):
        return {"tid": top[1], "turn": top[2], "family": top[3], "match": "approx",
                "score": top[0], "ambiguous": False}
    return {"tid": None, "turn": None, "family": None, "match": "unmatched",
            "score": top[0], "ambiguous": False}


def manifest_shas(manifest_path: str | None):
    if not manifest_path or not os.path.exists(manifest_path):
        return {}
    d = load(manifest_path)
    out = {}
    for row in d.get("files") or []:
        out[row["file"]] = row.get("sha256")
    return out


def load_replies(replies_dir: str | None, tag: str | None):
    """本侧每题回复产物（探针落盘）: <dir>/agent<tag>-<tid>.txt → tid: 全文（用于连续性归因的**交叉确认**）。"""
    if not replies_dir or not tag or not os.path.isdir(replies_dir):
        return {}
    out = {}
    for p in glob.glob(os.path.join(replies_dir, "agent%s-*.txt" % tag)):
        base = os.path.basename(p)
        tid = base.rsplit("-", 1)[-1][:-4]
        try:
            out[tid] = open(p, encoding="utf-8-sig", errors="replace").read()
        except OSError:
            pass
    return out


def scan(dirpath: str, refs, manifest_path: str | None = None,
         replies: dict | None = None):
    import hashlib
    sha_map = manifest_shas(manifest_path)
    per_side = defaultdict(list)
    sha_bad = []
    for p in sorted(glob.glob(os.path.join(dirpath, "side-*.json")), key=_seq):
        base = os.path.basename(p)
        rec = load(p)
        side = rec.get("side") or ("codex" if "-codex-" in base else "agent")
        head = head_of_user_msg(rec)
        att = attribute(head, refs) if head else None
        u = ((rec.get("response") or {}).get("usage") or {})
        row = {
            "file": base, "side": side,
            "tid": (att or {}).get("tid"), "turn": (att or {}).get("turn"),
            "family": (att or {}).get("family"), "match": (att or {}).get("match"),
            "ambiguous": (att or {}).get("ambiguous"),
            "resp_head": (((rec.get("response") or {}).get("text") or "")[:200]),
            "in_tokens": int(u.get("prompt_tokens") or u.get("input_tokens") or 0),
            "out_tokens": int(u.get("completion_tokens") or u.get("output_tokens") or 0),
            "cached_tokens": int(u.get("prompt_cache_hit_tokens") or 0),
            "model": ((rec.get("request") or {}).get("upstream_request") or {}).get("model"),
        }
        if sha_map and base in sha_map:
            got = hashlib.sha256(open(p, "rb").read()).hexdigest()
            if got != sha_map[base]:
                sha_bad.append({"file": base, "want": sha_map[base], "got": got})
        per_side[side].append(row)

    # 第二阶段: 同一轮对话的**延续调用**（tool-loop / 修正轮）
    #   adapter 落盘的 tail_messages 只有最后 4 条 ⇒ 深轮次已看不到题面, 首阶段必然未归因。
    #   判据（确定性）: 请求到达序紧邻且前一条已归因 ⇒ 归到同一题, match=continuity（与 prompt 命中分列）。
    #   交叉确认: 若该题有回复产物且本轮产出文本出现在其中 ⇒ reply_confirmed=true。
    for side, rows in per_side.items():
        prev = None
        for r in rows:
            if not r["tid"] and prev is not None and prev.get("tid"):
                r["stage1"] = r.get("match") or "none"
                r["tid"], r["family"], r["turn"], r["match"] = (
                    prev["tid"], prev["family"], "continuation", "continuity")
                r["ambiguous"] = False
                if replies and r["tid"] in replies:
                    probe = (r.get("resp_head") or "").strip()[:60]
                    r["reply_confirmed"] = (probe in replies[r["tid"]]) if probe else None
            prev = r

    out = {}
    for side, rows in per_side.items():
        by_task = {}
        for r in rows:
            key = r["tid"] or ("UNMATCHED:" + r["file"])
            e = by_task.setdefault(key, {"tid": r["tid"], "family": r["family"], "calls": 0,
                                         "first_calls": 0, "fix_calls": 0, "cont_calls": 0,
                                         "reply_confirmed": 0, "reply_checked": 0,
                                         "in_tokens": 0, "out_tokens": 0, "cached_tokens": 0})
            e["calls"] += 1
            e["first_calls"] += 1 if r["turn"] == "first" else 0
            e["fix_calls"] += 1 if r["turn"] == "fix" else 0
            e["cont_calls"] += 1 if r["turn"] == "continuation" else 0
            if "reply_confirmed" in r:
                e["reply_checked"] += 1
                e["reply_confirmed"] += 1 if r["reply_confirmed"] else 0
            e["in_tokens"] += r["in_tokens"]
            e["out_tokens"] += r["out_tokens"]
            e["cached_tokens"] += r["cached_tokens"]
        out[side] = {
            "calls": len(rows),
            "by_task": sorted(by_task.values(), key=lambda e: (-e["calls"], str(e["tid"]))),
            "rows": rows,
            "unmatched": [r["file"] for r in rows if not r["tid"]],
            "ambiguous": [r["file"] for r in rows if r["ambiguous"]],
            "sha_mismatch": sha_bad,
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="adapter 落盘目录")
    ap.add_argument("--taskset", default=os.path.join(HERE, "taskset-r505.json"))
    ap.add_argument("--manifest", default=None, help="逐文件 sha256 清单 (runner 生成)")
    ap.add_argument("--replies-dir", default=os.path.join(REPO, "data", "probe", "replies"),
                    help="探针回复产物目录（连续性归因的交叉确认; 缺则记 null 不阻断）")
    ap.add_argument("--tag", default=None, help="本侧探针 tag（如 agent-r505a）")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    if not os.path.isdir(a.dir):
        print("[致命] adapter 目录不存在: %s ⇒ fail-closed (rc=3)" % a.dir)
        return 3
    if not os.path.exists(a.taskset):
        print("[致命] 缺冻结题集: %s ⇒ rc=3" % a.taskset)
        return 3
    ts, refs = build_refs(a.taskset)
    replies = load_replies(a.replies_dir, a.tag)
    res = scan(a.dir, refs, a.manifest, replies=replies)
    payload = {"dir": a.dir, "taskset": os.path.relpath(a.taskset, REPO), "n_tasks": len(ts),
               "replies_confirmed": {k: v for k, v in {"n_replies": len(replies)}.items()},
               "sides": res}
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
    bad = 0
    for side in sorted(res):
        d = res[side]
        print("== %s: %d 调用" % (side, d["calls"]))
        for e in d["by_task"]:
            print("   %-8s %-26s calls=%d (first=%d fix=%d cont=%d) in=%d out=%d cached=%d reply_ok=%s/%s" % (
                e["tid"] or "UNMATCHED", e["family"], e["calls"], e["first_calls"],
                e["fix_calls"], e.get("cont_calls", 0), e["in_tokens"], e["out_tokens"],
                e["cached_tokens"], e.get("reply_confirmed"), e.get("reply_checked")))
        if d["unmatched"]:
            bad = 1
            print("   [未归因] %s" % ", ".join(d["unmatched"]))
        if d["ambiguous"]:
            bad = 1
            print("   [歧义] %s" % ", ".join(d["ambiguous"]))
        if d["sha_mismatch"]:
            bad = 1
            print("   [快照失配] %s" % json.dumps(d["sha_mismatch"], ensure_ascii=False))
    if a.out:
        print("attribution -> %s" % a.out)
    return 2 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
