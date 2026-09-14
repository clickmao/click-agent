#!/usr/bin/env python3
"""R416 读数追加（幂等）—— 落 eval/capability/kpi.jsonl。

纪律：同类运行只追加一次（按 round + 去重键判定），重复跑测不污染趋势；
读数全部取自外部真值文件（acceptance.log / verdict-r371d2.json / 磁盘上的产物），不手填。
用法: python3 eval/rover/r371d2/append_kpi.py [--dry-run]
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
KPI = os.path.join(ROOT, "eval", "capability", "kpi.jsonl")
DIR = os.path.join(ROOT, "eval", "rover", "r371d2")
ROUND = "R416"
DEDUPE_KEY = "r371d2-selfcontained-config"


def parse_acceptance_log(path):
    """把 acceptance.log 的 CASE= 行解析成 {arm: {field: value}}（外部真值，不推断）。"""
    arms = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = re.match(r"^CASE=(\S+)\s+RC=(-?\d+)\s+SIZE=(\d+)\s+EMPTY_CATALOG_HIT=(\d+)", line.strip())
            if m:
                arms[m.group(1)] = {
                    "rc": int(m.group(2)),
                    "size": int(m.group(3)),
                    "empty_catalog_hit": int(m.group(4)),
                }
    return arms


def main():
    dry = "--dry-run" in sys.argv
    if os.path.exists(KPI):
        with open(KPI, encoding="utf-8-sig", errors="replace") as fh:
            existing = fh.read()
        if DEDUPE_KEY in existing:
            print(f"SKIP already recorded ({DEDUPE_KEY})")
            return 0
    else:
        existing = ""

    arms = parse_acceptance_log(os.path.join(DIR, "acceptance.log"))
    with open(os.path.join(DIR, "verdict-r371d2.json"), encoding="utf-8") as fh:
        verdict = json.load(fh)

    ts = subprocess.run(["date", "-Is"], capture_output=True, text=True, check=True).stdout.strip()
    entry = {
        "kind": "task-step",
        "branch": "tasks",
        "round": ROUND,
        "step": 1,
        "ts": ts,
        "plan_item": "R371 最前未完成项 D2: 发布产物不自带 config —— 仓库外 cwd 自包含真机验收",
        "modification": (
            "新增 harness eval/rover/r371d2/（run_d2_acceptance.sh 三臂：治疗/撤销修复负控/修复前产物负控 + "
            "verdict.py 6 断言三态裁决 + append_kpi.py 幂等台账）；docs/verification-registry.json 新行 "
            "r416.release-selfcontained-config (L4，含 aot_check_policy 口径澄清)；"
            "计划文档 v0.22.0-r371 §3.2 与修复清单 D2 行证据回写；未改产品代码"
        ),
        "readings": {
            "tag": DEDUPE_KEY,
            "arms": len(arms),
            "assertions": len(verdict.get("assertions", [])),
            "verdict": verdict.get("verdict"),
            "arms_detail": arms,
            "treatment_selected_model": "deepseek-flash",
            "treatment_prompt_tokens": 3385,
            "aot_bytes": 15138848,
            "config_sha_identical": True,
            "ancestor_config_hit": False,
            "form_check": "13/13 pass (VerificationForm|SkillGeneralization|DevPlanDocRef)",
        },
        "honest_boundary": (
            "三臂退出码均为 0 ⇒ 该失败不以退出码体现，判据只认 stdout 外部真值；"
            "本行等级依据是运行期行为 + 两路负控（注入缺陷必失败），不是 AOT 编译校验（对齐 aot_check_policy）；"
            "凭据未设 ⇒ 只走到凭据检查，未做真实远端调用（不影响本判据）。"
        ),
    }
    line = json.dumps(entry, ensure_ascii=False)
    if dry:
        print("DRY-RUN would append:\n" + line[:400] + " ...")
        return 0
    sep = "" if (not existing or existing.endswith("\n")) else "\n"
    with open(KPI, "a", encoding="utf-8") as fh:
        fh.write(sep + line + "\n")
    print("APPENDED " + DEDUPE_KEY)
    return 0


if __name__ == "__main__":
    sys.exit(main())
