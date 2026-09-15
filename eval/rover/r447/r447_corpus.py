#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R447 语料构建器 v2：判官 (msg, prev) 真实对 —— 遥测+网格派生，prompt 源码派生（禁手打）。

为什么 v1 被推翻（器具自纠，留痕）
────────────────────────────────
v1 从 `calls-*.jsonl` 的 `messages` 里取「最后一条 user 消息」当 msg。**错**：那条 user 消息
含内联上下文块（`换个说法。\n\n[本轮参考上下文]…`），而判官实收的是**裸** question
（`eval/rover/r446/run-BRJ-M20-s2/data/telemetry/host.jsonl` 的 `correction_judge` 行
`msg_head` = `换个说法。`，无块）。用 v1 语料等于给模型喂产品的另一种输入 ⇒ 等价性结论无效。

本器具的证据链（三通道机械对齐，零人工转录）
──────────────────────────────────────────
  1. **prompt 模板** ← `CorrectionDetector.cs:BuildJudgePromptVerbose` 字面量 + `CorrectionJudgeSystem`
     （派生器 = `eval/rover/r444/channel_marks.py`，R436 立的「禁手打」通道标记器）。
  2. **硬闸·忠实性** ← `eval/rover/r435/judge-prompt-golden-v2.jsonl`：9 条**产品实发** prompt 原文，
     本构建器重建必须**逐字相同**，否则 fail-closed（器材不可信，停）。
  3. **msg** ← 网格 `turns[]`（`eval/rover/r*/grid/task-<grid>.json`）原文，经 `run-<arm>-<grid>-s<N>`
     目录名映射到同一网格；以遥测 `msg_head`（前 18 字符）为前缀锚点校验。
  4. **prev** ← 两候选常量（桩应答 / 跳过应答），用遥测 `prompt_len` 解方程
     `len(prev) = prompt_len − (len(head)+len("上一轮: ")+len("\n用户: ")+len("\n")+len("答案:\n")) − len(msg)`
     定位；候选集合由归档全量扫描得出，不手写。
  5. **存档字母**（三值）作为**第三通道**：J0 基线必须与存档字母逐条一致（同 prompt 同模型同温度），
     不一致 ⇒ 器具漂移告警（如实登记，不作为 fail-closed）。

输出 `corpus.json`：pairs[]（msg/prev/prompt/archived_letter/来源）+ 计数 + 三通道校验读数。
"""
import collections
import hashlib
import importlib.util
import json
import pathlib
import re

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
CM_PATH = ROOT / "eval/rover/r444/channel_marks.py"
GOLDEN = ROOT / "eval/rover/r435/judge-prompt-golden-v2.jsonl"
OUT = ROOT / "eval/rover/r447/corpus.json"
N_PAIRS = 18          # 语料总规模（墙钟约束：基线臂每条约 30s）
N_TELE_CAP = 12       # 其中遥测派生对上限（其余留给 golden 真值对，补 prev/字母多样性）
N_NEG = 8             # 负控（错配 prev）子集规模


def _load_cm():
    spec = importlib.util.spec_from_file_location("cm_r444", CM_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def derive_prompt_template() -> dict:
    cm = _load_cm()
    lits = [x for x in cm._literals_of(cm.CS_DETECT, "BuildJudgePromptVerbose") if x != ""]
    sysmsg = cm._const_of(cm.CS_JUDGE, "CorrectionJudgeSystem")
    holder = [i for i, l in enumerate(lits) if "{prev}" in l and "{user}" in l]
    if len(holder) != 1:
        raise ValueError(f"占位字面量不唯一: {holder}")
    i = holder[0]
    seg = lits[i]                       # 例如 '上一轮: {prev}\n用户: {user}\n'
    pre, rest = seg.split("{prev}", 1)
    mid, post = rest.split("{user}", 1)
    tail = "".join(lits[i + 1:])
    if pre != "上一轮: " or mid != "\n用户: ":
        raise ValueError(f"占位字面量形状异常: {seg!r}")
    return {"system": sysmsg, "head": "".join(lits[:i]), "pre": pre, "mid": mid,
            "tpl_mid": post, "tail": tail, "n_literals": len(lits)}


def build_prompt(tpl: dict, prev: str, user: str) -> str:
    """BuildJudgePromptVerbose 逐字重实现（截断 120/160 与源码一致）。"""
    cu = user if len(user) <= 120 else user[:120]
    cp = prev if len(prev) <= 160 else prev[:160]
    return tpl["head"] + tpl["pre"] + cp + tpl["mid"] + cu + tpl["tpl_mid"] + tpl["tail"]


def prompt_head_len(tpl: dict) -> int:
    return len(tpl["head"]) + len(tpl["pre"]) + len(tpl["mid"]) + len(tpl["tpl_mid"]) + len(tpl["tail"])


def sha16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def faithfulness(tpl: dict) -> dict:
    rows = [json.loads(l) for l in GOLDEN.read_text(encoding="utf-8").splitlines() if l.strip()]
    bad = []
    for r in rows:
        got = build_prompt(tpl, r.get("prev", ""), r.get("user", ""))
        if got != r.get("prompt"):
            bad.append({"case": r.get("case")})
    if bad:
        raise SystemExit(f"[致命] 忠实性校验失败 ⇒ fail-closed: {bad}")
    return {"golden_rows": len(rows), "match": len(rows), "mismatches": []}


def load_grids() -> dict:
    """grid 名 → turns[] 原文。"""
    g = {}
    for f in sorted(ROOT.glob("eval/rover/r*/grid/task-*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        turns = d.get("turns")
        if isinstance(turns, list):
            g[(f.parent.parent.name, f.stem.replace("task-", ""))] = {
                "turns": turns, "file": str(f.relative_to(ROOT))}
    return g


def prev_candidates() -> list:
    """归档全量扫描 assistant 回复的候选集合（不手写常量）。"""
    c = collections.Counter()
    for f in ROOT.glob("eval/rover/r*/calls-*.jsonl"):
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.lstrip("\ufeff")
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            for m in (rec.get("messages") or []):
                if str(m.get("role")) == "assistant":
                    c[str(m.get("content") or "")] += 1
    return [k for k, _ in c.most_common() if k.strip()]


def harvest_judge_rows() -> list:
    """从归档遥测抓 correction_judge 本地行（三通道对齐用）。"""
    out = []
    for f in sorted(ROOT.glob("eval/rover/r*/run-*/data/telemetry/host.jsonl")):
        run = f.parts[-4]
        m = re.match(r"run-(.+)-([A-Za-z0-9]+)-s(\d+)$", run)
        if not m:
            continue
        arm, grid, seed = m.group(1), m.group(2), m.group(3)
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.lstrip("\ufeff")
            if not line.strip() or "correction_judge" not in line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("point") != "correction_judge":
                continue
            kv = r.get("kv") or {}
            if kv.get("source") != "local":
                continue
            out.append({"run": run, "arm": arm, "grid": grid, "seed": seed,
                        "round_dir": f.parts[-5], "ts": r.get("ts"), "kv": kv})
    return out


def main():
    tpl = derive_prompt_template()
    faith = faithfulness(tpl)
    ph = prompt_head_len(tpl)
    grids = load_grids()
    prevs = prev_candidates()
    rows = harvest_judge_rows()
    print(f"[tpl] system={tpl['system']!r} literals={tpl['n_literals']} head={len(tpl['head'])} fixed={ph}")
    print(f"[faithfulness] {faith['match']}/{faith['golden_rows']} 逐字相同 (hard gate)")
    print(f"[prev candidates] {len(prevs)}: {[(p[:12], len(p)) for p in prevs]}")
    print(f"[judge local rows] {len(rows)}")

    pairs, seen, unresolved = [], set(), collections.Counter()
    for r in rows:
        kv = r["kv"]
        mh = str(kv.get("msg_head") or "")
        plen = kv.get("prompt_len")
        g = grids.get((r["round_dir"], r["grid"]))
        if not g or plen is None:
            unresolved["no_grid_or_len"] += 1
            continue
        cands = [t for t in g["turns"] if t[:18] == mh]
        if len(cands) != 1:
            unresolved["msg_ambiguous" if cands else "msg_not_found"] += 1
            continue
        msg = cands[0]
        need = plen - ph - len(msg)
        pc = [p for p in prevs if len(p) == need and len(p) <= 160]
        if len(pc) != 1:
            unresolved["prev_ambiguous" if pc else "prev_not_found"] += 1
            continue
        prev = pc[0]
        if len(build_prompt(tpl, prev, msg)) != plen:
            unresolved["len_mismatch"] += 1
            continue
        key = (msg, prev)
        if key in seen:
            continue
        seen.add(key)
        pairs.append({"msg": msg, "prev": prev,
                      "archived_letter": kv.get("letter"), "archived_source": kv.get("source"),
                      "prov": {"run": r["run"], "ts": r["ts"], "grid_file": g["file"],
                               "prompt_len": plen, "msg_head": mh}})

    # 选样：字母分层轮转（保证 A/C/N 三类都在，指标才有判别力），确定性排序
    by_letter = collections.defaultdict(list)
    for p in pairs:
        by_letter[p["archived_letter"] or "?"].append(p)
    for k in by_letter:
        by_letter[k].sort(key=lambda p: sha16(p["msg"] + "\x00" + p["prev"]))
    sel, order = [], sorted(by_letter, key=lambda k: (k == "?", k))
    tele_cap = min(N_TELE_CAP, len(pairs))
    while len(sel) < tele_cap:
        progressed = False
        for k in order:
            if by_letter[k] and len(sel) < tele_cap:
                sel.append(by_letter[k].pop(0))
                progressed = True
        if not progressed:
            break

    # golden 真值对（产品实发 prompt 原文；含真实 prev 26 字符 + C 类样本，补多样性）
    gold = [json.loads(l) for l in GOLDEN.read_text(encoding="utf-8").splitlines() if l.strip()]
    tele_keys = {(p["msg"], p["prev"]) for p in sel}
    for g in gold:
        if not (g.get("prev") or "").strip() or not (g.get("user") or "").strip():
            continue
        if (g["user"], g["prev"]) in tele_keys:
            continue
        if len(sel) >= N_PAIRS:
            break
        sel.append({"msg": g["user"], "prev": g["prev"], "archived_letter": None,
                    "archived_source": None, "golden_case": g.get("case"),
                    "prompt_verbatim": g["prompt"], "origin": "golden-r435",
                    "prov": {"golden_file": str(GOLDEN.relative_to(ROOT)), "case": g.get("case")}})

    for i, p in enumerate(sel):
        p["i"] = i
        p["origin"] = p.get("origin", "telemetry-run")
        # golden 对直接用产品实发原文（已过忠实性硬闸）；其余用源码派生重建
        if p.get("prompt_verbatim"):
            p["prompt"] = p["prompt_verbatim"]
        else:
            built = build_prompt(tpl, p["prev"], p["msg"])
            assert len(built) == p["prov"]["prompt_len"], p["prov"]   # 三通道对齐硬校验
            p["prompt"] = built
        p["prompt_len"] = len(p["prompt"])
        p["pair_sha16"] = sha16(p["msg"] + "\x00" + p["prev"])

    doc = {
        "round": "R447", "instrument": "r447_corpus/v2",
        "template": {"system": tpl["system"], "head": tpl["head"], "tail": tpl["tail"],
                     "fixed_len": ph, "n_literals": tpl["n_literals"],
                     "source": "src/agent.roles/CorrectionDetector.cs:BuildJudgePromptVerbose"},
        "faithfulness": faith,
        "prev_candidates": [{"text": p, "len": len(p)} for p in prevs],
        "rejected_sources": [{
            "source": "eval/rover/r*/calls-*.jsonl 的 messages 最后一条 user",
            "reason": "该 user 文本含内联上下文块（[本轮参考上下文]…），判官实收为裸 question；"
                      "用它会改变被测输入 ⇒ v1 语料作废"}],
        "counts": {"judge_local_rows": len(rows), "distinct_pairs": len(pairs), "selected": len(sel),
                   "unresolved": dict(unresolved), "n_neg_subset": min(N_NEG, len(sel))},
        "letter_mix": dict(collections.Counter([p["archived_letter"] for p in sel])),
        "pairs": sel,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[corpus] 本地判官行 {len(rows)} → 去重对 {len(pairs)} → 选样 {len(sel)} "
          f"(字母 {doc['letter_mix']}) unresolved={dict(unresolved)} → {OUT}")


if __name__ == "__main__":
    main()
