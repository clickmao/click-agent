#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q9 定版补丁: probe_doc_ref_integrity v2.4.1 -> v2.5.0
增补「文档→代码」引用图**边强轴** (强边 declared_* / 弱边 *_mention), 见 prereg_q9.json (先写判据后测)。
锚点全部为**定版字面**替换, 每条替换断言命中次数, 命中数不符即中止 (不静默)。
"""
import hashlib
import json
import py_compile
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "eval/capability/exp1-q4/probe_doc_ref_integrity.py"
DST = Path(__file__).resolve().parent / "probe_v250.py"

# ---------------------------------------------------------------- 新代码块
EDGE_BLOCK = '''# ---------------------------------------------------------------- 引用图边强轴 (v2.5.0)
# 计划定义 (docs/plans/v0.22.0-longterm-backlog.md 最前未完成项):
#   「文档→代码」引用图的**边强**: 强边 = 引用了被引文件里**有声明**的符号 (declared_*);
#   弱边 = 引用了只在该文件里**出现**的符号 (*_mention: 注释 / 字符串 / 调用点)。
# 平行轴纪律 (与 v2.4.0 阶梯同): 只给边打标, **不改判**任何 citation 的 verdict, 不动打分层。
EDGE_STRONG = "strong"
EDGE_WEAK = "weak"
EDGE_BROKEN = "broken"
EDGE_WAIVED = "waived"
EDGE_LEVELS = (EDGE_STRONG, EDGE_WEAK, EDGE_BROKEN, EDGE_WAIVED)
WEAK_CODE = "weak_code"
WEAK_NONCODE = "weak_noncode"
STRONG_RUNGS = ("declared_type", "declared_member")
WEAK_RUNGS = ("code_mention", "noncode_mention")


def edge_strength(rec: dict) -> dict:
    """由 citation 记录自身的符号形态派生边强 (faces 来自 symbol_faces / relocated_symbol_faces)。

    聚合口径**预注册 = 最强胜**: 一条边只要有一枚符号在该文件里有声明即判强边; 同边内
    较弱/断符号数单独计数 (n_weak / n_broken) ⇒ 强边里混弱符号**可见**, 不被最强胜吞掉。
    faces 缺失或全 n/a_kind ⇒ **弃权** (测不到, 不进分母): 测不到 != 判为弱边。
    """
    faces = rec.get("symbol_faces")
    if faces is None:
        faces = rec.get("relocated_symbol_faces")
    real = {k: v for k, v in (faces or {}).items() if v != FACE_NA}
    if not real:
        return {"edge": EDGE_WAIVED, "sublevel": None, "rungs": {}, "n_weak": 0, "n_broken": 0}
    n_weak = sum(1 for v in real.values() if v in WEAK_RUNGS)
    n_broken = sum(1 for v in real.values() if v == "absent")
    if any(v in STRONG_RUNGS for v in real.values()):
        return {"edge": EDGE_STRONG, "sublevel": None, "rungs": real,
                "n_weak": n_weak, "n_broken": n_broken}
    if n_weak:
        sub = WEAK_CODE if any(v == "code_mention" for v in real.values()) else WEAK_NONCODE
        return {"edge": EDGE_WEAK, "sublevel": sub, "rungs": real,
                "n_weak": n_weak, "n_broken": n_broken}
    return {"edge": EDGE_BROKEN, "sublevel": None, "rungs": real,
            "n_weak": 0, "n_broken": n_broken}


def edge_of(c: dict) -> str:
    return c.get("edge_strength") if c.get("edge_strength") else edge_strength(c)["edge"]


def weak_edges_of(citations: list):
    """弱边**全量**清单 (供人工全量抽检): 逐条给 doc/doc_line/被引文件/符号形态/行窗定位。"""
    out = []
    for c in citations:
        if c.get("in_code_fence") or c.get("kind") != "code":
            continue
        e = edge_strength(c)
        if e["edge"] != EDGE_WEAK:
            continue
        out.append({"doc": c["doc"], "doc_line": c["doc_line"], "raw": c["raw"],
                    "resolved": c.get("resolved"), "path": c["path"],
                    "verdict": c["verdict"], "symbols": c["symbols"],
                    "rungs": e["rungs"], "sublevel": e["sublevel"],
                    "weak_symbols": e["n_weak"], "broken_symbols": e["n_broken"],
                    "line_start": c["line_start"], "line_end": c["line_end"],
                    "input_sha": c.get("input_sha")})
    return out


'''

AGG_BLOCK = '''    # ---- v2.5.0 边强轴 (平行轴): 逐条 live 代码引用打边强标签, 再聚合分布 + 弱边全量清单
    for c in live_code:
        _e = edge_strength(c)
        c["edge_strength"] = _e["edge"]
        c["edge_sublevel"] = _e["sublevel"]
        c["edge_weak_symbols"] = _e["n_weak"]
        c["edge_broken_symbols"] = _e["n_broken"]
    edge_counts = Counter(c["edge_strength"] for c in live_code)
    edge_subs = Counter(c["edge_sublevel"] for c in live_code if c["edge_sublevel"])
    weak_edges = weak_edges_of(live_code)
    mixed_weak_in_strong = sum(1 for c in live_code
                               if c["edge_strength"] == EDGE_STRONG and c["edge_weak_symbols"] > 0)
    edge_levels_nontrivial = len([k for k in edge_counts if k != EDGE_WAIVED]) >= 2
'''

SELFTEST_BLOCK = '''    # ---- 边强轴 (v2.5.0) 两侧夹具: 强 / 弱(码面) / 弱(非码面) / 断 / 弃权 + 混边可见 + 不改判负控
    _by = {}
    for _j in judged:
        if len(_j.get("symbols") or []) == 1:
            _by.setdefault(_j["symbols"][0], []).append(_j)
    ck("E1_edge_strong_declared", [edge_strength(j)["edge"] for j in _by["DeltaThing"]], [EDGE_STRONG])
    ck("E2_edge_weak_code_mention", [edge_strength(j)["edge"] for j in _by["OtherThing"]], [EDGE_WEAK])
    ck("E3_edge_weak_sublevel_code", [edge_strength(j)["sublevel"] for j in _by["OtherThing"]], [WEAK_CODE])
    ck("E4_edge_weak_noncode_comment",
       [edge_strength(j)["edge"] for j in _by["CommentedThing"]], [EDGE_WEAK])
    ck("E5_edge_weak_sublevel_noncode",
       [edge_strength(j)["sublevel"] for j in _by["CommentedThing"]], [WEAK_NONCODE])
    ck("E6_edge_broken_on_absent", [edge_strength(j)["edge"] for j in _by["MissingThing"]], [EDGE_BROKEN])
    ck("E7_edge_weak_does_not_rejudge",
       [j["verdict"] for j in _by["CommentedThing"]], ["ok"])  # 负控: 弱边 verdict 仍是 ok
    ck("E8_edge_broken_verdict_unchanged",
       [j["verdict"] for j in _by["MissingThing"]], ["symbol_absent"])
    _mix = [j for j in judged if set(j.get("symbols") or []) == {"DeltaThing", "OnlyCommentThing"}]
    ck("E9_edge_mixed_strongest_wins", [edge_strength(j)["edge"] for j in _mix], [EDGE_STRONG])
    ck("E10_edge_mixed_weak_symbols_visible", [edge_strength(j)["n_weak"] for j in _mix], [1])
    _wv = [edge_strength(j)["edge"] for j in judged
           if j["verdict"] in ("stale_path", "waived", "retired")]
    ck("E11_edge_waived_when_unresolved", sorted(set(_wv)), [EDGE_WAIVED])
    ck("E12_edge_waived_nonempty", len(_wv) > 0, True)
    _lv = Counter(edge_strength(j)["edge"] for j in judged)
    ck("E13_edge_levels_conserved", sum(_lv.values()), len(judged))
    ck("E14_edge_levels_nontrivial_fixture",
       len([k for k in _lv if k != EDGE_WAIVED]) >= 3, True)
    ck("E15_weak_edges_of_both_sublevels_present",
       sorted({e["sublevel"] for e in weak_edges_of(judged)}), [WEAK_CODE, WEAK_NONCODE])
    ck("E16_weak_edges_of_conserved",
       len(weak_edges_of(judged)),
       len([j for j in judged if edge_strength(j)["edge"] == EDGE_WEAK]))
    ck("E17_weak_edges_of_context_locatable",
       all(bool(e["resolved"]) and e["line_start"] >= 1 and e["rungs"] for e in weak_edges_of(judged)),
       True)
'''

# --------- 夹具: Beta.cs 增一条**只出现在注释里**的符号; t.md 增一条单引用两符号的混边行
FIXTURE_BETA_OLD = '''    (tmp / "src/agent/x/Beta.cs").write_text(
        "class BetaThing { void Go() {} }\\n" * 40'''
FIXTURE_BETA_NEW = '''    (tmp / "src/agent/x/Beta.cs").write_text(
        "// OnlyCommentThing 只出现在本注释里\\n"
        + "class BetaThing { void Go() {} }\\n" * 40'''

FIXTURE_DOC_OLD = '''           "- 阶梯 absent: `MissingThing` [src/agent/x/Beta.cs:3]\\n")'''
FIXTURE_DOC_NEW = '''           "- 阶梯 absent: `MissingThing` [src/agent/x/Beta.cs:3]\\n"
           # ---- 边强轴 (v2.5.0): 单引用两符号 ⇒ 混边夹具 (强 declared_member + 弱 noncode_mention)
           "- 边强 混边(强+弱非码): `DeltaThing` 与 `OnlyCommentThing` [src/agent/x/Beta.cs:3]\\n")'''

REPLACEMENTS = [
    ('PROBE_VERSION = "2.4.1"', 'PROBE_VERSION = "2.5.0"', 1),
    ('    "G7_ladder_nontrivial": "符号存在性阶梯在真实语料上 >=2 级分布 (恒同一级 ⇒ 该轴无判别力 ⇒ 先查仪器再谈被测)",\n}',
     '    "G7_ladder_nontrivial": "符号存在性阶梯在真实语料上 >=2 级分布 (恒同一级 ⇒ 该轴无判别力 ⇒ 先查仪器再谈被测)",\n'
     '    "G8_edge_levels_nontrivial_and_conserved": "边强档位 (非弃权) >=2 类 ∧ 边强计数之和 == live 代码引用数 (恒同一档 ⇒ 该轴无判别力; 和不等 ⇒ 归属漏项)",\n}',
     1),
    ('def judge_citation(repo: Repo, c: dict):', EDGE_BLOCK + 'def judge_citation(repo: Repo, c: dict):', 1),
    ('    all_syms = POSITIVE_SYMBOLS + NEGATIVE_SYMBOLS + TARGET_SYMBOLS', AGG_BLOCK + '\n    all_syms = POSITIVE_SYMBOLS + NEGATIVE_SYMBOLS + TARGET_SYMBOLS', 1),
    ('        "n_symbol_faces": sum(face_rungs.values()),',
     '        "n_symbol_faces": sum(face_rungs.values()),\n'
     '        "edge_strength_counts": dict(edge_counts),\n'
     '        "edge_sublevel_counts": dict(edge_subs),\n'
     '        "n_edges_strong_with_weak_symbols": mixed_weak_in_strong,\n'
     '        "edge_weak_list": weak_edges,\n'
     '        "edge_levels_nontrivial": edge_levels_nontrivial,',
     1),
    ('        g7 = bool(r1["n_symbol_faces"] == 0 or len(rungs_real) >= 2)',
     '        g7 = bool(r1["n_symbol_faces"] == 0 or len(rungs_real) >= 2)\n'
     '        _ec = r1["edge_strength_counts"]\n'
     '        g8 = bool(r1["n_citations_code_live"] == 0 or\n'
     '                  (sum(_ec.values()) == r1["n_citations_code_live"]\n'
     '                   and r1["edge_levels_nontrivial"]))',
     1),
    ('            "G7_n_symbol_faces": r1["n_symbol_faces"],',
     '            "G7_n_symbol_faces": r1["n_symbol_faces"],\n'
     '            "G8_edge_counts": r1["edge_strength_counts"],\n'
     '            "G8_edge_counts_sum_eq_live": sum(r1["edge_strength_counts"].values()) == r1["n_citations_code_live"],\n'
     '            "G8_edge_levels_nontrivial": r1["edge_levels_nontrivial"],',
     1),
    ('        all_pass = bool(g1 and g2 and g5 and g3 and g6 and g7)',
     '        all_pass = bool(g1 and g2 and g5 and g3 and g6 and g7 and g8)', 1),
    ('            "n_symbol_faces": r1["n_symbol_faces"],\n            "stale_like_n": stale_like,',
     '            "n_symbol_faces": r1["n_symbol_faces"],\n'
     '            "edge_strength_criteria": {\n'
     '                "strong": "至少一枚被引符号在该文件里有声明 (declared_type/declared_member)",\n'
     '                "weak": "无声明但至少一枚符号在该文件里出现 (*_mention)",\n'
     '                "broken": "全部符号在该文件查无",\n'
     '                "waived": "引用未解析/不可剥离/本身 waived ⇒ 弃权, 不进分母",\n'
     '                "aggregation": "strongest-wins (混边内弱/断符号数单独计数, 不丢信息)"},\n'
     '            "edge_strength_counts": r1["edge_strength_counts"],\n'
     '            "edge_sublevel_counts": r1["edge_sublevel_counts"],\n'
     '            "edge_weak_n": len(r1["edge_weak_list"]),\n'
     '            "edge_weak_list": r1["edge_weak_list"],\n'
     '            "n_edges_strong_with_weak_symbols": r1["n_edges_strong_with_weak_symbols"],\n'
     '            "stale_like_n": stale_like,',
     1),
    ('                                          "relocated_to", "relocated_fact_verdict") if k in c},',
     '                                          "relocated_to", "relocated_fact_verdict",\n'
     '                                          "edge_strength", "edge_sublevel",\n'
     '                                          "edge_weak_symbols", "edge_broken_symbols") if k in c},',
     1),
    ('''    ok = all(c["pass"] for c in checks)
    print(json.dumps({"selftest": "probe_doc_ref_integrity-v" + PROBE_VERSION''',
     SELFTEST_BLOCK + '''    ok = all(c["pass"] for c in checks)
    print(json.dumps({"selftest": "probe_doc_ref_integrity-v" + PROBE_VERSION''',
     1),
    (FIXTURE_BETA_OLD, FIXTURE_BETA_NEW, 1),
    (FIXTURE_DOC_OLD, FIXTURE_DOC_NEW, 1),
    ('''                "本探针只读文件, 不改产品源码, 不跑 dotnet, 不占轮号",''',
     '''                "v2.5.0 边强轴是**词法级**分类 (非 AST): noncode_mention 只说明该符号在此文件不是代码事实的声明/使用面 (引用可能指向注释/字符串/历史示例里的同名串), **不说明引用错误** —— 弱边 != 缺陷, 需人工全量复核",\n'''
     '''                "边强聚合口径 = 最强胜 (单枚声明即强边): 强边里混弱符号的情形由 n_edges_strong_with_weak_symbols + 逐条 edge_weak_symbols 单独可见, 不因聚合而消失",\n'''
     '''                "边强只看**被引文件内部**的符号形态, 不做跨文件符号解析 (符号声明在他处的情形由 weak_edge_inspect.py 的 declared_elsewhere 旁证另计)",\n'''
     '''                "本探针只读文件, 不改产品源码, 不跑 dotnet, 不占轮号",''',
     1),
    ('''            "n_inputs_fingerprinted": r1["n_inputs_fingerprinted"],''',
     '''            "n_inputs_fingerprinted": r1["n_inputs_fingerprinted"],\n'''
     '''            "edge_strength_counts": r1["edge_strength_counts"],\n'''
     '''            "edge_sublevel_counts": r1["edge_sublevel_counts"],\n'''
     '''            "edge_weak_n": len(r1["edge_weak_list"]),\n'''
     '''            "n_edges_strong_with_weak_symbols": r1["n_edges_strong_with_weak_symbols"],''',
     1),
]


def main():
    src = SRC.read_text(encoding="utf-8")
    out = src
    report = []
    for old, new, want in REPLACEMENTS:
        got = out.count(old)
        report.append({"anchor": old.strip().splitlines()[0][:72], "hits": got, "want": want})
        if got != want:
            print(json.dumps({"stage": "anchor", "error": "hit_count_mismatch", "report": report},
                             ensure_ascii=False, indent=2))
            return 2
        out = out.replace(old, new)
    DST.write_text(out, encoding="utf-8")
    py_compile.compile(str(DST), doraise=True)
    pins = {"source": str(SRC.relative_to(ROOT)),
            "source_sha256": hashlib.sha256(src.encode("utf-8")).hexdigest(),
            "target": str(DST.relative_to(ROOT)),
            "target_sha256": hashlib.sha256(out.encode("utf-8")).hexdigest(),
            "n_replacements": len(REPLACEMENTS)}
    (DST.with_name("patch_pins.json")).write_text(
        json.dumps({**pins, "anchors": report}, ensure_ascii=False, indent=2), encoding="utf-8")
    st = subprocess.run([sys.executable, str(DST), "--selftest"], capture_output=True, text=True)
    ok = None
    try:
        ok = json.loads(st.stdout)["all_pass"]
    except Exception:
        pass
    print(json.dumps({"stage": "patch+selftest", **pins, "selftest_exit": st.returncode,
                      "selftest_all_pass": ok}, ensure_ascii=False, indent=2))
    return 0 if (st.returncode == 0 and ok) else 2


if __name__ == "__main__":
    sys.exit(main())
