#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R567 器具端口: 从 R566 派生, 逐处替换断言命中 (禁手抄); 差异逐条声明。

差异 (唯一来源 = 本轮设计):
  ① 轮号命名空间 r566→r567 / R566→R567 (含 /tmp/r567, 端口 49447)
  ② WIN0 125→131, NWIN 6 ⇒ 新窗 w131..w136 (与 w119..w124 / w125..w130 并列不相减)
  ③ 臂集 C1 + R567B0 + R567B3: **两臂同一枚二进制, 唯一差异 = 既有开关
     AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR 的值 (0 vs 3)** ⇒ 同窗单变量
  ④ 起手闸条款 prev-postcheck 指 R566 实测振幅 (swing_mb=70) ⇒ MARGIN=70 / REQ=2720
  ⑤ require 18 (3 臂 × 6 窗) —— 与 R566 同数
  ⑥ 候选④ 行使臂换 B0→B3 (R566 实测 B0 每窗恒 1 次调用 ⇒ C4-3 敏感性不可判);
     判据 C4-1/2/3 文本**不变**, 只换行使臂。
零产品源码改动 / 零新增夹具 / 零新增开关。

【R566 自捕在本轮的落实】R566 端口遗漏「分析侧窗口名列表」⇒ 首跑 errors=18/18 / rc=2。
本脚本的替换规则覆盖**一切随轮次/窗集/臂名/dose 取值变化的字面量**, 并有 RESIDUAL 机检
(生成物里出现旧轮号 / 旧窗号 / 旧臂名 / 旧端口 ⇒ 直接 FAIL, 不落盘可用件)。
所有补丁块**必须命中**(MISS>0 ⇒ rc=2), 禁静默忽略。
"""
import io, os, re, sys

REPO = "/home/agentuser/AgentFramework"
SRC = os.path.join(REPO, "eval/rover/r566")
DST = os.path.join(REPO, "eval/rover/r567")

MAP = {
    "run_r566.sh": "run_r567.sh",
    "ingest_r566.py": "ingest_r567.py",
    "kpi_r566.py": "kpi_r567.py",
    "matrix_r566.py": "matrix_r567.py",
    "adjudicate_r566.py": "adjudicate_r567.py",
    "fingerprint_r566.py": "fingerprint_r567.py",
    "gate_margin_r566.py": "gate_margin_r567.py",
    "mem_sample_once.py": "mem_sample_once.py",
    "mem_sampler.py": "mem_sampler.py",
}

HEADER = """#!/usr/bin/env bash
# R567 驱动器: **同窗单变量对照轮** —— 既有开关 AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR 取值 **0 vs 3** × 外部真值 codex,
#             6 新窗 w131..w136; 起手闸振幅余量条款按上轮实测振幅派生行使; 候选④ 指纹/命中率双口径新窗复核
#             (候选④行使臂由 B0 换为 B3 —— R566 实测 B0 每窗恒 1 调用 ⇒ C4-3 敏感性不可判; 判据文本不变)。
# 同一枚二进制 (R556 交付件 sha 320d0eb1…) ⇒ 单变量由**构造**保证 (全臂除该开关取值外 env 逐项相同);
# 同窗 3 臂 (codex 真值 + R567B0 轴=0 + R567B3 轴=3), 6 新窗 (w131..w136; 与 w119..w124 / w125..w130 **并列不相减**)。
# 结构同 run_r566.sh 骨架; 本轮差异 (逐条声明, 其余逐字节相同):
#   ① 轮号命名空间 R566→R567 / r566→r567 (工作目录 /tmp/r567, 端口 49447);
#   ② 窗号 WIN0 125→131, NWIN 6 (w131..w136);
#   ③ 本侧臂 env 定义: **两臂剂量键都显式落盘** (R567B0 =0 / R567B3 =3) —— 单变量 = 该键的**取值**, 其余 env
#      (R1_CONTRACT / R1_MAX_REPAIR=1 / PUBLIC_SELFCHECK / ROLE_FILE / TRANSCRIPT / WORKSPACE / TAG) 逐项相同;
#   ④ 起手闸条款以 `--prev-postcheck` 指 **R566** 运行窗口实测振幅 (swing_mb=70) 派生 MARGIN=70 / REQ=2720;
#   ⑤ 判别力成对控制 (同内存态 2650 vs REQ 反判 + 400MB 占用负控) 与候选④ 指纹/口径恒等式落盘;
#   ⑥ 端口替换规则已覆盖窗口名/臂名/dose 取值并逐项机检 + RESIDUAL 机检 (R566 自捕的遗漏项族)。
# 用法: D=/tmp/r567 PORT=49447 WIN0=131 NWIN=6 bash eval/rover/r567/run_r567.sh
"""

WIN_MAP = [("w%d" % i, "w%d" % (i + 6)) for i in range(125, 131)]


def port(text: str) -> str:
    text = text.replace("r566", "r567").replace("R566", "R567")
    text = text.replace("49446", "49447")
    text = text.replace("WIN0:-125", "WIN0:-131").replace("WIN0=125", "WIN0=131")
    # 分析侧窗口名列表 (R566 自捕遗漏项族: 一切随窗集变化的字面量)
    for a, b in WIN_MAP:
        text = text.replace(a, b)
    # 上一轮实测振幅落盘件: 在通用替换之后执行 (否则刚写入的 r566 会被再换成 r567)
    text = text.replace("eval/rover/r565/gate-postcheck-r565.json",
                        "eval/rover/r566/gate-postcheck-r566.json")
    # 臂名: 第三臂 = 既有剂量轴另一档 3 (R566 为 1)
    text = text.replace("R567B1", "R567B3").replace("agentB1", "agentB3")
    text = text.replace("b1_range", "b3_range").replace("b1-range", "b3-range")
    text = text.replace("b1_rc", "b3_rc").replace('\\"b1\\"', '\\"b3\\"')
    return text


# 补丁块: (文件, 旧文本, 新文本) —— 作用于**已端口化**的文本; 未命中即 FAIL
PATCHES = [
    ("run_r567.sh",
     '  read -r a10 a11 < <(run_agent R567B3 "$W" agentB3 1)\n',
     '  read -r a10 a11 < <(run_agent R567B3 "$W" agentB3 3)\n'),
    ("run_r567.sh",
     'assert int(_doses["R567B3"]["AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"]) == 1, _doses\n',
     'assert int(_doses["R567B3"]["AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"]) == 3, _doses\n'),
    ("run_r567.sh",
     '每窗 = codex 真值 + R567B0(轴=0) + R567B3(轴=1))"',
     '每窗 = codex 真值 + R567B0(轴=0) + R567B3(轴=3))"'),
    ("run_r567.sh",
     'bash eval/rover/r567/run_r567.sh\nset -uo pipefail\n',
     'bash eval/rover/r567/run_r567.sh\nset -uo pipefail\n'),
    # ingest 差异声明: 臂集与 dose 说明
    ("ingest_r567.py",
     '  · 臂 = C1 (codex 外部真值) + R567B0 (MAX_EXEC_REPAIR=0) （产品默认档; 剂量轴按 R561 收口不再复跑）。\n',
     '  · 臂 = C1 (codex 外部真值) + R567B0 (MAX_EXEC_REPAIR=0) + R567B3 (MAX_EXEC_REPAIR=3)\n'
     '    —— 同一枚二进制 (R556 交付件 sha 320d0eb1…), 单变量 = 唯一 env 开关**取值** ⇒ 同窗三臂配对对照;\n'),
    # 候选④ 行使臂换 B0→B3 (判据文本不变)
    ("fingerprint_r567.py",
     '"""R567 候选④ 器具: **判定输入指纹 + 命中率口径恒等式**',
     '"""R567 候选④ 器具 (行使臂 = agentB3 = 剂量轴 3 档; R566 的行使臂 agentB0 结构性恒 1 调用\n⇒ C4-3 敏感性不可判 ⇒ 本轮换臂, C4-1/2/3 判据文本不变): **判定输入指纹 + 命中率口径恒等式**'),
    ("fingerprint_r567.py",
     'for i in range(rng["b0"][0] + 1, rng["b0"][1] + 1):',
     'for i in range(rng["b3"][0] + 1, rng["b3"][1] + 1):'),
    ("fingerprint_r567.py",
     'tp = os.path.join(a.D, win, "agentB0", "g1", "transcript.json")',
     'tp = os.path.join(a.D, win, "agentB3", "g1", "transcript.json")'),
]


def main():
    os.makedirs(DST, exist_ok=True)
    text_cache, miss, ported_pre = {}, [], {}
    for src, dst in MAP.items():
        t = port(io.open(os.path.join(SRC, src), encoding="utf-8").read())
        ported_pre[dst] = t          # 端口化后、人工补丁/表头之前 ⇒ RESIDUAL 机检的靶面
        if dst == "run_r567.sh":
            head, sep, tail = t.partition("set -uo pipefail")
            assert sep, "run_r567.sh 未找到 'set -uo pipefail' 锚点"
            t = HEADER + sep + tail
        text_cache[dst] = t
    for f, old, new in PATCHES:
        if old not in text_cache[f]:
            miss.append((f, old[:60]))
        else:
            text_cache[f] = text_cache[f].replace(old, new)
    for dst, t in text_cache.items():
        io.open(os.path.join(DST, dst), "w", encoding="utf-8").write(t)
    for dst in sorted(text_cache):
        print("%-24s bytes=%d" % (dst, len(text_cache[dst].encode())))
    print("PATCH_MISS=%d" % len(miss))
    for f, o in miss:
        print("  [MISS] %s :: %s" % (f, o.replace("\n", "\\n")))

    # --- RESIDUAL 机检: 旧轮号 / 旧窗号 / 旧臂名 / 旧端口不得残留 -----------------
    bad_tokens = ["r566", "R566", "/tmp/r566", "49446", "agentB1", "R567B1",
                  "b1_range", "b1-range", "b1_rc"] + [w for w, _ in WIN_MAP]
    residual = {}
    ALLOW = "eval/rover/r566/gate-postcheck-r566.json"   # 条款派生源 (上一轮实测振幅) 是**有意**指向 r566
    for dst, t in ported_pre.items():
        hit = [tok for tok in bad_tokens if tok in t.replace(ALLOW, "")]
        if hit:
            residual[dst] = hit
    print("RESIDUAL_FILES=%d (靶面 = 端口化后 / 人工补丁与表头之前)" % len(residual))
    for k, v in residual.items():
        print("  [RESIDUAL] %s :: %s" % (k, v))

    # --- 关键命中核验 ----------------------------------------------------------
    run = text_cache["run_r567.sh"]
    ing = text_cache["ingest_r567.py"]
    mt = text_cache["matrix_r567.py"]
    adj = text_cache["adjudicate_r567.py"]
    kp = text_cache["kpi_r567.py"]
    fp = text_cache["fingerprint_r567.py"]
    checks = {
        "win0_131": "WIN0=${WIN0:-131}" in run,
        "port_49447": "PORT=${PORT:-49447}" in run,
        "dose_0": 'int(_doses["R567B0"]["AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"]) == 0' in run,
        "dose_3": 'int(_doses["R567B3"]["AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"]) == 3' in run,
        "arm_call_3": 'run_agent R567B3 "$W" agentB3 3' in run,
        "require_18": 'len(d["evidence_scope"]["require"]) == 18' in run,
        "prev_postcheck_r566": "eval/rover/r566/gate-postcheck-r566.json" in run,
        "b3_range_arg": '--b3-range "$a10,$a11"' in run,
        "b3_rc_jsonl": "b3_rc" in run and '\\"b3\\"' in run,
        "snap_b3": '"$PDIR/snapshots/$W/R567B3/g1/"' in run,
        "loop_sub_b3": "for sub in codex agentB0 agentB3; do" in run,
        "no_stale_arm": "R567B1" not in run and "/unset" not in run,
        "ingest_three": '("R567B3", "agent", "agentB3", rng(a.b3_range))' in ing,
        "ingest_b3_arg": '--b3-range' in ing,
        "matrix_three": '"arms": ["C1", "R567B0", "R567B3"]' in mt,
        "matrix_wins": '"wins": ["w131", "w132", "w133", "w134", "w135", "w136"]' in mt,
        "matrix_work_default": "/tmp/r567/pc" in mt,
        "adj_three": 'ARMS = ["C1", "R567B0", "R567B3"]' in adj,
        "adj_wins": '"w131", "w132", "w133", "w134", "w135", "w136"' in adj,
        "kpi_three": '("C1", "R567B0", "R567B3")' in kp,
        "fp_exercise_arm_b3": 'rng["b3"]' in fp and '"agentB3", "g1", "transcript.json"' in fp,
        "fp_identity_kept": "identity_ok" in fp and "C4-3_nontrivial" in fp,
        "gate_prev_swing": "prev-postcheck" in text_cache["gate_margin_r567.py"],
    }
    bad = [k for k, v in checks.items() if not v]
    for k in sorted(checks):
        print("  [check] %-22s %s" % (k, "OK" if checks[k] else "FAIL"))
    print("CHECK_FAIL=%d" % len(bad))
    return 2 if (bad or miss or residual) else 0


if __name__ == "__main__":
    sys.exit(main())
