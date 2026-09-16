#!/usr/bin/env python3
"""archive_field_provenance.py v1.0 — EXP1-Q17「归档缺字段」归因判定器具

问题: 已登记读数所计数的**逐行字段** `symbol_faces` 在归档语料 citations.jsonl 出现 0 次。
归因二选一: (①) 落盘块(写点)白名单**丢掉**了生产者已产出的字段; (②) 该字段在落盘后另行填充。

器具形态: **真源码 AST 派生** 三集合 → 与**真归档语料**做 MECE 分类:
  P  = 生产者键集 = P1(抽取器字面键) ∪ P2(判定器 rec 赋值/update 键) ∪ P3(run_pass 内**接收者为外层循环变量**的赋值键)
  D  = 落盘白名单键集 = open("citations.jsonl") 写块内 DictComp 的 iter 元组字面键 (+ `if k in c` 守卫检测)
  A  = 归档实际键并集 (逐键行数)

MECE 五类 (优先级从上到下):
  1 C_archive_foreign_key        ∉D ∧ ∈A                          → 归档含写点从未写过的键 ⇒ 同源失效
  2 C_dump_dead_entry            ∈D ∧ ∉P ∧ ∉A                     → 白名单要了一个从不存在的键, 守卫静默丢
  3 C_dump_producer_branch_unhit ∈D ∧ ∈P ∧ ∉A                     → 条件分支字段, 本语料 0 行命中
  4 C_producer_dump_omission     ∈P ∧ ∉D ∧ ∉A                     → 生产者产出后被白名单**丢掉**  ← 归因①
  5 C_written_and_archived       ∈D ∧ ∈A                          → 正常落盘

守恒: Σ classes == |P ∪ D|   (逐键恰一类, 穷尽)

退出码: 0 全绿 / 2 断言失败(真红) / 3 测量或环境失败(弃权, 不判红)
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

EXIT_OK, EXIT_ASSERT, EXIT_MEASURE = 0, 2, 3

CLASS_ORDER = [
    "C_archive_foreign_key",
    "C_dump_dead_entry",
    "C_dump_producer_branch_unhit",
    "C_producer_dump_omission",
    "C_written_and_archived",
]
ATTRIBUTION_DUMP_OMISSION = "① 落盘块丢字段（写点白名单漏生产者字段，由 `if k in c` 静默丢弃）"
ATTRIBUTION_POST_FILL = "② 落盘后另行填充（写点当时该字段不存在）"


# ---------------------------------------------------------------- AST 派生
def _str_key(node) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _dict_keys(node: ast.Dict, sink: dict) -> None:
    for k in node.keys:
        s = _str_key(k)
        if s is not None:
            sink[s] = getattr(k, "lineno", 0)


def _subscript_assign_keys(scope: ast.AST, var: str | None, sink: dict, funcname: str) -> None:
    for n in ast.walk(scope):
        if not isinstance(n, ast.Assign):
            continue
        for t in n.targets:
            if not isinstance(t, ast.Subscript):
                continue
            if not isinstance(t.value, ast.Name):
                continue
            if var is not None and t.value.id != var:
                continue
            s = _str_key(t.slice)
            if s is not None and s not in sink:
                sink[s] = n.lineno


def _lit_set(node) -> set:
    return {c.value for c in ast.walk(node)
            if isinstance(c, ast.Constant) and isinstance(c.value, str)}


def _name_set(node) -> set:
    return {x.id for x in ast.walk(node) if isinstance(x, ast.Name)}


def _target_names(t) -> set:
    if isinstance(t, ast.Name):
        return {t.id}
    if isinstance(t, ast.Subscript):
        return _target_names(t.value)
    if isinstance(t, (ast.Tuple, ast.List)):
        acc = set()
        for e in t.elts:
            acc |= _target_names(e)
        return acc
    return set()


def _assigned_names(node) -> set:
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                out |= _target_names(t)
        elif isinstance(n, (ast.AugAssign, ast.AnnAssign)):
            out |= _target_names(n.target)
    return out


def flow_deps(func: ast.AST, hub_exclusion: bool = True) -> dict:
    """数据流派生: 名字 → 写入它的语句所引用的字面量/名字集合（含所在外层 For 的 iter/ifs 上下文）。

    用于回答「登记读数的值表达式**传递地**依赖哪些行字段名」——例如 result["symbol_face_rungs"]
    = dict(face_rungs)，而 face_rungs 在外层 for 循环体内被累加，其 iter 引用 "symbol_faces"。
    纯 AST、无语义猜测；上下文只取外层循环、不外扩 If（保守不过度包含）。
    """
    lit: dict = {}
    nm: dict = {}

    def walk_stmt(stmt, ctx_lit: set, ctx_nm: set):
        here_lit = _lit_set(stmt)
        here_nm = _name_set(stmt)
        for t in _assigned_names(stmt):
            lit.setdefault(t, set()).update(here_lit | ctx_lit)
            nm.setdefault(t, set()).update(here_nm | ctx_nm)
        for child in ast.iter_child_nodes(stmt):
            if not isinstance(child, ast.stmt):
                continue
            if isinstance(child, (ast.For, ast.AsyncFor)):
                walk_stmt(child, ctx_lit | _lit_set(child.iter),
                          ctx_nm | _name_set(child.iter))
            elif isinstance(child, ast.While):
                walk_stmt(child, ctx_lit | _lit_set(child.test), ctx_nm | _name_set(child.test))
            else:
                walk_stmt(child, ctx_lit, ctx_nm)

    for stmt in getattr(func, "body", []):
        if isinstance(stmt, (ast.For, ast.AsyncFor)):
            walk_stmt(stmt, _lit_set(stmt.iter), _name_set(stmt.iter))
        else:
            walk_stmt(stmt, set(), set())

    hubs = set()
    for n in ast.walk(func):
        if isinstance(n, (ast.For, ast.AsyncFor)) and isinstance(n.target, ast.Name):
            hubs.add(n.target.id)
        if isinstance(n, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for g in n.generators:
                if isinstance(g.target, ast.Name):
                    hubs.add(g.target.id)

    def expand(seed_names: set) -> tuple:
        """名字→名字 传递闭包。**循环变量不作传播枢纽**: 逐元素变量（如 c/_rung）被大量语句共享，
        经它传播会让任意登记键都「依赖」任意字段名（首版实测 15 键伪依赖）。只沿非循环变量扩展。"""
        names, lits = set(seed_names), set()
        for _ in range(6):
            new_names = set()
            for n in names:
                lits |= lit.get(n, set())
                for m in nm.get(n, set()):
                    if m not in names and (not hub_exclusion or m not in hubs):
                        new_names.add(m)
            if not new_names:
                break
            names |= new_names
            for n in new_names:
                lits |= lit.get(n, set())
        return names, lits

    return {"lit": lit, "nm": nm, "expand": expand}


def derive_sets(src: str) -> dict:
    """返回 {'P1','P2','P3','dump','dump_guard','dump_tuple_span','early_returns','result_keys'}"""
    tree = ast.parse(src)
    funcs = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    for need in ("extract_citations", "judge_citation", "run_pass"):
        if need not in funcs:
            raise ValueError(f"派生失败: 源码缺函数 {need}")

    p1: dict = {}
    for n in ast.walk(funcs["extract_citations"]):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "append":
            for a in n.args:
                if isinstance(a, ast.Dict):
                    _dict_keys(a, p1)

    p2: dict = {}
    _subscript_assign_keys(funcs["judge_citation"], "rec", p2, "judge_citation")
    for n in ast.walk(funcs["judge_citation"]):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "update" and isinstance(n.func.value, ast.Name)
                and n.func.value.id == "rec"):
            for a in n.args:
                if isinstance(a, ast.Dict):
                    _dict_keys(a, p2)

    p3: dict = {}
    for n in ast.walk(funcs["run_pass"]):
        if isinstance(n, ast.For) and isinstance(n.target, ast.Name):
            _subscript_assign_keys(n, n.target.id, p3, "run_pass")

    # 落盘块: with ...open("citations.jsonl") -> fh.write(json.dumps({k: c[k] ...} + "\n"))
    dump: dict = {}
    guard = False
    tuple_span = None
    for n in ast.walk(tree):
        if not isinstance(n, ast.With):
            continue
        for item in n.items:
            ce = item.context_expr
            if not (isinstance(ce, ast.Call) and isinstance(ce.func, ast.Attribute) and ce.func.attr == "open"):
                continue
            # 文件名可能出现在 open() 实参或链式 with_name() 中 ⇒ 在整段 context_expr 内找字面量
            if not any(isinstance(c, ast.Constant) and c.value == "citations.jsonl" for c in ast.walk(ce)):
                continue
            body = ast.Module(body=n.body, type_ignores=[])
            for m in ast.walk(body):
                if (isinstance(m, ast.DictComp)
                        and isinstance(m.key, ast.Name) and m.key.id == "k"
                        and isinstance(m.value, ast.Subscript)
                        and isinstance(m.value.value, ast.Name)):
                    gen = m.generators[0] if m.generators else None
                    if gen is None or not isinstance(gen.iter, ast.Tuple):
                        raise ValueError("落盘块 DictComp 的 iter 不是元组字面量（器具需更新）")
                    for e in gen.iter.elts:
                        s = _str_key(e)
                        if s is None:
                            raise ValueError("落盘白名单含非字符串元素（器具 fail-closed）")
                        dump[s] = getattr(e, "lineno", 0)
                    guard = bool(gen.ifs)
                    it = gen.iter
                    tuple_span = (it.lineno, it.col_offset, it.end_lineno, it.end_col_offset)
    if not dump:
        raise ValueError("派生失败: 未定位到 citations.jsonl 落盘白名单")

    # judge_citation 内在 face 赋值之前的早退 return rec 数（= 缺字段行属分支条件的证据）
    early = 0
    jc = funcs["judge_citation"]
    face_line = min([v for k, v in p2.items() if k == "symbol_faces"] or [10 ** 9])
    for n in ast.walk(jc):
        if isinstance(n, ast.Return) and n.lineno < face_line:
            if isinstance(n.value, ast.Name) and n.value.id == "rec":
                early += 1

    result_keys: dict = {}
    result_key_deps: dict = {}
    flow = flow_deps(funcs["run_pass"])
    for n in ast.walk(funcs["run_pass"]):
        if isinstance(n, ast.Return) and isinstance(n.value, ast.Dict):
            _dict_keys(n.value, result_keys)
            for k, v in zip(n.value.keys, n.value.values):
                s = _str_key(k)
                if s is None:
                    continue
                seed_lits = {c.value for c in ast.walk(v)
                             if isinstance(c, ast.Constant) and isinstance(c.value, str)}
                _names, trans_lits = flow["expand"](_name_set(v))
                result_key_deps.setdefault(s, set()).update(seed_lits | trans_lits)

    return {"P1": p1, "P2": p2, "P3": p3, "dump": dump, "dump_guard": guard,
            "dump_tuple_span": tuple_span, "early_returns": early, "result_keys": result_keys,
            "result_key_deps": result_key_deps}


def splice_tuple_keys(src: str, extra: list[str]) -> str:
    """把 extra 键插到落盘元组左括号之后（负控用: 证明白名单确实取自源码, 非硬编码）。"""
    info = derive_sets(src)
    lineno, col, _el, _ec = info["dump_tuple_span"]
    lines = src.splitlines(keepends=True)
    idx = sum(len(l) for l in lines[: lineno - 1]) + col + 1   # 左括号之后
    ins = "".join(f'"{k}", ' for k in extra)
    return src[:idx] + ins + src[idx:]


# ---------------------------------------------------------------- 归档面
def load_archive(path: Path) -> dict:
    rows = []
    bad = 0
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                bad += 1
    if not rows:
        raise ValueError(f"归档语料为空或不可解析: {path} (bad_lines={bad})")
    key_rows = Counter()
    key_present_rows = Counter()
    for r in rows:
        for k in r.keys():
            key_rows[k] += 1
        for k, v in r.items():
            if v is not None:
                key_present_rows[k] += 1
    live = [r for r in rows if r.get("kind") == "code" and not r.get("in_code_fence")]
    edge_rows = [r for r in rows if "edge_strength" in r]
    return {"path": str(path), "rows": rows, "n_rows": len(rows), "bad_lines": bad,
            "keys": key_rows, "keys_nonnull": key_present_rows,
            "n_live": len(live), "n_edge_rows": len(edge_rows),
            "verdicts": Counter(r.get("verdict") for r in rows)}


# ---------------------------------------------------------------- 分类
def classify(P: set, D: set, A: set) -> dict:
    universe = sorted(P | D | A)          # 必须含 A: 归档外来键否则被静默丢弃（FX07 抓出的真洞）
    cls: dict = {}
    for k in universe:
        if k in A and k not in D:
            c = CLASS_ORDER[0]
        elif k in D and k not in P and k not in A:
            c = CLASS_ORDER[1]
        elif k in D and k in P and k not in A:
            c = CLASS_ORDER[2]
        elif k in P and k not in D and k not in A:
            c = CLASS_ORDER[3]
        else:
            c = CLASS_ORDER[4]
        cls[k] = c
    dist = Counter(cls.values())
    return {"universe": universe, "by_key": cls, "distribution": {c: dist.get(c, 0) for c in CLASS_ORDER},
            "conserved_sum": sum(dist.values()), "universe_size": len(universe)}


def load_registered(attribution_path: Path | None) -> dict:
    """登记面键集（真值来自已归档的 attribution 台账）——用于把「补漏字段解除哪些登记读数」机检化。"""
    if attribution_path is None or not Path(attribution_path).exists():
        return {"path": str(attribution_path), "keys": [], "available": False}
    d = json.loads(Path(attribution_path).read_text(encoding="utf-8"))
    ignore = {"probe", "probe_version", "repo", "corpus", "target_doc", "target_question",
              "run_started_epoch", "run_finished_epoch", "exit_code", "gate_pass", "gates",
              "criteria_pre_registered", "decision_rules", "honest_boundaries", "checks_posthoc",
              "evidence_level"}
    return {"path": str(attribution_path), "available": True,
            "keys": sorted(k for k in d.keys() if k not in ignore)}


def load_q16_not_replayable(verdict_path: Path | None) -> dict:
    """Q16 台账里的 not_replayable_typed（键 → 类型化原因），用于「4 → N」的天花板机检。"""
    if verdict_path is None or not Path(verdict_path).exists():
        return {"path": str(verdict_path), "available": False, "typed": {}}
    d = json.loads(Path(verdict_path).read_text(encoding="utf-8"))
    typed: dict = {}
    for art, body in (d.get("artifacts") or {}).items():
        for k, v in ((body or {}).get("not_replayable_typed") or {}).items():
            typed[k] = v
    return {"path": str(verdict_path), "available": bool(typed), "typed": typed}


def run_core(probe_path: Path, archive_path: Path, registered: dict | None = None,
             q16: dict | None = None) -> dict:
    src = probe_path.read_text(encoding="utf-8")
    sets = derive_sets(src)
    arch = load_archive(archive_path)
    P = set(sets["P1"]) | set(sets["P2"]) | set(sets["P3"])
    D = set(sets["dump"])
    A = set(arch["keys"])
    cl = classify(P, D, A)
    face = "symbol_faces"
    rface = "relocated_symbol_faces"
    face_cls = cl["by_key"].get(face)
    attr = ATTRIBUTION_DUMP_OMISSION if face_cls == "C_producer_dump_omission" else (
        ATTRIBUTION_POST_FILL if face_cls in ("C_dump_dead_entry", None) else f"未预期类: {face_cls}")
    omitted = sorted(k for k, c in cl["by_key"].items() if c == "C_producer_dump_omission")
    unblocked = sorted(k for k, deps in sets["result_key_deps"].items() if deps & set(omitted))
    face_deps = sorted(k for k, deps in sets["result_key_deps"].items()
                       if deps & {"symbol_faces", "relocated_symbol_faces"})
    reg_keys = sorted(set((registered or {}).get("keys") or []))
    unblocked_registered = sorted(k for k in unblocked if k in reg_keys) if reg_keys else []
    nrt = dict((q16 or {}).get("typed") or {})
    face_unblocked_nonreplayable = sorted(k for k in nrt if k in face_deps)
    return {"probe": str(probe_path), "archive": str(archive_path), "sets": sets, "archive": arch,
            "P": sorted(P), "D": sorted(D), "A": sorted(A), "classification": cl,
            "face_class": face_cls, "relocated_face_class": cl["by_key"].get(rface),
            "attribution": attr, "omitted_fields": omitted, "unblocked_registered_keys": unblocked_registered,
            "face_dependent_registered_keys": [k for k in face_deps if k in reg_keys] if reg_keys else face_deps,
            "all_face_dependent_keys": face_deps,
            "not_replayable_total": len(nrt), "not_replayable_typed": nrt,
            "face_unblocked_nonreplayable": face_unblocked_nonreplayable,
            "unblocked_all_result_keys": unblocked}


# ---------------------------------------------------------------- 检查
def evaluate(core: dict, det: dict | None = None) -> list:
    sets, arch, cl = core["sets"], core["archive"], core["classification"]
    chk = []

    def add(cid, claim, ok, detail, posthoc=False):
        chk.append({"id": cid, "claim": claim, "passed": bool(ok), "detail": detail,
                    "posthoc": bool(posthoc)})

    n_face = arch["keys"].get("symbol_faces", 0)
    add("C1", "symbol_faces 在归档出现行数 == 0", n_face == 0,
        f"rows_with_symbol_faces={n_face} / {arch['n_rows']}")
    add("C2", "symbol_faces ∈ 生产者字段集(P2, 带行号)", "symbol_faces" in sets["P2"],
        f"P2 span={sets['P2'].get('symbol_faces')} P=|{len(sets['P1'])}|{len(sets['P2'])}|{len(sets['P3'])}|")
    add("C3", "symbol_faces ∉ 落盘白名单(D)", "symbol_faces" not in sets["dump"],
        f"|D|={len(sets['dump'])}")
    add("C4", "class(symbol_faces) == C_producer_dump_omission ⇒ 归因①", core["face_class"] == "C_producer_dump_omission",
        f"class={core['face_class']} verdict={core['attribution']}")
    add("C5", "class(relocated_symbol_faces) 同 C4", core["relocated_face_class"] == "C_producer_dump_omission",
        f"class={core['relocated_face_class']}")
    add("C6", "写点存在静默丢弃机制(`if k in c` 守卫在场)", sets["dump_guard"] is True, f"guard={sets['dump_guard']}")
    add("C7", "归档域自洽: 归档字段复算 live 行数 == 带 edge_* 行数", arch["n_live"] == arch["n_edge_rows"],
        f"live_from_archive={arch['n_live']} edge_field_rows={arch['n_edge_rows']}")
    nz = [c for c, n in cl["distribution"].items() if n > 0]
    add("C8", "分类非平凡(≥2 类非零)", len(nz) >= 2 and len(core["P"]) > 20 and len(core["D"]) > 20,
        f"nonzero_classes={nz} |P|={len(core['P'])} |D|={len(core['D'])}")
    add("C9", "修法天花板: 补 9 枚漏字段后不可重放登记键 4 → 2（解除 set == {symbol_face_rungs, n_symbol_faces}）",
        set(core["face_unblocked_nonreplayable"]) == {"symbol_face_rungs", "n_symbol_faces"}
        and core["not_replayable_total"] == 4,
        f"unblocked={core['face_unblocked_nonreplayable']} / not_replayable_total={core['not_replayable_total']} "
        f"face_dependent_registered={core['face_dependent_registered_keys']} omitted_n={len(core['omitted_fields'])}")
    add("C10", "闭环守恒: P∪D∪A 每键恰一类且 Σ == |universe|", cl["conserved_sum"] == cl["universe_size"],
        f"sum={cl['conserved_sum']} universe={cl['universe_size']}")
    add("C11", "归档面缺字段行是分支条件产物: face 赋值前早退 return rec == 7",
        sets["early_returns"] == 7,
        f"early_returns_before_face_assign={sets['early_returns']} verdicts={dict(arch['verdicts'])}")
    if det is not None:
        add("C12", "确定性: 两跑核心读数逐字节相同", det.get("identical") is True,
            f"sha={str(det.get('sha_a'))[:16]}")
    add("PH1", "（事后）归档键集 ⊆ 落盘白名单 ⇒ 同源", not (set(arch["keys"]) - set(sets["dump"])),
        f"foreign={sorted(set(arch['keys']) - set(sets['dump']))}", posthoc=True)
    add("PH2", "（事后）依赖面精确集 == {n_symbol_faces, symbol_face_candidates, symbol_face_rungs}",
        set(core["all_face_dependent_keys"]) == {"n_symbol_faces", "symbol_face_candidates", "symbol_face_rungs"},
        f"all_face_dependent={core['all_face_dependent_keys']}", posthoc=True)
    return chk


def _writer_class(rel: str) -> str:
    """EXP1-Q37 候选①: 窗口内写入的**归属分类** —— 判据不放宽, 只让红自己说清是谁写的。

    `src/**/*.cs` 这个 glob 同时覆盖**手写源码**与**构建产物** (obj/.../AssemblyInfo.cs,
    GlobalUsings.g.cs); 后者由任何一次 `dotnet build/publish` 生成 ⇒ 兄弟写者在飞时该判据如实报红。
    分类只进 detail, 不参与 passed (放行噪声 = 掏空判据)。
    """
    p = rel.replace('\\', '/')
    return 'build_artifact' if ('/obj/' in p or '/bin/' in p) else 'handwritten'


def zero_regression(round_start: float, probe_path: Path, archive_path: Path,
                    probe_sha: str, archive_sha: str) -> dict:
    """C14: 本轮零产品/零依赖改动 —— 源与归档在其后逐字节未变, 且 src/ 与 skills/ 无新写入。

    判据面 (与 claim 逐字对应, 机取而非注释): `src/**/*.cs` + `skills/**/*.md` 中
    mtime > 进程起点的文件数必须为 0。因 glob 含构建产物 .cs, 该判据等价于
    「窗口内无 dotnet 构建」。明细带 owner_class 供分诊 (手写 vs 构建产物)。
    """
    now_probe = hashlib.sha256(probe_path.read_bytes()).hexdigest()
    now_arch = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    root = probe_path.resolve().parent
    while root != root.parent and not (root / "src").exists():
        root = root.parent
    touched = []
    for pat in ("src/**/*.cs", "skills/**/*.md"):
        for p in root.glob(pat):
            try:
                m = p.stat().st_mtime
            except OSError:
                continue
            if m > round_start:
                rel = str(p.relative_to(root))
                touched.append({"path": rel, "owner_class": _writer_class(rel),
                                "mtime": round(m, 3)})
    by_class = {}
    for t in touched:
        by_class[t["owner_class"]] = by_class.get(t["owner_class"], 0) + 1
    return {"probe_unchanged": now_probe == probe_sha, "archive_unchanged": now_arch == archive_sha,
            "src_or_skills_written_after_start": touched, "n_touched": len(touched),
            "n_touched_by_class": by_class,
            "passed": now_probe == probe_sha and now_arch == archive_sha and not touched}


# ---------------------------------------------------------------- 自检夹具
def _write(p: Path, s: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")
    return p


def _mini_archive(rows: int, extra=None, drop=None) -> str:
    extra, drop = extra or {}, drop or set()
    out = []
    for i in range(rows):
        r = {"doc": "docs/x.md", "doc_line": i + 1, "path": "src/a/x.py", "kind": "code",
             "line_start": 1, "line_end": 1, "verdict": "ok", "in_code_fence": False,
             "symbols": [], "symbol_attr": "line", "retire_marker": False, "symbols_absent": False,
             "resolve_mode": "path", "resolved": "src/a/x.py", "waive_reason": None,
             "file_lines": 10, "input_sha": "deadbeef", "edge_strength": "strong",
             "edge_sublevel": None, "edge_weak_symbols": 0, "edge_broken_symbols": 0,
             "edge_kind": "code", "kind_reason": "resolved_code", "kind_per_symbol": {}}
        r.update(extra)
        for d in drop:
            r.pop(d, None)
        out.append(json.dumps(r, ensure_ascii=False))
    return "\n".join(out) + "\n"


def selftest(core_real: dict, probe_path: Path) -> list:
    fx = []

    def add(fid, claim, ok, detail):
        fx.append({"id": fid, "claim": claim, "passed": bool(ok), "detail": detail})

    src = probe_path.read_text(encoding="utf-8")
    tmp = Path(tempfile.mkdtemp(prefix="q17_selftest_"))

    # FX01 三轴派生非平凡
    s = core_real["sets"]
    add("FX01", "三集合派生非平凡且互不空", all(len(s[k]) >= 5 for k in ("P1", "P2", "P3", "dump")),
        f"|P1|={len(s['P1'])} |P2|={len(s['P2'])} |P3|={len(s['P3'])} |D|={len(s['dump'])}")
    # FX02 守卫在场
    add("FX02", "落盘守卫 `if k in c` 在场", s["dump_guard"], f"guard={s['dump_guard']}")
    # FX03 正控: 落入归档且被白名单覆盖的键判 5
    add("FX03", "正控 edge_kind → C_written_and_archived",
        core_real["classification"]["by_key"].get("edge_kind") == "C_written_and_archived",
        f"class={core_real['classification']['by_key'].get('edge_kind')}")
    # FX04 组合负控: 白名单补 symbol_faces 的源码 + 归档含该字段 ⇒ 必须判 5（证明两读同时真读）
    src4 = _write(tmp / "probe_v260_dump_patched_a.py", splice_tuple_keys(src, ["symbol_faces"]))
    a4 = _write(tmp / "fx04.jsonl", _mini_archive(3, extra={"symbol_faces": {"Foo.Bar": "declared_type"}}))
    c4 = run_core(src4, a4)
    add("FX04", "组合负控(白名单补 face + 归档含 face) → C_written_and_archived",
        c4["face_class"] == "C_written_and_archived",
        f"class={c4['face_class']} attr={c4['attribution']}")
    # FX05 单变量负控: 白名单补 symbol_faces 的源码 + **真归档** ⇒ 必须离开类 4（证明 D 取自源码）
    src5 = _write(tmp / "probe_v260_dump_patched_b.py", splice_tuple_keys(src, ["symbol_faces"]))
    c5 = run_core(src5, Path(core_real["archive"]["path"]))
    add("FX05", "单变量负控(只改白名单) → 类目离开 4 且键进 D",
        c5["face_class"] != "C_producer_dump_omission" and "symbol_faces" in c5["sets"]["dump"],
        f"class={c5['face_class']} in_D={'symbol_faces' in c5['sets']['dump']}")
    # FX06 负控: 白名单插入从不存在的键 ⇒ 类目 2（证明 class-2 检测非空转）
    src6 = _write(tmp / "probe_v260_bogus.py", splice_tuple_keys(src, ["__bogus_never_produced__"]))
    c6 = run_core(src6, Path(core_real["archive"]["path"]))
    add("FX06", "负控(白名单插入从不产出键) → C_dump_dead_entry 命中",
        c6["classification"]["by_key"].get("__bogus_never_produced__") == "C_dump_dead_entry",
        f"class={c6['classification']['by_key'].get('__bogus_never_produced__')}")
    # FX07 负控: 归档含外来键 ⇒ 类目 1
    a7 = _write(tmp / "fx07.jsonl", _mini_archive(2, extra={"__foreign_key__": 1}))
    c7 = run_core(probe_path, a7)
    add("FX07", "负控(归档含外来键) → C_archive_foreign_key 命中",
        c7["classification"]["by_key"].get("__foreign_key__") == "C_archive_foreign_key",
        f"class={c7['classification']['by_key'].get('__foreign_key__')}")
    # FX08 负控: 归档缺 branch 字段 ⇒ 类目 3（relocated 条件分支）
    a8 = _write(tmp / "fx08.jsonl", _mini_archive(2, drop={"edge_kind"}))
    c8 = run_core(probe_path, a8)
    add("FX08", "负控(归档缺条件分支字段 edge_kind) → C_dump_producer_branch_unhit",
        c8["classification"]["by_key"].get("edge_kind") == "C_dump_producer_branch_unhit",
        f"class={c8['classification']['by_key'].get('edge_kind')}")
    # FX09 守恒在合成输入上也成立
    ok9 = all(run_core(probe_path, p)["classification"]["conserved_sum"]
              == run_core(probe_path, p)["classification"]["universe_size"] for p in (a4, a7, a8))
    add("FX09", "守恒式在合成输入上成立", ok9, "Σ==|universe| on fx04/fx07/fx08")
    # FX10 fail-closed: 归档缺失/空 ⇒ 弃权(3) 而非判红
    try:
        run_core(probe_path, tmp / "nonexistent.jsonl")
        ok10, det10 = False, "未抛异常"
    except Exception as e:
        ok10, det10 = True, f"{type(e).__name__}: {e}"
    add("FX10", "fail-closed: 归档缺失 ⇒ 异常(映射为弃权 3)", ok10, det10)
    # FX11 空归档同样弃权
    a11 = _write(tmp / "fx11.jsonl", "")
    try:
        run_core(probe_path, a11)
        ok11, det11 = False, "未抛异常"
    except Exception as e:
        ok11, det11 = True, f"{type(e).__name__}"
    add("FX11", "fail-closed: 空归档 ⇒ 弃权", ok11, det11)
    # FX12 源码缺函数 ⇒ 弃权
    src12 = _write(tmp / "probe_missing_fn.py", src.replace("def run_pass(", "def run_pass_renamed("))
    try:
        run_core(src12, Path(core_real["archive"]["path"]))
        ok12, det12 = False, "未抛异常"
    except Exception as e:
        ok12, det12 = True, f"{type(e).__name__}"
    add("FX12", "fail-closed: 源码缺 run_pass ⇒ 弃权", ok12, det12)
    # FX13 universe == P ∪ D ∪ A（含归档外来键，不得静默丢弃）
    u = set(core_real["classification"]["universe"])
    add("FX13", "universe == P ∪ D ∪ A", u == (set(core_real["P"]) | set(core_real["D"]) | set(core_real["A"])),
        f"|universe|={len(u)}")
    # FX14 域读数两路一致（真语料）
    add("FX14", "真语料域双读数一致", core_real["archive"]["n_live"] == core_real["archive"]["n_edge_rows"],
        f"live={core_real['archive']['n_live']} edge_rows={core_real['archive']['n_edge_rows']}")
    # FX15 负控: 关掉「循环变量不作枢纽」规则 ⇒ 依赖面必须变宽（证明该规则承重, 非装饰）
    rp = [n for n in ast.walk(ast.parse(src))
          if isinstance(n, ast.FunctionDef) and n.name == "run_pass"][0]

    def face_dep_width(hub_exclusion: bool) -> set:
        fl = flow_deps(rp, hub_exclusion=hub_exclusion)
        all_k = _assigned_names(rp)
        lit_map, nm_map = fl["lit"], fl["nm"]
        dep_names = {}
        for nm_ in all_k:
            nms, lits = fl["expand"]({nm_})
            dep_names[nm_] = lits
        return {k for k, v in dep_names.items() if v & {"symbol_faces", "relocated_symbol_faces"}}

    w_on, w_off = face_dep_width(True), face_dep_width(False)
    add("FX15", "负控: 去枢纽规则 ⇒ 依赖面变宽（规则承重）", len(w_on) < len(w_off) and len(w_off) >= 5,
        f"with_hub_rule={len(w_on)} without={len(w_off)}")

    # ---- EXP1-Q37 候选①: C14「窗口内写入」判据的**确定性机理重演** (不依赖同机负载)
    tree = tmp / "c14_tree"
    (tree / "src").mkdir(parents=True, exist_ok=True)
    z_probe = _write(tree / "probe.py", "x = 1\n")
    z_arch = _write(tree / "a.jsonl", "{}\n")
    zps = hashlib.sha256(z_probe.read_bytes()).hexdigest()
    zas = hashlib.sha256(z_arch.read_bytes()).hexdigest()
    t_start = time.time()
    time.sleep(0.02)
    fx_hand = _write(tree / "src" / "touched.cs", "// t\n")            # 手写源
    r_hand = zero_regression(t_start, z_probe, z_arch, zps, zas)
    fx_hand.unlink()
    fx_bld = _write(tree / "src" / "obj" / "Release" / "x.AssemblyInfo.cs", "//\n")  # 构建产物
    r_bld = zero_regression(t_start, z_probe, z_arch, zps, zas)
    fx_bld.unlink()
    r_clean = zero_regression(t_start, z_probe, z_arch, zps, zas)      # 空窗
    add("FX16", "C14 正控: 窗口内写 src/**/*.cs ⇒ 判红 ∧ owner_class=handwritten",
        (not r_hand["passed"]) and r_hand["n_touched_by_class"] == {"handwritten": 1},
        f"passed={r_hand['passed']} by_class={r_hand['n_touched_by_class']}")
    add("FX17", "C14 负控: 窗口内只写构建产物 obj/*.cs ⇒ 同判红 ∧ owner_class=build_artifact",
        (not r_bld["passed"]) and r_bld["n_touched_by_class"] == {"build_artifact": 1},
        f"passed={r_bld['passed']} by_class={r_bld['n_touched_by_class']}")
    add("FX18", "C14 空窗正控: 无窗口内写入 ⇒ 判绿 (判据非恒红)",
        bool(r_clean["passed"]) and r_clean["n_touched"] == 0,
        f"passed={r_clean['passed']} n={r_clean['n_touched']}")
    return fx


def canon_sha(obj: dict) -> str:
    core = {k: obj[k] for k in ("face_class", "relocated_face_class", "attribution",
                                "omitted_fields", "classification", "P", "D", "A",
                                "unblocked_registered_keys")}
    return hashlib.sha256(json.dumps(core, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", default="eval/capability/exp1-q10/probe_v260.py")
    ap.add_argument("--archive", default="eval/capability/exp1-q10/citations.jsonl")
    ap.add_argument("--registered", default="eval/capability/exp1-q10/attribution_q10.json")
    ap.add_argument("--q16-verdict", default="eval/capability/exp1-q16/verdict_q16.json")
    ap.add_argument("--out", default="eval/capability/exp1-q17/verdict_q17.json")
    ap.add_argument("--fixtures-out", default="eval/capability/exp1-q17/selftest_q17.json")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--determinism", action="store_true")
    args = ap.parse_args(argv)

    t0 = time.time()
    probe_path, archive_path = Path(args.probe), Path(args.archive)
    if not probe_path.exists() or not archive_path.exists():
        print(f"MEASUREMENT_FAILURE: 输入缺失 probe={probe_path.exists()} archive={archive_path.exists()}",
              file=sys.stderr)
        return EXIT_MEASURE
    registered = load_registered(Path(args.registered))
    q16 = load_q16_not_replayable(Path(args.q16_verdict))
    core_sha = (hashlib.sha256(probe_path.read_bytes()).hexdigest(),
                hashlib.sha256(archive_path.read_bytes()).hexdigest())
    if not registered["available"] or not q16["available"]:
        print(f"MEASUREMENT_FAILURE: 台账输入缺失 registered={registered['available']} "
              f"q16_not_replayable={q16['available']}", file=sys.stderr)
        return EXIT_MEASURE
    try:
        core = run_core(probe_path, archive_path, registered, q16)
    except Exception as e:
        print(f"MEASUREMENT_FAILURE: {type(e).__name__}: {e}", file=sys.stderr)
        return EXIT_MEASURE

    det = None
    if args.determinism:
        core2 = run_core(probe_path, archive_path, registered, q16)
        det = {"sha_a": canon_sha(core), "sha_b": canon_sha(core2),
               "identical": canon_sha(core) == canon_sha(core2)}
    checks = evaluate(core, det)
    fixtures = selftest(core, probe_path) if args.selftest else []
    checks.append({"id": "C13", "claim": "夹具全绿（含 4 负控 + 1 正控 + 3 fail-closed + 组合）",
                   "passed": bool(fixtures) and all(f["passed"] for f in fixtures),
                   "detail": f"{sum(1 for f in fixtures if f['passed'])}/{len(fixtures)}", "posthoc": False})
    zr = zero_regression(t0, probe_path, archive_path, core_sha[0], core_sha[1])
    checks.append({"id": "C14", "claim": "零回归: probe/归档逐字节未变 ∧ src/ 与 skills/ 无新写入 "
                                        "(mtime 判据, glob 含构建产物 .cs ⇒ 等价于窗口内无 dotnet 构建)",
                   "passed": zr["passed"], "detail": json.dumps(zr, ensure_ascii=False)[:400], "posthoc": False})

    failed = [c for c in checks if not c["passed"]]
    verdict = {
        "round": "EXP1-Q17",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "elapsed_s": round(time.time() - t0, 3),
        "inputs": {"probe": str(probe_path), "archive": str(archive_path),
                   "registered": registered["path"], "q16_verdict": q16["path"],
                   "probe_sha256": core_sha[0], "archive_sha256": core_sha[1]},
        "readings": {
            "archive_rows": core["archive"]["n_rows"],
            "archive_bad_lines": core["archive"]["bad_lines"],
            "archive_key_count": len(core["archive"]["keys"]),
            "rows_with_symbol_faces": core["archive"]["keys"].get("symbol_faces", 0),
            "domain_live_from_archive": core["archive"]["n_live"],
            "domain_edge_field_rows": core["archive"]["n_edge_rows"],
            "P_size": len(core["P"]), "P1_size": len(core["sets"]["P1"]),
            "P2_size": len(core["sets"]["P2"]), "P3_size": len(core["sets"]["P3"]),
            "D_size": len(core["D"]), "A_size": len(core["A"]),
            "universe_size": core["classification"]["universe_size"],
            "class_conserved_sum": core["classification"]["conserved_sum"],
            "class_distribution": core["classification"]["distribution"],
            "class_by_key": core["classification"]["by_key"],
            "early_returns_before_face_assign": core["sets"]["early_returns"],
            "omitted_fields": core["omitted_fields"],
            "branch_unhit_fields": sorted(k for k, c in core["classification"]["by_key"].items()
                                          if c == "C_dump_producer_branch_unhit"),
            "attribution": core["attribution"],
            "face_field_class": core["face_class"],
            "relocated_face_field_class": core["relocated_face_class"],
            "unblocked_registered_keys": core["unblocked_registered_keys"],
            "face_dependent_registered_keys": core["face_dependent_registered_keys"],
            "face_unblocked_nonreplayable": core["face_unblocked_nonreplayable"],
            "not_replayable_total": core["not_replayable_total"],
            "not_replayable_typed": core["not_replayable_typed"],
            "all_face_dependent_result_keys": core["all_face_dependent_keys"],
            "unblocked_all_result_keys": core["unblocked_all_result_keys"],
            "producer_key_spans": {"P1": core["sets"]["P1"], "P2": core["sets"]["P2"], "P3": core["sets"]["P3"]},
            "dump_key_spans": core["sets"]["dump"],
        },
        "checks": checks,
        "fixtures": fixtures,
        "determinism": det,
        "exit_code": EXIT_ASSERT if failed else EXIT_OK,
    }
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(verdict, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    if args.selftest:
        fo = Path(args.fixtures_out)
        fo.parent.mkdir(parents=True, exist_ok=True)
        fo.write_text(json.dumps(fixtures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"verdict → {outp}")
    print(f"归因: {core['attribution']}")
    print(f"类分布: {core['classification']['distribution']}  Σ={core['classification']['conserved_sum']}"
          f" == |P∪D∪A|={core['classification']['universe_size']}")
    print(f"漏字段({len(core['omitted_fields'])}): {core['omitted_fields']}")
    print(f"checks {sum(1 for c in checks if c['passed'])}/{len(checks)} · fixtures "
          f"{sum(1 for f in fixtures if f['passed'])}/{len(fixtures)} · exit={verdict['exit_code']}")
    for c in checks + fixtures:
        if not c["passed"]:
            print(f"  RED {c['id']}: {c['claim']} | {c['detail']}")
    return verdict["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
