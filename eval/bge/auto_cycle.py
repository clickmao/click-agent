#!/usr/bin/env python3
"""BGE 闸门 + 融合 静默自动巡检 (watchdog 形态)。

设计口径 (用户钦定: bge 相关汇报保持静默):
  * 一切正常  -> stdout **零输出** (cron no_agent 直投; 空输出不打扰用户)。
  * 任何异常  -> stdout 输出**紧凑告警**(含 exit_code / 关键路径 / 日志尾), 用户的 cron 才会出声。
  * 每次运行无论成败 -> 追加一行结构化摘要(含 alerts)到 data/bge/auto_cycle_log.jsonl。

巡检内容:
  0) 前置资产存在性 (缺失即秒退并出声, 列出检查过的路径 —— 含 /tmp 下的易失模型)
  1) 闸门静态审计 (AST 真值判定, 非文本匹配): 空心闸门(literal bool) / 闸门键缺失 / G3 三子判据缺一 / 阈值漂移
  2) 闸门判定件真机机检 (test_gates.py 全绿)
  3) 融合真值重算 (fusion.py --md 落盘) + 产出物新鲜度
  4) 指标地板 (RRF r@10 不得低于地板, 且不得低于单路最优)

用法: python3 eval/bge/auto_cycle.py [--selftest]   (cwd 必须是仓库根)
"""
import ast
import json
import os
import re
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_JSONL = os.path.join(REPO, "data", "bge", "auto_cycle_log.jsonl")
GATE_SRC = os.path.join(REPO, "eval", "bge", "train_adapter.py")
TEST_GATES = os.path.join(REPO, "eval", "bge", "test_gates.py")
FUSION = os.path.join(REPO, "eval", "bge", "fusion.py")
FIXTURES = os.path.join(REPO, "eval", "bge", "fixtures")
CACHE = os.path.join(REPO, "data", "bge", "cache")

# env 显式设置 => 该路径即权威候选(不回落); 否则用默认候选列表。
SMALL_MODEL_CANDIDATES = (
    [os.environ["BGE_MODEL"]] if os.environ.get("BGE_MODEL") else
    [os.path.expanduser("~/.agentframework/models/bge-q8.gguf"),
     os.path.join(REPO, ".agentframework", "models", "bge-q8.gguf")]
)
BASE_MODEL_CANDIDATES = (
    [os.environ["BGE_BASE_MODEL"]] if os.environ.get("BGE_BASE_MODEL") else
    ["/tmp/models/bge-base-zh-v1.5-q8.gguf"]
)

RRF_FLOOR = float(os.environ.get("BGE_AUTO_RRF_FLOOR", "0.83"))  # 2pt 容差 (基线 0.8500); 跌破即真回归
GATE_KEYS = ("G1", "G2", "G3", "G4", "G5")
G3_CONSTS = {"MAC_BUDGET": 0.05, "LAT_BUDGET": 0.15, "MEM_BUDGET": 0.15}
ARTIFACT_MAX_AGE_S = 120

alerts: list = []
summary: dict = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "outcome": "ok"}


# ─────────────────────── 静态闸门审计 (AST) ───────────────────────

def _gate_assignments(tree):
    """{gate_key: (value_node, lineno)}"""
    out = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        tgt = node.targets[0]
        if not isinstance(tgt, ast.Subscript) or not isinstance(tgt.value, ast.Name):
            continue
        if tgt.value.id != "g":
            continue
        key = getattr(tgt.slice, "value", None)
        if isinstance(key, str):
            out[key] = (node.value, node.lineno)
    return out


def _module_consts(tree):
    """{name: literal} —— 只取能静态求值的模块级赋值。"""
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            try:
                out[name] = ("lit", ast.literal_eval(node.value))
            except (ValueError, SyntaxError):
                out[name] = ("expr", None)
    return out


def _names(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def scan_gates_source(src, label):
    """对一份闸门源码做 AST 审计, 返回告警列表 (纯函数, 可被 selftest 负控)。"""
    out = []
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return ["GATE-PARSE %s 语法错误: %s" % (label, e)]
    gates = _gate_assignments(tree)
    consts = _module_consts(tree)

    for key in GATE_KEYS:
        if key not in gates:
            out.append("GATE-KEYS %s 缺闸门 %s" % (label, key))
            continue
        expr, lineno = gates[key]
        if isinstance(expr, ast.Constant) and isinstance(expr.value, bool):
            out.append("HOLLOW-GATE %s:%d  %s = %r (恒真恒假的空心闸门)"
                       % (label, lineno, 'g["%s"]' % key, expr.value))

    g3 = gates.get("G3")
    if g3 is not None:
        used = _names(g3[0])
        missing = sorted(set(G3_CONSTS) - used)
        if missing:
            out.append("GATE-SEMANTICS %s:%d  G3 未引用子判据常量 %s (三子判据缺一不可)"
                       % (label, g3[1], missing))

    for name, expect in G3_CONSTS.items():
        kind, val = consts.get(name, ("missing", None))
        if kind == "missing":
            out.append("GATE-DRIFT %s 缺常量 %s (应 = %.2f)" % (label, name, expect))
        elif kind == "lit" and abs(float(val) - expect) > 1e-12:
            out.append("GATE-DRIFT %s %s = %r (应 = %.2f)" % (label, name, val, expect))
    return out


# ─────────────────────── 融合报告解析 ───────────────────────

def parse_rrf_r10(md_text):
    """从融合报告表格抽取 RRF(lexical+dense-base, k0=10, 1:1) 的 r@10; 抽不到返回 None。"""
    m = re.search(r'\|\s*lexical\+dense-base\s*\|\s*10\s*\|\s*1:1\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|', md_text)
    return float(m.group(2)) if m else None


def parse_best_single_r10(md_text):
    """§1 单路表里 lexical / dense-base 的 r@10 最大值; 缺则 None。"""
    vals = []
    for name in ("lexical", "dense-base"):
        m = re.search(r'\|\s*' + re.escape(name) + r'\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|', md_text)
        if m:
            vals.append(float(m.group(3)))
    return max(vals) if vals else None


# ─────────────────────── 前置资产 ───────────────────────

def first_existing(cands):
    for c in cands:
        if c and os.path.isfile(c):
            return os.path.expanduser(c)
    return None


def check_assets():
    """缺失即 alert (列出检查过的路径) —— 不进入后续阶段的傻等。"""
    small = first_existing(SMALL_MODEL_CANDIDATES)
    base = first_existing(BASE_MODEL_CANDIDATES)
    missing = []
    if not small:
        missing.append("bge-small 模型: " + " | ".join(SMALL_MODEL_CANDIDATES))
    if not base:
        missing.append("bge-base 模型: " + " | ".join(BASE_MODEL_CANDIDATES))
    for p in [GATE_SRC, TEST_GATES, FUSION,
              os.path.join(FIXTURES, "corpus.jsonl"), os.path.join(FIXTURES, "queries.jsonl")]:
        if not os.path.isfile(p):
            missing.append("缺文件: " + p)
    if not os.path.isdir(CACHE):
        missing.append("缺向量缓存目录: " + CACHE)
    if missing:
        alerts.append("PRECHECK 资产缺失 =>\n    " + "\n    ".join(missing))
    summary["model"] = os.path.basename(small) if small else None
    summary["base_model"] = os.path.basename(base) if base else None
    return small, base


# ─────────────────────── 子进程 ───────────────────────

def run(cmd, timeout, env=None, cwd=REPO):
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, timeout=timeout,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return p.returncode, p.stdout, time.time() - t0
    except subprocess.TimeoutExpired as e:
        return 124, (e.output or "") + "\n[TIMEOUT after %ss]" % timeout, time.time() - t0


def tail(s, n=12):
    lines = [l for l in s.splitlines() if l.strip()]
    return "\n    ".join(lines[-n:])


def finish():
    os.makedirs(os.path.dirname(OUT_JSONL), exist_ok=True)
    summary["alerts"] = alerts
    with open(OUT_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(summary, ensure_ascii=False) + "\n")
    if os.environ.get("BGE_AUTO_VERBOSE"):
        print("SUMMARY " + json.dumps(summary, ensure_ascii=False))


def emit():
    """告警出口: 有告警才出声 (cron 直投), 无告警零输出。"""
    if alerts:
        print("ALERT bge-auto (%s) 闸门/融合异常:" % summary["ts"])
        for a in alerts:
            print("  " + a)


# ─────────────────────── 主流程 ───────────────────────

def main():
    if not os.path.isdir(os.path.join(REPO, ".git")):
        print("ALERT bge-auto: 仓库根识别失败 -> " + REPO)
        return 0

    small, base = check_assets()
    if not (small and base):
        summary["outcome"] = "precheck-failed"
        finish()
        emit()                      # 前置缺失必须出声 (曾在此静默 —— 最危险的失效模式)
        return 0

    rel = os.path.relpath(GATE_SRC, REPO)
    gate_alerts = scan_gates_source(open(GATE_SRC, encoding="utf-8").read(), rel)
    alerts.extend(gate_alerts)
    summary["gate_alerts"] = len(gate_alerts)
    summary["gate_keys"] = len(_gate_assignments(ast.parse(open(GATE_SRC, encoding="utf-8").read())))

    env = dict(os.environ)
    env["BGE_MODEL"] = small
    env["BGE_BASE_MODEL"] = base

    rc, out, dur = run([sys.executable, TEST_GATES], 300, env=env)
    summary["gates_rc"] = rc
    summary["gates_s"] = round(dur, 1)
    if rc != 0:
        alerts.append("GATE-CHECK 判定件机检失败 (exit=%d, %.1fs) =>\n    %s" % (rc, dur, tail(out, 15)))

    md = os.path.join(REPO, "docs", "reports", "bge", "fusion-%s.md" % time.strftime("%Y-%m-%d"))
    rc2, out2, dur2 = run([sys.executable, FUSION, "--md", md], 900, env=env)
    summary["fusion_rc"] = rc2
    summary["fusion_s"] = round(dur2, 1)
    if rc2 != 0:
        alerts.append("FUSION 融合重算失败 (exit=%d, %.1fs) =>\n    %s" % (rc2, dur2, tail(out2, 15)))
    else:
        if not os.path.isfile(md):
            alerts.append("ARTIFACT 融合报告未落盘: " + md)
        else:
            md_text = open(md, encoding="utf-8").read()
            age = time.time() - os.path.getmtime(md)     # 新鲜度 = now - mtime
            summary["artifact_age_s"] = round(age, 1)
            if age > ARTIFACT_MAX_AGE_S:
                alerts.append("ARTIFACT 融合报告非本轮产出 (mtime 早于本轮 %.0fs): %s" % (age, md))
            rrf10 = parse_rrf_r10(md_text)
            if rrf10 is None:
                alerts.append("ARTIFACT 融合报告解析不出 RRF(lexical+dense-base,10,1:1) 行: " + md)
            else:
                summary["rrf_r@10"] = rrf10
                best = parse_best_single_r10(md_text)
                if best is not None:
                    summary["best_single_r@10"] = best
                    if rrf10 < best:
                        alerts.append("FLOOR 融合 r@10=%.4f 低于单路最优 %.4f (融合不再有增益)" % (rrf10, best))
                if rrf10 < RRF_FLOOR:
                    alerts.append("FLOOR 融合 r@10=%.4f 跌破地板 %.2f (基线 0.8500)" % (rrf10, RRF_FLOOR))

    summary["outcome"] = "alert" if alerts else "ok"
    finish()
    emit()
    return 0


# ─────────────────────── 负控 (证明本巡检器非空心) ───────────────────────

def selftest():
    LBL = "synthetic.py"

    # ① 空心闸门: literal True 必须命中; 真表达式必须放行
    bad = 'g = {}\nMAC_BUDGET = 0.05\nLAT_BUDGET = 0.15\nMEM_BUDGET = 0.15\n' \
          'g["G1"] = a\ng["G2"] = b\ng["G3"] = gd["mac"] <= MAC_BUDGET and gd["lat"] <= LAT_BUDGET and gd["mem"] <= MEM_BUDGET\n' \
          'g["G4"] = c\ng["G5"] = True\n'
    good = bad.replace('g["G5"] = True', 'g["G5"] = all(v is True for v in gd["G5_detail"].values())')
    a_bad = scan_gates_source(bad, LBL)
    a_good = scan_gates_source(good, LBL)
    assert any(x.startswith("HOLLOW-GATE") for x in a_bad), ("负控①: literal True 未命中", a_bad)
    assert not a_good, ("负控①: 合法源码被误报", a_good)
    print("OK ① 空心闸门 AST 命中 (literal True 报警 / 真表达式放行)")

    # ② G3 三子判据缺一必须报 (只留 mac)
    g3_short = good.replace('and gd["lat"] <= LAT_BUDGET and gd["mem"] <= MEM_BUDGET', '')
    a_short = scan_gates_source(g3_short, LBL)
    assert any(x.startswith("GATE-SEMANTICS") and "LAT_BUDGET" in x and "MEM_BUDGET" in x for x in a_short), \
        ("负控②: G3 缺子判据未报", a_short)
    print("OK ② G3 三子判据缺一报警")

    # ③ 阈值漂移 + 闸门键缺失必须报
    drift = good.replace("MAC_BUDGET = 0.05", "MAC_BUDGET = 0.5").replace('g["G2"] = b\n', '')
    a_drift = scan_gates_source(drift, LBL)
    assert any(x.startswith("GATE-DRIFT") for x in a_drift), ("负控③: 阈值漂移未报", a_drift)
    assert any(x.startswith("GATE-KEYS") and "G2" in x for x in a_drift), ("负控③: 键缺失未报", a_drift)
    print("OK ③ 阈值漂移 / 闸门键缺失 报警")

    # ④ 融合报告解析: 缺行 -> None
    md_bad = "| lexical | 0.4417 | 0.7167 | 0.75 | 0.7667 | 0.5571 | 0.2 |\n"
    md_good = md_bad + "| lexical+dense-base | 10 | 1:1 | 0.5333 | 0.85 | 0.875 | 0.6439 | 0.0917 | 0.8667 |\n"
    assert parse_rrf_r10(md_bad) is None, "负控④: 缺行却能解析 => 解析器空心"
    assert parse_rrf_r10(md_good) == 0.85, ("负控④: 正确解析失败", parse_rrf_r10(md_good))
    assert parse_best_single_r10(md_good) == 0.75, ("负控④: 单路最优解析错", parse_best_single_r10(md_good))
    print("OK ④ 融合报告解析 (缺行 -> None / 正常 -> 0.85, 单路最优 0.75)")

    # ⑤ 指标地板
    assert (0.82 < RRF_FLOOR) and not (0.84 < RRF_FLOOR), ("负控⑤: 地板判定错", RRF_FLOOR)
    print("OK ⑤ 指标地板 (0.82 触发 / 0.84 放行, floor=%.2f)" % RRF_FLOOR)

    print("OK: 静默巡检器负控 全部通过 (非空心)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    sys.exit(main())
