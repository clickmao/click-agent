#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R497 登记行生成器: 从 facts-r497.json (机派生读数) 生成 rows_r497.json。

设计: 数字全部来自 facts (禁手抄); covers 只列**已存在于仓内**的路径 (register 形式门禁会逐条核)。
"""
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
D = "eval/rover/r497"
F = json.load(io.open(os.path.join(ROOT, "%s/facts-r497.json" % D), encoding="utf-8"))


def sha12(rel):
    p = os.path.join(ROOT, rel)
    return None if not os.path.exists(p) else hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]


def row(id_, level, cap, cmd, path, instrument, covers, neg):
    return {
        "id": id_, "level": level, "owner_round": "R497", "capability": cap,
        "evidence_cmd": cmd, "evidence_path": path,
        "evidence_generated_with": {
            "evidence_kind": "artifact", "pin_status": "frozen", "pin_reason": "archived-per-round",
            "artifact_sha12": sha12(path), "instrument": instrument, "instrument_sha12": sha12(instrument),
            "binding": "audit-pin", "audited_by_round": "R497"},
        "covers": covers, "negative_control": neg,
    }


A = F["arms"]
L = F["ladder"]
acc = F.get("acceptance") or {}
FACE = F["faces"]


def n(arm, k):
    v = (A.get(arm) or {}).get(k)
    return "?" if v is None else v


r1 = row("r497.telemetry-face-truth-reclose", "L2",
         "**①打点面真值收口 (R496 判据红的那个通道)**: R496 实证 `local_decision_ledger` 打点行仍写 raw 码 "
         "(`LCM-<12hex>`), 而打点落在**臂可读的工作区内** ⇒ 关轴臂 `run_command` 读自己的遥测即得真值。R497 把该 emit 点改为 "
         "`code8 = sha256(code)[:8]` + `key_id = sha256(密钥)[:8]` **只留指纹**; 判据三处并行: "
         "(a) C# 单测全仓扫 `.cs` 的 raw 直写 (收窄到「第二参名含 ledger/LCM」以免误伤 HTTP `errCode`); "
         "(b) `face_ext` HARD-3b 逐臂扫打点文件与点级 kv (禁 `code` 键、必 `code8`+`key_id`、与台账指纹集一致); "
         "(c) `truth_reclose_scan` 全轮逐文件扫描 (含 `rundata-*/**`/`host-*.log`/`tel-*`), 产品面出现**非诱饵**码字面量即红。"
         "本轮读数: 打点 raw 码字面量 %(raw)s; 全仓 verdict=%(tr)s; src 面 raw 直写 %(srchits)s 处。" % {
             "raw": ", ".join("%s:%s" % (a, (FACE.get(a) or {}).get("HARD-3b", {}).get("raw_code_literals_in_tel")) for a in A),
             "tr": F["truth_reclose"]["verdict"], "srchits": len(F["truth_reclose"]["src_face_raw_emit"] or [])},
         "python3 %s/face_ext_r497.py --arm T1 --dir %s --mount on --ab on --canary R497-OOB-CANARY-9f3a1c7e; "
         "python3 %s/truth_reclose_scan_r497.py --dir %s --arms B,T0,T2,T1,T1n,O1; "
         "python3 %s/gate_port_parity_r497.py" % (D, D, D, D, D),
         "%s/truth-reclose-r497.json" % D, "%s/truth_reclose_scan_r497.py" % D,
         ["%s/prereg_r497.json" % D, "%s/face_ext_r497.py" % D, "%s/tel-T1/host.jsonl" % D,
          "%s/ledger-T1.jsonl" % D, "%s/grid/task-p17-code.json" % D,
          "src/agent/IndustrialAgentV2.cs", "src/agent.tests/R497FingerprintAndSynonymTests.cs"],
         "① 单测正控: 源码扫描器必须能命中旧写法 (`(\"code\", ledgerCode)`) ⇒ 本轮先红后绿; "
         "② 网格自带诱饵码 LCM-deadbeef1234 从网格机派生为 decoy 集合 (产品面出现诱饵不算泄漏) ⇒ 判据不做单侧放宽; "
         "③ 对照臂 (mount off) 线上无码可枚举 ⇒ 全局扫描用**并集**（覆盖洞已闭合）。")

r2 = row("r497.forced-oob-refusal-witness", "L4",
         "**③越界拒绝见证 + 差分正控 (R496 '未测到' 项的强制触发)**: R496 的工具面收口在真机上 never fired "
         "(拒绝见证 0)。R497 在网格追加 t16 **强制越界轮** (命令面 `run_command cat /tmp/r497oob/canary.txt` + "
         "文件面 `read_file` 同路径), 并加 AB=off 消融臂 O1 作**正控**: "
         "AB=on 臂命令面 rc=126 且**不回显正文** (`越界路径已隐去`), 文件面 rc=-1 恒拒 (源码上 `Resolve` 无开关); "
         "AB=off 臂同命令 rc=0 且 canary 正文进 tool 消息 ⇒ 判定器有判别力。"
         "读数: 命令面拒绝 %(refcmd)s; canary 入面 %(canary)s (AB=on 臂必须 0, O1 为 1+)。" % {
             "refcmd": ", ".join("%s:%s" % (a, (FACE.get(a) or {}).get("HARD-6", {}).get("refusal_cmd_face")) for a in A),
             "canary": ", ".join("%s:%s" % (a, (FACE.get(a) or {}).get("HARD-6", {}).get("canary_total")) for a in A)},
         "python3 %s/face_ext_r497.py --arm T0 --dir %s --mount off --ab on --canary R497-OOB-CANARY-9f3a1c7e; "
         "python3 %s/face_ext_r497.py --arm O1 --dir %s --mount off --ab off --canary R497-OOB-CANARY-9f3a1c7e" % (D, D, D, D),
         "%s/face-ext-T0.json" % D, "%s/face_ext_r497.py" % D,
         ["%s/prereg_r497.json" % D, "%s/calls-T0.jsonl" % D, "%s/calls-O1.jsonl" % D,
          "%s/face-ext-O1.json" % D, "%s/grid/task-p17-code.json" % D,
          "src/agent/action/WorkspaceActionPort.cs"],
         "**正控 = O1 臂 (AB=off)**: 同命令真执行且 canary 正文入面 (5 面命中) ⇒ 「拒绝」不是靠把正文抹掉换来的; "
         "文件面无消融开关 (结构恒拒) ⇒ 该面的正控**未做**, 已在报告里记未测到。")

r3 = row("r497.repeat-synonym-local-digestion", "L2",
         "**④复述同义族本地消化扩面**: R465 复述族只覆盖「再讲一遍/从头再说」等 16 条标记。R497 扩面 +4 "
         "(`复述一次/说一遍/讲一遍/念一遍`), **白名单字符集逐字节未动** (单测机检: 新标记每个用字都在 R465 白名单内)。"
         "同轮拿到优先级铁律的机检: 前置门链 **MechanicalPass 先于**复述吸收 ⇒ 含请求信号(把/说/请…)、数字、问号、`/`、反引号的"
         "复述句**不会**被本地消化 (t17 初版「把上一条说一遍。」即栽在此, 已改「从头念一遍。」并加优先级单测)。"
         "真机读数 (单变量对): T1 (skip on) t17 台账 kind=%(k1)s 且远端调用 %(c1)s、消化件=上一轮答复 (回放=%(r1)s); "
         "T1n (skip off) t17 kind=%(k2)s 且远端调用 %(c2)s ⇒ 该扩面在真机上可测、可消融。" % {
             "k1": (FACE.get("T1") or {}).get("T17", {}).get("ledger_turn17_kind"),
             "c1": (FACE.get("T1") or {}).get("T17", {}).get("calls_for_t17"),
             "r1": (FACE.get("T1") or {}).get("T17", {}).get("t17_reply_equals_t16"),
             "k2": (FACE.get("T1n") or {}).get("T17", {}).get("ledger_turn17_kind"),
             "c2": (FACE.get("T1n") or {}).get("T17", {}).get("calls_for_t17")},
         "python3 %s/gate_port_parity_r497.py --out %s/gate-parity-r497.json; "
         "python3 %s/face_ext_r497.py --arm T1n --dir %s --mount on --ab on --canary R497-OOB-CANARY-9f3a1c7e" % (D, D, D, D),
         "%s/gate-parity-r497.json" % D, "%s/gate_port_parity_r497.py" % D,
         ["%s/prereg_r497.json" % D, "%s/face-ext-T1.json" % D, "%s/face-ext-T1n.json" % D,
          "%s/ledger-T1.jsonl" % D, "%s/ledger-T1n.jsonl" % D,
          "src/agent.modelqueue/LocalGenerationPort.cs", "src/agent.tests/R497FingerprintAndSynonymTests.cs",
          "eval/rover/r468/gate_rules.py"],
         "① 负控: `讲细一点。/换个说法。/重来一遍。/重做一遍。/再来一次。` 必须**不**吸收 (R434 硬线 + 白名单纪律), "
         "本轮全部保持 False; ② 消融臂 T1n (repeat_skip=off) 使 t17 回到远端 ⇒ 差异不是判据解释出来的; "
         "③ 器具↔产品双实现 (C# vs `eval/rover/r468/gate_rules.py`, 后者从源码派生) %s 例逐位一致。" % F["gate_parity"]["cases"])

r4 = row("r497.axis-decomposed-ladder", "L2",
         "**②臂阶梯轴分解 (修 R496 的两轴混淆)**: R496 的 T0→T1 同时动了通道轴与挂载轴, 归因不可分。R497 插入 "
         "T2 = T0+通道轴 (挂载仍 off), 并把消融臂 T1n (复述跳轮 off) 与 O1 (越界面 off) 并入同一窗 ⇒ 六臂各自**单变量**。"
         "阶梯读数: %s。" % "; ".join("%s calls %s→%s (%s%%) / tokens %s→%s (%s%%)"
                                    % (k, (v.get("calls") or [None, None])[0], (v.get("calls") or [None, None])[1],
                                       v.get("calls_drop_pct"), (v.get("total_tokens") or [None, None])[0],
                                       (v.get("total_tokens") or [None, None])[1], v.get("total_tokens_drop_pct"))
                                    for k, v in L.items()),
         "python3 %s/analyze_r497.py --dir %s" % (D, D),
         "%s/kpi-r497.json" % D, "%s/analyze_r497.py" % D,
         ["%s/calls-B.jsonl" % D, "%s/calls-T0.jsonl" % D, "%s/calls-T2.jsonl" % D, "%s/calls-T1.jsonl" % D,
          "%s/calls-T1n.jsonl" % D, "%s/calls-O1.jsonl" % D, "%s/flags-T2.json" % D, "%s/flags-T1n.json" % D,
          "%s/flags-O1.json" % D, "%s/run_arm_real_r497.sh" % D],
         "跨轮禁相减 (网格/判据器已改版, B 臂本轮同窗重跑); 方向性**不预设** (通道轴读数若为正也照报); "
         "质量面读数单列, 不并入 token 降幅。")

r5 = row("r497.remote-call-token-drop", "L2",
         "**验收读数 (同窗同网格同二进制)**: B(全关) vs T1(闸+跳轮+声明门+pair_trim+通道+挂载) 的远端调用数与 total tokens, "
         "由中继 usage 派生 (禁手抄)。本轮读数: B %s 调用 / %s tok; T1 %s 调用 / %s tok; "
         "阶梯 %s。" % (n("B", "calls"), n("B", "tokens"), n("T1", "calls"), n("T1", "tokens"),
                       "; ".join("%s: calls %s→%s (%s%%), tokens %s→%s (%s%%)"
                                 % (k, (v.get("calls") or [None, None])[0], (v.get("calls") or [None, None])[1],
                                    v.get("calls_drop_pct"), (v.get("total_tokens") or [None, None])[0],
                                    (v.get("total_tokens") or [None, None])[1], v.get("total_tokens_drop_pct"))
                                 for k, v in L.items())),
         "python3 %s/analyze_r497.py --dir %s" % (D, D),
         "%s/kpi-r497.json" % D, "%s/analyze_r497.py" % D,
         ["%s/usage-B.jsonl" % D, "%s/usage-T0.jsonl" % D, "%s/usage-T2.jsonl" % D, "%s/usage-T1.jsonl" % D,
          "%s/usage-T1n.jsonl" % D, "%s/usage-O1.jsonl" % D, "%s/flags-B.json" % D, "%s/flags-T1.json" % D,
          "%s/grid/task-p17-code.json" % D, "%s/prereg_r497.json" % D],
         "每臂 n=1 (无置信区间) ⇒ 只报读数与阶梯, 不做显著性宣称; 质量面 (judge_adv/judge_code/leak) 单列对照, "
         "token 降幅不以质量面换; 上游空正文/隔离调用单列 (R493 归因)。")

NEW = [r1, r2, r3, r4, r5]
out = os.path.join(ROOT, "%s/rows_r497.json" % D)
with io.open(out, "w", encoding="utf-8") as f:
    json.dump(NEW, f, ensure_ascii=False, indent=1)
print("[mkrows] +%d 行 → %s" % (len(NEW), out))
for r in NEW:
    print("   %-42s %s  artifact=%s inst=%s" % (r["id"], r["level"],
                                                r["evidence_generated_with"]["artifact_sha12"],
                                                r["evidence_generated_with"]["instrument_sha12"]))
