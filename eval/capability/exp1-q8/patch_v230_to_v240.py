#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R-EXP1Q8: 仪器 v2.3.0 -> v2.4.0 —— 追加**平行轴**「符号存在性阶梯」。

纪律 (照 R409/R-EXP1Q7):
  ① 定点字符串替换, 每处断言命中次数; ② 不改主判据 (只加平行轴); ③ 写后 py_compile + selftest。
"""
from pathlib import Path

P = Path("/home/agentuser/AgentFramework/eval/capability/exp1-q4/probe_doc_ref_integrity.py")
src = P.read_text(encoding="utf-8")
orig_len = len(src)
edits = []


def sub(old, new, n=1):
    global src
    assert src.count(old) == n, f"anchor hits={src.count(old)} want={n}: {old[:70]!r}"
    src = src.replace(old, new, n)
    edits.append(old.splitlines()[0][:60])


# ---------------------------------------------------------------- 1) 判据 + 版本常量
sub(
    '    "G6_cont_nontrivial": "续引数==0 ∨ 续引归属 tier 分布>=2 类 (全同一 tier ⇒ 子探针无判别力)",\n}',
    '    "G6_cont_nontrivial": "续引数==0 ∨ 续引归属 tier 分布>=2 类 (全同一 tier ⇒ 子探针无判别力)",\n'
    '    "G7_ladder_nontrivial": "符号存在性阶梯在真实语料上 >=2 级分布 (恒同一级 ⇒ 该轴无判别力 ⇒ 先查仪器再谈被测)",\n'
    '}\nPROBE_VERSION = "2.4.0"',
)

# ---------------------------------------------------------------- 2) Repo.codeface
sub(
    """        self._cache[rel] = out
        return out

    def exists(self, rel: str) -> bool:""",
    """        self._cache[rel] = out
        return out

    def codeface(self, rel: str):
        \"\"\"剥离注释/字符串后的「代码面」文本 (缓存); 不可剥离的类型返回 None。\"\"\"
        key = ("__codeface__", rel)
        if key not in self._cache:
            text, _ = self.read(rel)
            if text is None:
                self._cache[key] = (None, None)
            else:
                tok = "#" if os.path.splitext(rel)[1].lower() in (".py", ".sh") else "//"
                self._cache[key] = (strip_noncode(text, tok), None)
        return self._cache[key][0]

    def exists(self, rel: str) -> bool:""",
)

# ---------------------------------------------------------------- 3) 阶梯模块
LADDER = '''# ---------------------------------------------------------------- 符号存在性阶梯 (v2.4.0)
# 与主 verdict **平行**的独立测量轴 (只细分, 不改判): 引用指向的文件里被引符号以**什么形态**存在。
#   五级 (强 -> 弱): declared_type > declared_member > code_mention > noncode_mention > absent
#   另加 n/a_kind = 该文件类型不做词法剥离 (非 .cs/.py) ⇒ 弃权单列, 不进阶梯分母。
# 诚实边界: 本轴是**词法级** (剥离注释/字符串 + 声明形态正则), **不是 AST**——
#   AST 需语法库/编译器 (与本探针「不跑 dotnet / 不引第三方依赖」的纪律冲突),
#   故候选 #3 提的 "AST 级独立判据" 本轮**降级为词法级**并如实登记。
#   因此 declared_member 是**启发式** (同句出现修饰符/返回类型), 裸 `Sym(` 在语义上无法区分
#   「声明」与「调用」⇒ 一律只记 code_mention (宁漏勿错)。
FACE_NA = "n/a_kind"
FACE_REAL_RUNGS = ("declared_type", "declared_member", "code_mention", "noncode_mention", "absent")
STRIPPABLE_EXT = (".cs", ".py")
DECL_TYPE_TMPL = r'\\b(?:class|interface|record|struct|enum|delegate)\\s+%s\\b'
# `new Foo(` 是**实例化**不是声明 ⇒ new 不入修饰符表 (误列会把 `new X(` 判成 declared_member)
DECL_MEMBER_PREFIX = (r'(?:public|private|protected|internal|static|virtual|override|async|sealed|'
                      r'partial|readonly|extern|unsafe|abstract|const|event|required|'
                      r'void|bool|int|long|double|string|object|Task|ValueTask|byte|char|float|decimal)')


def _blank(seg: str) -> str:
    """等长空白替换 (换行保留) ⇒ 剥离后行号/列偏移不变。"""
    return "".join("\\n" if ch == "\\n" else " " for ch in seg)


def strip_noncode(text: str, line_comment: str = "//") -> str:
    """剥离注释与字符串/字符字面量 (词法级状态机, 非 AST), **逐行保长度**。

    line_comment="//" (C 族) 时块注释为 /* */; "#" (脚本族) 时块注释为三引号。
    诚实边界: 撇号出现在非字面量语境 (英文缩写等) 会吞到下一个撇号——只影响本平行轴,
    主 verdict 完全不受影响。
    """
    blocks = (('"""', '"""'), ("'''", "'''")) if line_comment == "#" else (("/*", "*/"),)
    out, i, n = [], 0, len(text)
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if (line_comment == "#" and ch == "#") or (line_comment == "//" and ch == "/" and nxt == "/"):
            j = text.find("\\n", i)
            j = n if j < 0 else j
            out.append(_blank(text[i:j]))
            i = j
            continue
        blk = None
        for op, cl in blocks:
            if text.startswith(op, i):
                j = text.find(cl, i + len(op))
                blk = n if j < 0 else j + len(cl)
                break
        if blk is not None:
            out.append(_blank(text[i:blk]))
            i = blk
            continue
        if ch == "@" and nxt in ('"', "'"):
            j = i + 2
            while j < n:
                if text[j] == nxt:
                    if nxt == '"' and j + 1 < n and text[j + 1] == '"':
                        j += 2
                        continue
                    j += 1
                    break
                j += 1
            out.append(_blank(text[i:j]))
            i = j
            continue
        if ch in ('"', "'"):
            j = i + 1
            while j < n:
                if j + 1 < n and text[j] == "\\\\":
                    j += 2
                    continue
                if text[j] == ch:
                    j += 1
                    break
                if text[j] == "\\n":
                    break
                j += 1
            out.append(_blank(text[i:j]))
            i = j
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def symbol_face(sym: str, code_text: str, full_text: str) -> str:
    """单个符号在**该文件**里的存在形态 (五级之一)。输入: 代码面文本 + 全文。"""
    esc = re.escape(sym)
    if re.search(DECL_TYPE_TMPL % esc, code_text):
        return "declared_type"
    if re.search(DECL_MEMBER_PREFIX + r'\\b[^\\n;{}]{0,90}?\\b' + esc + r'\\s*[\\(<{]', code_text):
        return "declared_member"
    if re.search(r'\\b' + esc + r'\\b', code_text):
        return "code_mention"
    if re.search(r'\\b' + esc + r'\\b', full_text):
        return "noncode_mention"
    return "absent"


def faces_for(repo, rel: str, text: str, syms) -> dict:
    """该引用全部符号的形态; 不可剥离的文件类型 ⇒ 全 n/a_kind (弃权单列, 不进分母)。"""
    if os.path.splitext(rel)[1].lower() not in STRIPPABLE_EXT:
        return {s: FACE_NA for s in syms}
    code_text = repo.codeface(rel)
    if code_text is None:
        return {s: FACE_NA for s in syms}
    return {s: symbol_face(s, code_text, text) for s in syms}


'''
sub("def judge_citation(repo: Repo, c: dict):", LADDER + "def judge_citation(repo: Repo, c: dict):")

# ---------------------------------------------------------------- 4) 接线: relocated 分支
sub(
    """                    rec["relocated_fact_verdict"] = (
                        "ok" if (lines_ok and not absent)
                        else ("stale_lines" if not lines_ok else "symbol_absent"))""",
    """                    rec["relocated_fact_verdict"] = (
                        "ok" if (lines_ok and not absent)
                        else ("stale_lines" if not lines_ok else "symbol_absent"))
                    rec["relocated_symbol_faces"] = faces_for(repo, cands[0], text, c["symbols"])""",
)

# ---------------------------------------------------------------- 5) 接线: 主路径
sub(
    """    rec["symbols_absent"] = absent
    rec["verdict"] = "symbol_absent" if absent else "ok\"""",
    """    rec["symbols_absent"] = absent
    # 平行轴 (v2.4.0): 只记录形态, **不参与** verdict 判定 ⇒ 与主判据解耦
    rec["symbol_faces"] = faces_for(repo, rel, text, c["symbols"])
    rec["verdict"] = "symbol_absent" if absent else "ok\"""",
)

# ---------------------------------------------------------------- 6) 聚合
sub(
    "    all_syms = POSITIVE_SYMBOLS + NEGATIVE_SYMBOLS + TARGET_SYMBOLS",
    """    # ---- v2.4.0 符号存在性阶梯聚合 (平行轴; 与 verdict_counts 分开计, 不互相解释)
    face_rungs = Counter()
    for c in live_code:
        for _rung in (c.get("symbol_faces") or {}).values():
            face_rungs[_rung] += 1
    face_candidates = [
        {"doc": c["doc"], "doc_line": c["doc_line"], "resolved": c["resolved"],
         "symbol": _sym, "rung": _rung, "verdict": c["verdict"]}
        for c in live_code
        for _sym, _rung in sorted((c.get("symbol_faces") or {}).items())
        if _rung in ("noncode_mention", "code_mention")
    ]

    all_syms = POSITIVE_SYMBOLS + NEGATIVE_SYMBOLS + TARGET_SYMBOLS""",
)
sub(
    '        "n_continuations_live": len(cont_live),\n        "fingerprints": repo.fingerprints(),',
    '        "n_continuations_live": len(cont_live),\n'
    '        "symbol_face_rungs": dict(face_rungs),\n'
    '        "symbol_face_candidates": face_candidates,\n'
    '        "n_symbol_faces": sum(face_rungs.values()),\n'
    '        "fingerprints": repo.fingerprints(),',
)

# ---------------------------------------------------------------- 7) G7 闸
sub(
    """        # ---- G6 续引子探针非退化 (tier 分布 >= 2 类 ∨ 无量): 必须在 gate_dict 构造**之前**算
        g6 = bool(r1["n_continuations_live"] == 0 or len(r1["cont_tier_counts"]) >= 2)""",
    """        # ---- G6 续引子探针非退化 (tier 分布 >= 2 类 ∨ 无量): 必须在 gate_dict 构造**之前**算
        g6 = bool(r1["n_continuations_live"] == 0 or len(r1["cont_tier_counts"]) >= 2)

        # ---- G7 阶梯非退化 (真语料上 >=2 级; 恒同一级 ⇒ 该轴无判别力 ⇒ 先查仪器再谈被测)
        rungs_real = sorted(k for k in r1["symbol_face_rungs"] if k != FACE_NA)
        g7 = bool(r1["n_symbol_faces"] == 0 or len(rungs_real) >= 2)""",
)
sub(
    '            "G6_cont_nontrivial": g6,',
    '            "G6_cont_nontrivial": g6,\n'
    '            "G7_ladder_nontrivial": g7,\n'
    '            "G7_symbol_face_rungs": r1["symbol_face_rungs"],\n'
    '            "G7_symbol_face_rungs_real": rungs_real,\n'
    '            "G7_n_symbol_faces": r1["n_symbol_faces"],',
)
sub(
    "        all_pass = bool(g1 and g2 and g5 and g3 and g6)",
    "        all_pass = bool(g1 and g2 and g5 and g3 and g6 and g7)",
)

# ---------------------------------------------------------------- 8) 结果体
sub('            "probe_version": "2.3.0",', '            "probe_version": PROBE_VERSION,')
sub(
    '            "symbol_files": r1["symbol_files"],',
    '            "symbol_files": r1["symbol_files"],\n'
    '            "symbol_face_rungs": r1["symbol_face_rungs"],\n'
    '            "symbol_face_candidates": r1["symbol_face_candidates"],\n'
    '            "n_symbol_faces": r1["n_symbol_faces"],',
)
sub(
    '                "符号命中检查是**全文匹配**启发式 (非 AST): 同名出现在注释/字符串/历史示例里也算命中 ⇒ symbol_absent 只作候选, 不作对外结论",',
    '                "符号命中检查 (主 verdict) 是**全文匹配**启发式 (非 AST): 同名出现在注释/字符串/历史示例里也算命中 ⇒ symbol_absent 只作候选, 不作对外结论",\n'
    '                "v2.4.0 新增**平行轴**「符号存在性阶梯」(declared_type > declared_member > code_mention > noncode_mention > absent): 词法级剥离注释/字符串, **非 AST** (AST 需语法库 ⇒ 与本探针纪律冲突, 候选#3 的 AST 级要求本轮降级为词法级并登记); declared_member 为启发式 (同句修饰符/返回类型), 裸 `Sym(` 只记 code_mention (宁漏勿错); 非 .cs/.py 记 n/a_kind 弃权 ⇒ 该轴**不改判**任何 citation 的 verdict",',
)

# ---------------------------------------------------------------- 9) selftest 夹具
sub(
    '''    (tmp / "src/agent/x/Alpha.cs").write_text("class AlphaThing { void Run() {} }\\n" * 40, encoding="utf-8")
    (tmp / "src/agent/x/Beta.cs").write_text("class BetaThing { void Go() {} }\\n" * 40, encoding="utf-8")''',
    '''    (tmp / "src/agent/x/Alpha.cs").write_text(
        "// CommentedThing 只出现在本注释里\\n" + "class AlphaThing { void Run() {} }\\n" * 40,
        encoding="utf-8")
    (tmp / "src/agent/x/Beta.cs").write_text(
        "class BetaThing { void Go() {} }\\n" * 40
        + "public void DeltaThing() { }\\n"
        + "void useIt() { OtherThing.Factory(); }\\n",
        encoding="utf-8")''',
)
sub(
    '''           + "y" * (RETIRED_WINDOW + 10) + " [src/agent/x/Gone5.cs:3] 与 [:2]\\n")''',
    '''           + "y" * (RETIRED_WINDOW + 10) + " [src/agent/x/Gone5.cs:3] 与 [:2]\\n"
           # ---- 符号存在性阶梯 (v2.4.0): 四级端到端 + "细分不改判" 两侧
           "\\n"
           "- 阶梯 declared_member: `DeltaThing` [src/agent/x/Beta.cs:3]\\n"
           "- 阶梯 code_mention: `OtherThing` [src/agent/x/Beta.cs:3]\\n"
           "- 阶梯 noncode_comment_only: `CommentedThing` [src/agent/x/Alpha.cs:3]\\n"
           "- 阶梯 absent: `MissingThing` [src/agent/x/Beta.cs:3]\\n")''',
)
sub(
    "    ok = all(c[\"pass\"] for c in checks)\n    print(json.dumps({\"selftest\": \"probe_doc_ref_integrity-v2.3.0\", \"all_pass\": ok,",
    '''    # ---- v2.4.0 符号存在性阶梯: 五级常量两侧 + 剥离保行 + 注释/字符串内「声明形态」负控
    cfg = ("class GammaThing { }\\n"
           "public void DeltaThing() { }\\n"
           "var t = OtherThing.Factory();\\n"
           "// EpsilonThing only in comment\\n"
           'var s = "ZetaThing";\\n'
           "var u = new NewThing();\\n")
    cfg_code = strip_noncode(cfg, "//")
    face = {s: symbol_face(s, cfg_code, cfg) for s in
            ("GammaThing", "DeltaThing", "OtherThing", "EpsilonThing",
             "ZetaThing", "NewThing", "NowhereThing")}
    ck("F1_ladder_declared_type", face["GammaThing"], "declared_type")
    ck("F2_ladder_declared_member", face["DeltaThing"], "declared_member")
    ck("F3_ladder_code_mention", face["OtherThing"], "code_mention")
    ck("F4_ladder_noncode_comment", face["EpsilonThing"], "noncode_mention")
    ck("F5_ladder_noncode_string", face["ZetaThing"], "noncode_mention")
    ck("F6_ladder_absent", face["NowhereThing"], "absent")
    ck("F7_new_expr_not_declaration", face["NewThing"], "code_mention")
    ck("F8_strip_preserves_lines", len(cfg_code.splitlines()), len(cfg.splitlines()))
    cmt = "// class CommentedThing { }\\n"            # 负控: 注释里的**声明形态**不得算声明
    ck("F9_comment_decl_not_counted",
       symbol_face("CommentedThing", strip_noncode(cmt, "//"), cmt), "noncode_mention")
    strd = 'var q = "class StringThing { }";\\n'      # 负控: 字符串里的声明形态同上
    ck("F10_string_decl_not_counted",
       symbol_face("StringThing", strip_noncode(strd, "//"), strd), "noncode_mention")
    # ---- 端到端: 新轴真进主链 (t.md 末尾四条阶梯引用) + 「细分不改判」两侧
    face_by_sym = {}
    for _j in judged:
        if len(_j.get("symbols") or []) == 1:
            face_by_sym.setdefault(_j["symbols"][0], []).append(_j)
    ck("F11_e2e_declared_member",
       [j["symbol_faces"]["DeltaThing"] for j in face_by_sym["DeltaThing"]], ["declared_member"])
    ck("F12_e2e_code_mention",
       [j["symbol_faces"]["OtherThing"] for j in face_by_sym["OtherThing"]], ["code_mention"])
    ck("F13_e2e_noncode_comment",
       [j["symbol_faces"]["CommentedThing"] for j in face_by_sym["CommentedThing"]],
       ["noncode_mention"])
    ck("F14_e2e_absent",
       [j["symbol_faces"]["MissingThing"] for j in face_by_sym["MissingThing"]], ["absent"])
    ck("F15_verdict_unchanged_noncode_hit",
       [j["verdict"] for j in face_by_sym["CommentedThing"]], ["ok"])
    ck("F16_verdict_unchanged_absent",
       [j["verdict"] for j in face_by_sym["MissingThing"]], ["symbol_absent"])
    _rungs = {r for j in judged for r in (j.get("symbol_faces") or {}).values()} - {FACE_NA}
    ck("F17_ladder_rungs_nontrivial", len(_rungs) >= 4, True)
    ok = all(c["pass"] for c in checks)
    print(json.dumps({"selftest": "probe_doc_ref_integrity-v" + PROBE_VERSION, "all_pass": ok,''',
)
sub(
    '''          活引用带标记不豁免 / 标记越过窗口仍红 / 常量形态按码点自检。''',
    '''          活引用带标记不豁免 / 标记越过窗口仍红 / 常量形态按码点自检 /
          v2.4.0 符号存在性阶梯五级两侧 + 注释/字符串内声明形态负控 + 细分不改判。''',
)

P.write_text(src, encoding="utf-8")
print(f"edits={len(edits)} bytes {orig_len} -> {len(src)}")
for e in edits:
    print("  ok:", e)
