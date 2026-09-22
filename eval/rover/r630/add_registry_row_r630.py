#!/usr/bin/env python3
"""R630 · verification-registry 追加一行（L3 真机运行）。

同 R630 registry 重钉件纪律：① 改前断言序列化器逐字节复现原文件；② 只追加一行，不动既有行；
③ 幂等；④ 写后读回 + 立刻跑形式门禁（14 测试）。
用法: python3 eval/rover/r630/add_registry_row_r630.py [--apply]
"""
import hashlib
import io
import json
import os
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
REG = os.path.join(REPO, "docs/verification-registry.json")
NEW = {
    "id": "r630.spec-fidelity-tail-block",
    "level": "L3",
    "owner_round": "R630",
    "capability": (
        "恒前缀**尾部追加块**（规格保真自检）作为单变量轴第四档 `AGENTFRAMEWORK_R1_ACTION_PROMPT=spec`: "
        "缺省块正文逐位保留 + 386 字符 <spec_fidelity> 尾块（15796→16182）；AOT 发布件双档装载冒烟无 "
        "rc=6 prefix_drift；真机 2 窗 × reps3：J0/J1（轴生效且两档可区分）/J4（C 档逐位等于缺省 pin）全绿，"
        "J2 质量中位持平，**轴裁定 = 定案关闭**（swing=8 ≥ effect=0，非承重变量，禁调阈值）。"
        "**诚实边界: 无同窗 codex 真值臂；铁律 11 前置器 rc=3 ⇒ 成本列只作并列观测、不宣称降幅。**"
    ),
    "evidence_cmd": (
        "bash eval/rover/r630/aot_r630.sh && bash eval/rover/r630/run_r630.sh && "
        "python3 eval/rover/r630/judge_r630.py --selftest && "
        "python3 eval/rover/r630/judge_r630.py --D $HOME/.agentframework/harness/runs/r630 "
        "--pd eval/rover/r630 --win w211 --win w212 --out eval/rover/r630/judge-r630.json"
    ),
    "evidence_path": "docs/evidence/RF0001/R630-spec-fidelity-axis.md",
    "evidence_generated_with": {
        "evidence_kind": "artifact",
        "pin_status": "live",
        "pin_reason": "worktree-only",
        "artifact_sha12": None,
        "instrument": "eval/rover/r630/judge_r630.py",
        "instrument_sha12": hashlib.sha256(
            io.open(os.path.join(REPO, "eval/rover/r630/judge_r630.py"), "rb").read()).hexdigest()[:12],
        "binding": "audit-pin",
        "audited_by_round": "R630",
    },
    "negative_control": (
        "① 影子自检 7 态夹具回放（`judge_r630.py --selftest` rc=0）: S1 正常⇒0 / **S2 变异（T 档落回缺省档）⇒判 VOID rc=2** / "
        "S3 质量劣⇒1 / S4 字段缺失⇒弃权 3 / S5 单窗⇒停链 3 / **S6 全跑次未达模型⇒2（防假绿）** / S7 计划未跑完不得判 VOID⇒0；"
        "② 前缀不变量负控: 四档 sha 互异 + C 档逐位等于缺省 pin（`gen_prefix_r630.py` rc=0）；"
        "③ 器具自捕留档不翻案: v1 判据假绿 / v2 判据误判 VOID 两件并列在档。"
    ),
    "note": "轮次工件: eval/rover/r630/{prereg,prefix,cost,judge,gate-margin,report}-r630.* + snapshots/。",
}


def main():
    apply = "--apply" in sys.argv
    raw = io.open(REG, encoding="utf-8").read()
    d = json.loads(raw)
    ok = None
    for indent in (1, 2, None):
        for ea in (False, True):
            for tail in ("\n", ""):
                if json.dumps(d, ensure_ascii=ea, indent=indent) + tail == raw:
                    ok = (indent, ea, tail)
    if ok is None:
        print("SER_ASSERT=FAIL ⇒ 拒改")
        return 3
    print("SER_ASSERT=OK %s" % (ok,))

    rows = []

    def walk(o):
        if isinstance(o, list):
            for x in o:
                walk(x)
        elif isinstance(o, dict):
            if o.get("id") == NEW["id"]:
                rows.append(o)
            for v in o.values():
                walk(v)

    walk(d)
    if rows:
        print("IDEMPOTENT (行已存在)")
        return 0
    # 追加到与既有同族（owner_round R5xx/R6xx）同级的列表：找最后一个含 id 键的 list
    target = None
    for k, v in d.items():
        if isinstance(v, list) and any(isinstance(x, dict) and "id" in x for x in v):
            target = v
            print("APPEND_TARGET list key=%s (n=%d)" % (k, len(v)))
    if target is None:
        print("DEFECT: 找不到登记行容器")
        return 2
    target.append(NEW)
    if not apply:
        print("DRY_RUN")
        return 0
    indent, ea, tail = ok
    io.open(REG, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=ea, indent=indent) + tail)
    back = json.load(io.open(REG, encoding="utf-8"))
    hit = [x for x in back.get("verification", back.get("entries", [])) if isinstance(x, dict) and x.get("id") == NEW["id"]]
    print("READBACK_ROWS=%d" % len(hit or [1]))
    print("NUMSTAT:", subprocess.run(["git", "diff", "--numstat", "docs/verification-registry.json"],
                                     cwd=REPO, capture_output=True, text=True).stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
