#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R500 登记表写入 (幂等 + 并发守卫)。用法: python3 register_r500.py [--apply]"""
import hashlib
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "r499"))
from check_concurrent_touch import guard_or_die, verify_or_die  # noqa: E402

REG = "docs/verification-registry.json"
ROUND = "R500"
APPLY = "--apply" in sys.argv


def sha12(path):
    h = hashlib.sha256()
    with io.open(path, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()[:12]


def row(i, cap, cmd, path, instrument, nc):
    r = {
        "id": "r500." + i,
        "level": "L2",
        "owner_round": ROUND,
        "capability": cap,
        "evidence_cmd": cmd,
        "evidence_path": path,
    }
    if os.path.isfile(path):
        r["evidence_generated_with"] = {
            "evidence_kind": "artifact",
            "pin_status": "live",
            "pin_reason": "worktree-only",
            "artifact_sha12": None,  # R2e: live 行不得带 pin (只有冻结行才钉字节)
            "instrument": instrument,
            "instrument_sha12": sha12(instrument) if os.path.isfile(instrument) else None,
            "binding": "audit-pin",
            "audited_by_round": ROUND,
        }
    r["negative_control"] = nc
    return r


ROWS = [
    row(
        "paraphrase-channel-real-4arms",
        "**本地改写通道真机 4 臂 (同窗单变量, 先于任何结论)**: C(闸 off, 端口 49910/49912) + P1/P2/P3(闸 on, 49920/49922, 49930/49932, 49940/49942), 同一 AOT 产物 "
        "`/tmp/pub_r499/agenthost` (sha16 3a79bbb4cfbec807, IL 0) 与同一网格 (task-p17-code.json 与 r497 逐字节同)。读数: C 13 调用 / 71,294 tok; P1 12/78,556(+10.19%); "
        "P2 12/72,222(+1.30%); P3 12/70,415(−1.23%); 中位 +1.30%。teardown 4/4 clean (procs=None/listeners=[])。臂 flags 正控: C local_paraphrase=off, P*=on。",
        "python3 eval/rover/r499/analyze_r499.py --dir eval/rover/r499 --out eval/rover/r499/analyze_r499.json",
        "eval/rover/r499/analyze_r499.json",
        "eval/rover/r499/analyze_r499.py",
        "实测对照: ① 臂 flags 正控 C=off / P*=on; ② H4 阴性对照 = C 臂 t8 basis 不得含 paraphrase 且须有远端调用 (实测 `mechanical:nonack→remote` ✓); ③ 判据器负控 `nc_c_absorb` 对 R500 C 臂实跑 ⇒ VERDICT=RED red=1 rc=1 (期望 1) ⇒ 判据器不是「恒绿」。[NC nc_c_absorb] rc=1。",
    ),
    row(
        "paraphrase-channel-deadcode-rootcause",
        "**根因 (机检 fail-closed, 非推断)**: P 臂 t8 (`换个说法。`, msg_sha16 eb52df19f61ca2b8) 的 `local_turn_gate_reject.kv.r1_raw_len == 21 == len(\"mechanical:paraphrase\")` ⇒ 判决来自 "
        "`src/agent/IndustrialAgentV2.cs:1607-1613` 的**改写吸收支** (族匹配器工作正常), 随即被 `:1636-1638` 的 R444 后置否决 `Skip ∧ ¬Ack ∧ ¬IsPureRepeat` (**未豁免改写族**) 改写为 "
        "`Pass(\"gate:skip_rejected_nonack\")` ⇒ 远端; 同轮 `:1642-1649` 落盘 `gate_prefilter_invariant_violation`。⇒ R498 改写通道在生产形态为**死代码**。机检 K1–K5 全过 (C 臂 0 reject / 0 violation, basis=mechanical:nonack→remote)。",
        "python3 eval/rover/r500/rootcause_check_r500.py eval/rover/r499 eval/rover/r500/rootcause_r500.txt",
        "eval/rover/r500/rootcause_r500.txt",
        "eval/rover/r500/rootcause_check_r500.py",
        "实测阴性对照 (真跑): 删掉 P1 的 `local_turn_gate_reject` 行 ⇒ 机检 K1/K2 立红 ⇒ VERDICT=NOT_CONFIRMED rc=1 (期望 1); C 臂同消息 sha16 ⇒ 0 reject / 0 violation 且 basis=`mechanical:nonack→remote` (实测) ⇒ 证伪「该打点是全体臂共有噪声」。[NC K1-drop-reject-row] rc=1。",
    ),
    row(
        "arm-runner-arg-mismatch",
        "**自伤登记 (可复核)**: `eval/rover/r499/run_rest_r499.sh` P 行传 5 实参 (`P 1 r499 49920 49922`) 而执行器形参 4 个 (`<ARM> [tag] [relay_port] [api_port]`) ⇒ `relay_real_r475.py:29 PORT=int('r499')` ValueError ⇒ 首跑 P 臂 0 读数 "
        "(C 臂已完成 rc=0, 读数有效故未重跑)。零读数残留归档 `eval/rover/r499/invalid-run2-partial-P1/`; 修正版 `eval/rover/r500/run_p_arms_r500.sh` (4 实参 + 闸连续 2 次 PASS + 非零 rc 即中止)。",
        "bash eval/rover/r500/run_p_arms_r500.sh",
        "eval/rover/r499/invalid-run2-partial-P1/flags-P1.json",
        "eval/rover/r500/run_p_arms_r500.sh",
        "阴性对照 = 归档残留中 `calls-P1.jsonl`/`usage-P1.jsonl` 实测均 0 字节 (零读数) ⇒ 证伪「首跑 P 臂其实产出了读数」; 阳性对照 = `relay-P1.log` 留存 `ValueError: invalid literal for int() with base 10: 'r499'` 踪迹 ⇒ 缺陷可复现。修正版起手断言: 4 实参 + 闸连续 2 次 PASS + 非零 rc 即中止矩阵。",
    ),
    row(
        "nc-pending-not-judgeable",
        "**负控未判 (not_run, 非通过)**: R499 判据器的三态负控中 `nc_c_absorb` 已抓 (干跑 R497/T1, 注入即 rc=1)。另两态 `nc_drop_gate_row` / `nc_template_reply` 的载体是「通道生效的 P 臂」⇒ H1 已证伪 (3/3), "
        "载体不存在 ⇒ **不可判**, 如实登记 `not_run`, 禁当 0 或通过。",
        "python3 eval/rover/r499/judge_paraphrase_r499.py --dir eval/rover/r499 --arm P1 --mode P",
        "eval/rover/r499/analyze_r499.json",
        "eval/rover/r499/judge_paraphrase_r499.py",
        "**未跑 (not_run) 禁当通过**: 两态负控的载体是「改写通道生效的 P 臂」, 而 H1 已证伪 (3/3 吸收被否决) ⇒ 载体不存在 ⇒ 不可判。已实测的邻近对照 = `nc_c_absorb` 对 R500 C 臂 rc=1 red=1; `nc_drop_gate_row`/`nc_template_reply` 待 R501 修正后复测时补跑。",
    ),
]

d = json.load(io.open(REG, encoding="utf-8-sig"))
rows = d["rows"]
tok = None
if APPLY:
    tok = guard_or_die(REG, ROUND)
    rows[:] = [r for r in rows if r.get("owner_round") != ROUND]
    rows.extend(ROWS)
    d["updated_round"] = ROUND
    with io.open(REG, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")
    verify_or_die(REG, ROUND, tok)
    back = json.load(io.open(REG, encoding="utf-8-sig"))
    got = [r["id"] for r in back["rows"] if r.get("owner_round") == ROUND]
    print("APPLIED rows=%d total=%d ids=%s" % (len(got), len(back["rows"]), got))
else:
    print("DRYRUN add=%d total_after=%d ids=%s" % (len(ROWS), len(rows) - len([r for r in rows if r.get("owner_round") == ROUND]) + len(ROWS), [r["id"] for r in ROWS]))
