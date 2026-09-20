#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R600 收口②: ① 跑后补生成 bins-r600.json（同 runner 算法）② 登记表加行 + bump updated_round。"""
import hashlib
import io
import json
import os
import subprocess

REPO = "/home/agentuser/AgentFramework"
R = os.path.join(REPO, "eval/rover/r600")
D = os.path.expanduser("~/.agentframework/harness/runs/r600")
BIN = os.path.expanduser("~/.agentframework/artifacts/pub_r600/agenthost")
CODEX = os.path.expanduser("~/.agentframework/tools/codex-env/node_modules/.bin/codex")
CFGSRC = os.path.expanduser("~/.agentframework/harness/agent/cfg")
TS = subprocess.run(["date", "+%Y-%m-%dT%H:%M:%S%z"], capture_output=True, text=True).stdout.strip()


def sha12(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:12]


def h(p):
    if os.path.isdir(p):
        acc = {}
        for root, _, fs in os.walk(p):
            for f in sorted(fs):
                fp = os.path.join(root, f)
                acc[os.path.relpath(fp, p)] = hashlib.sha256(io.open(fp, "rb").read()).hexdigest()
        return {"path": p, "files": acc}
    return {"path": p, "sha256": hashlib.sha256(io.open(p, "rb").read()).hexdigest(), "bytes": os.path.getsize(p)}


# ① bins-r600.json（同 runner 第 0 步算法；跑后补生成, 原因见 report §起手闸/环境）
prereg = json.load(io.open(os.path.join(R, "prereg-r600.json"), encoding="utf-8"))
rep = {
    "note": "runner 第 0 步落盘 (先写后跑闸之后, 起臂之前); 全臂共用同一枚二进制 ⇒ 臂身份单变量由构造保证。"
            "**本件为跑后补生成**: 首跑时 runner 内联 heredoc 的臂名未随派生替换 ⇒ KeyError('R600D'), "
            "起臂前那份缺档（如实登记于 report-r600.md）；补生成用同算法同输入, 并由 bin-sha-check.json "
            "(BIN_SHA_BEFORE==AFTER) + 逐跑次 arm_env.txt 双证臂身份。",
    "generated_after_run": True, "generated_at": TS,
    "bin_all_arms": h(BIN), "codex": h(CODEX), "cfg_src": h(CFGSRC),
    "arm_env": {k: prereg["arms"][k].get("env") for k in ("C1", "T", "C")},
    "bin_sha_before_after": json.load(io.open(os.path.join(D, "bin-sha-check.json"), encoding="utf-8")),
}
json.dump(rep, io.open(os.path.join(R, "bins-r600.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("[bins] bin sha256 =", rep["bin_all_arms"]["sha256"][:16], "bytes =", rep["bin_all_arms"]["bytes"])

# ② 登记行
reg = json.load(io.open(os.path.join(REPO, "docs/verification-registry.json"), encoding="utf-8"))
ev_path = os.path.join(REPO, "docs/evidence/RF0001/R600-repair-carryover.md")
inst_path = os.path.join(R, "judge_r600.py")
cap = (
    "R1 管道回灌修复环「带现状」（用户令 2026-09-20「放行」；定因 = R585–R599 缺口 100% 集中 wythoff 族、"
    "失败臂产物在**题面公开用例**上即失败而管道已回放已回灌修复仍同错类 ⇒ 无状态管道下修复为「盲修」）。"
    "新增 `src/agent/r1/ArtifactCarryover.cs`（**只做字节搬运**：按执行器 write_file 步骤重读盘上原文, 单文件 4096B/总量 16384 字符预算, "
    "超限截断留显式标记, 越界/盘上缺失/含 NUL 二进制不随附但显式列出, `__` 前缀生成物目录静默跳过; 语言无关, 不解析语义不识别后缀）"
    "+ `R1Options` 新轴 `AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER`（**缺省 on** = 产品默认档即治疗档; =0/off/false ⇒ 关且 user 轮逐位等于旧行为）"
    "+ `R1Pipeline` 两处回灌修复点（探针证据修复 / 执行证据修复）接线 + 台账字段 `artifact_carryover_rounds/chars`（轴关恒 0 ⇒ 字段不出现 ⇒ 旧台账逐字节同）。"
    "**真机单变量 A/B**（同二进制 sha12 8c3ade04d542 / 同题集 e0c667c2a313c04b / 同剂量键 / 窗集 w184–w186 × T3+C3+C1 1）: "
    "J1 机制 **PASS**（T 8/9 跑次随附轮数≥1, C 0/9）· J2 修复收敛（主）**PASS**（T 3/9 Wilson[0.1206,0.6458] vs C 1/9 Wilson[0.0199,0.435]）· "
    "J3 成本 **PASS**（T max calls 4 = C max calls 4, 增量只在修复轮）· J4 能力（次级/欠功率）**FAIL**（T 4/9 vs C 3/9, 逐窗 2/3·0/3·2/3 vs 1/3·2/3·0/3 ⇒ w185 窗下降）。"
    "闸: 定向 7/7 · 全量 1943/1943（前态 1936+7）· 形式门禁 14/14 · API 基线 +8/−0 · AOT rc=0 IL 警告 0 原生 ELF 19,735,472 B。"
)
row = {
    "id": "r600.repair-carryover",
    "level": "L3",
    "owner_round": "R600",
    "capability": cap,
    "evidence_cmd": ("python3 eval/rover/r600/judge_r600.py --D $HOME/.agentframework/harness/runs/r600 --pd eval/rover/r600"
                     " && dotnet test src/agent.tests -c Release --filter \"FullyQualifiedName~ArtifactCarryoverTests\""),
    "evidence_path": "docs/evidence/RF0001/R600-repair-carryover.md",
    "evidence_generated_with": {
        "evidence_kind": "artifact", "pin_status": "frozen", "pin_reason": "archived-per-round",
        "artifact_sha12": sha12(ev_path),
        "instrument": "eval/rover/r600/judge_r600.py", "instrument_sha12": sha12(inst_path),
        "binding": "audit-pin", "audited_by_round": "R600",
    },
    "negative_control": (
        "① 判别性负控（真机同窗同二进制）: 对照档 C = 同二进制 + `AGENTFRAMEWORK_R1_ARTIFACT_CARRYOVER=0` ⇒ 9/9 跑次台账**无** "
        "artifact_carryover_rounds 字段（机制不得无差别触发）; ② 单测级负控: 一次即过的跑次**不产生**随附块与字段（机制只在回灌修复轮挂上）; "
        "③ 零回归（逐位前缀）: 同场景轴关 vs 轴开 ⇒ 去掉 `</repair>` 闭合标记后轴开消息 = 轴关消息 + 追加块（只增不改, 调用数同为 2 ⇒ 同预算）; "
        "④ 边界负控（有牙）: 越界路径 `../x` / 盘上缺失 / `__pycache__` 生成物 / 含 NUL 二进制 —— 前二只列名不搬内容、生成物静默跳过（不入任何列表）、二进制只报大小; "
        "⑤ 预算负控: 单文件超限必留显式截断标记、总量超限必落「未随附」尾注（不静默丢弃）。"
    ),
}
rows = [r for r in reg["rows"] if r.get("id") != row["id"]]
rows.append(row)
reg["rows"] = rows
reg["updated_round"] = "R600"
with io.open(os.path.join(REPO, "docs/verification-registry.json"), "w", encoding="utf-8") as fh:
    json.dump(reg, fh, ensure_ascii=False, indent=1)
    fh.write("\n")   # EXP1-Q40 尾 LF 契约（提交面规范形）
print("[registry] rows =", len(rows), "updated_round =", reg["updated_round"],
      "artifact_sha12 =", row["evidence_generated_with"]["artifact_sha12"],
      "instrument_sha12 =", row["evidence_generated_with"]["instrument_sha12"])
