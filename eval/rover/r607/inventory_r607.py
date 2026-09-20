#!/usr/bin/env python3
"""R607 · RF0004.0 打点盘点机检器（零产品改动轮的**盘点件**器）。

用途：把「三面（开放域识别 / 生成类 / 多轮工具编排）打点是否齐全」写成**现盘可核对**的件，
而不是散文。两条通路：
  python3 eval/rover/r607/inventory_r607.py --write    生成 inventory（从现盘 grep 派生 file:line，禁手打）
  python3 eval/rover/r607/inventory_r607.py --check    断言现盘与 inventory 一致（防盘点漂移）

判据（单源 = 本文件 DECL，不用第二份字面表）：
  C1 emit_site  ：每个声明键在**声明的文件:行**上确有 `Emit("<key>"` 字面（现盘字节）。
  C2 face_gap   ：每个面声明的缺口（missing 键/件）在现盘仍**不存在**（缺口若已被补上 ⇒ 盘点过期 ⇒ 判红）。
  C3 reading    ：现读数（键在 data/telemetry/host.jsonl 的出现次数）与 inventory 记录一致（同源重算）。
  C4 consumer   ：每个键声明的**主链消费点**（文件:行）在现盘存在。
rc: 0 全过 / 1 盘点与现盘不符 / 2 器具缺陷(fail-closed) / 3 输入缺失。
"""
import argparse
import io
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HOST_JSONL = ROOT / "data" / "telemetry" / "host.jsonl"
OUT = ROOT / "eval" / "rover" / "r607" / "telemetry-inventory-r607.json"

# ── 声明面（人判：键 ↔ 面；file:line 与读数一律**派生**，不手打） ──────────────
# src_globs: 在这些源文件里搜 Emit("<key>" 的首发射点
DECL = {
    "开放域识别": {
        "question": "输入任意域文本 ⇒ {标签|abstain, 依据} 的统一出口是否存在可机检打点？",
        "keys": [
            "nlp_shape", "local_turn_gate", "local_turn_gate_config",
            "local_turn_gate_reject", "local_gate_skip_reply", "local_gate_skip_history",
            "repeat_degrade_remote", "paraphrase_degrade_remote", "local_decision_ledger",
        ],
        "consumers": {
            "nlp_shape": "eval/rover/r579-tick/shape_kpi_face_check.py",
            "local_turn_gate": "eval/rover/r583/plane_split_r583.py",
        },
        "gaps": [
            "统一出口结构 RecognitionVerdict{label|abstain,evidence} 的打点键",
            "abstain ⇒ 远端 ⇒ 补丁 ⇒ 下次命中的闭环打点键",
        ],
    },
    "生成类": {
        "question": "TaskKindHint 是否有 Generation 档，且该档有独立打点？",
        "keys": ["local_channel_warmup", "render_call", "contract_declaration_hidden", "artifact_feedback"],
        "consumers": {"render_call": "src/agent.modelqueue/LocalSvgRenderer.cs"},
        "gaps": [
            "TaskKindHint.Generation 枚举档（现盘不存在）",
            "生成类产物的独立验收器打点键（产物回放通过率）",
        ],
    },
    "多轮工具编排": {
        "question": "编排决策面是否有专用打点（不是自由文本动作环）？",
        "keys": ["tool_decl_gate", "plan_local_gated"],
        "consumers": {"tool_decl_gate": "src/agent.modelqueue/ModelQueueRouter.Recovery.cs"},
        "gaps": [
            "ActionLoopRunner 专用打点键（现盘该文件 Emit 数 == 0）",
            "结构化编排字段（动作候选进 R1 契约）的生效打点键",
        ],
    },
}
SRC_GLOBS = [str(ROOT / "src")]


def _grep_first(key: str):
    """返回键的**首发射点** (relpath, lineno, line_text) 或 None。"""
    hits = []
    for f in sorted(Path(SRC_GLOBS[0]).rglob("*.cs")):
        if "/obj/" in str(f) or "/bin/" in str(f):
            continue
        try:
            txt = io.open(f, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for i, ln in enumerate(txt.splitlines(), 1):
            if ('Emit("%s"' % key) in ln:
                hits.append((str(f.relative_to(ROOT)), i, ln.strip()))
    return hits


def _key_counts():
    c = {}
    if not HOST_JSONL.exists():
        return c
    with io.open(HOST_JSONL, encoding="utf-8-sig", errors="replace") as f:
        for l in f:
            l = l.strip()
            if not l:
                continue
            try:
                d = json.loads(l)
            except Exception:
                continue
            k = d.get("point")
            c[k] = c.get(k, 0) + 1
    return c


def build():
    counts = _key_counts()
    inv = {"round": "R607", "kind": "RF0004.0 三面打点盘点（现盘派生）",
           "telemetry_source": "data/telemetry/host.jsonl",
           "host_jsonl_rows": sum(counts.values()),
           "faces": {}}
    for face, d in DECL.items():
        rows = []
        for k in d["keys"]:
            hits = _grep_first(k)
            rows.append({
                "key": k,
                "emit_sites": [{"file": h[0], "line": h[1]} for h in hits],
                "emit_count_sites": len(hits),
                "reading_total": counts.get(k, 0),
                "consumer": d["consumers"].get(k, ""),
            })
        inv["faces"][face] = {
            "question": d["question"],
            "keys": rows,
            "gaps": d["gaps"],
            "gaps_missing_confirmed": True,  # 由 --check 现盘重验
        }
    return inv


def check(inv):
    """返回 (verdict_dict, code)。禁 grep 文本锚判 verdict：结论键无条件计算。"""
    v = {"round": "R607", "checks": {}, "defects": []}

    def fail(name, msg):
        v["checks"][name] = {"ok": False, "why": msg}

    # C1 emit_site
    c1_bad = []
    for face, fd in inv["faces"].items():
        for row in fd["keys"]:
            hits = _grep_first(row["key"])
            got = sorted((h[0], h[1]) for h in hits)
            want = sorted((s["file"], s["line"]) for s in row["emit_sites"])
            if not got:
                c1_bad.append("%s/%s 现盘零发射点" % (face, row["key"]))
            elif got != want:
                c1_bad.append("%s/%s 发射点漂移 want=%s got=%s" % (face, row["key"], want[:3], got[:3]))
    v["checks"]["C1_emit_site"] = {"ok": not c1_bad, "bad": c1_bad}

    # C2 face_gap（缺口若已被补上 ⇒ 盘点过期）
    c2_bad = []
    if "Generation" in io.open(ROOT / "src/agent.modelqueue/TaskKindHint.cs", encoding="utf-8").read():
        c2_bad.append("生成类缺口「TaskKindHint 无 Generation 档」已被补上 ⇒ 盘点过期")
    al = io.open(ROOT / "src/agent.modelqueue/ActionLoopRunner.cs", encoding="utf-8").read()
    if "Emit(" in al:
        c2_bad.append("编排面缺口「ActionLoopRunner 零打点」已被补上 ⇒ 盘点过期")
    v["checks"]["C2_face_gap"] = {"ok": not c2_bad, "bad": c2_bad}

    # C3 reading（同源重算）——**单调不变量**: host.jsonl 只追加 ⇒ 现读数只增不减。
    # v2 修（自捕仪器缺陷，2026-09-21）: v1 用「逐键相等」⇒ 盘点件落盘后**每次新轮都会把 C3 判红**
    #   （实测跑完 6 臂后 8 键全体漂移，读起来像盘点过期，实为「追加」这一正常动作）⇒ 判据与语义脱钩。
    #   改为 disk >= inventory（缺量才判红）并把两侧数值一并落盘；负控仍在 C1/NC（改错行号必红）。
    counts = _key_counts()
    c3_bad = []
    c3_delta = {}
    for face, fd in inv["faces"].items():
        for row in fd["keys"]:
            now = counts.get(row["key"], 0)
            c3_delta["%s/%s" % (face, row["key"])] = now - row["reading_total"]
            if now < row["reading_total"]:
                c3_bad.append("%s/%s 读数回退（违反追加单调）inv=%s disk=%s" % (
                    face, row["key"], row["reading_total"], now))
    v["checks"]["C3_reading"] = {"ok": not c3_bad, "bad": c3_bad, "invariant": "disk >= inventory",
                                 "delta_disk_minus_inv": c3_delta}
    v["host_jsonl_rows"] = sum(counts.values())

    # C4 consumer
    c4_bad = []
    for face, fd in inv["faces"].items():
        for row in fd["keys"]:
            cp = row.get("consumer") or ""
            if not cp:
                continue
            if not (ROOT / cp).exists():
                c4_bad.append("%s/%s 消费点不存在: %s" % (face, row["key"], cp))
    v["checks"]["C4_consumer"] = {"ok": not c4_bad, "bad": c4_bad}

    # 有牙（负控）：把一条现盘确实存在的发射点改错 ⇒ C1 必须判红
    neg = json.loads(json.dumps(inv))
    first = next(iter(neg["faces"].values()))["keys"][0]
    if first["emit_sites"]:
        first["emit_sites"][0]["line"] = 99999
    snap = OUT
    keep_inv = inv
    nc_bad = []
    tmp_inv = json.loads(json.dumps(neg))
    # 就地跑一次 check 内核（不再递归调用自身）
    bad = []
    for face, fd in tmp_inv["faces"].items():
        for row in fd["keys"]:
            got = sorted((h[0], h[1]) for h in _grep_first(row["key"]))
            want = sorted((s["file"], s["line"]) for s in row["emit_sites"])
            if got != want:
                bad.append(row["key"])
    v["checks"]["NC_gate_has_teeth"] = {"ok": bool(bad), "why": "改错发射点行号 ⇒ C1 必须判红",
                                       "caught": bad[:3]}

    all_ok = all(c.get("ok") for c in v["checks"].values())
    v["verdict"] = "PASS" if all_ok else "FAIL"
    for c in v["checks"].values():
        if not c.get("ok"):
            v["defects"].append(c.get("why") or c.get("bad"))
    return v, (0 if all_ok else 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if not HOST_JSONL.exists():
        print(json.dumps({"verdict": "VOID", "why": "缺 %s" % HOST_JSONL}, ensure_ascii=False))
        return 3
    if a.write:
        inv = build()
        io.open(OUT, "w", encoding="utf-8").write(
            json.dumps(inv, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
        n = sum(len(f["keys"]) for f in inv["faces"].values())
        print("[write] %s faces=%d keys=%d host_rows=%d" % (OUT.name, len(inv["faces"]), n, inv["host_jsonl_rows"]))
        return 0
    if a.check:
        inv = json.loads(io.open(a.out or OUT, encoding="utf-8").read())
        v, code = check(inv)
        dest = a.out or OUT
        io.open(str(dest).replace(".json", "-verdict.json"), "w", encoding="utf-8").write(
            json.dumps(v, ensure_ascii=False, indent=1) + "\n")
        print(json.dumps(v, ensure_ascii=False))
        return code
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
