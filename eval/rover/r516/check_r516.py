#!/usr/bin/env python3
"""R516 判据器: 逐臂读 report.json, 机械判定「节点成功绑定产物证据」是否真落地。

只读落盘产物 + 退出码, 不做模型裁判, 不事后补记 (铁律 11 / 主线四硬条件③)。
  RED : 旧 AOT (R515) 同一计划 ⇒ 零产物节点**仍 Completed**  (前态; 未复现 ⇒ 本轮 RED 证据无效)
  G1  : 新 AOT + 同计划 + scope ⇒ 节点 **Failed** + violation kind=no_artifact
  G2  : 新 AOT + 写 out/hello.py + scope out/ ⇒ **Completed** 且 files 含 "A out/hello.py" (契约不误杀)
  G3  : 新 AOT + 写 outside/rogue.py + scope out/ ⇒ **Failed** + violation kind=out_of_scope, 路径点名
  N   : 新 AOT + 同层重叠 scope ⇒ **rc=2** 且 adapter 零新增请求 (起臂前拒收, 零 LLM)
输出 verdict JSON: rc 0 = 全臂符合预期。
"""
import argparse
import glob
import json
import os
import re
import sys

ADAPTER_CALL_RE = re.compile(r"^side-[A-Za-z0-9_]+-(\d+)\.json$")
REPO = "/home/agentuser/AgentFramework"


def load_report(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8-sig") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def node0(report):
    nodes = (report or {}).get("nodes") or []
    return nodes[0] if nodes else {}


def max_call_idx(adapter_dir):
    top = 0
    try:
        for fn in os.listdir(adapter_dir):
            m = ADAPTER_CALL_RE.match(fn)
            if m:
                top = max(top, int(m.group(1)))
    except OSError:
        pass
    return top


def violation_kinds(report):
    return sorted({v.get("kind") for v in ((report or {}).get("scope_violations") or [])})


def violation_paths(report):
    return sorted({v.get("path") for v in ((report or {}).get("scope_violations") or [])})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    d = args.run_dir

    checks = []

    def check(arm, ok, detail):
        checks.append({"arm": arm, "ok": bool(ok), "detail": detail})

    # RED: 旧宿主**无范围机制** (同一计划逐字节) —— 越过范围也只判 Completed, 报告里不存在 scope 字段
    rep = load_report(os.path.join(d, "red", "report.json"))
    n0 = node0(rep)
    rc_red = read_rc(os.path.join(d, "logs", "red.txt"))
    check("RED", rep is not None and rc_red == "0" and n0.get("state") == "Completed"
          and "scope_violations" not in (rep or {}) and "scope_file" not in (rep or {}),
          f"旧AOT rc={rc_red} state={n0.get('state')} files={n0.get('files')} "
          f"scope_keys={'scope_violations' in (rep or {}) or 'scope_file' in (rep or {})} (期望: 无范围机制)")

    # A5 前态锚: R515 归档报告里存在 Completed 且 0 产物的节点 (假绿现场, 冻结证据, 非本轮自报)
    anchor = load_report(os.path.join(REPO, "eval/rover/r515/evidence/report-orch-v2-12step.json"))
    ghost = [n.get("node_id") for n in (anchor or {}).get("nodes", [])
             if n.get("state") == "Completed" and not n.get("files")]
    check("A5-pre-state-anchor", bool(ghost),
          f"R515 归档 report-orch-v2-12step.json: Completed∧0产物 节点 = {ghost} (前态锚, 冻结)")

    # G1: 零产物 ⇒ Failed + no_artifact
    rep = load_report(os.path.join(d, "g1", "report.json"))
    n0 = node0(rep)
    rc = read_rc(os.path.join(d, "logs", "g1.txt"))
    check("G1", rc == "1" and n0.get("state") == "Failed" and "no_artifact" in violation_kinds(rep),
          f"rc={rc} state={n0.get('state')} violations={violation_kinds(rep)} error={(n0.get('error') or '')[:60]}")

    # G2: 真干活 ⇒ Completed 且产物在册 (不误杀)
    rep = load_report(os.path.join(d, "g2", "report.json"))
    n0 = node0(rep)
    rc = read_rc(os.path.join(d, "logs", "g2.txt"))
    files = n0.get("files") or []
    check("G2", rc == "0" and n0.get("state") == "Completed" and any("out/hello.py" in f for f in files) and not violation_kinds(rep),
          f"rc={rc} state={n0.get('state')} files={files} violations={violation_kinds(rep)}")

    # G3: 越界写 ⇒ Failed + out_of_scope + 点名路径
    rep = load_report(os.path.join(d, "g3", "report.json"))
    n0 = node0(rep)
    rc = read_rc(os.path.join(d, "logs", "g3.txt"))
    check("G3", rc == "1" and n0.get("state") == "Failed" and "out_of_scope" in violation_kinds(rep)
          and any("outside/rogue.py" in p for p in violation_paths(rep)),
          f"rc={rc} state={n0.get('state')} violations={violation_kinds(rep)} paths={violation_paths(rep)}")

    # N: 同层重叠 ⇒ 起臂前拒收, 零 adapter 调用
    rc = read_rc(os.path.join(d, "logs", "n.txt"))
    before = read_rc(os.path.join(d, "n", "idx-before.rc")) or "0"
    after = read_rc(os.path.join(d, "n", "idx-after.rc")) or "0"
    no_report = not os.path.exists(os.path.join(d, "n", "report.json"))
    stderr_txt = read_text(os.path.join(d, "n", "stderr.txt"))
    check("N", rc == "2" and no_report and before == after and "重叠" in stderr_txt,
          f"rc={rc} report_absent={no_report} adapter_calls {before}->{after} stderr_has_overlap={'重叠' in stderr_txt}")

    ok = all(c["ok"] for c in checks)
    verdict = {
        "round": "R516",
        "verdict": "PASS" if ok else "FAIL",
        "run_dir": d,
        "adapter_calls_total": max_call_idx(os.path.join(d, "adapter")),
        "checks": checks,
    }
    text = json.dumps(verdict, ensure_ascii=False, indent=1)
    print(text)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    return 0 if ok else 1


def read_rc(path):
    """读日志文件里的最后一个 `...=N` 数值 (rc 记录形式 = 器具与实发文本逐位比对的一部分)。"""
    txt = read_text(path)
    vals = re.findall(r"=(\d+)\b", txt)
    return vals[-1] if vals else ""


def read_text(path):
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


if __name__ == "__main__":
    sys.exit(main())
