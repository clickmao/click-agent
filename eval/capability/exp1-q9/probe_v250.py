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
  G6 续引子探针非退化: 续引数 == 0 ∨ 续引**归属 tier 分布 >= 2 类**
                (tier 全同一 ⇒ 分级规则被单一规则支配, 该子探针无判别力 ⇒ 判测量失败)

三态退出码: 0 判据全过 / 2 判据失败(真红) / 3 测量或环境失败(弃权, 不判红)
证据等级: **L1 静态机检** (无真机运行) —— 不得对外报为 L3/L4。

续引形态 `[:NNN]` (同一文件内的后续行号, 不重复写路径) 归属四级降级, 逐级只在**有证据**时才认:
  T1 stem_symbol       前窗 (上一条完整引用之后 -> 本续引之前) 内**反引号包裹**的 `Stem.Member`,
                       其主干唯一映射到树内某文件 ⇒ 认该文件 (位置无关, 最强证据)
  T2 same_line_prev    同行最近的前一条完整引用 ⇒ 认其路径
  T3 block_unique_prev 无同行前引时: 同「块」(连续非空行) 内**所有**前序引用的路径集合唯一 ⇒ 认之
  T4 弃权              以上皆不成立 (或 stem 多候选互相冲突) ⇒ 弃权单列, 不判红
  续引判定只查**路径存在 + 行号在文件范围内**; 符号归属仍归其锚点引用 (不重复判符号)。

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
    "G6_cont_nontrivial": "续引数==0 ∨ 续引归属 tier 分布>=2 类 (全同一 tier ⇒ 子探针无判别力)",
    "G7_ladder_nontrivial": "符号存在性阶梯在真实语料上 >=2 级分布 (恒同一级 ⇒ 该轴无判别力 ⇒ 先查仪器再谈被测)",
    "G8_edge_levels_nontrivial_and_conserved": "边强档位 (非弃权) >=2 类 ∧ 边强计数之和 == live 代码引用数 (恒同一档 ⇒ 该轴无判别力; 和不等 ⇒ 归属漏项)",
}
PROBE_VERSION = "2.5.0"
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

# ---- 退役留痕标记 (R409 同族判据: 标记「出现」≠「误用」)
# 显式登记退役的引用是**合法留痕**; 未登记的死引用才是缺陷。判据绑**位置**(窗口内)而非词面出现。
# 字面量一律由码点构造 (禁手打, 防写入通道替换), 形态在 selftest 里按码点自检。
RETIRED_WINDOW = 60            # 标记必须落在引用两侧该窗口内, 且不得越过相邻引用
RETIRED_MARKERS = (
    "\u5df2\u5220",          # yi_shan      -> 已删
    "\u5df2\u5220\u9664",   # yi_shan_chu  -> 已删除
    "\u5df2\u9000\u5f79",   # yi_tui_yi    -> 已退役
    "\u9000\u5f79\u4e8e",   # tui_yi_yu    -> 退役于
    "RETIRED",
    "removed in",
    "deleted in",
)
RETIRE_RE = re.compile("|".join(re.escape(x) for x in RETIRED_MARKERS))

# ---- 续引形态 `[:NNN]` (同文件后续行号): 字面量一律由**码点**构造 (禁手打, 防写入通道替换)
CONT_OPEN, CONT_COLON, CONT_CLOSE = chr(0x5B), chr(0x3A), chr(0x5D)   # [ : ]
CONT_RE = re.compile(
    re.escape(CONT_OPEN) + re.escape(CONT_COLON)
    + r'([0-9][0-9,\s\-\u2013~]*?)' + re.escape(CONT_CLOSE))
CONT_WINDOW = 80                       # T1 前窗上限 (字符)
# `Stem.Member` 形态 (只统计**反引号包裹**者, 防路径文本/散文里的 "a.b" 污染)
STEM_MEMBER_RE = re.compile(
    r'(?:^|[^A-Za-z0-9_.])([A-Za-z_][A-Za-z0-9_]{2,})[.][A-Za-z_][A-Za-z0-9_]*')


def _cont_line_numbers(group: str):
    """`42` / `280-287` / `100,106,112` ⇒ 展开后的行号列表。"""
    out = []
    for part in group.split(","):
        part = part.strip()
        m = re.match(r'^(\d+)\s*[-~\u2013]\s*(\d+)$', part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            out.extend(range(a, b + 1) if a <= b else [a, b])
        elif part.isdigit():
            out.append(int(part))
    return out


def _block_ids(lines):
    """连续非空行 = 同一「块」(段落/列表项连排/表格连排); 空行分段。"""
    ids, cur = [], 0
    for ln in lines:
        if not ln.strip():
            cur += 1
            ids.append(None)
        else:
            ids.append(cur)
    return ids


# ---------------------------------------------------------------- 仓库读取器 (带输入指纹)
class Repo:
    """只读仓库; 每次读取记录 sha256 ⇒ 输入指纹自证 (R430 纪律)。"""

    def __init__(self, root: Path):
        self.root = root
        self._cache = {}
        self._by_basename = None
        self._by_stem = None

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

    def codeface(self, rel: str):
        """剥离注释/字符串后的「代码面」文本 (缓存); 不可剥离的类型返回 None。"""
        key = ("__codeface__", rel)
        if key not in self._cache:
            text, _ = self.read(rel)
            if text is None:
                self._cache[key] = (None, None)
            else:
                tok = "#" if os.path.splitext(rel)[1].lower() in (".py", ".sh") else "//"
                self._cache[key] = (strip_noncode(text, tok), None)
        return self._cache[key][0]

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

    def stem_index(self):
        """basename 去扩展名 ⇒ 路径列表 (T1 归属用: `Stem.Member` 的主干 → 文件)。"""
        if self._by_stem is None:
            idx = defaultdict(set)
            for fn, rels in self.basename_index().items():
                for rel in rels:
                    idx[Path(fn).stem].add(rel)
            self._by_stem = {k: sorted(v) for k, v in idx.items()}
        return self._by_stem

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


def _symbol_tokens(line: str):
    """整行反引号**一次性配对** ⇒ [(start, end, text)] 标识符记号。

    关键: 配对必须在整行上做一次。若按窗口切片再配对, 窗口若以「上一条引用的收尾反引号」开头,
    配对就整体错位一格 ⇒ 紧随其后的符号被静默吞掉 (实测 L62/L406 的 `X`(`path:line`, n 实现) 形态)。
    """
    toks = []
    for mm in BACKTICK_RE.finditer(line):
        t = mm.group(1).strip().rstrip("()").lstrip("`")
        if SYMBOL_RE.match(t) and "." not in t and t not in STOPWORDS:
            if any(ch.isupper() for ch in t[1:]) or "_" in t:
                toks.append((mm.start(), mm.end(), t))
    return toks


def extract_citations(doc_rel: str, text: str):
    out = []
    in_fence = False
    lines = text.splitlines()
    bids = _block_ids(lines)
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        matches = list(CITE_RE.finditer(line))
        spans = [(mm.start(), mm.end()) for mm in matches]
        # 引用自身也可能是反引号包裹的 `path:line` ⇒ 先从记号表里剔掉与引用重叠者
        toks = [(s, e, t) for (s, e, t) in _symbol_tokens(line)
                if not any(s < ce and cs < e for (cs, ce) in spans)]
        for i, m in enumerate(matches):
            path, l1, l2 = m.group(1), int(m.group(2)), m.group(3)
            l2 = int(l2) if l2 else None
            # 符号归属 (测量层缺陷修复): 符号只归**自己那条**引用, 不整行共享。
            #   单引用行 = 整行 (与旧版逐位兼容); 多引用行 = 上一条引用结束 -> 本条引用起点,
            #   末条若前面空则回退到本引用之后 (兼容 `path:line` 在前、符号在后的写法)。
            prev_end = matches[i - 1].end() if i > 0 else 0
            next_start = matches[i + 1].start() if i + 1 < len(matches) else len(line)
            if len(matches) == 1:
                attr, syms = "line", [t for (_s, _e, t) in toks]
            else:
                attr = "nearest_prev"
                syms = [t for (s, e, t) in toks if s >= prev_end and e <= m.start()]
                if not syms and i == len(matches) - 1:
                    attr = "nearest_prev_tail"
                    syms = [t for (s, e, t) in toks if s >= m.end()]
            # 退役标记窗口: 引用两侧各 RETIRED_WINDOW 字符, 且被相邻引用截断 (绑位置)
            win = (line[max(prev_end, m.start() - RETIRED_WINDOW):m.start()]
                   + line[m.end():min(next_start, m.end() + RETIRED_WINDOW)])
            out.append({
                "doc": doc_rel, "doc_line": lineno, "raw": stripped[:160],
                "path": path, "kind": _kind_of(path),
                "line_start": l1, "line_end": l2 if l2 else l1,
                "in_code_fence": in_fence, "symbols": sorted(set(syms)),
                "symbol_attr": attr, "retire_marker": bool(RETIRE_RE.search(win)),
                "pos_start": m.start(), "pos_end": m.end(),
                "block_id": bids[lineno - 1],
            })
    return out


def extract_continuations(doc_rel: str, text: str):
    """抽取续引 `[:NNN]` (与完整引用**不重叠**: 形态带冒号前缀, 不进 CITE_RE)。

    前窗纪律与退役标记窗口同源: 「上一条**完整引用**之后 -> 本续引之前」,
    截断到 CONT_WINDOW 字符 —— 防路径文本自身 (含 `Stem.cs`) 污染 T1 主干匹配。
    """
    lines = text.splitlines()
    bids = _block_ids(lines)
    out = []
    in_fence = False
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        cites = list(CITE_RE.finditer(line))
        ticks = [(mm.start(), mm.end()) for mm in BACKTICK_RE.finditer(line)]
        for m in CONT_RE.finditer(line):
            nums = _cont_line_numbers(m.group(1))
            if not nums:
                continue
            prev_end = max([0] + [c.end() for c in cites if c.end() <= m.start()])
            win_lo = max(prev_end, m.start() - CONT_WINDOW)
            pre = line[win_lo:m.start()]
            # T1 只用**反引号包裹**且落在本续引前窗内的 `Stem.Member`
            stems = []
            for mm in STEM_MEMBER_RE.finditer(pre):
                gs = win_lo + mm.start(1)
                ge = win_lo + mm.end(0)
                if any(ts <= gs and ge <= te for (ts, te) in ticks):
                    stems.append(mm.group(1))
            win = (line[max(prev_end, m.start() - RETIRED_WINDOW):m.start()]
                   + line[m.end():min(len(line), m.end() + RETIRED_WINDOW)])
            out.append({
                "doc": doc_rel, "doc_line": lineno, "raw": stripped[:160],
                "cont_lines": nums, "cont_first": nums[0], "cont_last": nums[-1],
                "pos_start": m.start(), "pos_end": m.end(),
                "prev_cite_end": prev_end, "pre_window": pre, "stems": stems,
                "block_id": bids[lineno - 1], "in_code_fence": in_fence,
                "retire_marker": bool(RETIRE_RE.search(win)),
            })
    return out


def judge_continuation(repo: Repo, c: dict, idx: dict):
    """续引归属四级 (T1 stem_symbol > T2 same_line_prev > T3 block_unique_prev > T4 弃权)。

    归属纪律 = R418「精确名 → 唯一候选 → n/a」的续引版: **多候选一律弃权**, 绝不任取。
    """
    rec = dict(c)
    rec.update({"anchor": None, "anchor_tier": None, "resolved": None,
                "file_lines": None, "input_sha": None, "waive_reason": None,
                "verdict": None})
    if c["in_code_fence"]:
        rec["anchor_tier"], rec["verdict"] = "skipped", "skipped_fence"
        return rec
    same_line = [x for x in idx["by_line"].get((c["doc"], c["doc_line"]), [])
                 if x["pos_start"] < c["pos_start"]]
    # ---- T1: `Stem.Member` 主干唯一映射到树内文件 (位置无关, 最强)
    uniq, amb = set(), set()
    for s in c["stems"]:
        cands = repo.stem_index().get(s, [])
        if len(cands) == 1:
            uniq.add(cands[0])
        elif len(cands) > 1:
            amb.add(s)
    if len(uniq) == 1 and not amb:
        rec["anchor"], rec["anchor_tier"] = next(iter(uniq)), "stem_symbol"
    elif len(uniq) > 1 or (uniq and amb):
        rec["anchor_tier"] = "waived"
        rec["waive_reason"] = "cont_stem_ambiguous"
    # ---- T2: 同行最近前引
    if rec["anchor"] is None and rec["anchor_tier"] is None and same_line:
        rec["anchor"], rec["anchor_tier"] = same_line[-1]["path"], "same_line_prev"
    # ---- T3: 块内前序引用路径集合唯一
    if rec["anchor"] is None and rec["anchor_tier"] is None:
        prior = [x["path"] for x in idx["by_block"].get((c["doc"], c["block_id"]), [])
                 if (x["doc_line"], x["pos_start"]) < (c["doc_line"], c["pos_start"])]
        distinct = sorted(set(prior))
        if len(distinct) == 1:
            rec["anchor"], rec["anchor_tier"] = distinct[0], "block_unique_prev"
        else:
            rec["anchor_tier"] = "waived"
            rec["waive_reason"] = ("continuation_unclaimed" if not distinct
                                   else "cont_block_ambiguous")
    # ---- 事实判定: 锚点路径存在 + 行号在范围内 (符号仍归锚点引用, 不重复判)
    if rec["anchor"] is not None:
        mode, info = resolve_ref(repo, rec["anchor"])
        if mode == "waived":
            rec["verdict"], rec["waive_reason"] = "waived", "cont_anchor_" + info
        elif mode == "absent":
            cands = [x for x in repo.basename_index().get(Path(info).name, []) if repo._rel_ok(x)]
            if cands:
                rec["verdict"], rec["relocated_to"] = "relocated", cands
            elif c["retire_marker"]:
                rec["verdict"] = "retired"
            else:
                rec["verdict"], rec["resolved"] = "stale_path", info
        else:
            text, sha = repo.read(info)
            if text is None:
                rec["verdict"], rec["waive_reason"] = "waived", "cont_anchor_unreadable"
            else:
                n = len(text.splitlines())
                rec["resolved"], rec["file_lines"], rec["input_sha"] = info, n, sha
                rec["verdict"] = ("stale_lines" if any(x > n for x in c["cont_lines"]) else "ok")
    if rec["verdict"] == "stale_path" and rec["anchor"]:
        # 留痕继承: 续引与其**同行**某条带退役标记的引用指向**同一路径** ⇒ 该路径的退役登记已覆盖此续引。
        # 绑「锚点路径相同」(不绑词面位置, 也不跨行) —— 反向控制: 同行异文件带标记不继承 (selftest C11)。
        for x in idx["by_line"].get((c["doc"], c["doc_line"]), []):
            if x.get("retire_marker") and x["path"] == rec["anchor"]:
                rec["verdict"], rec["retire_marker_inherited"] = "retired", True
                break
    if rec["verdict"] is None:
        rec["verdict"] = "waived"
    return rec


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


# ---------------------------------------------------------------- 符号存在性阶梯 (v2.4.0)
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
DECL_TYPE_TMPL = r'\b(?:class|interface|record|struct|enum|delegate)\s+%s\b'
# `new Foo(` 是**实例化**不是声明 ⇒ new 不入修饰符表 (误列会把 `new X(` 判成 declared_member)
DECL_MEMBER_PREFIX = (r'(?:public|private|protected|internal|static|virtual|override|async|sealed|'
                      r'partial|readonly|extern|unsafe|abstract|const|event|required|'
                      r'void|bool|int|long|double|string|object|Task|ValueTask|byte|char|float|decimal)')


def _blank(seg: str) -> str:
    """等长空白替换 (换行保留) ⇒ 剥离后行号/列偏移不变。"""
    return "".join("\n" if ch == "\n" else " " for ch in seg)


def strip_noncode(text: str, line_comment: str = "//") -> str:
    """剥离注释与字符串/字符字面量 (词法级状态机, 非 AST), **逐行保长度**。

    line_comment="//" (C 族) 时块注释为 /* */; "#" (脚本族) 时块注释为三引号。
    诚实边界: 撇号出现在非字面量语境 (英文缩写等) 会吞到下一个撇号——只影响本平行轴,
    主 verdict 完全不受影响。
    """
    blocks = (('"""', '"""'), (", ")) if line_comment == "#" else (("/*", "*/"),)
    out, i, n = [], 0, len(text)
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if (line_comment == "#" and ch == "#") or (line_comment == "//" and ch == "/" and nxt == "/"):
            j = text.find("\n", i)
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
                if j + 1 < n and text[j] == "\\":
                    j += 2
                    continue
                if text[j] == ch:
                    j += 1
                    break
                if text[j] == "\n":
                    break
                j += 1
            out.append(_blank(text[i:j]))
            i = j
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def symbol_face(sym: str, code_text: str, full_text: str) -> str:
    """单个符号在**该文件**里的存在形态 (五级之一)。输入: 代码面文本 + 全文。

    防御守卫 (v2.4.1): code_text 为 None (文件不可读/类型不可剥离) ⇒ 弃权 n/a_kind,
    而不是抛 TypeError —— 测量层必须**出声地弃权**, 不得把"测不到"表现成崩溃或静默命中。
    """
    if code_text is None:
        return FACE_NA
    esc = re.escape(sym)
    if re.search(DECL_TYPE_TMPL % esc, code_text):
        return "declared_type"
    if re.search(DECL_MEMBER_PREFIX + r'\b[^\n;{}]{0,90}?\b' + esc + r'\s*[\(<{]', code_text):
        return "declared_member"
    if re.search(r'\b' + esc + r'\b', code_text):
        return "code_mention"
    if re.search(r'\b' + esc + r'\b', full_text):
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


# ---------------------------------------------------------------- 引用图边强轴 (v2.5.0)
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
                    rec["relocated_symbol_faces"] = faces_for(repo, cands[0], text, c["symbols"])
            return rec
        if c.get("retire_marker"):
            # R409 同族: 显式登记退役的引用是合法留痕, 与"未登记的死引用"分开计。
            #   反向控制: 无标记的死引用仍判 stale_path; 路径**存在**时标记不生效 (绑误用不绑词面)。
            rec["verdict"] = "retired"
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
    # 平行轴 (v2.4.0): 只记录形态, **不参与** verdict 判定 ⇒ 与主判据解耦
    rec["symbol_faces"] = faces_for(repo, rel, text, c["symbols"])
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
    citations, conts = [], []
    for rel in sorted(set(doc_rels)):
        text, _ = repo.read(rel)
        if text is None:
            continue
        cites = extract_citations(rel, text)
        citations.extend(cites)
        conts.extend(extract_continuations(rel, text))
    judged = [judge_citation(repo, c) for c in citations]
    # 续引归属索引: 按 (文档, 行) 与 (文档, 块) 两套, 组内按 (行号, 位置) 排序
    idx = {"by_line": defaultdict(list), "by_block": defaultdict(list)}
    for c in citations:
        idx["by_line"][(c["doc"], c["doc_line"])].append(c)
        idx["by_block"][(c["doc"], c["block_id"])].append(c)
    for k in idx:
        for kk in list(idx[k]):
            idx[k][kk].sort(key=lambda x: (x["doc_line"], x["pos_start"]))
    judged_cont = [judge_continuation(repo, c, idx) for c in conts]
    cont_live = [c for c in judged_cont if not c["in_code_fence"]]
    cont_verdicts = Counter(c["verdict"] for c in cont_live)
    cont_tiers = Counter(c["anchor_tier"] for c in cont_live)
    cont_waive = Counter(c.get("waive_reason") for c in cont_live if c["verdict"] == "waived")
    live_code = [c for c in judged if c["kind"] == "code" and not c["in_code_fence"]]
    verdicts = Counter(c["verdict"] for c in live_code)
    waive = Counter(c.get("waive_reason") for c in live_code if c["verdict"] == "waived")

    # ---- v2.4.0 符号存在性阶梯聚合 (平行轴; 与 verdict_counts 分开计, 不互相解释)
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

    # ---- v2.5.0 边强轴 (平行轴): 逐条 live 代码引用打边强标签, 再聚合分布 + 弱边全量清单
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
        "continuations": judged_cont,
        "cont_verdict_counts": dict(cont_verdicts),
        "cont_tier_counts": dict(cont_tiers),
        "cont_waive_reasons": {str(k): v for k, v in cont_waive.items()},
        "n_continuations_live": len(cont_live),
        "symbol_face_rungs": dict(face_rungs),
        "symbol_face_candidates": face_candidates,
        "n_symbol_faces": sum(face_rungs.values()),
        "edge_strength_counts": dict(edge_counts),
        "edge_sublevel_counts": dict(edge_subs),
        "n_edges_strong_with_weak_symbols": mixed_weak_in_strong,
        "edge_weak_list": weak_edges,
        "edge_levels_nontrivial": edge_levels_nontrivial,
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


def run_selftest():
    """仪器自证: 每条判据必须两侧都有夹具 (必须绿 + 必须红), 夹具不读真实语料。

    覆盖: 单引用兼容 / 多引用归属不串台 / 死引用无标记仍红 / 死引用带标记入 retired /
          活引用带标记不豁免 / 标记越过窗口仍红 / 常量形态按码点自检 /
          v2.4.0 符号存在性阶梯五级两侧 + 注释/字符串内声明形态负控 + 细分不改判。
    """
    import tempfile
    checks = []

    def ck(name, got, want):
        checks.append({"check": name, "got": got, "want": want, "pass": got == want})

    ck("const_codepoints_0", [ord(ch) for ch in RETIRED_MARKERS[0]], [0x5DF2, 0x5220])
    ck("const_codepoints_2", [ord(ch) for ch in RETIRED_MARKERS[2]], [0x5DF2, 0x9000, 0x5F79])
    ck("const_window", RETIRED_WINDOW, 60)

    tmp = Path(tempfile.mkdtemp(prefix="docref-selftest-"))
    (tmp / "src/agent/x").mkdir(parents=True, exist_ok=True)
    # 夹具符号必须满足仪器自身的标识符启发式 (首字符后含大写 或 含下划线),
    # 否则符号根本不会被采 ⇒ 夹具判红而仪器无辜 (首版夹具即踩此坑, 见 checks_posthoc)。
    (tmp / "src/agent/x/Alpha.cs").write_text(
        "// CommentedThing 只出现在本注释里\n" + "class AlphaThing { void Run() {} }\n" * 40,
        encoding="utf-8")
    (tmp / "src/agent/x/Beta.cs").write_text(
        "// OnlyCommentThing 只出现在本注释里\n"
        + "class BetaThing { void Go() {} }\n" * 40
        + "public void DeltaThing() { }\n"
        + "void useIt() { OtherThing.Factory(); }\n",
        encoding="utf-8")
    mk = RETIRED_MARKERS[0]
    far = "x" * (RETIRED_WINDOW + 40)
    doc = ("# t\n"
           "- 单引用 真缺符号: `NopeThing` [src/agent/x/Alpha.cs:3]\n"
           "- 多引用 归属: `AlphaThing` [src/agent/x/Alpha.cs:3]\u3001`BetaThing` [src/agent/x/Beta.cs:3]\n"
           "- 单引用 命中: `AlphaThing` [src/agent/x/Alpha.cs:3]\n"
           "- 死引用 无标记: [src/agent/x/Gone.cs:3]\n"
           "- 死引用 带标记: [src/agent/x/Gone.cs:3]\u3010" + mk + " deadbee\u3011\n"
           "- 活引用 带标记: [src/agent/x/Alpha.cs:3]\u3010" + mk + " deadbee\u3011\n"
           "- 死引用 标记越窗: [src/agent/x/Gone.cs:3] " + far + "\u3010" + mk + " deadbee\u3011\n"
           "- 收尾反引号邻接: `AlphaThing`(`src/agent/x/Alpha.cs:3`, 1)\u3001"
           "`BetaThing`(`src/agent/x/Beta.cs:3`, 1)\n"
           # ---- 续引 [:NNN] 形态 (v2.3.0): T1/T2/T3/T4 各两侧
           "- 续引 T1 符号主干锚: `Alpha.Run` 见下 [:5]\n"
           "- 续引 T1 行号越界: `AlphaThing.Run` [src/agent/x/Alpha.cs:3] 与 [:9999]\n"
           "- 续引 T2 同行前引锚: [src/agent/x/Beta.cs:3] 与 [:2]\n"
           "- 续引 死文件无标记: `GoneThing.Run` [src/agent/x/Gone.cs:3] 与 [:2]\n"
           "- 续引 死文件带标记: `GoneThing.Run` [src/agent/x/Gone.cs:3] 与 [:2]\u3010" + mk + " deadbee\u3011\n"
           "\n"
           "- 续引 块内多锚 A: [src/agent/x/Alpha.cs:3]\n"
           "- 续引 块内多锚 B: [src/agent/x/Beta.cs:3]\n"
           "- 续引 T4 无同行前引且块内多锚: [:7]\n"
           "\n"
           "- 续引 块内唯一前锚: [src/agent/x/Beta.cs:3]\n"
           "- 续引 T3 承接上行: [:4]\n"
           "- 续引 形态负控(普通引用不得被续引正则吃掉): [src/agent/x/Alpha.cs:3]\n"
           "\n"
           "- 续引 T4b 块内零前锚: [:9]\n"
           "\n"
           "- 续引 留痕继承(同行同文件, 标记在本续引窗口外): [src/agent/x/Gone4.cs:3]\u3010" + mk + " deadbee\u3011"
           + "y" * (RETIRED_WINDOW + 10) + " 与 [:2]\n"
           "- 续引 留痕继承负控(同行带标记但**异路径**): [src/agent/x/Alpha.cs:3]\u3010" + mk + " deadbee\u3011"
           + "y" * (RETIRED_WINDOW + 10) + " [src/agent/x/Gone5.cs:3] 与 [:2]\n"
           # ---- 符号存在性阶梯 (v2.4.0): 四级端到端 + "细分不改判" 两侧
           "\n"
           "- 阶梯 declared_member: `DeltaThing` [src/agent/x/Beta.cs:3]\n"
           "- 阶梯 code_mention: `OtherThing` [src/agent/x/Beta.cs:3]\n"
           "- 阶梯 noncode_comment_only: `CommentedThing` [src/agent/x/Alpha.cs:3]\n"
           "- 阶梯 absent: `MissingThing` [src/agent/x/Beta.cs:3]\n"
           # ---- 边强轴 (v2.5.0): 单引用两符号 ⇒ 混边夹具 (强 declared_member + 弱 noncode_mention)
           "- 边强 混边(强+弱非码): `DeltaThing` 与 `OnlyCommentThing` [src/agent/x/Beta.cs:3]\n")
    ck("cont_const_codepoints", [ord(CONT_OPEN), ord(CONT_COLON), ord(CONT_CLOSE)],
       [0x5B, 0x3A, 0x5D])
    ck("cont_re_negative_on_plain_cite", CONT_RE.findall("[src/agent/x/Alpha.cs:3]"), [])
    ck("cont_re_positive_forms", CONT_RE.findall("a [:280-287] b [:100,106] c [:15]"),
       ["280-287", "100,106", "15"])
    ck("cont_expand_range", _cont_line_numbers("280-287")[:3], [280, 281, 282])
    ck("cont_expand_list", _cont_line_numbers("100,106,112"), [100, 106, 112])

    repo = Repo(tmp)
    cites = extract_citations("t.md", doc)
    idx = {"by_line": defaultdict(list), "by_block": defaultdict(list)}
    for c in cites:
        idx["by_line"][(c["doc"], c["doc_line"])].append(c)
        idx["by_block"][(c["doc"], c["block_id"])].append(c)
    for k in idx:
        for kk in list(idx[k]):
            idx[k][kk].sort(key=lambda x: (x["doc_line"], x["pos_start"]))
    judged = [judge_citation(repo, c) for c in cites]
    cj = [judge_continuation(repo, c, idx) for c in extract_continuations("t.md", doc)]
    cby = {}
    for j in cj:
        cby.setdefault(j["doc_line"], []).append(j)
    by_line = {}
    for j in judged:
        by_line.setdefault(j["doc_line"], []).append(j)

    ck("L2_single_cite_true_absent", [j["verdict"] for j in by_line[2]], ["symbol_absent"])
    ck("L3_multi_cite_no_cross_flag", [j["verdict"] for j in by_line[3]], ["ok", "ok"])
    ck("L3_attr_mode", [j["symbol_attr"] for j in by_line[3]], ["nearest_prev", "nearest_prev"])
    ck("L3_symbols_per_citation", [j["symbols"] for j in by_line[3]],
       [["AlphaThing"], ["BetaThing"]])
    ck("L4_single_cite_ok", [j["verdict"] for j in by_line[4]], ["ok"])
    ck("L5_dead_no_marker_stays_red", [j["verdict"] for j in by_line[5]], ["stale_path"])
    ck("L6_dead_marker_retired", [j["verdict"] for j in by_line[6]], ["retired"])
    ck("L7_live_path_marker_ignored", [j["verdict"] for j in by_line[7]], ["ok"])
    ck("L8_marker_beyond_window_stays_red", [j["verdict"] for j in by_line[8]], ["stale_path"])
    ck("L9_adjacent_closing_tick_no_swallow", [j["verdict"] for j in by_line[9]], ["ok", "ok"])
    ck("L9_symbols_survive_window_slice", [j["symbols"] for j in by_line[9]],
       [["AlphaThing"], ["BetaThing"]])
    # ---- 续引两侧样例 (v2.3.0)
    ck("C1_tier_stem_symbol", [j["anchor_tier"] for j in cby[10]], ["stem_symbol"])
    ck("C1_verdict_ok", [j["verdict"] for j in cby[10]], ["ok"])
    ck("C1_anchor", [j["resolved"] for j in cby[10]], ["src/agent/x/Alpha.cs"])
    ck("C2_out_of_range_red", [j["verdict"] for j in cby[11]], ["stale_lines"])
    ck("C3_tier_same_line", [j["anchor_tier"] for j in cby[12]], ["same_line_prev"])
    ck("C3_verdict_ok", [j["verdict"] for j in cby[12]], ["ok"])
    ck("C4_dead_anchor_no_marker_red", [j["verdict"] for j in cby[13]], ["stale_path"])
    ck("C5_dead_anchor_marker_retired", [j["verdict"] for j in cby[14]], ["retired"])
    ck("C6_tier_waived_multi_anchor", [j["anchor_tier"] for j in cby[18]], ["waived"])
    ck("C6_waive_reason_multi_anchor", [j["waive_reason"] for j in cby[18]],
       ["cont_block_ambiguous"])
    ck("C7_tier_block_unique", [j["anchor_tier"] for j in cby[21]], ["block_unique_prev"])
    ck("C7_verdict_ok", [j["verdict"] for j in cby[21]], ["ok"])
    ck("C8_plain_cite_not_counted_as_cont", [len(cby.get(22, []))], [0])
    ck("C9_zero_prior_anchor_waived", [j["anchor_tier"] for j in cby[24]], ["waived"])
    ck("C9_waive_reason_unclaimed", [j["waive_reason"] for j in cby[24]],
       ["continuation_unclaimed"])
    ck("C10_marker_inherited_same_path", [j["verdict"] for j in cby[26]], ["retired"])
    ck("C10_inherited_flag", [j.get("retire_marker_inherited") for j in cby[26]], [True])
    ck("C11_no_inherit_on_other_path", [j["verdict"] for j in cby[27]], ["stale_path"])
    # ---- v2.4.0 符号存在性阶梯: 五级常量两侧 + 剥离保行 + 注释/字符串内「声明形态」负控
    cfg = ("class GammaThing { }\n"
           "public void DeltaThing() { }\n"
           "var t = OtherThing.Factory();\n"
           "// EpsilonThing only in comment\n"
           'var s = "ZetaThing";\n'
           "var u = new NewThing();\n")
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
    cmt = "// class CommentedThing { }\n"            # 负控: 注释里的**声明形态**不得算声明
    ck("F9_comment_decl_not_counted",
       symbol_face("CommentedThing", strip_noncode(cmt, "//"), cmt), "noncode_mention")
    strd = 'var q = "class StringThing { }";\n'      # 负控: 字符串里的声明形态同上
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
    # ---- 边强轴 (v2.5.0) 两侧夹具: 强 / 弱(码面) / 弱(非码面) / 断 / 弃权 + 混边可见 + 不改判负控
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
    ok = all(c["pass"] for c in checks)
    print(json.dumps({"selftest": "probe_doc_ref_integrity-v" + PROBE_VERSION, "all_pass": ok,
                      "n_checks": len(checks), "n_pass": sum(1 for c in checks if c["pass"]),
                      "checks": checks, "exit_code": 0 if ok else 2},
                     ensure_ascii=False, indent=2))
    return 0 if ok else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--out", default=None)
    ap.add_argument("--expect-mixed", action="store_true", help="自检用: 断言弃权闸判 exit 3")
    ap.add_argument("--selftest", action="store_true",
                    help="仪器自证: 归属/退役标记 双向控制夹具 (不读真实语料)")
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()

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

        # ---- G6 续引子探针非退化 (tier 分布 >= 2 类 ∨ 无量): 必须在 gate_dict 构造**之前**算
        g6 = bool(r1["n_continuations_live"] == 0 or len(r1["cont_tier_counts"]) >= 2)

        # ---- G7 阶梯非退化 (真语料上 >=2 级; 恒同一级 ⇒ 该轴无判别力 ⇒ 先查仪器再谈被测)
        rungs_real = sorted(k for k in r1["symbol_face_rungs"] if k != FACE_NA)
        g7 = bool(r1["n_symbol_faces"] == 0 or len(rungs_real) >= 2)
        _ec = r1["edge_strength_counts"]
        g8 = bool(r1["n_citations_code_live"] == 0 or
                  (sum(_ec.values()) == r1["n_citations_code_live"]
                   and r1["edge_levels_nontrivial"]))
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
            "G6_cont_nontrivial": g6,
            "G7_ladder_nontrivial": g7,
            "G7_symbol_face_rungs": r1["symbol_face_rungs"],
            "G7_symbol_face_rungs_real": rungs_real,
            "G7_n_symbol_faces": r1["n_symbol_faces"],
            "G8_edge_counts": r1["edge_strength_counts"],
            "G8_edge_counts_sum_eq_live": sum(r1["edge_strength_counts"].values()) == r1["n_citations_code_live"],
            "G8_edge_levels_nontrivial": r1["edge_levels_nontrivial"],
            "G6_cont_verdict_counts": r1["cont_verdict_counts"],
            "G6_cont_tier_counts": r1["cont_tier_counts"],
            "G6_cont_waive_reasons": r1["cont_waive_reasons"],
            "G6_n_continuations_live": r1["n_continuations_live"],
            "G5_family_docs": {k: v[:6] for k, v in fam_docs.items()},
        }
        all_pass = bool(g1 and g2 and g5 and g3 and g6 and g7 and g8)
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
            "probe": "exp1-q4-doc-ref-integrity-and-contract-surface",
            "probe_version": PROBE_VERSION,
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
            "symbol_face_rungs": r1["symbol_face_rungs"],
            "symbol_face_candidates": r1["symbol_face_candidates"],
            "n_symbol_faces": r1["n_symbol_faces"],
            "edge_strength_criteria": {
                "strong": "至少一枚被引符号在该文件里有声明 (declared_type/declared_member)",
                "weak": "无声明但至少一枚符号在该文件里出现 (*_mention)",
                "broken": "全部符号在该文件查无",
                "waived": "引用未解析/不可剥离/本身 waived ⇒ 弃权, 不进分母",
                "aggregation": "strongest-wins (混边内弱/断符号数单独计数, 不丢信息)"},
            "edge_strength_counts": r1["edge_strength_counts"],
            "edge_sublevel_counts": r1["edge_sublevel_counts"],
            "edge_weak_n": len(r1["edge_weak_list"]),
            "edge_weak_list": r1["edge_weak_list"],
            "n_edges_strong_with_weak_symbols": r1["n_edges_strong_with_weak_symbols"],
            "stale_like_n": stale_like,
            "stale_citations": stale,
            "relocated_n": len(relocated),
            "relocated_fact_verdicts": {str(k): v for k, v in relocated_fact.items()},
            "relocated_citations": relocated,
            "retired_n": r1["verdict_counts"].get("retired", 0),
            "retired_citations": [c for c in r1["citations"] if c["verdict"] == "retired"],
            "continuation_verdicts": r1["cont_verdict_counts"],
            "continuation_tiers": r1["cont_tier_counts"],
            "continuation_waive_reasons": r1["cont_waive_reasons"],
            "continuation_n_live": r1["n_continuations_live"],
            "continuation_citations": r1["continuations"],
            "contracts": contracts,
            "q2_decision_data": q2,
            "gates": gate_dict,
            "checks_posthoc": {
                "instrument_gap_v4": (
                    "v2.3.0 补**续引 `[:NNN]` 形态**建模 (v2.2.0 及以前: 续引既不进 CITE_RE 也无归属规则 "
                    "⇒ 本档 L80/L81/L82/L83/L85/L89/L90 的多条续引**从未被检查** = 保守漏检)。 "
                    "归属四级 T1~T4: T1 只用**反引号包裹**的 `Stem.Member`, 且**前窗截断到上一条完整引用之后** "
                    "(反例: 若把路径文本自身纳入前窗, `.../ContextAssembler.cs` 会被当成主干候选 "
                    "⇒ 与 `Workspace` 主干冲突 ⇒ 正确锚点被误判弃权); T3 的「块」= 连续非空行, 且**块内前序路径集合必须唯一**。 "
                    "续引判定只查路径+行号 (符号仍归锚点引用, 不重复判) ⇒ 该子探针不放大符号启发式的假阳性。"),
                "instrument_defect_v1": ("v1.0.0 把无目录裸文件名判为 stale_path (389 条, 其中多数实为"
                                         "'无法解析' 而非'文件已删') ⇒ v2.0.0 引入三级归属: 裸名唯一候选才解析, "
                                         "0/多候选一律弃权单列, 不判红 (照 R418 纪律)"),
                "fixture_defect_v1": (
                    "夹具缺陷(非仪器缺陷): selftest 首版夹具用了 `Nope`/`Alpha` 作符号, 但仪器采符号的启发式"
                    "要求**首字符之后含大写或含下划线** ⇒ 符号压根没被采 ⇒ 夹具判红而仪器无辜。"
                    "与「夹具派生字段单位错」同族: 夹具自身出错时, 全绿/全红都不承载任何关于被测对象的结论; "
                    "夹具符号必须先过与仪器同一套采集规则。"),
                "instrument_defect_v3": (
                    "v2.2.0 修两处**测量层**缺陷: (a) 符号归属原为**整行**——一行内多条引用时, "
                    "每条引用都被拿整行符号去验 ⇒ 多引用行产出成片假 symbol_absent "
                    "(实测本档 L62/L406 一行三接口互相串台); 改为逐引用就近窗口 (上一条引用结束→本条起点), "
                    "单引用行 = 整行 ⇒ 与旧版逐位兼容。(b) 原判据'路径必须存在'对**显式登记退役**的引用误杀 "
                    "(R409 同族: 标记出现≠误用) ⇒ 新增 retired 判定: 引用两侧 60 字符内出现退役标记且不得越过相邻引用, "
                    "**且仅当路径确实不存在**才生效; 无标记的死引用仍判 stale_path (反向控制)。"),
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
                "符号命中检查 (主 verdict) 是**全文匹配**启发式 (非 AST): 同名出现在注释/字符串/历史示例里也算命中 ⇒ symbol_absent 只作候选, 不作对外结论",
                "v2.4.0 新增**平行轴**「符号存在性阶梯」(declared_type > declared_member > code_mention > noncode_mention > absent): 词法级剥离注释/字符串, **非 AST** (AST 需语法库 ⇒ 与本探针纪律冲突, 候选#3 的 AST 级要求本轮降级为词法级并登记); declared_member 为启发式 (同句修饰符/返回类型), 裸 `Sym(` 只记 code_mention (宁漏勿错); 非 .cs/.py 记 n/a_kind 弃权 ⇒ 该轴**不改判**任何 citation 的 verdict",
                "引用抽取跳过 ``` 代码围栏内的行 (命令输出/样例不算引用事实); 该规则影响计数, 已在 in_code_fence 字段可见",
                "文档语料 = docs/**/*.md + 根 *.md; 不含 .txt/.json 与 website/ 站点副本",
                "契约盘点按正则扫 interface 声明与 'class X : ... IFoo' 形态: 泛型约束/多接口链/partial 可能漏计 (n_impls_prod 是下界)",
                "stale_lines 只用行号越界判定 (文件变短), 行号偏移但未越界不报 ⇒ 该口径会**低估**",
                "续引 [:NNN] 归属只有 T1/T2/T3 三级有证据时才认; 归属不成立一律弃权单列 (绝不任取候选) ⇒ 覆盖面受文档写法限制, 未认领的续引不判红",
                "续引判定不查符号: 续引所在行的符号归其锚点引用 ⇒ 续引读数与符号启发式读数**分开计**, 不可互相解释",
                "续引留痕**继承**只在「同行 ∧ 锚点路径完全相同」时生效 (绑路径不绑词面位置); 跨行/异路径不继承",
                "T2/T3 的锚点是**位置**证据: 句子的语义所指与最近前引不一致时 (本档 L68 实例: 括号内说明指向同一路径的 DI 工厂) 会错锚 ⇒ 该类读数须人工复核, 修法是**把路径写显式**而不是改判据",
                "verdict 分四桶且互斥: ok / stale_path(basename 全树 0 候选=真删) / relocated(路径失效但同名文件在别处) / waived(不可解析, 弃权)",
                "relocated 仅在同名唯一候选时才给 relocated_fact_verdict (行号/符号按候选文件核对); 多候选只记 relocated_to 列表, 不做事实判定",
                "v2.5.0 边强轴是**词法级**分类 (非 AST): noncode_mention 只说明该符号在此文件不是代码事实的声明/使用面 (引用可能指向注释/字符串/历史示例里的同名串), **不说明引用错误** —— 弱边 != 缺陷, 需人工全量复核",
                "边强聚合口径 = 最强胜 (单枚声明即强边): 强边里混弱符号的情形由 n_edges_strong_with_weak_symbols + 逐条 edge_weak_symbols 单独可见, 不因聚合而消失",
                "边强只看**被引文件内部**的符号形态, 不做跨文件符号解析 (符号声明在他处的情形由 weak_edge_inspect.py 的 declared_elsewhere 旁证另计)",
                "本探针只读文件, 不改产品源码, 不跑 dotnet, 不占轮号",
            ],
        }
        if args.out:
            Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            with Path(args.out).with_name("continuations.jsonl").open("w", encoding="utf-8") as fh:
                for c in r1["continuations"]:
                    fh.write(json.dumps({k: c[k] for k in
                                         ("doc", "doc_line", "cont_lines", "anchor", "anchor_tier",
                                          "verdict", "resolved", "waive_reason", "file_lines",
                                          "input_sha", "in_code_fence", "retire_marker", "stems",
                                          "raw") if k in c}, ensure_ascii=False) + "\n")
            with Path(args.out).with_name("citations.jsonl").open("w", encoding="utf-8") as fh:
                for c in r1["citations"]:
                    fh.write(json.dumps({k: c[k] for k in
                                         ("doc", "doc_line", "path", "kind", "line_start", "line_end",
                                          "verdict", "in_code_fence", "symbols", "symbol_attr",
                                          "retire_marker", "symbols_absent",
                                          "resolve_mode", "resolved", "waive_reason",
                                          "file_lines", "input_sha",
                                          "relocated_to", "relocated_fact_verdict",
                                          "edge_strength", "edge_sublevel",
                                          "edge_weak_symbols", "edge_broken_symbols") if k in c},
                                        ensure_ascii=False) + "\n")
        print(json.dumps({
            "n_docs": r1["n_docs"],
            "citation_verdicts": r1["verdict_counts"],
            "waive_reasons": r1["waive_reasons"],
            "relocated_n": len(relocated),
            "relocated_fact_verdicts": {str(k): v for k, v in relocated_fact.items()},
            "continuation_n_live": r1["n_continuations_live"],
            "continuation_verdicts": r1["cont_verdict_counts"],
            "continuation_tiers": r1["cont_tier_counts"],
            "continuation_waive_reasons": r1["cont_waive_reasons"],
            "n_inputs_fingerprinted": r1["n_inputs_fingerprinted"],
            "edge_strength_counts": r1["edge_strength_counts"],
            "edge_sublevel_counts": r1["edge_sublevel_counts"],
            "edge_weak_n": len(r1["edge_weak_list"]),
            "n_edges_strong_with_weak_symbols": r1["n_edges_strong_with_weak_symbols"],
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
