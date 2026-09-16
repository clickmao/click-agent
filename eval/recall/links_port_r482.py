#!/usr/bin/env python3
"""R481-F: 源码派生的链接面端口 (产品规则移植) + 语料重测。

承 R481-A (Python 代理面基线) 与 R481-C (解析基准改写)。本器具的目的只有一个:
把产品**实际**的地址接受与解析规则搬到一个可批量跑的端口上, 并让「端口抄得对不对」
本身可机检 —— 旧端口 (links_probe.py) 手写规则 (后缀白名单 / 裸名计入相对档 /
lstrip 兜底解析), 与产品规则已静默漂移, 故其读数不可用于新基准的 G3。

纪律:
 - 规则常量**由产品源码正则派生**; 任一派生失败 => rc=3 弃权 (fail-closed), 不入红绿。
 - 期望值取**产品自身断言**的用例 (测试源码里派生的输入/引用方/期望值), 端口必须逐条一致。
 - 判别力自证: 4 条规则变异必须各被至少一个探针抓到 (两侧都动: 端口注入样本 + 派生常量)。
 - 语言无关: 端口不做任何后缀判断 (后缀白名单只留在旧端口作对照臂)。
 - 确定性: 输出不含时间/路径/耗时; 同语料两次运行逐字节相同。

用法:
  python3 eval/recall/links_port_r482.py --selftest            # 派生 + 差分 + 变异负控
  python3 eval/recall/links_port_r482.py --out <path>          # 语料重测 (默认 eval/recall/r481b/port-corpus.json)
退出码: 0 = 测量完成 (判据达标/越线都算完成) / 2 = 断言失败 / 3 = 弃权 (测量或环境失败)
"""
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RULE_SRC = os.path.join(ROOT, "src", "agent.recall", "RecallLinks.cs")
TEST_SRC = os.path.join(ROOT, "src", "agent.recall.tests", "RecallModuleTests.cs")
OLD_PORT = os.path.join(HERE, "links_probe.py")
OUT_DIR = os.path.join(HERE, "r481b")

# 语料收集口径沿用 R481-A (同一 SKIP / 大小上限 / 文本探测); 唯一变量 = 抽取规则。
SKIP = {".git", "bin", "obj", "node_modules", ".vs", "dist", "artifacts", "__pycache__"}
MAX_BYTES = 1_000_000
# 测量产物必须落在语料之外 (frozen-corpus): 器具自己的产出目录不进语料。
SELF_OUT = {os.path.relpath(OUT_DIR, ROOT).replace(os.sep, "/")}
SELF_SRC = {os.path.relpath(os.path.abspath(__file__), ROOT).replace(os.sep, "/")}

FIXTURE_METHOD = "Relative_References_Resolve_Against_Referrer_Directory"
REGISTERED_R481A = {"files": 6647, "refs": 20155, "resolved_rate": 0.8508, "dangling_rate": 0.1492,
                    "rel_ok_rate": 0.2718}


class DeriveError(Exception):
    pass


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _unescape_cs(lit):
    """把 C# 字符串字面量 (含引号) 解成 python str。"""
    body = lit[1:-1]
    out, i = [], 0
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            n = body[i + 1]
            mapping = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "'": "'"}
            if n == "u" and i + 5 < len(body) + 1:
                out.append(chr(int(body[i + 2:i + 6], 16)))
                i += 6
                continue
            if n in mapping:
                out.append(mapping[n])
                i += 2
                continue
        out.append(c)
        i += 1
    return "".join(out)


def derive():
    """从产品源码派生规则常量。任何一项拿不到 => DeriveError (fail-closed)。"""
    src = open(RULE_SRC, encoding="utf-8").read()

    def grab(pattern, name, group=1, flags=0):
        m = re.search(pattern, src, flags)
        if not m:
            raise DeriveError(f"派生失败: {name}")
        return m.group(group)

    const = {}
    for field, default in (("MarkdownTargets", "true"), ("BareUrls", "true"), ("RelativeAddresses", "true")):
        v = grab(rf"{field}\s*\{{\s*get;\s*init;\s*\}}\s*=\s*(true|false)\s*;", f"{field} 开关")
        const[field] = (v == "true")
    const["MaxLinksPerDoc"] = int(grab(r"MaxLinksPerDoc\s*\{[^}]*\}\s*=\s*(\d+)\s*;", "MaxLinksPerDoc"))
    const["MaxLinkChars"] = int(grab(r"MaxLinkChars\s*\{[^}]*\}\s*=\s*(\d+)\s*;", "MaxLinkChars"))
    schemes_raw = grab(r"Schemes\s*\{[^}]*\}\s*=\s*\{([^}]*)\}", "Schemes 列表")
    const["Schemes"] = [_unescape_cs(s) for s in re.findall(r'"(?:[^"\\]|\\.)*"', schemes_raw)]
    if not const["Schemes"]:
        raise DeriveError("派生失败: Schemes 为空")

    # C# char 字面量 (含引号) => 单字符; 形状不合即 fail-closed (防「抓错 span 得到空串」这类静默失效)
    cs_char_lit = r"('(?:\\.|[^'\\])*')"

    def cs_literals(text):
        vals = [_unescape_cs(s) for s in re.findall(r"c == " + cs_char_lit, text)]
        if not vals:
            raise DeriveError("派生失败: 字面量集合为空")
        bad = [v for v in vals if len(v) != 1]
        if bad:
            raise DeriveError(f"派生失败: 字面量形状非法 (应为单字符): {bad}")
        return vals

    addr_body = grab(r"IsAddressChar\(char c\)\s*=(.*?);\n", "IsAddressChar 表达式", flags=re.S)
    const["AddressCharLiterals"] = cs_literals(addr_body)
    if not re.search(r"char\.IsLetterOrDigit\(", addr_body):
        raise DeriveError("派生失败: IsAddressChar 未含 IsLetterOrDigit (字母数字面缺失)")
    for need in ("/", "."):
        if need not in const["AddressCharLiterals"]:
            raise DeriveError(f"派生失败: IsAddressChar 字面量缺 '{need}' (端口会静默丢地址串)")

    trim_body = grab(r"TrimTrailingPunctuation\(string s\)(.*?)\n    \}", "TrimTrailingPunctuation 体", flags=re.S)
    const["TrailingPunctuation"] = cs_literals(trim_body)
    if ")" not in const["TrailingPunctuation"]:
        raise DeriveError("派生失败: 尾部标点集合缺 ')'")

    const["MinRunLen"] = int(grab(r"if \(len < (\d+) \|\| len > options\.MaxLinkChars\)", "相对地址最短长度"))
    const["RelativePrefixes"] = [_unescape_cs(s) for s in
                                 re.findall(r"candidate\.StartsWith\(" + r'("(?:\\.|[^"\\])*")' + r", StringComparison\.Ordinal\)", src)]
    if set(const["RelativePrefixes"]) != {"./", "../"} or len(const["RelativePrefixes"]) != 2:
        raise DeriveError(f"派生失败: 相对前缀应为 ['./','../'], 实得 {const['RelativePrefixes']}")
    if not re.search(r"slice\.IndexOf\('/'\) < 0", src):
        raise DeriveError("派生失败: 相对档未含 '/' 结构性要求")
    if not re.search(r"normalized\.Contains\('/'\)\s*&&\s*!normalized\.Any\(char\.IsWhiteSpace\)", src):
        raise DeriveError("派生失败: Accept 未含 '/' 且无空白 的结构性判据")
    if not re.search(r"if \(stack\.Count == 0\)\s*\{\s*return candidate;", src):
        raise DeriveError("派生失败: 越根 fail-closed 分支缺失 (原值返回)")
    if "越根" not in src:
        raise DeriveError("派生失败: 越根 fail-closed 语义注释缺失 (源码形状变化, 需人工复核)")
    if not re.search(r"AddIfNew\(sink, seen, md, options\)", src) or not re.search(r"sink\.Count < options\.MaxLinksPerDoc", src):
        raise DeriveError("派生失败: 去重/上限接线缺失")

    const["_rule_sha256"] = hashlib.sha256(src.encode("utf-8")).hexdigest()
    return const


def derive_fixtures():
    """从产品测试源码派生出 (输入, 引用方, 期望计数, 期望值集合)。"""
    src = open(TEST_SRC, encoding="utf-8").read()
    m = re.search(rf"public void {FIXTURE_METHOD}\(\)(.*?)\n    \[Fact\]", src, re.S)
    if not m:
        raise DeriveError(f"派生失败: 找不到用例 {FIXTURE_METHOD}")
    body = m.group(1)
    call_pat = (r'RecallLinkExtractor\.Extract\(\s*("(?:[^"\\]|\\.)*")\.AsSpan\(\),\s*(\w+),\s*(\w+),\s*("(?:[^"\\]|\\.)*")\)')
    calls = re.findall(call_pat, body)
    if len(calls) != 2:
        raise DeriveError(f"派生失败: 期望 2 处 Extract 调用, 实得 {len(calls)}")
    count_var = re.search(r"int\s+(\w+)\s*=\s*RecallLinkExtractor\.Extract", body)
    if not count_var:
        raise DeriveError("派生失败: 找不到计数变量赋值")
    counts = re.findall(rf"Assert\.Equal\((\d+),\s*{count_var.group(1)}\);", body)
    if len(counts) != 1:
        raise DeriveError(f"派生失败: 计数断言应 1 条, 实得 {len(counts)}")
    expects = re.findall(r'Assert\.Contains\(("(?:[^"\\]|\\.)*"),\s*(\w+)\);', body)
    if not expects:
        raise DeriveError("派生失败: 无期望值断言")
    fixtures = []
    for idx, (text_lit, _opt, sink_var, ref_lit) in enumerate(calls):
        exp = [_unescape_cs(v) for v, var in expects if var == sink_var]
        if idx == 0:
            exp_count, need_count = int(counts[0]), True
        else:
            exp_count, need_count = len(exp), False
        if not exp:
            raise DeriveError(f"派生失败: 第 {idx+1} 处调用无期望值")
        fixtures.append({"text": _unescape_cs(text_lit), "referrer": _unescape_cs(ref_lit),
                         "sink_var": sink_var, "expect": exp, "expect_count": exp_count,
                         "count_asserted": need_count})
    return fixtures


# ---------------------------------------------------------------- 端口 (规则来自 derive())

try:
    C = derive()
except DeriveError as _e:  # 派生失败必须在入口就 fail-closed (rc=3), 不得退化成 traceback (rc=1)
    print(json.dumps({"status": "abstain", "reason": str(_e)}, ensure_ascii=False))
    print("PORT_EXIT=3")
    sys.exit(3)
ADDR_LITERALS = set(C["AddressCharLiterals"]) | {"%"}
TRAILING = set(C["TrailingPunctuation"])
SCHEMES = C["Schemes"]
MAXLINK = C["MaxLinkChars"]
MAXDOC = C["MaxLinksPerDoc"]
MIN_RUN = C["MinRunLen"]
REL_PREFIXES = tuple(C["RelativePrefixes"])


def _is_addr(c):
    # 边界: python str.isalnum 与产品 char.IsLetterOrDigit 的 Unicode 类覆盖不完全一致 (已在输出声明)
    return c.isalnum() or c in ADDR_LITERALS


def _trim_trailing(s, mutate=None):
    if mutate == "no_trailing_trim":
        return s
    end = len(s)
    while end > 0 and s[end - 1] in TRAILING:
        end -= 1
    return s[:end]


def _is_scheme_start(text, i):
    for s in SCHEMES:
        if text.startswith(s, i):
            return True
    return False


def resolve_referrer_relative(candidate, referrer, mutate=None):
    if mutate == "no_rewrite":
        return candidate
    if not referrer:
        return candidate
    if not candidate.startswith(REL_PREFIXES):
        return candidate
    slash = referrer.rfind("/")
    d = referrer[:slash] if slash > 0 else ""
    stack = [seg for seg in d.split("/") if seg and seg != "."]
    for seg in candidate.split("/"):
        if not seg or seg == ".":
            continue
        if seg == "..":
            if not stack:
                if mutate == "clamp_root":
                    return "e.md"
                return candidate  # 越根: 原值返回 (fail-closed)
            stack.pop()
            continue
        stack.append(seg)
    return candidate if not stack else "/".join(stack)


def accept(candidate, referrer, mutate=None):
    n = candidate.strip()
    if not n or len(n) > MAXLINK:
        return None
    for s in SCHEMES:
        if n.lower().startswith(s.lower()):
            return n
    has_slash = "/" in n
    if mutate == "allow_bare":
        has_slash = True
    if has_slash and not any(ch.isspace() for ch in n):
        return resolve_referrer_relative(n, referrer, mutate)
    return None


def _addr_class_regex():
    extra = "".join(re.escape(c) for c in sorted(ADDR_LITERALS))
    return re.compile(r"[\w" + extra + r"]+")


def extract(text, referrer=None, mutate=None):
    """产品 Extract 的端口实现。返回 [(最终值, 原始候选)] 保序去重, 上限 MAXDOC。"""
    sink, seen, out = [], set(), []
    if mutate is not None and mutate.startswith("min_len"):
        min_run = int(mutate.split("_")[-1])
    else:
        min_run = MIN_RUN

    def add(value, raw, origin):
        if len(sink) >= MAXDOC:
            return
        if mutate == "no_dedup" or value not in seen:
            seen.add(value)
            sink.append(value)
            out.append((value, raw, origin))

    if C["MarkdownTargets"]:
        for m in re.finditer(r"\]\(", text):
            j, buf = m.end(), []
            while j < len(text) and len(buf) < MAXLINK:
                if text[j] == ")":
                    break
                buf.append(text[j])
                j += 1
            else:
                continue
            if not buf:
                continue
            cand = "".join(buf)
            v = accept(cand, referrer, mutate)
            if v is not None:
                add(v, cand, "markdown")

    if C["BareUrls"]:
        starts = []
        for s in SCHEMES:
            p = text.find(s)
            while p >= 0:
                starts.append(p)
                p = text.find(s, p + 1)
        for i in sorted(set(starts)):
            j, buf = i, []
            while j < len(text) and len(buf) < MAXLINK and (_is_addr(text[j]) or text[j] == "%"):
                buf.append(text[j])
                j += 1
            if not buf:
                continue
            cand = _trim_trailing("".join(buf), mutate)
            v = accept(cand, referrer, mutate)
            if v is not None:
                add(v, cand, "url")

    if C["RelativeAddresses"]:
        for m in _addr_class_regex().finditer(text):
            run = m.group(0)
            if len(run) < min_run or len(run) > MAXLINK:
                continue
            if "/" not in run and mutate != "allow_bare":
                continue
            cand = _trim_trailing(run, mutate)
            v = accept(cand, referrer, mutate)
            if v is not None:
                add(v, cand, "rel")
    return out


# ---------------------------------------------------------------- 语料

def is_text(b):
    if not b or b"\x00" in b[:8192]:
        return False
    sample = b[:4096]
    ctrl = sum(1 for c in sample if c < 9 or (13 < c < 32))
    return ctrl <= max(1, len(sample) // 100)


def collect():
    out = []
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = sorted(d for d in dns if d not in SKIP and not d.startswith(".git"))
        for fn in sorted(fns):
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
            if rel in SELF_OUT or rel in SELF_SRC or rel.startswith(tuple(x + "/" for x in SELF_OUT)):
                continue
            if os.path.dirname(rel) and os.path.basename(rel) == ".DS_Store":
                continue
            try:
                if os.path.getsize(p) > MAX_BYTES:
                    continue
                with open(p, "rb") as f:
                    b = f.read()
            except OSError:
                continue
            if not is_text(b):
                continue
            out.append((rel, b.decode("utf-8", "replace")))
    return out


def measure():
    files = collect()
    if not files:
        raise DeriveError("语料根为空 (环境失败)")
    st = dict(files=len(files), refs=0, external=0, local=0, resolved=0, dangling=0,
              explicit_rel=0, rewrite_ok=0, rewrite_failclosed=0, escaped_root=0,
              absolute_path_like=0, escape_kept_raw=0,
              base_dir_fallback_ok=0, zero_ref_files=0)
    by_origin = {k: dict(refs=0, resolved=0, dangling=0, external=0) for k in ("markdown", "url", "rel")}
    per_file, dangling_samples, fallback_samples = [], [], []
    corpus_h = hashlib.sha256()
    for rel, txt in files:
        corpus_h.update(f"{rel}:{len(txt.encode('utf-8'))}\n".encode("utf-8"))
        items = extract(txt, referrer=rel)
        per_file.append(len(items))
        if not items:
            st["zero_ref_files"] += 1
        base = os.path.dirname(rel)
        for value, raw, origin in items:
            st["refs"] += 1
            by_origin[origin]["refs"] += 1
            if any(value.lower().startswith(s.lower()) for s in SCHEMES):
                st["external"] += 1
                by_origin[origin]["external"] += 1
                continue
            st["local"] += 1
            explicit = raw.startswith(REL_PREFIXES)
            if explicit:
                st["explicit_rel"] += 1
                if value == raw:
                    st["rewrite_failclosed"] += 1
            full = os.path.normpath(os.path.join(ROOT, value))
            inside = full == ROOT or full.startswith(ROOT + os.sep)
            if not inside:
                st["escaped_root"] += 1
                if value.startswith("/"):
                    st["absolute_path_like"] += 1
                else:
                    st["escape_kept_raw"] += 1
                st["dangling"] += 1
                by_origin[origin]["dangling"] += 1
                if len(dangling_samples) < 5:
                    dangling_samples.append(f"{rel} -> {value} (escaped)")
                continue
            if os.path.isfile(full):
                st["resolved"] += 1
                by_origin[origin]["resolved"] += 1
                if explicit and value != raw:
                    st["rewrite_ok"] += 1
                continue
            st["dangling"] += 1
            by_origin[origin]["dangling"] += 1
            if len(dangling_samples) < 5:
                dangling_samples.append(f"{rel} -> {value}")
            if base and os.path.isfile(os.path.normpath(os.path.join(ROOT, base, value))):
                st["base_dir_fallback_ok"] += 1
                if len(fallback_samples) < 5:
                    fallback_samples.append(f"{rel} -> {value}")
    loc = max(1, st["local"])
    res_rate = st["resolved"] / loc
    dang_rate = st["dangling"] / loc
    ok_rate = st["rewrite_ok"] / max(1, st["explicit_rel"])
    per_file_sorted = sorted(per_file)
    n = len(per_file_sorted)
    p50 = per_file_sorted[n // 2] if n % 2 else (per_file_sorted[n // 2 - 1] + per_file_sorted[n // 2]) / 2
    out = {
        "instrument": {"path": os.path.relpath(__file__, ROOT), "port": "r482",
                       "rule_source": os.path.relpath(RULE_SRC, ROOT),
                       "rule_source_sha16": C["_rule_sha256"][:16],
                       "rule_source_sha256": C["_rule_sha256"],
                       "rule_source_clean": subprocess.run(
                           ["git", "-C", ROOT, "diff", "--quiet", "--", os.path.relpath(RULE_SRC, ROOT)],
                           capture_output=True).returncode == 0},
        "corpus": {"files": st["files"], "files_sha16": corpus_h.hexdigest()[:16],
                   "skip": sorted(SKIP), "self_out_excluded": sorted(SELF_OUT), "self_src_excluded": sorted(SELF_SRC),
                   "files_with_0_refs_rate": round(st["zero_ref_files"] / max(1, st["files"]), 4),
                   "per_file_p50_refs": p50,
                   "per_file_mean": round(sum(per_file) / max(1, len(per_file)), 2)},
        "readings": {"refs": st["refs"], "external_urls_unreported": st["external"], "local": st["local"],
                     "resolved": st["resolved"], "dangling": st["dangling"],
                     "resolved_rate": round(res_rate, 4), "dangling_rate": round(dang_rate, 4),
                     "explicit_rel": st["explicit_rel"], "rewrite_ok": st["rewrite_ok"],
                     "rewrite_ok_rate": round(ok_rate, 4),
                     "rewrite_failclosed_raw": st["rewrite_failclosed"],
                     "escaped_root": st["escaped_root"],
                     "absolute_path_like": st["absolute_path_like"],
                     "escape_kept_raw": st["escape_kept_raw"],
                     "base_dir_fallback_ok": st["base_dir_fallback_ok"]},
        "by_origin": {k: dict(v, resolved_rate=round(v["resolved"] / max(1, v["refs"] - v["external"]), 4))
                      for k, v in by_origin.items()},
        "samples": {"dangling": dangling_samples, "base_dir_fallback": fallback_samples},
        "judgment": {
            "G1": {"rule": "resolved_rate >= 0.90", "value": round(res_rate, 4),
                   "verdict": "达标" if res_rate >= 0.90 else "越线"},
            "G2": {"rule": "dangling_rate <= 0.10", "value": round(dang_rate, 4),
                   "verdict": "达标" if dang_rate <= 0.10 else "越线"},
            "G3": {"rule": "rewrite_ok_rate >= 0.85", "value": round(ok_rate, 4),
                   "verdict": "达标" if ok_rate >= 0.85 else "越线"},
            "G4": {"rule": "per_file_p50_refs >= 1", "value": p50,
                   "verdict": "达标" if p50 >= 1 else "越线"},
        },
        "port_boundaries": [
            "字母数字面用 python str.isalnum 近似 char.IsLetterOrDigit (Unicode 类覆盖不完全一致)",
            "空白判定用 str.isspace 近似 char.IsWhiteSpace",
            "scheme 前缀比较用 lower() 近似 OrdinalIgnoreCase",
            "CJK 属字母 => 无空格中文串会作为地址串参与相对档 (产品同此行为, 非端口偏差)",
        ],
    }
    return out


def run_old_arm():
    """逐字调用旧端口 (对照臂), 取旧口径读数。仅诊断, 不作判据。"""
    try:
        p = subprocess.run([sys.executable, OLD_PORT], cwd=ROOT, capture_output=True, text=True, timeout=1800)
    except Exception as e:  # noqa: BLE001
        return {"status": "unavailable", "error": type(e).__name__}
    if p.returncode != 0:
        return {"status": "failed", "rc": p.returncode, "tail": p.stderr[-300:]}
    try:
        d = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        return {"status": "unparsable", "tail": p.stdout[-300:]}
    diffs = {k: {"registered": v, "measured": d.get(k)} for k, v in REGISTERED_R481A.items()
             if d.get(k) != v}
    return {"status": "ok", "reading": {k: d.get(k) for k in list(REGISTERED_R481A) + ["root_fallback_ok"]},
            "vs_registered_r481a": {"match": not diffs, "deltas": diffs}}


# ---------------------------------------------------------------- 自检

def selftest():
    res = {"derivation": {}, "fixture_differential": {}, "mutation_controls": {}, "probe_samples": {}}
    res["derivation"] = {"ok": True, "constants": {k: v for k, v in C.items() if not k.startswith("_")},
                         "rule_source_sha16": C["_rule_sha256"][:16]}
    try:
        fixtures = derive_fixtures()
    except DeriveError as e:
        res["fixture_differential"] = {"ok": False, "error": str(e)}
        return res, 2

    ok = True
    det = []
    for f in fixtures:
        got = extract(f["text"], referrer=f["referrer"])
        vals = [v for v, _, _ in got]
        hit = len(vals) == f["expect_count"] and set(f["expect"]) == set(vals)
        ok = ok and hit
        det.append({"text": f["text"], "referrer": f["referrer"], "expected": f["expect"],
                    "expect_count": f["expect_count"], "got": vals, "ok": hit})
    res["fixture_differential"] = {"ok": ok, "cases": det}

    probes = [
        ("bare_name_rejected", "见 readme.md 说明", None, None),
        ("short_run_rejected", "x /a 结束", None, None),
        ("root_kept", "src/x.cs", "docs/plans/a.md", None),
        ("rewritten", "./c.md", "docs/plans/a.md", None),
        ("escape_failclosed", "../../../e.md", "a.md", None),
        ("trailing_punct_trimmed", "见 docs/x.md. 结束", None, None),
    ]
    sample_out = {}
    for name, text, ref, _ in probes:
        sample_out[name] = [v for v, _, _ in extract(text, referrer=ref)]
    res["probe_samples"] = sample_out
    n1 = sample_out["bare_name_rejected"] == [] and sample_out["short_run_rejected"] == []
    n2 = sample_out["escape_failclosed"] == ["../../../e.md"] and sample_out["root_kept"] == ["src/x.cs"]
    n3 = sample_out["rewritten"] == ["docs/plans/c.md"]
    n4 = sample_out["trailing_punct_trimmed"] == ["docs/x.md"]
    ok = ok and n1 and n2 and n3 and n4

    muts = {}
    for mut in ("no_rewrite", "clamp_root", "min_len_2", "allow_bare", "no_trailing_trim", "no_dedup"):
        caught = []
        for f in fixtures:
            vals = [v for v, _, _ in extract(f["text"], referrer=f["referrer"], mutate=mut)]
            if len(vals) != f["expect_count"] or set(f["expect"]) != set(vals):
                caught.append(f"{f['sink_var']}:fixture")
        for name, text, ref, _ in probes:
            vals = [v for v, _, _ in extract(text, referrer=ref, mutate=mut)]
            if vals != sample_out[name]:
                caught.append(name)
        muts[mut] = {"caught_by": caught, "ok": bool(caught)}
        ok = ok and bool(caught)
    res["mutation_controls"] = muts
    res["negative_controls"] = {"N1_bare_name_rejected": n1, "N2_escape_failclosed": n2,
                               "N3_mutations_caught": all(m["ok"] for m in muts.values())}
    return res, (0 if ok else 2)


def main(argv):
    out_path = os.path.join(OUT_DIR, "port-corpus.json")
    if "--out" in argv:
        out_path = argv[argv.index("--out") + 1]
    if "--selftest" in argv:
        res, rc = selftest()
        print(json.dumps(res, ensure_ascii=False, indent=2))
        print(f"SELFTEST_EXIT={rc}")
        return rc
    try:
        st, rc = selftest()
    except DeriveError as e:
        print(json.dumps({"status": "abstain", "reason": f"派生失败: {e}"}, ensure_ascii=False))
        print("PORT_EXIT=3")
        return 3
    if rc != 0:
        print(json.dumps({"status": "abstain", "reason": "器具自检未过 (派生/差分/变异)", "selftest": st},
                         ensure_ascii=False))
        print("PORT_EXIT=3")
        return 3
    try:
        m = measure()
    except DeriveError as e:
        print(json.dumps({"status": "abstain", "reason": str(e)}, ensure_ascii=False))
        print("PORT_EXIT=3")
        return 3
    m["selftest"] = {"derivation_ok": st["derivation"]["ok"],
                     "fixture_differential_ok": st["fixture_differential"]["ok"],
                     "mutations_caught": sum(1 for v in st["mutation_controls"].values() if v["ok"]),
                     "mutations_total": len(st["mutation_controls"]),
                     "probe_samples": st["probe_samples"]}
    m["old_arm"] = run_old_arm()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(m, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps(m, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"PORT_EXIT=0")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except DeriveError as e:
        print(json.dumps({"status": "abstain", "reason": f"派生失败: {e}"}, ensure_ascii=False))
        print("PORT_EXIT=3")
        sys.exit(3)
