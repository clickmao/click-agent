#!/usr/bin/env python3
"""R520 登记行证据绑定修复: evidence_generated_with 必须是对象 (R2e/R2f), 且 instrument_sha12 取现盘字节。

纪律 (R409): 改写前先证「序列化器逐字节复现原文件」; 改写后读回校验。
"""
import hashlib
import json
import os
import sys

PATH = "docs/verification-registry.json"


def sha12(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:12]


FIX = {
    "agent.shadow-path-gate": {
        "evidence_kind": "artifact",
        "pin_status": "live",
        "pin_reason": "archived-per-round",
        "artifact_sha12": None,
        "instrument": "eval/rover/r520/shadow_check_r520.py",
        "instrument_sha12": sha12("eval/rover/r520/shadow_check_r520.py"),
        "binding": "audit-pin",
        "audited_by_round": "R520",
    },
    "external.contrast-orch-arm-r520": {
        "evidence_kind": "artifact",
        "pin_status": "live",
        "pin_reason": "archived-per-round",
        "artifact_sha12": None,
        "instrument": "eval/rover/r520/grade_r520.py",
        "instrument_sha12": sha12("eval/rover/r520/grade_r520.py"),
        "binding": "audit-pin",
        "audited_by_round": "R520",
    },
}

# evidence_path 归一为**文件** (目录聚合按 live 处理易失真; 本轮证据文件真实存在)
EV_PATH = {
    "agent.shadow-path-gate": "eval/rover/r520/REPORT-r520.md",
    "external.contrast-orch-arm-r520": "eval/rover/r520/evidence/orch-report-r520.json",
}
EV_CMD = {
    "external.contrast-orch-arm-r520": "bash eval/rover/r520/run_r520.sh",
}


def main():
    original = open(PATH, encoding="utf-8").read()
    doc = json.loads(original)
    if json.dumps(doc, ensure_ascii=False, indent=2) + "\n" != original:
        print("FAIL: 序列化器不能逐字节复现原文件")
        return 2
    touched = 0
    for row in doc["rows"]:
        rid = row.get("id")
        if rid not in FIX:
            continue
        for p in [FIX[rid]["instrument"]] + [EV_PATH[rid]]:
            if not os.path.exists(p):
                print("FAIL: 证据/器具路径不存在", p)
                return 2
        row["evidence_generated_with"] = FIX[rid]
        row["evidence_path"] = EV_PATH[rid]
        if rid in EV_CMD:
            row["evidence_cmd"] = EV_CMD[rid]
        touched += 1
    if touched != 2:
        print("FAIL: 命中行数 %d != 2" % touched)
        return 2
    open(PATH, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    back = json.loads(open(PATH, encoding="utf-8").read())
    for r in back["rows"]:
        if r.get("id") in FIX:
            g = r["evidence_generated_with"]
            assert isinstance(g, dict) and set(g) == {
                "evidence_kind", "pin_status", "pin_reason", "artifact_sha12",
                "instrument", "instrument_sha12", "binding", "audited_by_round"}, r["id"]
            print("OK", r["id"], "|", r["evidence_path"], "| instrument_sha12 =", g["instrument_sha12"])
    print("ROWS_TOTAL=%d" % len(back["rows"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
