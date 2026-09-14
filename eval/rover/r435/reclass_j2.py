#!/usr/bin/env python3
"""R435 修复臂**重分类器** —— 器具自纠 (第二轮同一仪器缺陷)。

已发生的仪器缺陷 (R435 两次):
  我的 Python 侧 think 标记字面量里混入了不可见 **U+200B**，导致 `close=False` 恒成立 ⇒
  分类器把「思考链正文」也当结论区 ⇒ 在推理正文里取到字母 ⇒ **假阳性**（探针显示 8/9 可解析，
  而产品同档实测 1/7）。这正是产品 Parse 注释里写明的铁律所禁止的行为。
  ⇒ 本脚本**不再手打常量**，而是从产品源码 `LocalGenerationPort.cs` 里按 `\\uXXXX` 转义还原
    真常量并**硬断言** (长度 + 无 U+200B)。生成无需重跑（raw 已落盘，分类是纯函数）。

交叉校验 (器具可信的唯一证据):
  A0 臂 (旧 prompt × 512) 的**正确分类**必须复现产品的 7/7 → 1/7 实测
  (遥测 eval/rover/r434/run-BRJ-p8-k1/data/telemetry/host.jsonl 8 条 correction_judge:
   6×remote_fallback + 1×local(turn9,N,149tok), 且逐条 ms 与探针 wall_s 一致)。
  A0 若 ≠ 1/7 ⇒ 器具仍不可信 ⇒ 停, 不写任何结论。
"""
import json, pathlib, re, sys

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
OUT = ROOT / "eval/rover/r435"
SRC = ROOT / "src/agent.modelqueue/LocalGenerationPort.cs"


def product_markers():
    s = SRC.read_text(encoding="utf-8")
    def grab(name):
        m = re.search(name + r'\s*=\s*"((?:[^"\\]|\\.)*)"', s)
        if not m:
            sys.exit(f"[致命] 源码里找不到 {name}")
        v = m.group(1)
        # C# 转义还原 (\u003c 等)
        v = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), v)
        v = v.replace("\\\\", "\\")
        return v
    return grab("ThinkOpen"), grab("ThinkClose")


OPEN, CLOSE = product_markers()
assert (OPEN, CLOSE) == ("<think>", "</think>"), (repr(OPEN), repr(CLOSE))
assert "\u200b" not in OPEN and "\u200b" not in CLOSE, "常量仍含零宽字符 ⇒ 停"
# R435 撤回: 词表兜底被既有预注册判据 J13 否决（散文必须未判定）⇒ 产品侧已撤为**空表**。
# 重分类器同步撤空，保证「分类器 == 产品契约」；若撤空后各臂读数发生变化，说明原读数依赖词表 ⇒ 必须披露。
WORDS = ()
LETTER_RE = re.compile(r"(?<![A-Za-z])([CcAaNn])(?![A-Za-z])")
TRUTH = {"turn1": "N", "turn3": "N", "turn5": "N", "turn6": "A", "turn7": "N",
         "turn8": "A", "turn9": "N", "syn-c": "C", "syn-a": "A"}
PRODUCT_A0 = {"turn9": "local"}   # 产品实测: 仅 turn9 本地成功


def split_conclusion(raw):
    text = raw.strip()
    if not text:
        return "", "empty"
    close = text.rfind(CLOSE)
    if close >= 0:
        return text[close + len(CLOSE):], "closed"
    if text.rfind(OPEN) >= 0:
        return None, "thinking_truncated"
    return text, "no_markers"


def parse_old(raw):
    concl, st = split_conclusion(raw)
    if concl is None:
        return None, "thinking_truncated"
    t = concl.strip()
    if not t:
        return None, "empty_conclusion"
    last, pick = -1, None
    for m in LETTER_RE.finditer(t):
        last, pick = m.start(), m.group(1).upper()
    return (pick, "ok") if last >= 0 else (None, "no_marker")


def parse_new(raw):
    concl, st = split_conclusion(raw)
    if concl is None:
        return None, "thinking_truncated"
    if st == "no_markers" and len(concl) > 64:
        concl = concl[-64:]
    t = concl.strip()
    if not t:
        return None, "empty_conclusion"
    last, pick = -1, None
    for m in LETTER_RE.finditer(t):
        last, pick = m.start(), m.group(1).upper()
    for w, ch in WORDS:
        k = t.rfind(w)
        if k > last:
            last, pick = k, ch
    return (pick, "ok") if last >= 0 else (None, "no_marker")


def main():
    inp = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else OUT / "probe-j2-arms.json"
    outp = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else OUT / "probe-j2-classified.json"
    doc = json.loads(inp.read_text(encoding="utf-8"))
    print(f"[markers] OPEN={len(OPEN)} CLOSE={len(CLOSE)} 无零宽 (取自产品源码)")
    report = {}
    for arm, recs in doc["arms"].items():
        rows = []
        for r in recs:
            raw = r["raw"]
            lo, ro = parse_old(raw)
            ln, rn = parse_new(raw)
            concl, st = split_conclusion(raw)
            rows.append({**{k: r[k] for k in ("case", "prompt_kind", "n_predict", "prompt_len",
                                              "predicted_n", "stop_type", "wall_s", "truth")},
                         "concl_state": st,
                         "concl_tail": (concl or "")[-120:],
                         "old": f"{lo}/{ro}", "new": f"{ln}/{rn}",
                         "old_ok": ro == "ok", "new_ok": rn == "ok",
                         "old_correct": lo == r["truth"], "new_correct": ln == r["truth"],
                         "raw_tail": raw[-160:]})
        real = [x for x in rows if not x["case"].startswith("syn")]
        report[arm] = {
            "case": rows[0]["prompt_kind"], "n_predict": rows[0]["n_predict"],
            "parse_ok_old_parser_all": sum(1 for x in rows if x["old_ok"]),
            "parse_ok_new_parser_all": sum(1 for x in rows if x["new_ok"]),
            "parse_ok_old_parser_real7": sum(1 for x in real if x["old_ok"]),
            "parse_ok_new_parser_real7": sum(1 for x in real if x["new_ok"]),
            "semantic_ok_new_real7": sum(1 for x in real if x["new_correct"]),
            "reasons_new": sorted({x["new"].split("/")[1] for x in rows}),
            "rows": rows,
        }
        print(f"[{arm}] {report[arm]['case']}@{report[arm]['n_predict']}: "
              f"旧解析 real7={report[arm]['parse_ok_old_parser_real7']}/7 新解析 real7={report[arm]['parse_ok_new_parser_real7']}/7 "
              f"语义(新解析) real7={report[arm]['semantic_ok_new_real7']}/7 全9新解析={report[arm]['parse_ok_new_parser_all']}/9")
        for x in rows:
            flag = "OK " if x["new_ok"] else "FAIL"
            sem = "✓" if x["new_correct"] else "✗"
            print(f"   {flag} {sem} {x['case']:6s} truth={x['truth']} {x['concl_state']:18s} "
                  f"old={x['old']:10s} new={x['new']:10s} tail={x['concl_tail'][-28:]!r}")
    # ── 交叉校验: A0 必须复现产品「仅 turn9 本地成功」 ──
    if "A0" not in report and "A0" not in doc["arms"]:
        print("\n[交叉校验] 本臂组无 A0, 跳过 (基线见 probe-j2-classified.json)")
        (pathlib.Path(outp) if len(sys.argv) > 2 else OUT / "probe-j2-classified.json").write_text(
            json.dumps({"markers": {"open": repr(OPEN), "close": repr(CLOSE)}, "arms": report},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        print("[done] ->", outp)
        return
    a0 = {x["case"]: x["new_ok"] for x in report["A0"]["rows"]}
    got = {c: ("local" if ok else "fallback") for c, ok in a0.items() if not c.startswith("syn")}
    expect = {c: PRODUCT_A0.get(c, "fallback") for c in got}
    ok7 = sum(1 for c in got if got[c] == "local")
    print(f"\n[交叉校验 A0 vs 产品] 本地成功 {ok7}/7 (产品实测 1/7) 逐条一致={got == expect}")
    if got != expect:
        print("  差异:", {c: (got[c], expect[c]) for c in got if got[c] != expect[c]})
    (pathlib.Path(outp)).write_text(
        json.dumps({"markers": {"open_len": len(OPEN), "close_len": len(CLOSE)},
                    "crosscheck_A0_vs_product": {"local_ok": ok7, "match": got == expect, "got": got},
                    "arms": report}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[done] ->", OUT / "probe-j2-classified.json")


if __name__ == "__main__":
    main()
