#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R506 · 候选④ 闭合判定器: r433 冻结行证据面**可完整重放**吗?

对 R504 夹具 (`eval/rover/r504/replay_r433_face.py`) 的三处升级 —— 每处都是实测过的缺陷形态:

  ① **命令从登记行派生, 不硬编码**: R504 夹具把 `--glob 'data/probe/probe-*r433*.json'`
     写死在脚本第 27 行 ⇒ 被审对象(登记行)与判据(脚本)是两个写者, 行改了脚本不说。
     本工具按 `registry.rows[id].evidence_cmd` 逐段执行 (` && ` 分段, 段数 ≠ 3 ⇒ rc=3 fail-closed)。
  ② **成对判据 (正控 + 负控)**: 只跑「现在过不过」会放行**空心闭合**。
     负控 = 用**前态命令**(缺 `--run <基线>` 那一版, 由夹具逐字钉住) 重放, 必须**复现缺口**
     (缺 baseline 行) ⇒ 证明「缺的那一行真的是那条操作数补上的」, 而不是判据本来就看不见它。
  ③ **越界也判红 (extra 行)**: 原夹具只查 `missing_in_replay`; 多加通配符把**无关 run 吸进报告**
     同样会被读成 PASS (缺的那行补上了, 却混进别的 run) ⇒ 本工具把 `extra_in_replay` 也列为红。

等价性判据 (强): 重放报告与冻结台账 **逐字节相同**, 白名单只含 1 条**非语义**字段
  —— `生成时间: <墙钟>` 行 (工具每次运行必然不同, 只作信息项)。
白名单之外任一字节不同 ⇒ FAIL (不是「行级 drift=0」就算过)。

重放替身 (唯一两处, 均只改**输出目的地**, 不改被测语义; 写在读契约里):
  * `--report <冻结路径>` → `--report <scratch>` : 防重放**覆盖冻结产物** (冻结件是归档, 不得被副作用改写)
  * 追加 `--no-ledger`                          : 防重放**污染在账台账** `data/probe/kpi.jsonl` (幂等追加 + 无谓行)

用法:
  python3 eval/rover/r506/replay_row2_closure.py            # 跑双臂 ⇒ 落证据
退出码: 0 = 闭合成立 (正控 PASS_CLOSED ∧ 负控 GAP_REPRODUCED); 1 = 判据不成立; 3 = 输入/器具缺失。
"""
import hashlib
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
REG = "docs/verification-registry.json"
ROW_ID = "r433.probe-code-source-artifact-channel"
FROZEN = "eval/capability/r433/kpi-report.md"
PRESTATE_FIXTURE = "eval/rover/r506/prestate-kpi-stage.txt"
OUT = "eval/rover/r506/evidence/replay-row2-closure.json"
SCRATCH = "/tmp/r506_replay"
# 逐位相等判据的**非语义字段白名单** (墙钟; 只作信息项, 不参与红绿)
NONSEMANTIC = ((re.compile(r"^生成时间: .*$", re.M), "生成时间: <WALLCLOCK>"),)


def norm(path):
    t = io.open(path, encoding="utf-8", newline="").read()
    for pat, rep in NONSEMANTIC:
        t = pat.sub(rep, t)
    return t


def sha12_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()[:12]


def rows_of(path):
    """报告 §一 总览行: run 名 → 各列。

    归属键 = **run 名**(身份), **不含序号** —— 序号是位置量, 行集合一变就整体位移
    (实测: 前态命令少 1 行 ⇒ 其余 8 行序号整体 -1, 用 (序号,名) 作键会把 8 行**全部**
    误报为 missing, 看起来像「缺口 9 行」)。重名 ⇒ 抛错 (fail-closed, 不静默取末者)。
    """
    out = {}
    if not os.path.isfile(path):
        return out
    for line in io.open(path, encoding="utf-8", errors="replace"):
        if not line.startswith("| "):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 11 or not c[0].isdigit():
            continue
        if c[1] in out:
            raise ValueError("报告内 run 名重复: %s" % c[1])
        out[c[1]] = c
    return out


def run_stage(stage):
    argv = shlex.split(stage, posix=True)
    p = subprocess.run(argv, cwd=REPO, capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def redirect(stage, scratch_report):
    """把 `--report <路径>` 重定向到 scratch 并追加 `--no-ledger` (只改输出目的地)。"""
    new, n = re.subn(r"--report\s+\S+", "--report " + scratch_report, stage, count=1)
    if n != 1:
        raise ValueError("--report 未唯一命中 (n=%d): 读契约不成立" % n)
    if "--no-ledger" not in new:
        new += " --no-ledger"
    return new


def main():
    reg = os.path.join(REPO, REG)
    if not os.path.isfile(reg):
        print("[致命] 登记表缺失")
        return 3
    doc = json.load(io.open(reg, encoding="utf-8"))
    rs = [r for r in doc["rows"] if r.get("id") == ROW_ID]
    if len(rs) != 1:
        print("[致命] 行定位失败 n=%d" % len(rs))
        return 3
    cmd = rs[0]["evidence_cmd"]

    rep: dict = {"round": "R506", "row": ROW_ID, "round_upgrade_of": "eval/rover/r504/replay_r433_face.py"}

    # ---- 0. 命令分段 (fail-closed: 段数与预期不符即弃权)
    stages = [s.strip() for s in cmd.split(" && ") if s.strip()]
    rep["cmd_from_row"] = cmd
    rep["cmd_stages"] = stages
    if len(stages) != 3:
        rep["verdict"] = "VOID"
        rep["note"] = "evidence_cmd 段数 != 3 (读契约不成立)"
        print(json.dumps(rep, ensure_ascii=False))
        return 3

    # ---- 1. 两个自检段 (行自带)
    rep["stages"] = {}
    for name, st in (("grade_selftest", stages[0]), ("runprobe_selftest", stages[1])):
        rc, out = run_stage(st)
        rep["stages"][name] = {"rc": rc, "counts": re.findall(r"selftest\s+(\d+)/(\d+)", out)}

    # ---- 2. 正控臂: 行自带命令 (重定向输出)
    os.makedirs(SCRATCH, exist_ok=True)
    pos_path = os.path.join(SCRATCH, "kpi-report-poscontrol.md")
    neg_path = os.path.join(SCRATCH, "kpi-report-negcontrol.md")
    for p in (pos_path, neg_path):
        if os.path.exists(p):
            os.remove(p)

    pos_cmd = redirect(stages[2], pos_path)
    rc_pos, _ = run_stage(pos_cmd)
    rep["arm_positive"] = {"cmd": pos_cmd, "rc": rc_pos, "report": pos_path}

    # ---- 3. 负控臂: 前态命令 (夹具钉住; 结构变换必须与夹具逐字一致)
    fixture = os.path.join(REPO, PRESTATE_FIXTURE)
    if not os.path.isfile(fixture):
        print("[致命] 前态夹具缺失 %s" % PRESTATE_FIXTURE)
        return 3
    pre_stage = io.open(fixture, encoding="utf-8").read().strip()
    # 结构变换: 剥掉本轮新增的那两个操作数
    derived = stages[2].replace("--run data/probe/probe-m6-agent.json ", "")
    derived = derived.replace("--compare probe-m6-agent.json probe-agent-seed0-r433m6fix2.json ", "")
    rep["prestate_agrees"] = (derived == pre_stage)
    if not rep["prestate_agrees"]:
        rep["verdict"] = "VOID"
        rep["note"] = "前态夹具与结构变换不一致 (前态锚漂移 ⇒ 负控不可解读)"
        print(json.dumps(rep, ensure_ascii=False))
        return 3
    neg_cmd = redirect(pre_stage, neg_path)
    rc_neg, _ = run_stage(neg_cmd)
    rep["arm_negative"] = {"cmd": neg_cmd, "rc": rc_neg, "report": neg_path}

    # ---- 4. 判据 (正控 5 条)
    fp, fn = os.path.join(REPO, FROZEN), pos_path
    frozen_rows, pos_rows, neg_rows = rows_of(fp), rows_of(fn), rows_of(neg_path)
    base_key = [k for k in frozen_rows if "probe-m6-agent.json" in k]

    rep["frozen"] = {"path": FROZEN, "rows": len(frozen_rows),
                     "norm_sha12": hashlib.sha256(norm(fp).encode()).hexdigest()[:12],
                     "raw_bytes": os.path.getsize(fp),
                     "nonsemantic_whitelist": [p.pattern for p, _ in NONSEMANTIC]}
    rep["positive"] = {
        "rows": len(pos_rows),
        "missing": sorted(k for k in frozen_rows if k not in pos_rows),
        "extra": sorted(k for k in pos_rows if k not in frozen_rows),
        "compare_section": "## 二、对比 A → B" in io.open(fn, encoding="utf-8", errors="replace").read(),
        "norm_equal": norm(fp) == norm(fn),
    }
    rep["negative"] = {
        "rows": len(neg_rows),
        "missing": sorted(k for k in frozen_rows if k not in neg_rows),
    }

    checks = {
        "正控: 重放行数 == 冻结行数": len(pos_rows) == len(frozen_rows),
        "正控: 无缺行": not rep["positive"]["missing"],
        "正控: 无越界行 (extra)": not rep["positive"]["extra"],
        "正控: 含 §二 对比段 (命令操作数完整)": rep["positive"]["compare_section"],
        "正控: 逐字节等价 (白名单外零差异)": rep["positive"]["norm_equal"],
        "负控: 前态命令复现缺口 (恰好缺 baseline 行)": base_key == rep["negative"]["missing"],
        "负控: 前态行数 == 冻结行数 - 1": len(neg_rows) == len(frozen_rows) - 1,
        "前态锚: 结构变换 == 夹具 (逐字)": rep["prestate_agrees"],
    }
    rep["checks"] = checks
    rep["fails"] = [k for k, v in checks.items() if not v]
    ok = (rc_pos == 0 and rc_neg == 0 and not rep["fails"]
          and all(s["rc"] == 0 for s in rep["stages"].values()))
    rep["verdict"] = "PASS_CLOSED" if ok else "FAIL"

    os.makedirs(os.path.join(REPO, os.path.dirname(OUT)), exist_ok=True)
    json.dump(rep, io.open(os.path.join(REPO, OUT), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: rep[k] for k in ("verdict", "fails")}, ensure_ascii=False, indent=1))
    print(json.dumps({"positive": rep["positive"], "negative": rep["negative"]},
                     ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
