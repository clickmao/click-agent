#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R448 语料构建器 v3：在 R447 忠实语料之上加**机械闸**（承 R447 候选 4）。

继承（不重写）的证据链
──────────────────────
- prompt 模板 = `CorrectionDetector.cs:BuildJudgePromptVerbose` 字面量派生（`eval/rover/r444/channel_marks.py`，禁手打）。
- 硬闸·忠实性 = `eval/rover/r435/judge-prompt-golden-v2.jsonl` 9 条产品实发 prompt 原文，重建须**逐字相同**（fail-closed）。
- (msg, prev) 对 = R447 三通道对齐语料（网格 turns + 遥测 prompt_len 恒等式 + 归档字母第三通道）。

本轮新增闸（全部机检，读数写进 corpus.json.gates）
────────────────────────────────────────────────
  G1  **独立重建等价**：用 r447_corpus 的构建函数对 18 对**(msg,prev) 重新派生 prompt**，
      必须与 `eval/rover/r448/input-corpus.json`（= R447 语料快照，带 sha256）**逐字节相同**。
      （防「直接搬运旧语料」⇒ 语料必须可再生产。）
  G2  **prev 面多样性 >= 3 且含 >=1 条长 prev（>25 字符）**——R447 自陈「prev 面弱」，此处把
      「弱」变成**可机检的下界**，并如实登记实际取值（不宣称强）。
  G3  **负控真错配 8/8**：NC 用的 prev 必须字符串不等且不互为前缀；这条直接针对 R447 C4a
      「8 条里只有 2 条真错配」的判定项设计缺陷（候选 4）。

输出 `eval/rover/r448/corpus.json`：pairs[]（含 prompt / prompt_limited）+ neg_control[] + gates。
"""
import hashlib
import importlib.util
import json
import pathlib
import shutil

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
R447 = ROOT / "eval/rover/r447"
R448 = ROOT / "eval/rover/r448"
INPUT = R448 / "input-corpus.json"     # R447 语料快照（本器具只读输入）
OUT = R448 / "corpus.json"
LIMIT_CLAUSE = "思考最多 2 句 (不超过 40 字), 不要展开推理。"
N_NEG = 8


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    R448.mkdir(parents=True, exist_ok=True)
    # 输入快照：把 R447 语料复制成只读输入并记 sha256（防「跑完再改输入」）
    snap = R447 / "corpus.json"
    shutil.copyfile(snap, INPUT)
    src_sha = hashlib.sha256(INPUT.read_bytes()).hexdigest()
    src = json.loads(INPUT.read_text(encoding="utf-8"))

    rc = _load("r447_corpus", R447 / "r447_corpus.py")
    tpl = rc.derive_prompt_template()
    faith = rc.faithfulness(tpl)                       # 硬闸，失败即 exit
    if faith["match"] != faith["golden_rows"]:
        raise SystemExit(f"[致命] 忠实性硬闸未过: {faith}")

    # 限长子句的插入锚点：从源码字面量取（禁手打）
    cm = rc._load_cm()
    lits = [x for x in cm._literals_of(cm.CS_DETECT, "BuildJudgePromptVerbose") if x != ""]
    anchors = [l for l in lits if "先思考" in l]
    if len(anchors) != 1:
        raise SystemExit(f"[致命] 限长插入锚点不唯一/未找到: {anchors}")
    anchor = anchors[0]

    # G1：独立重建等价（18/18 逐字节）
    rebuilt_ok, rebuilt_bad, limited_ok = 0, [], 0
    pairs = []
    for p in src["pairs"]:
        built = rc.build_prompt(tpl, p["prev"], p["msg"])
        if built != p["prompt"]:
            rebuilt_bad.append({"i": p["i"], "msg": p["msg"]})
        else:
            rebuilt_ok += 1
        if anchor not in built:
            raise SystemExit(f"[致命] 锚点不在重建 prompt 中: i={p['i']}")
        lim = built.replace(anchor, LIMIT_CLAUSE + anchor)
        if lim == built or anchor not in lim:
            raise SystemExit(f"[致命] 限长 prompt 未生效: i={p['i']}")
        limited_ok += 1
        pairs.append({"i": p["i"], "msg": p["msg"], "prev": p["prev"],
                      "prompt": built, "prompt_limited": lim,
                      "prompt_delta_chars": len(lim) - len(built),
                      "archived_letter": p.get("archived_letter"),
                      "archived_source": p.get("archived_source"),
                      "origin": p.get("origin"), "prov": p.get("prov")})
    if rebuilt_bad:
        raise SystemExit(f"[致命] G1 独立重建与快照不一致（fail-closed）: {rebuilt_bad}")

    # G2：prev 面多样性下界 + 如实登记
    prevs = sorted({p["prev"] for p in pairs})
    long_prevs = [p for p in prevs if len(p) > 25]
    g2_ok = len(prevs) >= 3 and len(long_prevs) >= 1

    # G3：负控真错配（8/8）
    pool = [p for p in prevs]                    # 全部真值 prev（不造字面量）
    neg, mismatches_ok = [], 0
    for k in range(min(N_NEG, len(pairs))):
        p = pairs[k]
        wrong = next((q for q in pool if q != p["prev"] and not q.startswith(p["prev"])
                      and not p["prev"].startswith(q)), None)
        if wrong is None:
            raise SystemExit(f"[致命] 无法为 i={k} 找到真错配 prev")
        if wrong == p["prev"]:
            raise SystemExit(f"[致命] 假错配: i={k}")
        mismatches_ok += 1
        # 用源码派生模板重建错配 prompt（两条：产品原样 + 限长版）
        q = rc.build_prompt(tpl, wrong, p["msg"])
        neg.append({"i": k, "msg": p["msg"], "prev": wrong, "prev_orig": p["prev"],
                    "prompt": q, "prompt_limited": q.replace(anchor, LIMIT_CLAUSE + anchor),
                    "truly_mismatched": True,
                    "from_pool": str(wrong)[:20]})
    g3_ok = mismatches_ok == min(N_NEG, len(pairs))

    doc = {
        "round": "R448", "instrument": "r448_corpus",
        "input_corpus": {"path": str(INPUT.relative_to(ROOT)), "sha256": src_sha,
                         "pairs": len(src.get("pairs", []))},
        "template": {"system": tpl["system"], "fixed_part_len": rc.prompt_head_len(tpl),
                     "literals": tpl["n_literals"], "limit_anchor": anchor,
                     "limit_clause": LIMIT_CLAUSE},
        "gates": {
            "G1_rebuild_equivalence": {"pass": not rebuilt_bad, "rebuilt_equal": rebuilt_ok,
                                       "n": len(pairs), "limited_built": limited_ok,
                                       "mismatches": rebuilt_bad},
            "G1b_faithfulness_vs_golden": {"pass": True, **faith},
            "G2_prev_diversity": {"pass": g2_ok, "distinct_prevs": len(prevs),
                                  "long_prevs_gt25": len(long_prevs),
                                  "note": "R447 自陈 prev 面弱；本轮只钉可机检下界，不宣称强"},
            "G3_neg_true_mismatch": {"pass": g3_ok, "true_mismatch": mismatches_ok,
                                     "n_neg": min(N_NEG, len(pairs))},
        },
        "counts": {"pairs": len(pairs), "telemetry_pairs": sum(1 for p in pairs if p.get("archived_letter")),
                   "golden_pairs": sum(1 for p in pairs if not p.get("archived_letter"))},
        "pairs": pairs, "neg_control": neg,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    for k, v in doc["gates"].items():
        print(f"[{k}] pass={v['pass']} {json.dumps({kk: vv for kk, vv in v.items() if kk != 'pass'}, ensure_ascii=False)}")
    print(f"[done] {OUT} pairs={len(pairs)} neg={len(neg)}")


if __name__ == "__main__":
    main()
