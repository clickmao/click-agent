#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""计划/范围契约机检 (R518 候选③: 生成器回归负控)。

起因 (本轮自抓事故): 起臂前生成的 **范围文件** 被生成器覆盖 (节点重复/错行) ⇒ 编排器臂
fail-closed rc=2「范围文件非法」, 整轮读数作废。旧流程只靠「跑不起来才发现」, 无起臂前机检。

本器具做两件事:
  A) **镜像机检** (mirror): 用与 C# 权威同形的规则静态校验 (计划, 范围) 对 —— 起臂前 0 LLM 成本;
  B) **权威绑定负控** (`--nc`): 对每个变异输入, 既要镜像报红, 也要**真实二进制** rc=2 拒收。
     权威二进制只可能在**校验期**拒收 (OrchestrateCommand: 计划校验/范围校验都在 InitializeAsync 之前),
     故负控一律传**不存在的工作区** —— 若某个变异漏检, 二进制会走到「工作区不存在」而非校验错误,
     本器具据此判 NC 失败 (不可能发生后置 LLM 调用)。

规则号 (镜像; 与 `src/agent/intent/TaskPlanFile.cs` / `NodeScopeFile.cs` 同源, 改一侧必同时改另一侧):
  P1 计划字段数 <5   P2 节点 id 重复   P3 节点文本为空   P4 未知位置
  P5 远端节点带执行器  P6 非远端节点缺执行器  P7 依赖未知节点  P8 依赖自环  P9 依赖环
  S1 范围字段数 <2   S2 **同一节点重复声明**   S3 节点 id 为空   S4 范围为空
  S5 路径越界 (绝对路径 / ..)   S6 范围指向未知节点   S7 同层写范围重叠   S8 范围文件无有效声明
  H1 覆盖不全 (harness 级, 非 DSL 规则: 未声明范围的节点在真机里会绕过「零产物假绿」防护 ⇒ 本臂要求全覆盖)

用法:
  python3 eval/rover/r518/check_plan_contract.py --plan plan.txt --scope scope.txt [--full-coverage] --out report.json
  python3 eval/rover/r518/check_plan_contract.py --nc --plan plan.txt --scope scope.txt --authority <agenthost> --out nc.json
退出码: 0 = 契约干净 (或 NC 全数被抓); 1 = 违反 (逐条点名); 3 = 输入缺失 fail-closed
"""
import argparse
import io
import json
import os
import subprocess
import sys
import tempfile

SEP = "|"


# ── 镜像: 路径语义 (逐字对齐 NodeScopeFile) ──────────────────────────────────

def normalize(path):
    if not path or not path.strip():
        return ""
    s = path.strip().replace("\\", "/")
    while s.startswith("./"):
        s = s[2:]
    while "//" in s:
        s = s.replace("//", "/")
    return s


def inside_workspace(n):
    if not n:
        return False
    if n.startswith("/"):
        return False
    if n == "..":
        return False
    if n.startswith("../") or "/../" in n or n.endswith("/.."):
        return False
    return True


def _prefix(pattern):
    p = pattern
    if p.endswith("/"):
        p = p[:-1]
    star = p.find("*")
    if star >= 0:
        p = p[:star]
    return p.rstrip("/")


def overlaps(a, b):
    pa, pb = _prefix(a), _prefix(b)
    if not pa or not pb:
        return True

    def compat(x, y):
        return x == y or y.startswith(x + "/") or x.startswith(y + "/")

    return compat(pa, pb) or compat(pb, pa)


def matches(pattern, rel):
    if not pattern or not rel:
        return False
    if pattern.endswith("/"):
        d = pattern[:-1]
        return rel == d or rel.startswith(pattern)
    star = pattern.find("*")
    if star >= 0:
        return rel.startswith(pattern[:star])
    return rel == pattern


# ── 镜像: 计划 ────────────────────────────────────────────────────────────────

def parse_plan(text, max_nodes=24):
    problems, nodes, seen = [], [], set()
    for i, raw in enumerate(text.replace("\r\n", "\n").replace("\r", "\n").split("\n")):
        ln = raw.strip()
        if not ln or ln.startswith("#"):
            continue
        parts = ln.split("|", 4)
        if len(parts) < 5:
            problems.append("P1 第 %d 行: 字段数 %d < 5" % (i + 1, len(parts)))
            continue
        nid = parts[0].strip()
        deps = [d.strip() for d in parts[1].split(",") if d.strip()]
        loc = parts[2].strip().lower()
        executor = parts[3].strip()
        body = "|".join(parts[4:]).strip()
        if not nid:
            problems.append("P1 第 %d 行: 节点 id 为空" % (i + 1))
            continue
        if nid in seen:
            problems.append("P2 第 %d 行: 节点 id 重复 %s" % (i + 1, nid))
            continue
        seen.add(nid)
        if not body:
            problems.append("P3 第 %d 行: 节点 %s 文本为空" % (i + 1, nid))
            continue
        if loc not in ("remote", "", "local", "hybrid"):
            problems.append("P4 第 %d 行: 未知位置 %s" % (i + 1, loc))
            continue
        loc = loc or "remote"
        if loc == "remote" and executor:
            problems.append("P5 第 %d 行: 远端节点 %s 不应带执行器" % (i + 1, nid))
            continue
        if loc != "remote" and not executor:
            problems.append("P6 第 %d 行: %s 节点 %s 缺执行器" % (i + 1, loc, nid))
            continue
        nodes.append({"id": nid, "deps": deps, "loc": loc, "executor": executor, "text": body})
    if not nodes:
        problems.append("P1 计划无任何节点")
    if len(nodes) > max_nodes:
        problems.append("P1 节点数 %d 超上限 %d" % (len(nodes), max_nodes))
    known = {n["id"] for n in nodes}
    for n in nodes:
        for d in n["deps"]:
            if d not in known:
                problems.append("P7 节点 %s 依赖未知节点 %s" % (n["id"], d))
            elif d == n["id"]:
                problems.append("P8 节点 %s 依赖自身" % n["id"])
    if problems:
        return nodes, problems
    levels, seen_l = {}, {}
    order = {n["id"]: n for n in nodes}

    def lvl(nid, stack):
        if nid in levels:
            return levels[nid]
        if nid in stack:
            return None
        stack = stack | {nid}
        best = 0
        for d in order[nid]["deps"]:
            v = lvl(d, stack)
            if v is None:
                return None
            best = max(best, v + 1)
        levels[nid] = best
        return best

    for n in nodes:
        v = lvl(n["id"], frozenset())
        if v is None:
            problems.append("P9 依赖环: 节点 %s 参与环" % n["id"])
    if problems:
        return nodes, problems
    for n in nodes:
        n["level"] = levels[n["id"]]
    return nodes, problems


# ── 镜像: 范围 ────────────────────────────────────────────────────────────────

def parse_scope(text):
    problems, scopes = [], {}
    if not text or not text.strip():
        return None, ["S8 范围文件为空"]
    for i, raw in enumerate(text.replace("\r\n", "\n").replace("\r", "\n").split("\n")):
        ln = raw.strip()
        if not ln or ln.startswith("#"):
            continue
        parts = ln.split("|", 1)
        if len(parts) < 2:
            problems.append("S1 第 %d 行: 字段数 < 2" % (i + 1))
            continue
        nid = parts[0].strip()
        if not nid:
            problems.append("S3 第 %d 行: 节点 id 为空" % (i + 1))
            continue
        if nid in scopes:
            problems.append("S2 第 %d 行: 节点 %s 范围重复声明" % (i + 1, nid))
            continue
        raw_paths = [p.strip() for p in parts[1].split(",") if p.strip()]
        if not raw_paths:
            problems.append("S4 第 %d 行: 节点 %s 范围为空" % (i + 1, nid))
            continue
        norm, bad = [], False
        for p in raw_paths:
            n = normalize(p)
            if not inside_workspace(n):
                problems.append("S5 第 %d 行: 节点 %s 路径越界 `%s`" % (i + 1, nid, p))
                bad = True
                break
            norm.append(n)
        if bad:
            continue
        scopes[nid] = norm
    if problems:
        return None, problems
    if not scopes:
        return None, ["S8 范围文件无任何有效声明"]
    return scopes, problems


def validate_scope_vs_plan(nodes, scopes, full_coverage=True):
    problems = []
    known = {n["id"] for n in nodes}
    for nid in sorted(scopes):
        if nid not in known:
            problems.append("S6 范围声明指向未知节点 %s" % nid)
    by_level = {}
    for n in nodes:
        by_level.setdefault(n.get("level", 0), []).append(n["id"])
    for level in sorted(by_level):
        scoped = [i for i in by_level[level] if i in scopes]
        for a in range(len(scoped)):
            for b in range(a + 1, len(scoped)):
                x, y = scoped[a], scoped[b]
                for pa in scopes[x]:
                    for pb in scopes[y]:
                        if overlaps(pa, pb):
                            problems.append("S7 同层节点 %s/%s 写范围重叠: `%s` ∩ `%s` (L%d 并发)"
                                            % (x, y, pa, pb, level))
    if full_coverage:
        remote_missing = [n["id"] for n in nodes
                          if n.get("loc", "remote") in ("remote", "hybrid") and n["id"] not in scopes]
        if remote_missing:
            problems.append("H1 远端节点覆盖不全 (harness 级): 未声明写范围的远端节点 %s ⇒ 真机「零产物假绿」防护对其失效"
                            % ",".join(remote_missing))
        local_declared = [n["id"] for n in nodes
                          if n.get("loc") == "local" and n["id"] in scopes]
        if local_declared:
            problems.append("H2 本地节点被声明写范围: %s ⇒ 本地自测执行器不产文件, 声明即被判「零产物」假绿"
                            % ",".join(local_declared))
    return problems


# ── 权威绑定 (负控) ───────────────────────────────────────────────────────────

VALIDATION_MARKERS = ("计划非法", "计划校验失败", "范围文件非法", "范围契约校验失败")
WORKSPACE_MARKER = "工作区不存在"


def authority_verdict(binary, plan_text, scope_text, tmpdir):
    """真二进制 verdict: 只可能在**校验期** rc=2 (传不存在的工作区 ⇒ 漏检会暴露为 workspace 错误)。"""
    pp = os.path.join(tmpdir, "plan.txt")
    sp = os.path.join(tmpdir, "scope.txt")
    io.open(pp, "w", encoding="utf-8", newline="\n").write(plan_text)
    io.open(sp, "w", encoding="utf-8", newline="\n").write(scope_text)
    env = dict(os.environ)
    env["DOTNET_ROOT"] = os.path.expanduser("~/.dotnet")
    try:
        p = subprocess.run([binary, "--orchestrate", pp, "--scope", sp,
                            "--workspace", os.path.join(tmpdir, "nonexistent-ws"),
                            "--node-steps", "1", "--report", os.path.join(tmpdir, "rep.json")],
                           capture_output=True, text=True, timeout=120, env=env, cwd=tmpdir)
    except Exception as e:  # pragma: no cover
        return {"rc": 125, "stderr": str(e)[:200], "validation_error": False}
    err = (p.stderr or "") + (p.stdout or "")
    return {"rc": p.returncode,
            "validation_error": p.returncode == 2 and any(m in err for m in VALIDATION_MARKERS),
            "workspace_error": WORKSPACE_MARKER in err,
            "stderr_head": err.strip().splitlines()[-1][:200] if err.strip() else ""}


def _first_data_line(text):
    """第一条**数据行** (跳过空行与 '#' 注释) —— 变异必须落在数据行上, 否则变异是空转 (NC 变弱)。"""
    for ln in text.splitlines():
        t = ln.strip()
        if t and not t.startswith("#"):
            return ln
    return ""


# (标签, 目标, 变异函数) —— 目标 ∈ {"plan","scope"}; 变异函数只接该目标的文本
MUTATIONS = [
    ("S2 范围重复声明", "scope", lambda s: s + _first_data_line(s) + "\n"),
    ("S6 范围指向未知节点", "scope", lambda s: s + "nZZ | tasksvc/zz.py\n"),
    ("S5 路径越界", "scope", lambda s: s + "n1 | /etc/passwd\n"),
    ("S5b 路径上跳", "scope", lambda s: s + "n1 | ../outside.txt\n"),
    ("S1 范围字段缺失", "scope", lambda s: s + "n1\n"),
    ("S4 范围为空", "scope", lambda s: s + "n1 |\n"),
    ("S8 范围文件空", "scope", lambda s: "# 只有注释\n"),
    ("P2 计划节点重复", "plan", lambda p: p + _first_data_line(p) + "\n"),
    ("P7 依赖未知节点", "plan", lambda p: p + "nZZ | nNOPE | remote | | 依赖未知\n"),
    ("P4 未知位置", "plan", lambda p: p + "nZZ | | nowhere | | 位置非法\n"),
    ("P3 节点文本为空", "plan", lambda p: p + "nZZ | | remote | |\n"),
    ("P9 依赖环", "plan", lambda p: p + "nCY1 | nCY2 | remote | | 环A\nnCY2 | nCY1 | remote | | 环B\n"),
]


def run_mirror(plan_text, scope_text, full_coverage):
    nodes, pprob = parse_plan(plan_text)
    if pprob:
        return pprob
    scopes, sprob = parse_scope(scope_text)
    if sprob:
        return sprob
    return validate_scope_vs_plan(nodes, scopes, full_coverage)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--out")
    ap.add_argument("--full-coverage", action="store_true", default=True)
    ap.add_argument("--no-full-coverage", dest="full_coverage", action="store_false")
    ap.add_argument("--nc", action="store_true", help="负控模式: 每个变异须镜像报红且真二进制校验期拒收")
    ap.add_argument("--authority", help="agent.host 二进制 (--nc 必需)")
    a = ap.parse_args()

    for p in (a.plan, a.scope):
        if not os.path.isfile(p):
            print("[致命] 输入缺失 %s ⇒ fail-closed rc=3" % p)
            return 3
    plan_text = io.open(a.plan, encoding="utf-8").read()
    scope_text = io.open(a.scope, encoding="utf-8").read()

    out = {"plan": a.plan, "scope": a.scope, "mirror": {}, "nc": []}
    problems = run_mirror(plan_text, scope_text, a.full_coverage)
    nodes, _ = parse_plan(plan_text)
    scopes, _ = parse_scope(scope_text)
    out["mirror"] = {"nodes_n": len(nodes), "scoped_n": len(scopes or {}),
                     "levels": sorted({n.get("level", 0) for n in nodes}),
                     "problems": problems, "clean": not problems}
    print("MIRROR plan=%s scope=%s nodes=%d scoped=%d clean=%s"
          % (os.path.basename(a.plan), os.path.basename(a.scope),
             len(nodes), len(scopes or {}), not problems))
    for p in problems:
        print("  · " + p)

    rc = 0 if not problems else 1

    if a.nc:
        if not a.authority or not os.path.isfile(a.authority):
            print("[致命] --nc 需 --authority <agent.host 二进制> 且在位 ⇒ rc=3")
            return 3
        ok = True
        tmpdir = tempfile.mkdtemp(prefix="r518nc-")
        for label, target, mutate in MUTATIONS:
            if target == "plan":
                mp, ms = mutate(plan_text), scope_text
            else:
                mp, ms = plan_text, mutate(scope_text)
            # 变异有效性自检: 必须真的改动了目标文本 (否则 NC 是空转, 白拿 PASS)
            if (mp, ms) == (plan_text, scope_text):
                print("  NC %-22s [无效变异: 文本未变] => FAIL" % label)
                out["nc"].append({"mutation": label, "passed": False,
                                  "reason": "mutation no-op (文本未变) ⇒ NC 空转, 判 FAIL"})
                ok = False
                continue
            mprobs = run_mirror(mp, ms, a.full_coverage)
            mir_red = bool(mprobs)
            au = authority_verdict(a.authority, mp, ms, tmpdir)
            au_red = bool(au["validation_error"])
            passed = mir_red and au_red
            ok = ok and passed
            out["nc"].append({"mutation": label, "target": target, "mirror_problems": mprobs[:3],
                              "mirror_red": mir_red, "authority_rc": au["rc"],
                              "authority_validation_error": au_red,
                              "authority_workspace_error": au["workspace_error"],
                              "authority_stderr_head": au["stderr_head"], "passed": passed})
            print("  NC %-22s target=%-5s mirror_red=%-5s authority_rc=%s validation_error=%-5s => %s"
                  % (label, target, mir_red, au["rc"], au_red, "PASS" if passed else "FAIL"))
        out["nc_all_passed"] = ok
        print("NC_ALL_PASSED=%s (%d 变异)" % (ok, len(MUTATIONS)))
        if not ok:
            rc = 1

    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        io.open(a.out, "w", encoding="utf-8", newline="\n").write(
            json.dumps(out, ensure_ascii=False, indent=1) + "\n")
        print("OUT=" + a.out)
    return rc


if __name__ == "__main__":
    sys.exit(main())
