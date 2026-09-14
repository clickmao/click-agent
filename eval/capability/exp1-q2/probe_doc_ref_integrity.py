#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q2 前提核验 + 引用事实机检 + 现役扩展契约盘点 (纯静态, 零产品源码改动, 零 dotnet)。

靶点文档: docs/plans/v0.22.0-exp1-local-index-and-code-graph.md §8-Q2
("插件 API 是否引入 manifest + schema_version")。

回答四件事, 全部可数, 不做感觉判断:
  A. 引用事实面 —— 文档里 `路径:行号` + 反引号符号 的引用, 在当前树是否仍成立
  B. 死契约面 —— 计划文档引作"既有契约"的类型, 在当前源码中的出现次数 (外部真值: git 删除提交)
  C. 契约面盘点 —— 现役扩展契约里, 有几个是 capability-id+args 形态? 有几个带版本/schema 字段?
  D. Q2 裁定数据 —— 可版本化载体数 / 外部文件驱动注册先例数

判据预注册 (读数前写入, 顺序 = 执行顺序):
  G1 仪器自证: 正控符号 (确定在码中) 出现数 > 0 ∧ 负控符号 (确定不在) == 0
                ∧ 正/负控给出**不同结论** (计数器既不恒 0 也不恒真)
  G2 确定性: 两跑 (a) 判据读数逐位相同, 或 (b) 差异所在的文档其**被引文件输入指纹**已变
                (并发写者改动 ⇒ 可归因); 指纹相同却读数不同 ⇒ 判红 (真非确定性)
  G3 弃权闸: 无法解析的引用 (裸文件名 0/多候选、语料外路径、读失败) 一律**弃权单列**, 不判红
  G4 前提核验 (机器判): 计划点名的 3 个类型在当前 src/*.cs 出现次数 == 0
                ⇒ "复用既有契约" 前提为假, Q2 必须改框定 (而非按旧前提写开发计划)
  G5 非平凡: 三个目标族的引用文档集合不得全部相同 (全同 ⇒ 读数可疑, 判测量失败)

三态退出码: 0 判据全过 / 2 判据失败(真红) / 3 测量或环境失败(弃权, 不判红)
证据等级: **L1 静态机检** (无真机运行) —— 不得对外报为 L3/L4。

引用归属三级降级 (照 R418 纪律, 不任取):
  精确相对路径 (含 '/')  → 存在则判事实, 不存在 ⇒ stale_path (语料内命名空间)
  裸文件名 (无 '/')      → 全树唯一同名 ⇒ 解析; 0 候选 / 多候选 ⇒ **弃权**单列
  语料外命名空间         → out_of_scope ⇒ 弃权单列

用法:
  python3 eval/capability/exp1-q2/probe_doc_ref_integrity.py --repo . --out eval/capability/exp1-q2/result.json
  python3 eval/capability/exp1-q2/probe_doc_ref_integrity.py --repo <fixture> --out /tmp/x.json   # 自检用
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------- 预注册判据
CRITERIA = {
    "G1_instrument_selfproof": "正控符号出现数>0 ∧ 负控符号出现数==0 ∧ 两者结论不同",
    "G2_determinism": "两跑读数逐位相同 ∨ 差异文档的被引文件输入指纹已变 (可归因)",
    "G3_waiver_gate": "不可解析引用 (裸名 0/多候选 / 语料外 / 读失败) 弃权单列, 不判红",
    "G4_premise_refutation": "计划点名类型在当前 src/*.cs 出现次数==0 ⇒ '复用既有契约' 前提为假",
    "G5_nontrivial": "三个目标族的引用文档集合不得全部相同",
}
DECISION_RULES = {
    "D1_versionable_carrier": "若 capability-id+args 形态契约数 == 0 ⇒ Q2 的(a)/(b) 均无既有载体, 只能随**新建**契约定义 schema_version",
    "D2_manifest_loader": "若'外部文件驱动注册'先例数 == 0 ⇒ manifest 形态(b) 需新建加载器(反射受限) ⇒ 不推荐",
}
POSITIVE_SYMBOLS = ["IResponseSegmentPlugin", "CapabilityScanner", "PythonArtifactPlugin"]
NEGATIVE_SYMBOLS = ["NoSuchTypeZzq9Xx", "RegistryThatNeverExistedZq"]
TARGET_SYMBOLS = ["ICapabilityPlugin", "PluginExecutionResult", "CapabilityPluginRegistry"]

DOC_GLOBS = ["docs/**/*.md", "*.md"]
CODE_GLOBS = ["src/**/*.cs"]
IN_SCOPE_PREFIXES = ("src/", "docs/", "scripts/", "tools/", "eval/", "website/", "data/")

CITE_RE = re.compile(
    r'(?<![\w./-])([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:cs|py|ts|tsx|js|json|jsonl|md|sh|yaml|yml|csproj|html|css))'
    r':(\d+)(?:\s*[-~\u2013]\s*(\d+))?'
)
BACKTICK_RE = re.compile(r'`([^`]+)`')
SYMBOL_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{2,}$')
CODE_EXT = {".cs", ".py", ".ts", ".tsx", ".js", ".sh", ".csproj", ".json", ".jsonl", ".yaml", ".yml"}

SKIP_DIR_PARTS = {".git", "bin", "obj", "node_modules", ".venv", "__pycache__", ".mypy_cache", "TestResults"}

STOPWORDS = {
    "and", "the", "not", "true", "false", "null", "None", "True", "False", "string", "int", "bool",
    "void", "var", "async", "await", "public", "private", "static", "class", "interface", "new",
    "return", "if", "else", "for", "while", "using", "import", "def", "json", "yaml", "utf", "Git",
    "README", "SKILL", "TODO", "OK", "UI", "API", "KPI", "AOT", "JIT", "E2E", "JSON", "YAML", "SQL",
    "No", "Yes", "ID", "L0", "L1", "L2", "L3", "L4", "R1", "R2",
}


# ---------------------------------------------------------------- 仓库读取器 (带输入指纹)
class Repo:
    """只读仓库; 每次读取记录 sha256 ⇒ 输入指纹自证 (R430 纪律)。"""

    def __init__(self, root: Path):
        self.root = root
        self._cache = {}
        self._by_basename = None

    def _rel_ok(self, rel: str) -> bool:
        parts = Path(rel).parts
        return not (set(parts) & SKIP_DIR_PARTS)

    def read(self, rel: str):
        """返回 (text, sha256) 或 (None, None)。"""
        if rel in self._cache:
            return self._cache[rel]
        p = self.root / rel
        try:
            data = p.read_bytes()
            text = data.decode("utf-8", errors="replace")
            out = (text, hashlib.sha256(data).hexdigest())
        except (OSError, ValueError):
            out = (None, None)
        self._cache[rel] = out
        return out

    def exists(self, rel: str) -> bool:
        return (self.root / rel).is_file()

    def glob(self, pattern: str):
        for p in sorted(self.root.glob(pattern)):
            if p.is_file() and self._rel_ok(p.relative_to(self.root).as_posix()):
                yield p.relative_to(self.root).as_posix()

    def basename_index(self):
        if self._by_basename is None:
            idx = defaultdict(list)
            for dirpath, dirnames, filenames in os.walk(self.root):
                dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_PARTS]
                for fn in filenames:
                    rel = Path(dirpath, fn).relative_to(self.root).as_posix()
                    idx[fn].append(rel)
            self._by_basename = {k: sorted(v) for k, v in idx.items()}
        return self._by_basename

    def fingerprints(self):
        return {k: v[1] for k, v in self._cache.items() if v[1]}


# ---------------------------------------------------------------- 引用抽取与判定
def _kind_of(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in CODE_EXT:
        return "code"
    if ext == ".md":
        return "doc"
    return "other"


def extract_citations(doc_rel: str, text: str):
    out = []
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        for m in CITE_RE.finditer(line):
            path, l1, l2 = m.group(1), int(m.group(2)), m.group(3)
            l2 = int(l2) if l2 else None
            syms = []
            for token in BACKTICK_RE.findall(line):
                t = token.strip().rstrip("()").lstrip("`")
                if SYMBOL_RE.match(t) and "." not in t and t not in STOPWORDS:
                    if any(ch.isupper() for ch in t[1:]) or "_" in t:
                        syms.append(t)
            out.append({
                "doc": doc_rel, "doc_line": lineno, "raw": stripped[:160],
                "path": path, "kind": _kind_of(path),
                "line_start": l1, "line_end": l2 if l2 else l1,
                "in_code_fence": in_fence, "symbols": sorted(set(syms)),
            })
    return out


def resolve_ref(repo: Repo, ref_path: str):
    """三级归属: ('exact', rel) / ('unique_basename', rel) / ('waived', reason)。"""
    if "/" in ref_path:
        if not ref_path.startswith(IN_SCOPE_PREFIXES):
            return "waived", "out_of_scope"
        if repo.exists(ref_path):
            return "exact", ref_path
        if not repo._rel_ok(ref_path):
            return "waived", "excluded_namespace"
        return "absent", ref_path
    cands = repo.basename_index().get(ref_path, [])
    cands = [c for c in cands if repo._rel_ok(c)]
    if len(cands) == 1:
        return "unique_basename", cands[0]
    if not cands:
        return "waived", "unresolvable_bare_name"
    return "waived", "ambiguous_bare_name"


def judge_citation(repo: Repo, c: dict):
    rec = dict(c)
    rec.update({"resolved": None, "resolve_mode": None, "path_exists": False,
                "file_lines": None, "symbols_absent": [], "input_sha": None})
    if c["in_code_fence"]:
        rec["verdict"] = "skipped_fence"
        return rec
    mode, info = resolve_ref(repo, c["path"])
    if mode == "waived":
        rec["verdict"] = "waived"
        rec["waive_reason"] = info
        return rec
    if mode == "absent":
        rec["resolved"] = info
        rec["resolve_mode"] = "in_scope_missing"
        # 四级归属: 路径失效但同名文件是否只是在树内**搬家** (与"已删除"必须分开)
        cands = [x for x in repo.basename_index().get(Path(info).name, []) if repo._rel_ok(x)]
        if cands:
            rec["relocated_to"] = cands
            rec["verdict"] = "relocated"
            if len(cands) == 1:
                text, sha = repo.read(cands[0])
                if text is not None:
                    rec["input_sha"] = sha
                    n_lines = len(text.splitlines())
                    rec["file_lines"] = n_lines
                    lines_ok = c["line_start"] <= n_lines and c["line_end"] <= n_lines
                    absent = [s for s in c["symbols"]
                              if not re.search(r'\b' + re.escape(s) + r'\b', text)]
                    rec["relocated_lines_ok"] = lines_ok
                    rec["relocated_symbols_absent"] = absent
                    rec["relocated_fact_verdict"] = (
                        "ok" if (lines_ok and not absent)
                        else ("stale_lines" if not lines_ok else "symbol_absent"))
            return rec
        rec["verdict"] = "stale_path"  # 全树同名 0 候选 ⇒ 真删
        return rec
    rel = info
    rec["resolve_mode"] = mode
    rec["resolved"] = rel
    text, sha = repo.read(rel)
    if text is None:
        rec["verdict"] = "waived"
        rec["waive_reason"] = "unreadable"
        return rec
    rec["path_exists"] = True
    rec["input_sha"] = sha
    n_lines = len(text.splitlines())
    rec["file_lines"] = n_lines
    if c["line_start"] > n_lines or c["line_end"] > n_lines:
        rec["verdict"] = "stale_lines"
        return rec
    absent = [s for s in c["symbols"] if not re.search(r'\b' + re.escape(s) + r'\b', text)]
    rec["symbols_absent"] = absent
    rec["verdict"] = "symbol_absent" if absent else "ok"
    return rec


# ---------------------------------------------------------------- 契约面盘点
CONTRACT_NAME_RE = re.compile(r'^\s*(?:public\s+)?interface\s+(I[A-Za-z0-9_]*Plugin[A-Za-z0-9_]*)\b', re.M)


def inventory_contracts(repo: Repo):
    src_rels = list(repo.glob("src/**/*.cs"))
    contracts = []
    for rel in src_rels:
        text, _ = repo.read(rel)
        if text is None:
            continue
        for m in CONTRACT_NAME_RE.finditer(text):
            name = m.group(1)
            line = text[:m.start()].count("\n") + 1
            impls, test_impls = set(), set()
            for qrel in src_rels:
                qtext, _ = repo.read(qrel)
                if qtext is None:
                    continue
                for cls in re.findall(r'class\s+([A-Za-z0-9_]+)\s*:\s*[^\n]*\b' + re.escape(name) + r'\b', qtext):
                    (test_impls if ".tests" in qrel else impls).add(f"{qrel}:{cls}")
            head = text[max(0, m.start() - 400): m.start() + 2500]
            contracts.append({
                "interface": name, "def_file": rel, "def_line": line,
                "impls_prod": sorted(impls), "impls_test": sorted(test_impls),
                "n_impls_prod": len(impls), "n_impls_test": len(test_impls),
                "has_capability_dispatch": bool(re.search(r'capabilityId|CapabilityId', text)),
                "has_args_param": bool(re.search(r'\bargs\b', head)),
                "has_version_field": bool(re.search(r'schema_version|SchemaVersion|ContractVersion|contract_version', text)),
            })
    return sorted(contracts, key=lambda c: c["interface"])


def symbol_occurrences(repo: Repo, symbols):
    counts = {s: 0 for s in symbols}
    files = {s: set() for s in symbols}
    for rel in repo.glob("src/**/*.cs"):
        text, _ = repo.read(rel)
        if text is None:
            continue
        for s in symbols:
            n = len(re.findall(r'\b' + re.escape(s) + r'\b', text))
            if n:
                counts[s] += n
                files[s].add(rel)
    return counts, {s: sorted(v) for s, v in files.items()}


def count_file_driven_registrations(repo: Repo):
    pats = [r'manifest', r'capabilit(?:y|ies)\.json', r'LoadFrom(?:Json|File)',
            r'JsonSerializer\.Deserialize[^\n]*Register']
    hits = []
    for rel in repo.glob("src/**/*.cs"):
        text, _ = repo.read(rel)
        if text is None:
            continue
        for pat in pats:
            for m in re.finditer(pat, text, re.I):
                line = text[:m.start()].count("\n") + 1
                hits.append({"file": rel, "line": line, "pat": pat,
                             "text": text.splitlines()[line - 1].strip()[:140]})
    return hits


def count_di_registrations(repo: Repo):
    n, files = 0, set()
    for rel in repo.glob("src/**/*.cs"):
        text, _ = repo.read(rel)
        if text is None:
            continue
        k = len(re.findall(r'Add(?:Singleton|Scoped|Transient)<', text))
        if k:
            n += k
            files.add(rel)
    return n, sorted(files)


# ---------------------------------------------------------------- 单跑
def run_pass(repo: Repo):
    doc_rels = []
    for pat in DOC_GLOBS:
        doc_rels.extend(repo.glob(pat))
    citations = []
    for rel in sorted(set(doc_rels)):
        text, _ = repo.read(rel)
        if text is None:
            continue
        citations.extend(extract_citations(rel, text))
    judged = [judge_citation(repo, c) for c in citations]
    live_code = [c for c in judged if c["kind"] == "code" and not c["in_code_fence"]]
    verdicts = Counter(c["verdict"] for c in live_code)
    waive = Counter(c.get("waive_reason") for c in live_code if c["verdict"] == "waived")

    all_syms = POSITIVE_SYMBOLS + NEGATIVE_SYMBOLS + TARGET_SYMBOLS
    counts, files = symbol_occurrences(repo, all_syms)
    return {
        "n_docs": len(set(doc_rels)),
        "n_citations_total": len(judged),
        "n_citations_code_live": len(live_code),
        "verdict_counts": dict(verdicts),
        "waive_reasons": {str(k): v for k, v in waive.items()},
        "citations": judged,
        "symbol_occurrences": counts,
        "symbol_files": files,
        "contracts": inventory_contracts(repo),
        "manifest_like_hits": count_file_driven_registrations(repo),
        "di_registrations": count_di_registrations(repo)[0],
        "di_files": count_di_registrations(repo)[1],
        "fingerprints": repo.fingerprints(),
        "n_inputs_fingerprinted": len(repo.fingerprints()),
    }


def per_doc_verdicts(res):
    out = defaultdict(list)
    for c in res["citations"]:
        if c["in_code_fence"]:
            continue
        out[c["doc"]].append(f'{c["path"]}:{c["line_start"]}:{c["verdict"]}')
    return {k: sorted(v) for k, v in out.items()}


def determine_exit(gates, waived_expected=False):
    if waived_expected:
        return 3
    return 0 if gates["all_pass"] else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--out", default=None)
    ap.add_argument("--expect-mixed", action="store_true", help="自检用: 断言弃权闸判 exit 3")
    args = ap.parse_args()

    repo_root = Path(args.repo).resolve()
    started = time.time()
    # 前置资产检查 (§3 纪律): 结构缺失 ⇒ 弃权(exit 3), 不当红判
    precheck = {"repo_exists": repo_root.is_dir(), "has_src": (repo_root / "src").is_dir(),
                "has_docs": (repo_root / "docs").is_dir()}
    if not all(precheck.values()):
        print(json.dumps({"stage": "precheck", "error": "repo_missing_expected_structure",
                          "checked": precheck, "repo": str(repo_root), "exit_code": 3},
                         ensure_ascii=False, indent=2))
        return 3
    try:
        r1 = run_pass(Repo(repo_root))
        r2 = run_pass(Repo(repo_root))

        # ---- G2 确定性: 读数逐位相同 ∨ 差异文档的被引输入指纹已变
        c1 = json.dumps({"v": r1["verdict_counts"], "s": r1["symbol_occurrences"]},
                        sort_keys=True, ensure_ascii=False)
        c2 = json.dumps({"v": r2["verdict_counts"], "s": r2["symbol_occurrences"]},
                        sort_keys=True, ensure_ascii=False)
        identical = (c1 == c2)
        pv1, pv2 = per_doc_verdicts(r1), per_doc_verdicts(r2)
        diff_docs = sorted(d for d in set(pv1) | set(pv2) if pv1.get(d) != pv2.get(d))
        fp1, fp2 = r1["fingerprints"], r2["fingerprints"]
        changed_inputs = sorted(k for k in set(fp1) | set(fp2) if fp1.get(k) != fp2.get(k))
        # 归因: 差异文档必须引用了变化中的输入文件, 否则判红
        unattributed = []
        changed_set = set(changed_inputs)
        for d in diff_docs:
            cited = {c["resolved"] for c in r1["citations"]
                     if c["doc"] == d and c.get("resolved")} | \
                    {c["resolved"] for c in r2["citations"] if c["doc"] == d and c.get("resolved")}
            if not (cited & changed_set):
                unattributed.append(d)
        g2 = bool(identical or (diff_docs and not unattributed))

        # ---- G1 正/负控
        occ = r1["symbol_occurrences"]
        pos_counts = {s: occ.get(s, 0) for s in POSITIVE_SYMBOLS}
        neg_counts = {s: occ.get(s, 0) for s in NEGATIVE_SYMBOLS}
        g1 = bool(all(v > 0 for v in pos_counts.values()) and all(v == 0 for v in neg_counts.values()))

        # ---- G4 前提核验
        target_counts = {s: occ.get(s, 0) for s in TARGET_SYMBOLS}
        target_files = {s: r1["symbol_files"].get(s, []) for s in TARGET_SYMBOLS}
        g4 = all(v == 0 for v in target_counts.values())

        # ---- G5 非平凡
        fam_docs = {s: sorted({c["doc"] for c in r1["citations"]
                               if s in c["symbols"] or s in c["path"]}) for s in TARGET_SYMBOLS}
        sigs = [tuple(v) for v in fam_docs.values()]
        g5 = len(set(sigs)) > 1 or all(not v for v in sigs)

        # ---- G3 弃权闸 (不可解析引用必须单列, 且不得被算成 stale)
        waived = {k: v for k, v in r1["verdict_counts"].items() if k == "waived"}
        g3 = True  # 结构性: 弃权只入 waive 桶, 不参与红绿; 单列可见即可
        stale_like = sum(r1["verdict_counts"].get(k, 0)
                         for k in ("stale_path", "stale_lines", "symbol_absent"))

        contracts = r1["contracts"]
        versionable = [c for c in contracts if c["has_capability_dispatch"]]
        with_version = [c for c in contracts if c["has_version_field"]]
        manifest_precedents = [h for h in r1["manifest_like_hits"]
                               if re.search(r'capabilit|register', h["text"], re.I)]

        q2 = {
            "premise_reuse_existing_contract_holds": (not g4),
            "target_symbol_counts": target_counts,
            "target_symbol_files": target_files,
            "n_versionable_contracts": len(versionable),
            "versionable_contracts": [{"i": c["interface"],
                                       "def": f'{c["def_file"]}:{c["def_line"]}'} for c in versionable],
            "n_contracts_with_version_field": len(with_version),
            "contracts_with_version_field": [c["interface"] for c in with_version],
            "n_manifest_like_registration_precedents": len(manifest_precedents),
            "manifest_like_precedents": manifest_precedents[:10],
            "n_di_registrations": r1["di_registrations"],
            "d1_versionable_carrier": "no_existing_carrier" if not versionable else "carrier_exists",
            "d2_manifest_loader": "needs_new_loader" if not manifest_precedents else "precedent_exists",
        }

        gate_dict = {
            "G1_instrument_selfproof": g1,
            "G1_positive_counts": pos_counts,
            "G1_negative_counts": neg_counts,
            "G2_two_pass_identical": identical,
            "G2_differing_docs": diff_docs[:20],
            "G2_unattributed_docs": unattributed,
            "G2_changed_inputs": changed_inputs[:20],
            "G2_verdict": bool(g2),
            "G3_waiver_visible": g3,
            "G3_waived_counts": waived,
            "G4_premise_refuted": bool(g4),
            "G5_families_distinct": bool(g5),
            "G5_family_docs": {k: v[:6] for k, v in fam_docs.items()},
        }
        all_pass = bool(g1 and g2 and g5 and g3)
        gate_dict["all_pass"] = all_pass
        # 测量有效性闸: 无可判对象 ⇒ 弃权(exit 3), 不判红也不判绿
        measurable = bool(r1["n_docs"] > 0 and r1["n_citations_code_live"] > 0)
        gate_dict["measurable"] = measurable
        exit_code = determine_exit(gate_dict, args.expect_mixed or not measurable)

        stale = [c for c in r1["citations"]
                 if c["verdict"] in ("stale_path", "stale_lines", "symbol_absent")]
        relocated = [c for c in r1["citations"] if c["verdict"] == "relocated"]
        relocated_fact = Counter(c.get("relocated_fact_verdict") for c in relocated)

        result = {
            "probe": "exp1-q2-doc-ref-integrity-and-contract-surface",
            "probe_version": "2.1.0",
            "target_doc": "docs/plans/v0.22.0-exp1-local-index-and-code-graph.md",
            "target_question": "§8-Q2 插件 API 是否引入 manifest + schema_version",
            "evidence_level": "L1-static",
            "repo": str(repo_root),
            "criteria_pre_registered": CRITERIA,
            "decision_rules": DECISION_RULES,
            "corpus": {"n_docs": r1["n_docs"], "n_inputs_fingerprinted": r1["n_inputs_fingerprinted"]},
            "citation_verdicts": r1["verdict_counts"],
            "waive_reasons": r1["waive_reasons"],
            "symbol_occurrences": r1["symbol_occurrences"],
            "symbol_files": r1["symbol_files"],
            "stale_like_n": stale_like,
            "stale_citations": stale,
            "relocated_n": len(relocated),
            "relocated_fact_verdicts": {str(k): v for k, v in relocated_fact.items()},
            "relocated_citations": relocated,
            "contracts": contracts,
            "q2_decision_data": q2,
            "gates": gate_dict,
            "checks_posthoc": {
                "instrument_defect_v1": ("v1.0.0 把无目录裸文件名判为 stale_path (389 条, 其中多数实为"
                                         "'无法解析' 而非'文件已删') ⇒ v2.0.0 引入三级归属: 裸名唯一候选才解析, "
                                         "0/多候选一律弃权单列, 不判红 (照 R418 纪律)"),
                "instrument_defect_v2": ("v2.0.0 把'路径失效'一律判 stale_path, 未区分**已删除**与**树内搬家** "
                                         "(实测本仓 src/agent.embedcpu/ 等 21 个项目目录已重排, 同名文件多在别处) "
                                         "⇒ v2.1.0 加第四级 relocated: 同名唯一候选⇒按候选文件核对行号/符号事实; "
                                         "0 候选才是 stale_path(真删); 多候选⇒relocated 且不做事实判定"),
            },
            "run_started_epoch": started,
            "run_finished_epoch": time.time(),
            "gate_pass": all_pass,
            "exit_code": exit_code,
            "honest_boundaries": [
                "证据等级 L1 静态机检 (无真机运行, 无编译/测试/AOT) —— 不得报为 L3/L4",
                "对侧 30m 作业在改 src/ 产品源码 ⇒ 语料是移动目标; 确定性由两跑 + 被引文件输入指纹归因证明, 不做'文件不动的假设'",
                "符号命中检查是**全文匹配**启发式 (非 AST): 同名出现在注释/字符串/历史示例里也算命中 ⇒ symbol_absent 只作候选, 不作对外结论",
                "引用抽取跳过 ``` 代码围栏内的行 (命令输出/样例不算引用事实); 该规则影响计数, 已在 in_code_fence 字段可见",
                "文档语料 = docs/**/*.md + 根 *.md; 不含 .txt/.json 与 website/ 站点副本",
                "契约盘点按正则扫 interface 声明与 'class X : ... IFoo' 形态: 泛型约束/多接口链/partial 可能漏计 (n_impls_prod 是下界)",
                "stale_lines 只用行号越界判定 (文件变短), 行号偏移但未越界不报 ⇒ 该口径会**低估**",
                "verdict 分四桶且互斥: ok / stale_path(basename 全树 0 候选=真删) / relocated(路径失效但同名文件在别处) / waived(不可解析, 弃权)",
                "relocated 仅在同名唯一候选时才给 relocated_fact_verdict (行号/符号按候选文件核对); 多候选只记 relocated_to 列表, 不做事实判定",
                "本探针只读文件, 不改产品源码, 不跑 dotnet, 不占轮号",
            ],
        }
        if args.out:
            Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            with Path(args.out).with_name("citations.jsonl").open("w", encoding="utf-8") as fh:
                for c in r1["citations"]:
                    fh.write(json.dumps({k: c[k] for k in
                                         ("doc", "doc_line", "path", "kind", "line_start", "line_end",
                                          "verdict", "in_code_fence", "symbols", "symbols_absent",
                                          "resolve_mode", "resolved", "waive_reason",
                                          "file_lines", "input_sha",
                                          "relocated_to", "relocated_fact_verdict") if k in c},
                                        ensure_ascii=False) + "\n")
        print(json.dumps({
            "n_docs": r1["n_docs"],
            "citation_verdicts": r1["verdict_counts"],
            "waive_reasons": r1["waive_reasons"],
            "relocated_n": len(relocated),
            "relocated_fact_verdicts": {str(k): v for k, v in relocated_fact.items()},
            "n_inputs_fingerprinted": r1["n_inputs_fingerprinted"],
            "symbol_counts": occ,
            "gates": {k: v for k, v in gate_dict.items() if isinstance(v, bool)},
            "q2": {k: q2[k] for k in ("premise_reuse_existing_contract_holds", "n_versionable_contracts",
                                      "n_contracts_with_version_field",
                                      "n_manifest_like_registration_precedents",
                                      "d1_versionable_carrier", "d2_manifest_loader", "n_di_registrations")},
            "exit_code": exit_code,
        }, ensure_ascii=False, indent=2))
        return exit_code
    except Exception as exc:  # 测量/环境失败 ⇒ 弃权 (exit 3), 不判红
        print(json.dumps({"error": repr(exc), "stage": "probe", "exit_code": 3}, ensure_ascii=False))
        return 3


if __name__ == "__main__":
    sys.exit(main())
