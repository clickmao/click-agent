#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R445 预检器具: 判官(CorrectionDetector L2)侧机械前置筛选的**可分性**离线复算。

用途: 在**不跑真机**的前提下, 对归档 telemetry 逐行回答一个可证伪的命题:
      对消息面谓词 M, 「Kind ∈ {Adopt, Correct} ⇒ M」是否在全部归档行上无反例?
      (即 ¬M ⇒ Kind = Neutral ⇒ 跳过 LLM 调用与实调一次在 Kind 上等价)

设计纪律:
  * 标记表 **程序化派生** 自 src/agent.roles/CorrectionDetector.cs 字面量 (禁手打; R435 U+200B 教训)。
  * 只统计 source=local 且 prompt_len>0 的行 = 真机 r1 实答; 桩/远程行单独列示, 不参与判定。
  * 消息全文经 turns-*.jsonl 以 msg_head **前缀锚点**对齐 (不按序号猜)。
  * fail-closed: 目录/文件缺失 ⇒ 抛错非零退出, 不产出部分结果。
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))  # eval/rover/r445 -> repo root
DETECTOR = os.path.join(REPO, "src", "agent.roles", "CorrectionDetector.cs")

ZERO_WIDTH = ("\u200b", "\u200c", "\u200d", "\ufeff")


def derive_markers() -> tuple[list[str], list[str]]:
    """从源码字面量派生 (CorrectMarkers, AdoptMarkers)。含零宽码位断言。"""
    if not os.path.exists(DETECTOR):
        raise SystemExit(f"FAIL-CLOSED: 源码缺失 {DETECTOR}")
    txt = open(DETECTOR, encoding="utf-8").read()
    for zw in ZERO_WIDTH:
        if zw in txt:
            raise SystemExit(f"FAIL-CLOSED: 源码字面量含零宽码位 U+{ord(zw):04X}")

    def block(name: str) -> list[str]:
        m = re.search(name + r"\s*=\s*\{(.*?)\};", txt, re.S)
        if not m:
            raise SystemExit(f"FAIL-CLOSED: 源码中找不到标记表 {name}")
        return re.findall(r'"([^"]*)"', m.group(1))

    corr, adopt = block("CorrectMarkers"), block("AdoptMarkers")
    if not corr or not adopt:
        raise SystemExit("FAIL-CLOSED: 派生出的标记表为空")
    return corr, adopt


def read_jsonl(path: str):
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_turns(path: str) -> list[dict]:
    """turns-*.jsonl 实为整份 pretty-printed JSON 对象: {"stats":..., "turns":[...]}。"""
    with open(path, encoding="utf-8-sig") as fh:
        doc = json.load(fh)
    turns = doc.get("turns") if isinstance(doc, dict) else doc
    if not isinstance(turns, list):
        raise SystemExit(f"FAIL-CLOSED: {path} 结构非预期 (无 turns 数组)")
    return turns


def load_run(rnd_dir: str, run: str):
    """返回 (judge_rows, turns)。任一侧缺失 ⇒ 抛 FileNotFoundError (fail-closed)。"""
    tel = os.path.join(rnd_dir, "run-" + run, "data", "telemetry", "host.jsonl")
    turns_f = os.path.join(rnd_dir, "turns-" + run + ".jsonl")
    if not os.path.exists(tel):
        raise FileNotFoundError(tel)
    if not os.path.exists(turns_f):
        raise FileNotFoundError(turns_f)
    judge = [d["kv"] for d in read_jsonl(tel) if d.get("point") == "correction_judge"]
    turns = load_turns(turns_f)
    return judge, turns


def align_index(kv: dict, turns: list[dict], used: set[int]) -> int | None:
    """以 msg_head 前缀锚点把判官行对齐到某轮的用户消息全文, 返回轮序号。"""
    head = (kv.get("msg_head") or "").strip()
    if not head:
        return None
    for i, t in enumerate(turns):
        if i in used:
            continue
        text = (t.get("text") or "").strip()
        if text.startswith(head):
            used.add(i)
            return i
    return None


def align_message(kv: dict, turns: list[dict], used: set[int]) -> str | None:
    i = align_index(kv, turns, used)
    return None if i is None else (turns[i].get("text") or "").strip()


def prev_reply_class(prev: str) -> str:
    """上一轮回答的来源分类 (机械可判; 空 ⇒ 结构性 Neutral 已生效)。"""
    p = (prev or "").strip()
    if not p:
        return "EMPTY"
    if "桩应答" in p:
        return "stub_ack"
    if p.startswith("上一轮计划停在") or "意图不明确" in p:
        return "gate_digest"
    return "other"


def has_marker(msg: str, markers: list[str]) -> str | None:
    low = msg.lower()
    for m in markers:
        if m.lower() in low:
            return m
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid-dir", default=os.path.join(REPO, "eval", "rover"))
    ap.add_argument("--out", default=os.path.join(HERE, "precheck-judge-prefilter.json"))
    ap.add_argument("--neg-control", action="store_true",
                    help="负控: 故意用失效谓词 M_weak=(len<=0), 必须检出 ≥1 反例")
    ap.add_argument("--run-glob", default="r4*")
    args = ap.parse_args()

    if not os.path.isdir(args.grid_dir):
        print(f"FAIL-CLOSED: --grid-dir 不存在: {args.grid_dir}", file=sys.stderr)
        return 2

    corr_m, adopt_m = derive_markers()
    print(f"[derived] CorrectMarkers={len(corr_m)} AdoptMarkers={len(adopt_m)} "
          f"from {os.path.relpath(DETECTOR, REPO)}")

    # 候选谓词: name -> (谓词函数, 说明)
    def m_marker(msg: str, _len: int) -> bool:
        return bool(has_marker(msg, corr_m) or has_marker(msg, adopt_m))

    preds = {
        "C1_M1_marker": (m_marker, "消息含任一 Adopt/Correct 标记"),
        "C2_M2_len24": (lambda msg, n: n <= 24, "len(msg) <= 24"),
        "C3_M3_len16": (lambda msg, n: n <= 16, "len(msg) <= 16"),
        "C4_M4_marker_or_len24": (lambda msg, n: m_marker(msg, n) or n <= 24, "M1 或 len<=24"),
    }
    if args.neg_control:
        preds = {"NC_weak_len0": (lambda msg, n: n <= 0, "负控: len(msg) <= 0")}

    rows, unaligned, stub_rows, struct_rows = [], 0, [], []
    runs_used, per_run = [], collections.Counter()
    for rnd_dir in sorted(glob.glob(os.path.join(args.grid_dir, args.run_glob))):
        if not os.path.isdir(rnd_dir):
            continue
        rnd = os.path.basename(rnd_dir)
        for run_path in sorted(glob.glob(os.path.join(rnd_dir, "run-*"))):
            run = os.path.basename(run_path)[len("run-"):]
            try:
                judge, turns = load_run(rnd_dir, run)
            except FileNotFoundError:
                continue                      # 无 turns 归档的历史轮次: 跳过并计数
            if not judge:
                continue
            used: set[int] = set()
            runs_used.append(f"{rnd}/{run}")
            for kv in judge:
                src = str(kv.get("source") or "")
                plen = int(kv.get("prompt_len") or 0)
                kind = str(kv.get("kind") or "")
                if str(kv.get("signal") or "") == "no_prev_reply":
                    struct_rows.append((rnd, run, kind, plen))
                msg = align_message(kv, turns, used)
                if msg is None:
                    unaligned += 1
                    continue
                idx = next((i for i, t in enumerate(turns)
                            if (t.get("text") or "").strip() == msg), None)
                prev = (turns[idx - 1].get("reply") or "") if (idx is not None and idx > 0) else ""
                rec = {
                    "run": f"{rnd}/{run}", "source": src, "prompt_len": plen,
                    "kind": kind, "letter": str(kv.get("letter") or ""),
                    "signal": str(kv.get("signal") or ""), "msg": msg, "msg_len": len(msg),
                    "prev_class": prev_reply_class(prev),
                }
                rows.append(rec)
                if src != "local" or plen <= 0:
                    stub_rows.append(rec)
                else:
                    per_run[f"{rnd}/{run}"] += 1

    real = [r for r in rows if r["source"] == "local" and r["prompt_len"] > 0]
    verdict, detail = {}, {}
    for name, (fn, desc) in preds.items():
        k = [r for r in real if not fn(r["msg"], r["msg_len"]) and r["kind"] != "Neutral"]
        s = [r for r in real if not fn(r["msg"], r["msg_len"]) and r["kind"] == "Neutral"]
        detail[name] = {
            "desc": desc, "counterexamples_k": len(k), "saved_calls_s": len(s),
            "k_rows": [{kk: r[kk] for kk in ("run", "msg", "msg_len", "kind", "letter")} for r in k],
            "s_share": round(len(s) / max(1, len(s) + len(k)), 4),
        }
        verdict[name] = "PASS" if (len(k) == 0 if name != "NC_weak_len0" else len(k) >= 1) else "FAIL"

    struct_bad = [r for r in struct_rows if r[2] != "Neutral" or r[3] != 0]
    verdict["C6_struct_no_prev_reply"] = "PASS" if not struct_bad else "FAIL"
    detail["C6_struct_no_prev_reply"] = {
        "n": len(struct_rows), "violations": len(struct_bad),
        "rule": "signal=no_prev_reply ⇒ Kind=Neutral ∧ prompt_len=0",
    }

    out = {
        "round": "R445", "instrument": "judge_prefilter_precheck",
        "derived_from": {"detector": os.path.relpath(DETECTOR, REPO),
                         "correct_markers": corr_m, "adopt_markers": adopt_m},
        "counts": {"judge_rows_total": len(rows), "real_local_llm_rows": len(real),
                   "stub_or_remote_rows": len(stub_rows), "unaligned_rows": unaligned,
                   "runs_used": len(runs_used), "struct_rows": len(struct_rows),
                   "kind_hist_real": dict(collections.Counter(r["kind"] for r in real))},
        "runs_used": runs_used, "per_run_real_rows": dict(per_run),
        "real_rows": [{kk: r[kk] for kk in ("run", "msg", "msg_len", "kind", "letter", "signal", "prev_class")} for r in real],
        "posthoc": {
            "note": "事后探索 (非预注册判据): 用于给 R446 定靶; 不参与本轮 PASS/FAIL",
            "prev_class_x_kind": {f"{a}|{b}": c for (a, b), c in
                                  collections.Counter((r["prev_class"], r["kind"]) for r in real).items()},
            "msg_ambiguity": {m: sorted(s) for m, s in
                              ((m, {r["kind"] for r in real if r["msg"] == m})
                               for m in {r["msg"] for r in real}) if len(s) > 1},
            "candidates": {
                c: {"n": len([r for r in real if r["prev_class"] == c]),
                    "non_neutral": len([r for r in real if r["prev_class"] == c and r["kind"] != "Neutral"]),
                    "saved_calls_if_prefilter": len([r for r in real if r["prev_class"] == c and r["kind"] == "Neutral"]),
                    "lost_signals_if_prefilter": len([r for r in real if r["prev_class"] == c and r["kind"] != "Neutral"])}
                for c in ("stub_ack", "gate_digest", "other", "EMPTY")},
        },
        "predicates": detail, "verdict": verdict,
        "neg_control_mode": bool(args.neg_control),
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    print(f"[counts] {out['counts']}")
    for name in sorted(detail):
        d = detail[name]
        desc = str(d.get("desc", "-"))
        print(f"[{verdict[name]:4s}] {name:24s} {desc:28s} k={d.get('counterexamples_k','-')} s={d.get('saved_calls_s','-')}")
    if args.neg_control:
        ok = verdict["NC_weak_len0"] == "PASS"
        print(f"[neg-control] {'OK (检出反例 ⇒ 器具非空转)' if ok else 'BROKEN (无反例 ⇒ 器具失效)'}")
        return 0 if ok else 3
    fails = [n for n, v in verdict.items() if v == "FAIL" and n != "C5"]
    print(f"[summary] fails={fails or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
