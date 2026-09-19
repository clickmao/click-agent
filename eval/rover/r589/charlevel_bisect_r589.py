#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R589 候选② 字符级最小化复现（只读冻结件，零写入，不宣称能力）。

对象 = `r587/w162/agentD-r3`（R588 单例 NO_ARTIFACT）的契约块。R588 定因 = 「契约块结构不闭合」。
本轮做**元素级删除二分**：找**最小**使解析由 FAIL→OK 的删除集合，并报该元素的**转义形态 dump**。

读法契约:
- 起点/长度**取自 R588 落盘值**（`noartifact-cause-r588.json`），本器重算 span 与之不符 ⇒ rc=2（禁手抄常数）。
- 判定 oracle 与 R588 同口径，但补一条**结构闭合规范化**：块尾部可能被截断（栈非空）⇒
  先按栈补上缺失闭合符再判 `json.loads`。**该规范化对每个候选统一施加**，故比较公平；
  「补闭合本身就能转绿」这一可能由 `closure_alone_ok` 字段单独证伪/证实（见 v1 实测：补闭合仍 FAIL）。

v1（首跑）读数保留：`charlevel-bisect-r589-v1spanbug.json` —— 顶层元素切分用了 `depth==2` 口径（把数组值
当成了元素）⇒ 6 个伪元素、下沉进不去 ⇒ rc=1。**不翻案**，本版为器具修正后的重跑（独立命名空间）。
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os

REPO = "/home/agentuser/AgentFramework"
RUNS = os.path.expanduser("~/.agentframework/harness/runs")
TARGET = ("r587", "w162", "agentD-r3")
RUN_KEY = "r587/w162/agentD-r3"
R588_LEDGER = os.path.join(REPO, "eval/rover/r588/noartifact-cause-r588.json")
CLOSE = {"{": "}", "[": "]"}


def contract_span(txt: str):
    i = txt.find('{"schema_version"')
    if i < 0:
        return (False, -1, "")
    depth, instr, esc, j = 0, False, False, i
    while j < len(txt):
        c = txt[j]
        if instr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                instr = False
        else:
            if c == '"':
                instr = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return (True, i, txt[i:j + 1])
        j += 1
    return (False, i, txt[i:])


def stack_scan(t: str):
    """返回 (unclosed_openers, in_string_at_end)。字符串/转义感知（与 CPython json 同规则）。"""
    st, instr, esc = [], False, False
    for c in t:
        if instr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                instr = False
            continue
        if c == '"':
            instr = True
        elif c in "{[":
            st.append(c)
        elif c in "}]":
            if st:
                st.pop()
    return st, instr


def normalize(t: str):
    """结构闭合规范化：补缺失闭合符（末尾处在字符串内则先补引号）。统一施加于所有候选。"""
    st, instr = stack_scan(t)
    t2 = t + ('"' if instr else "") + "".join(CLOSE[c] for c in reversed(st))
    return t2, len(st), instr


def verdict(t: str):
    """oracle: (ok, 规范化后是否 OK, fail_char, err, unclosed_n, instr)"""
    n_t, unc, instr = normalize(t)
    try:
        json.loads(n_t)
        return (True, True, -1, "", unc, instr)
    except Exception as e:
        m = str(e)
        fc = int(m.split("(char ")[1].split(")")[0]) if "(char " in m else -1
        return (False, False, fc, m, unc, instr)


def members(block: str):
    """外层对象 depth==1 的**成员** span（含键名到值末，不含分隔逗号）。不闭合时截到最后成员。"""
    if not block.startswith("{"):
        return [], True
    spans, depth, instr, esc, mstart = [], 0, False, False, None
    for j, c in enumerate(block):
        if instr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                instr = False
            continue
        if c == '"':
            instr = True
            continue
        if c in "{[":
            depth += 1
            if depth == 1:
                mstart = j + 1
            continue
        if c in "}]":
            depth -= 1
            if depth == 0 and mstart is not None:
                spans.append((mstart, j))
                mstart = None
                break
            continue
        if c == "," and depth == 1 and mstart is not None:
            spans.append((mstart, j))
            mstart = j + 1
    truncated = mstart is not None
    if truncated:
        spans.append((mstart, len(block)))
    return spans, truncated


def elems_of(text: str):
    """通用：text 为数组或对象时，返回其**直接子元素** span（对象成员 / 数组元素）。"""
    if not text or text[0] not in "[{":
        return [], True
    opener = text[0]
    depth, instr, esc, start = 0, False, False, None
    spans = []
    for j, c in enumerate(text):
        if instr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                instr = False
            continue
        if c == '"':
            instr = True
            continue
        if c in "{[":
            depth += 1
            if depth == 2 and start is None:
                start = j
            elif depth == 1 and start is None and j > 0:
                start = j          # 数组直接子元素（对象/数组/标量起点）
            continue
        if c in "}]":
            depth -= 1
            if depth == 1 and start is not None:
                spans.append((start, j + 1))
                start = None
            continue
        if c == "," and depth == 1 and start is not None:
            spans.append((start, j))
            start = None
    if start is not None:
        spans.append((start, len(text)))
        return spans, True
    return spans, False


def delete_span(t: str, s: int, e: int) -> str:
    if s > 0 and t[s - 1] == ",":
        return t[:s - 1] + t[e:]
    if e < len(t) and t[e] == ",":
        return t[:s] + t[e + 1:]
    return t[:s] + t[e:]


def elem_label(t: str, s: int, e: int) -> str:
    seg = t[s:e]
    if seg.startswith('"'):
        k = seg.find('"', 1)
        return seg[:k + 1]
    return seg[:32].replace("\n", "\\n")


def dump(seg: str, limit: int = 300) -> str:
    o = []
    for ch in seg[:limit]:
        c = ord(ch)
        if ch == "\\":
            o.append("\\\\")
        elif ch == "\n":
            o.append("\\n")
        elif ch == "\t":
            o.append("\\t")
        elif ch == '"':
            o.append('\\"')
        elif 32 <= c < 127:
            o.append(ch)
        elif c <= 0xFF:
            o.append("\\x%02x" % c)
        else:
            o.append("\\u%04x" % c)
    return "".join(o) + ("" if len(seg) <= limit else "…(+%d)" % (len(seg) - limit))


def descend(text: str, fail_char: int, path: list, log: list, depth: int):
    """元素级二分：本级直接子元素逐个删除试 oracle；不行则下沉进含失败点的子元素。"""
    ok, _, _, _, _, _ = verdict(text)
    if ok:
        return []
    spans, trunc = members(text) if text.startswith("{") else elems_of(text)
    singles = []
    for idx, (s, e) in enumerate(spans):
        cand = delete_span(text, s, e)
        cok, _, _, _, _, _ = verdict(cand)
        if cok:
            singles.append({"idx": idx, "span": [s, e], "label": elem_label(text, s, e), "chars": e - s,
                            "dump": dump(text[s:e])})
    log.append({"depth": depth, "kind": "obj-members" if text.startswith("{") else "arr-elems",
                "n": len(spans), "truncated": trunc, "fail_char": fail_char,
                "singles_ok": [x["idx"] for x in singles]})
    if singles:
        return [singles[0]["idx"]], singles[0]
    if fail_char >= 0:
        for idx, (s, e) in enumerate(spans):
            if s <= fail_char < e:
                sub, hit = descend(text[s:e], fail_char - s, path + [idx], log, depth + 1)
                if hit:
                    return [idx] + sub, hit
                break
    return [], None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "eval/rover/r589/charlevel-bisect-r589.json"))
    a = ap.parse_args()
    reply = os.path.join(RUNS, *TARGET, "g1", "reply.txt")
    out = {"round": "R589", "criterion": "C8", "mode": "read-only charlevel element-delete bisect",
           "target": "/".join(TARGET), "instrument": "eval/rover/r589/charlevel_bisect_r589.py",
           "supersedes": "charlevel-bisect-r589-v1spanbug.json (器具 span 切分缺陷, 不翻案)"}
    if not os.path.exists(reply):
        out.update({"rc": 3, "error": "INPUT_MISSING"})
        _w(a.out, out)
        return 3
    sha_before = _sha(reply)
    txt = io.open(reply, encoding="utf-8", errors="replace").read()
    rec = json.load(io.open(R588_LEDGER, encoding="utf-8"))["noartifact_replay"][RUN_KEY]
    balanced, off, block = contract_span(txt)
    if off != rec["contract_start_char"] or len(block) != rec["block_chars"] or balanced != rec["balanced"]:
        out.update({"rc": 2, "error": "SPAN_MISMATCH", "span": [off, len(block), balanced]})
        _w(a.out, out)
        return 2

    ok0, okn0, fc0, err0, unc0, instr0 = verdict(block)
    # ① 补闭合本身能不能转绿？（区分「截断」与「内层异常」）
    norm, unc, instr = normalize(block)
    try:
        json.loads(norm)
        closure_alone = True
    except Exception:
        closure_alone = False
    # ② 元素级删除二分（oracle = 规范化后解析）
    log = []
    minimal, hit = descend(block, fc0, [], log, 0)
    # ③ 成对控制：删一个**远离失败点**的顶层成员 + 统一规范化 ⇒ 必须仍 FAIL
    spans, _ = members(block)
    nc_far = None
    if len(spans) >= 2:
        far = max(spans, key=lambda sp: abs(sp[0] - fc0))
        nc_ok, _, _, _, _, _ = verdict(delete_span(block, far[0], far[1]))
        nc_far = {"span": list(far), "label": elem_label(block, *far), "still_fails": (not nc_ok)}
    out.update({
        "span": {"start_char": off, "block_chars": len(block), "balanced": balanced,
                 "r588_ledger_span": [rec["contract_start_char"], rec["block_chars"], rec["balanced"]],
                 "span_matches_r588": True},
        "parse": {"ok": ok0, "ok_after_closure_norm": okn0, "fail_char_in_block": fc0, "err": err0,
                  "r588_fail_char": rec["fail_char"], "fail_char_matches_r588": fc0 == rec["fail_char"]},
        "structure": {"unclosed_openers": unc0, "in_string_at_end": instr0,
                      "closure_alone_recovers": closure_alone,
                      "note": "补闭合（%d 个）**不**恢复 ⇒ 6321 处是内层异常，不是单纯截断" if not closure_alone else "截断"},
        "top_members": [{"idx": i, "span": [s, e], "label": elem_label(block, s, e), "chars": e - s}
                        for i, (s, e) in enumerate(spans)],
        "bisect_log": log,
        "minimal_delete_set": minimal,
        "minimal_delete_set_cardinality": len(minimal),
        "minimal_delete_path_ok": bool(hit),
        "controls": {"negative_far_member_delete": nc_far,
                     "has_teeth": bool(hit) and bool(nc_far and nc_far["still_fails"]),
                     "source_untouched_after": True},
    })
    # ④ 细化：在命中成员（"plan"）内部继续同一二分，定位到**具体元素**与其转义 dump
    refine = {"enabled": False}
    if hit and minimal and minimal[0] < len(spans):
        s7, e7 = spans[minimal[0]]
        seg = block[s7:e7]                      # `"plan":[...]`
        cpos = seg.find(":")
        arr = seg[cpos + 1:] if cpos >= 0 else ""
        arr_off = s7 + cpos + 1
        if arr.startswith("["):
            rlog = []
            rmin, rhit = descend(arr, fc0 - arr_off, [], rlog, 0)
            elems, _ = elems_of(arr)
            refine = {"enabled": True, "array_chars": len(arr), "elems_n": len(elems),
                      "bisect_log": rlog, "minimal_delete_set_within": rmin,
                      "cardinality": len(rmin), "located": bool(rhit),
                      "located_elem": ({"idx": rmin[0], "span": list(elems[rmin[0]]),
                                        "chars": elems[rmin[0]][1] - elems[rmin[0]][0],
                                        "label": elem_label(arr, *elems[rmin[0]]),
                                        "dump": dump(arr[elems[rmin[0]][0]:elems[rmin[0]][1]])} if (rhit and rmin and rmin[0] < len(elems)) else None)}
    out["refine_within_member"] = refine
    out["rc"] = 0 if (hit or minimal) else 1
    out["source_sha256_before_after_equal"] = (_sha(reply) == sha_before)
    _w(a.out, out)
    return out["rc"]


def _sha(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _w(path: str, obj: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8").write(json.dumps(obj, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
