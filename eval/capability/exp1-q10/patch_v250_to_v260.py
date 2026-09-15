#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q10 器具升级 v2.5.0 -> v2.6.0: 弱边再细分轴 (weak_kind)。

纯文本锚点补丁 (非正则改写), 每条锚点必须**恰好命中一次**; 源文件与产物 sha256 都落 patch_pins.json。
不做 AST, 不改产品源码, 不跑 dotnet。幂等: 每次都从 v2.5.0 源重建产物 (可重跑)。
"""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "exp1-q9" / "probe_v250.py"
DST = HERE / "probe_v260.py"
PINS = HERE / "patch_pins.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------- 新增代码块
KIND_CONSTS = '''
# ---------------------------------------------------------------- 弱边再细分轴 (v2.6.0)
# 预注册 (prereg_q10.json): 优先级 cross_file > named_fact > comment_only > other,
# 施加于**符号级**与**引用级边**两个粒度, 两个计数分开落盘, 互不换算。
# 语义: 名字类事实 (环境变量名/遥测键/JSON 键) 在代码里**不可能有声明形态** ⇒ 树内零声明
#       不构成缺陷证据; 仅非码面提及的非名字形态符号 (PascalCase 仅现于注释/字符串) 同理。
WEAK_CROSS_FILE = "cross_file"
WEAK_NAMED_FACT = "named_fact"
WEAK_COMMENT_ONLY = "comment_only"
WEAK_OTHER = "other"
WEAK_KINDS = (WEAK_CROSS_FILE, WEAK_NAMED_FACT, WEAK_COMMENT_ONLY, WEAK_OTHER)
NAME_SHAPE_SNAKE = "snake_case"
NAME_SHAPE_SCREAM = "SCREAMING_SNAKE"
NAME_SHAPE_OTHER = "other"
NAME_SHAPES = (NAME_SHAPE_SNAKE, NAME_SHAPE_SCREAM)
NAME_SHAPE_RE = {
    NAME_SHAPE_SNAKE: re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$"),
    NAME_SHAPE_SCREAM: re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$"),
}
'''

KIND_FUNCS = '''
def name_shape(sym: str) -> str:
    """符号名形态 (仅三种): snake_case / SCREAMING_SNAKE / other。"""
    if NAME_SHAPE_RE[NAME_SHAPE_SNAKE].match(sym):
        return NAME_SHAPE_SNAKE
    if NAME_SHAPE_RE[NAME_SHAPE_SCREAM].match(sym):
        return NAME_SHAPE_SCREAM
    return NAME_SHAPE_OTHER


def declaration_index(repo: Repo, symbols):
    """树内**他处声明**索引 (跨文件): {sym: [声明所在文件...]}。

    语料口径与 symbol_occurrences 完全一致 (repo.glob("src/**/*.cs")) —— 不新增语料根、不做 AST。
    优化: 先做子串预筛 (名不在文本里 ⇒ 不可能声明) 再算形态 ⇒ 语义等同逐文件 faces_for, 但只在含名文件上算。
    """
    syms = sorted(set(symbols))
    out = {s: [] for s in syms}
    if not syms:
        return out
    for rel in repo.glob("src/**/*.cs"):
        text, _ = repo.read(rel)
        if text is None:
            continue
        hit = [s for s in syms if s in text]
        if not hit:
            continue
        ff = faces_for(repo, rel, text, hit)
        for s in hit:
            if ff.get(s) in STRONG_RUNGS:
                out[s].append(rel)
    return {s: sorted(v) for s, v in out.items()}


def symbol_weak_kind(sym: str, rung: str, declared_elsewhere):
    """符号级细分 (同一规则的最小粒度): rung 为 None(=n/a_kind) ⇒ None (弃权不分类)。"""
    if rung in (None, FACE_NA):
        return None
    if declared_elsewhere:
        return WEAK_CROSS_FILE
    if rung != "noncode_mention":
        return WEAK_OTHER
    if name_shape(sym) in NAME_SHAPES:
        return WEAK_NAMED_FACT
    return WEAK_COMMENT_ONLY


def weak_kind(rec: dict, decl_idx: dict) -> dict:
    """弱边再细分 (v2.6.0 平行轴)。只读 rec 里**已记录**的字段 + 树内声明索引 ⇒ 不改判、不改语料口径。

    非弱边 (强/断/弃权) ⇒ edge_kind=None (只对弱边细分, 守恒分母 = 弱边数)。
    优先级 (预注册): cross_file > named_fact > comment_only > other。
    """
    faces = rec.get("symbol_faces")
    if faces is None:
        faces = rec.get("relocated_symbol_faces")
    real = {k: v for k, v in (faces or {}).items() if v != FACE_NA}
    e = edge_strength(rec)
    cited = rec.get("resolved") or rec.get("path")
    per = []
    for sym in sorted(real):
        files = [f for f in (decl_idx.get(sym) or []) if f != cited]
        per.append({"symbol": sym, "rung": real[sym], "shape": name_shape(sym),
                    "declared_elsewhere": len(files), "declared_elsewhere_files": files,
                    "symbol_kind": symbol_weak_kind(sym, real[sym], files)})
    if e["edge"] != EDGE_WEAK or not real:
        # 边级不分类 (守恒分母 = 弱边数), 但**逐符号细分照给**: 强边里混的弱符号
        # (v2.5.0 的 n_edges_strong_with_weak_symbols) 不因此从新轴上消失。
        return {"edge_kind": None,
                "kind_reason": "非弱边 (只给逐符号细分, 边级不分类)" if real else None,
                "kind_per_symbol": per}
    sym_kinds = [p["symbol_kind"] for p in per]
    if WEAK_CROSS_FILE in sym_kinds:
        kind, reason = WEAK_CROSS_FILE, "至少一枚弱符号在树内他处有声明"
    elif all(k == WEAK_NAMED_FACT for k in sym_kinds):
        kind, reason = WEAK_NAMED_FACT, "全部弱符号: 名字形态 ∧ 非码面 ∧ 他处零声明"
    elif all(k == WEAK_COMMENT_ONLY for k in sym_kinds):
        kind, reason = WEAK_COMMENT_ONLY, "全部弱符号: 非名字形态 ∧ 非码面 ∧ 他处零声明"
    else:
        kind, reason = WEAK_OTHER, "含码面提及或形态-面不齐 (catch-all)"
    return {"edge_kind": kind, "kind_reason": reason, "kind_per_symbol": per}

'''

EDITS = [
    # --- 版本号
    ('PROBE_VERSION = "2.5.0"', 'PROBE_VERSION = "2.6.0"'),
    # --- 常量
    ('WEAK_RUNGS = ("code_mention", "noncode_mention")\n',
     'WEAK_RUNGS = ("code_mention", "noncode_mention")\n' + KIND_CONSTS),
    # --- 函数 (插在 edge_of 之前)
    ('def edge_of(c: dict) -> str:', KIND_FUNCS + '\ndef edge_of(c: dict) -> str:'),
    # --- 弱边全量清单带上细分字段
    ('                    "weak_symbols": e["n_weak"], "broken_symbols": e["n_broken"],\n',
     '                    "weak_symbols": e["n_weak"], "broken_symbols": e["n_broken"],\n'
     '                    "edge_kind": c.get("edge_kind"),\n'
     '                    "kind_reason": c.get("kind_reason"),\n'
     '                    "kind_per_symbol": c.get("kind_per_symbol"),\n'),
    # --- run_pass: 计轴
    ('    edge_levels_nontrivial = len([k for k in edge_counts if k != EDGE_WAIVED]) >= 2\n',
     '    edge_levels_nontrivial = len([k for k in edge_counts if k != EDGE_WAIVED]) >= 2\n'
     '\n'
     '    # ---- v2.6.0 弱边再细分 (平行轴): 名字类事实 / 跨文件有声明 / 仅非码面 / 其余\n'
     '    _weak_syms = sorted({s for c in live_code\n'
     '                         for s, v in (c.get("symbol_faces") or {}).items()\n'
     '                         if v in WEAK_RUNGS})\n'
     '    decl_idx = declaration_index(repo, _weak_syms)\n'
     '    for c in live_code:\n'
     '        _k = weak_kind(c, decl_idx)\n'
     '        c["edge_kind"] = _k["edge_kind"]\n'
     '        c["kind_reason"] = _k["kind_reason"]\n'
     '        c["kind_per_symbol"] = _k["kind_per_symbol"]\n'
     '    kind_counts = Counter(c["edge_kind"] for c in live_code if c["edge_kind"])\n'
     '    kind_sym_counts = Counter(p["symbol_kind"] for c in live_code\n'
     '                              for p in (c.get("kind_per_symbol") or []))\n'
     '    mixed_strong_kind_counts = Counter(p["symbol_kind"] for c in live_code\n'
     '                                       if c["edge_strength"] == EDGE_STRONG\n'
     '                                       for p in (c.get("kind_per_symbol") or [])\n'
     '                                       if p["rung"] in WEAK_RUNGS)\n'
     '    n_weak_edges = sum(1 for c in live_code if c["edge_strength"] == EDGE_WEAK)\n'
     '    kind_conserved = (sum(kind_counts.values()) == n_weak_edges)\n'
     '    kind_kinds_nontrivial = len([k for k in kind_counts]) >= 2\n'
     '    n_weak_symbols_classified = sum(kind_sym_counts.values())\n'),
    # --- run_pass: 返回字段
    ('        "edge_weak_list": weak_edges,\n        "edge_levels_nontrivial": edge_levels_nontrivial,\n',
     '        "edge_weak_list": weak_edges,\n'
     '        "edge_levels_nontrivial": edge_levels_nontrivial,\n'
     '        "n_weak_edges": n_weak_edges,\n'
     '        "edge_kind_counts": dict(kind_counts),\n'
     '        "weak_symbol_kind_counts": dict(kind_sym_counts),\n'
     '        "mixed_strong_symbol_kind_counts": dict(mixed_strong_kind_counts),\n'
     '        "n_mixed_strong_symbols_classified": sum(mixed_strong_kind_counts.values()),\n'
     '        "n_weak_symbols_classified": n_weak_symbols_classified,\n'
     '        "kind_conserved": kind_conserved,\n'
     '        "kind_kinds_nontrivial": kind_kinds_nontrivial,\n'),
    # --- G9 计算
    ('        gate_dict = {\n',
     '        # ---- G9 细分轴非退化 + 守恒 (弱边数 == 0 ⇒ vacuous pass, 但显式记 vacuous)\n'
     '        _kc = r1["edge_kind_counts"]\n'
     '        g9 = bool(r1["n_citations_code_live"] == 0\n'
     '                  or r1["n_weak_edges"] == 0\n'
     '                  or (r1["kind_conserved"] and r1["kind_kinds_nontrivial"]))\n'
     '        g9_vacuous = bool(r1["n_citations_code_live"] == 0 or r1["n_weak_edges"] == 0)\n'
     '        gate_dict = {\n'),
    # --- G9 字段
    ('            "G6_n_continuations_live": r1["n_continuations_live"],\n',
     '            "G6_n_continuations_live": r1["n_continuations_live"],\n'
     '            "G9_kind_counts": dict(_kc),\n'
     '            "G9_weak_symbol_kind_counts": r1["weak_symbol_kind_counts"],\n'
     '            "G9_n_weak_edges": r1["n_weak_edges"],\n'
     '            "G9_mixed_strong_symbol_kind_counts": r1["mixed_strong_symbol_kind_counts"],\n'
     '            "G9_n_mixed_strong_symbols_classified": r1["n_mixed_strong_symbols_classified"],\n'
     '            "G9_conserved": r1["kind_conserved"],\n'
     '            "G9_kinds_nontrivial": r1["kind_kinds_nontrivial"],\n'
     '            "G9_vacuous": g9_vacuous,\n'
     '            "G9_kind_nontrivial": g9,\n'),
    # --- all_pass 纳入 G9
    ('        all_pass = bool(g1 and g2 and g5 and g3 and g6 and g7 and g8)',
     '        all_pass = bool(g1 and g2 and g5 and g3 and g6 and g7 and g8 and g9)'),
    # --- result 字段
    ('            "edge_weak_list": r1["edge_weak_list"],\n',
     '            "edge_weak_list": r1["edge_weak_list"],\n'
     '            "edge_kind_definitions": {\n'
     '                "cross_file": "存在弱符号在树内他处有声明 (declared_type|declared_member)",\n'
     '                "named_fact": "名字形态(snake/SCREAMING) ∧ 非码面 ∧ 他处零声明",\n'
     '                "comment_only": "非名字形态 ∧ 非码面 ∧ 他处零声明",\n'
     '                "other": "含码面提及或形态-面不齐 (catch-all, 不判红)",\n'
     '                "precedence": "cross_file > named_fact > comment_only > other",\n'
     '                "granularity": "符号级与边级两计数分开, 互不换算"},\n'
     '            "edge_kind_counts": r1["edge_kind_counts"],\n'
     '            "weak_symbol_kind_counts": r1["weak_symbol_kind_counts"],\n'
     '            "mixed_strong_symbol_kind_counts": r1["mixed_strong_symbol_kind_counts"],\n'
     '            "n_mixed_strong_symbols_classified": r1["n_mixed_strong_symbols_classified"],\n'
     '            "n_weak_edges": r1["n_weak_edges"],\n'
     '            "n_weak_symbols_classified": r1["n_weak_symbols_classified"],\n'
     '            "kind_conserved": r1["kind_conserved"],\n'),
    # --- stdout 摘要
    ('            "edge_weak_n": len(r1["edge_weak_list"]),\n'
     '            "n_edges_strong_with_weak_symbols": r1["n_edges_strong_with_weak_symbols"],\n',
     '            "edge_weak_n": len(r1["edge_weak_list"]),\n'
     '            "edge_kind_counts": r1["edge_kind_counts"],\n'
     '            "weak_symbol_kind_counts": r1["weak_symbol_kind_counts"],\n'
     '            "mixed_strong_symbol_kind_counts": r1["mixed_strong_symbol_kind_counts"],\n'
     '            "kind_conserved": r1["kind_conserved"],\n'
     '            "n_edges_strong_with_weak_symbols": r1["n_edges_strong_with_weak_symbols"],\n'),
    # --- citations.jsonl 落盘
    ('                                          "edge_weak_symbols", "edge_broken_symbols") if k in c},',
     '                                          "edge_weak_symbols", "edge_broken_symbols",\n'
     '                                          "edge_kind", "kind_reason", "kind_per_symbol") if k in c},'),
    # --- 诚实边界
    ('                "边强只看**被引文件内部**的符号形态, 不做跨文件符号解析 (符号声明在他处的情形由 weak_edge_inspect.py 的 declared_elsewhere 旁证另计)",\n',
     '                "边强只看**被引文件内部**的符号形态, 不做跨文件符号解析 (符号声明在他处的情形由 weak_edge_inspect.py 的 declared_elsewhere 旁证另计)",\n'
     '                "v2.6.0 细分轴 (weak_kind) 的声明索引仍是**词法级**启发式 (非 AST): declared_elsewhere 是**下界**, 漏计只会把 cross_file 降级为 named_fact/comment_only ⇒ 该轴**不会**把任何边判成缺陷, 只回答「树内有没有声明形态」",\n'
     '                "v2.6.0 只对**弱边**细分 (强/断/弃权边 edge_kind=None): 守恒分母 = 弱边数, 与符号级计数**不可换算** (同一条边可携带多枚弱符号)",\n'
     '                "v2.6.0 分类**不判红**: other 桶是 catch-all, 单列计数; 细分不改判任何 citation 的 verdict (与 v2.4.0/v2.5.0 平行轴纪律同)",\n'),
]

# ---------------------------------------------------------------- 自证夹具块 (K 系列)
K_FIXTURE = '''
    # ---- v2.6.0 弱边再细分轴两侧夹具 (独立临时仓, 与上面的夹具语料零耦合)
    tmp_k = Path(tempfile.mkdtemp(prefix="docref-kind-selftest-"))
    (tmp_k / "src/agent/x").mkdir(parents=True, exist_ok=True)
    (tmp_k / "src/agent/x/Kappa.cs").write_text(
        "class KappaThing { void Run() {} }\\n" * 3
        + 'var a = "telemetry_key_one";\\n'
        + 'var b = "telemetry_key_two";\\n'
        + "// OnlyCommentThing2 只在本注释里\\n"
        + "// uses NewHelperThing here\\n"
        + "// uses strong_local_thing here\\n"
        + "void useIt() { CodeFaceThing.Factory(); }\\n",
        encoding="utf-8")
    (tmp_k / "src/agent/x/Lambda.cs").write_text(
        "class LambdaThing {\\n"
        "    public void NewHelperThing() { }\\n"
        "    public void strong_local_thing() { }\\n"
        "    // MixedWeakThing2 仅注释\\n"
        "}\\n",
        encoding="utf-8")
    doc_k = ("# t_k\\n"
             "- K1 名字类事实(同边两枚): `telemetry_key_one` 与 `telemetry_key_two` [src/agent/x/Kappa.cs:4]\\n"
             "- K3a 他处有声明: `NewHelperThing` [src/agent/x/Kappa.cs:6]\\n"
             "- K3b 名字形态但他处有声明: `strong_local_thing` [src/agent/x/Kappa.cs:7]\\n"
             "- K4 仅注释非名字形态: `OnlyCommentThing2` [src/agent/x/Kappa.cs:5]\\n"
             "- K5 码面提及: `CodeFaceThing` [src/agent/x/Kappa.cs:8]\\n"
             "- K9 强边(不分类): `NewHelperThing` [src/agent/x/Lambda.cs:2]\\n"
             "- K11 混强边(强+弱非码): `NewHelperThing` 与 `MixedWeakThing2` [src/agent/x/Lambda.cs:2]\\n")
    repo_k = Repo(tmp_k)
    judged_k = [judge_citation(repo_k, c) for c in extract_citations("t_k.md", doc_k)]
    _ksyms = sorted({s for j in judged_k
                     for s, v in (j.get("symbol_faces") or {}).items() if v in WEAK_RUNGS})
    decl_k = declaration_index(repo_k, _ksyms)
    for j in judged_k:
        _k = weak_kind(j, decl_k)
        j["edge_kind"] = _k["edge_kind"]
        j["kind_reason"] = _k["kind_reason"]
        j["kind_per_symbol"] = _k["kind_per_symbol"]
    kby = {}
    for j in judged_k:
        # 夹具缺陷修复 (EXP1-Q10): 首版按**符号名**归组 ⇒ 同名符号在弱边(Kappa)与强边(Lambda)
        # 两处都被归到同一桶 ⇒ 断言读到 [cross_file, None]。归组键必须是 (符号, 被引文件) 二元组。
        kby.setdefault((tuple(j.get("symbols") or []), j.get("resolved")), []).append(j)
    _two = kby.get((("telemetry_key_one", "telemetry_key_two"), "src/agent/x/Kappa.cs"), [])
    ck("K1_edge_named_fact", [j["edge_kind"] for j in _two], [WEAK_NAMED_FACT])
    ck("K2_unit_separation_edge_vs_symbol",
       [len([p for p in j["kind_per_symbol"] if p["symbol_kind"] == WEAK_NAMED_FACT])
        for j in _two], [2])
    ck("K2_unit_separation_edge_count", [1 if j["edge_kind"] == WEAK_NAMED_FACT else 0 for j in _two], [1])
    ck("K6_named_fact_not_cross_file",
       [p["declared_elsewhere"] for j in _two for p in j["kind_per_symbol"]], [0, 0])
    _nh = kby.get((("NewHelperThing",), "src/agent/x/Kappa.cs"), [])
    ck("K3a_cross_file_declared_elsewhere", [j["edge_kind"] for j in _nh], [WEAK_CROSS_FILE])
    ck("K3c_declared_elsewhere_files_visible",
       [[p["declared_elsewhere_files"] for p in j["kind_per_symbol"]] for j in _nh],
       [[["src/agent/x/Lambda.cs"]]])
    ck("K3b_cross_file_overrides_name_shape",
       [j["edge_kind"] for j in kby.get((("strong_local_thing",), "src/agent/x/Kappa.cs"), [])],
       [WEAK_CROSS_FILE])
    ck("K4_comment_only_edge",
       [j["edge_kind"] for j in kby.get((("OnlyCommentThing2",), "src/agent/x/Kappa.cs"), [])],
       [WEAK_COMMENT_ONLY])
    ck("K5_code_mention_falls_to_other",
       [j["edge_kind"] for j in kby.get((("CodeFaceThing",), "src/agent/x/Kappa.cs"), [])],
       [WEAK_OTHER])
    _wk = [j for j in judged_k if edge_strength(j)["edge"] == EDGE_WEAK]
    _kc = Counter(j["edge_kind"] for j in judged_k if j["edge_kind"])
    ck("K7_kind_conserved_fixture", sum(_kc.values()), len(_wk))
    ck("K7_every_weak_edge_classified",
       sorted({j["edge_kind"] for j in _wk}) == sorted(set(_kc)), True)
    ck("K8_kinds_nontrivial_fixture", sorted(_kc), sorted(WEAK_KINDS))
    ck("K9_strong_edge_not_classified",
       [j["edge_kind"] for j in kby.get((("NewHelperThing",), "src/agent/x/Lambda.cs"), [])], [None])
    ck("K9_kind_does_not_rejudge_verdicts",
       sorted({j["verdict"] for j in _wk}), ["ok"])
    ck("K10_shape_vs_kind_distinct_units",
       (len([p for p in _two[0]["kind_per_symbol"] if p["symbol_kind"] == WEAK_NAMED_FACT]),
        len([j for j in _two if j["edge_kind"] == WEAK_NAMED_FACT])), (2, 1))
    # 归组键的符号元组是**排序后**的 (仪器对 symbols 排序) ⇒ 夹具键必须用排序序, 不能用文档书写序
    _mx = kby.get((("MixedWeakThing2", "NewHelperThing"), "src/agent/x/Lambda.cs"), [])
    ck("K11_mixed_edge_not_classified", [j["edge_kind"] for j in _mx], [None])
    ck("K11_mixed_symbol_kind_visible",
       [[p["symbol_kind"] for p in j["kind_per_symbol"] if p["symbol"] == "MixedWeakThing2"]
        for j in _mx], [[WEAK_COMMENT_ONLY]])
    ck("K11_mixed_edge_out_of_weak_conservation",
       sum(1 for j in judged_k if j["edge_kind"]) == len(_wk), True)
'''


def apply_edits(src_text: str):
    text = src_text
    log = []
    for old, new in EDITS:
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"ANCHOR_MISS: count={n} for {old[:70]!r}")
        text = text.replace(old, new, 1)
        log.append({"anchor": old.strip().splitlines()[0][:80], "count": n, "ok": True})
    # 自证夹具 (插在 ok = all(...) 之前)
    old = '    ok = all(c["pass"] for c in checks)'
    if text.count(old) != 1:
        raise SystemExit("ANCHOR_MISS: selftest tail")
    text = text.replace(old, K_FIXTURE + "\n" + old, 1)
    log.append({"anchor": "run_selftest: ok = all(...)", "count": 1, "ok": True})
    return text, log


def main():
    if not SRC.is_file():
        print(json.dumps({"stage": "precheck", "error": "source probe missing", "path": str(SRC)}))
        return 3
    src_text = SRC.read_text(encoding="utf-8")
    out_text, log = apply_edits(src_text)
    probe_version = re.search(r'PROBE_VERSION = "([^"]+)"', out_text).group(1)
    assert probe_version == "2.6.0", probe_version
    assert "weak_kind" in out_text and "declaration_index" in out_text
    assert out_text.count("def weak_kind(") == 1
    DST.write_text(out_text, encoding="utf-8")
    pins = {
        "round": "EXP1-Q10",
        "from_version": "2.5.0",
        "to_version": "2.6.0",
        "source": str(SRC.relative_to(HERE.parent.parent.parent)),
        "source_sha256": sha(SRC),
        "source_bytes": SRC.stat().st_size,
        "target": str(DST.relative_to(HERE.parent.parent.parent)),
        "target_sha256": sha(DST),
        "target_bytes": DST.stat().st_size,
        "n_edits": len(log),
        "edits": log,
        "additive_only": True,
        "note": "锚点式纯文本补丁, 每条锚点命中数 == 1 才写入; 未做任何 AST/正则级重写。",
    }
    PINS.write_text(json.dumps(pins, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"stage": "patch", "n_edits": len(log), "target": pins["target"],
                      "target_sha256": pins["target_sha256"], "bytes": pins["target_bytes"],
                      "anchors_all_unique": True, "exit_code": 0}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
