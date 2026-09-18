#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R566 器具端口: 从 R565 派生, 逐处替换断言命中 (禁手抄); 差异逐条声明。

差异 (唯一来源 = 本轮设计):
  ① 轮号命名空间 r565→r566 / R565→R566 (含 /tmp/r566, 端口 49446)
  ② WIN0 119→125, NWIN 6 ⇒ 新窗 w125..w130 (与 w119..w124 并列不相减)
  ③ 臂集 C1 + R566B0 + R566B1: **两臂同一枚二进制, 唯一差异 = 既有开关
     AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR 的值 (0 vs 1)** ⇒ 同窗单变量
  ④ 起手闸条款 prev-postcheck 指 R565 实测振幅
  ⑤ require 12→18 (3 臂 × 6 窗)
零产品源码改动 / 零新增夹具 / 零新增开关。

【自捕 · 本端口遗漏项 (事后补)】本脚本的替换规则**只覆盖文件名/轮号** (r565→r566 / R565→R566 / 端口 / WIN0),
**未覆盖分析侧脚本里的窗口名列表** ⇒ matrix_r566.py:30 / adjudicate_r566.py:23 首跑仍指向 w119..w124,
得到 `errors=18/18` 与 `rc=2 INSTRUMENT_DEFECT` (器具读法缺陷, 非被测缺陷)。修法 = 补窗口名替换后复跑
(`errors=0 / xref=18/18 agree` / 判决 rc=1); 首跑读数不采信。教训 (通用): **端口脚本的替换规则必须覆盖
「一切随轮次/窗集变化的字面量」并逐项机检** (本脚本 14 项断言全绿仍漏该项 ⇒ 断言集本身也是待审对象)。
"""
import io, os, re, sys

REPO = "/home/agentuser/AgentFramework"
SRC = os.path.join(REPO, "eval/rover/r565")
DST = os.path.join(REPO, "eval/rover/r566")

MAP = {
    "run_r565.sh": "run_r566.sh",
    "ingest_r565.py": "ingest_r566.py",
    "kpi_r565.py": "kpi_r566.py",
    "matrix_r565.py": "matrix_r566.py",
    "adjudicate_r565.py": "adjudicate_r566.py",
    "fingerprint_r565.py": "fingerprint_r566.py",
    "gate_margin_r565.py": "gate_margin_r566.py",
    "mem_sample_once.py": "mem_sample_once.py",
    "mem_sampler.py": "mem_sampler.py",
}


def port(text):
    text = text.replace("r565", "r566").replace("R565", "R566")
    text = text.replace("49445", "49446")
    text = text.replace("WIN0:-119", "WIN0:-125")
    # 起手闸条款派生源: 指向上一轮 (R565) 的实测振幅落盘件 (sed 不会改 r563)
    text = text.replace("eval/rover/r563/gate-postcheck-r563.json",
                        "eval/rover/r565/gate-postcheck-r565.json")
    return text


ARM_PATCHES = [
    # run_r566.sh: 第三臂 + 剂量显式
    ("  read -r a00 a01 < <(run_agent R566B0 \"$W\" agentB0 unset)\n",
     "  read -r a00 a01 < <(run_agent R566B0 \"$W\" agentB0 0)\n"
     "  read -r a10 a11 < <(run_agent R566B1 \"$W\" agentB1 1)\n"),
    ("  for sub in codex agentB0; do\n",
     "  for sub in codex agentB0 agentB1; do\n"),
    ("  mkdir -p \"$PDIR/snapshots/$W/C1/g1\" \"$PDIR/snapshots/$W/R566B0/g1\"\n",
     "  mkdir -p \"$PDIR/snapshots/$W/C1/g1\" \"$PDIR/snapshots/$W/R566B0/g1\" \"$PDIR/snapshots/$W/R566B1/g1\"\n"),
    ("  cp -a \"$D/$W/agentB0/g1/work/.\" \"$PDIR/snapshots/$W/R566B0/g1/\"\n",
     "  cp -a \"$D/$W/agentB0/g1/work/.\" \"$PDIR/snapshots/$W/R566B0/g1/\"\n"
     "  cp -a \"$D/$W/agentB1/g1/work/.\" \"$PDIR/snapshots/$W/R566B1/g1/\"\n"),
    ("      --codex-range \"$c0,$c1\" --b0-range \"$a00,$a01\" | tee -a \"$D/logs/run.txt\"\n",
     "      --codex-range \"$c0,$c1\" --b0-range \"$a00,$a01\" --b1-range \"$a10,$a11\" | tee -a \"$D/logs/run.txt\"\n"),
    ("  echo \"{\\\"win\\\":\\\"$W\\\",\\\"secs\\\":$((WEND-WSTART)),\\\"codex_rc\\\":\\\"$(cat \"$D/$W/codex/rc.txt\")\\\",\\\"b0_rc\\\":$(cat \"$D/$W/agentB0/g1/cli_rc.txt\"),\\\"ranges\\\":{\\\"codex\\\":[$c0,$c1],\\\"b0\\\":[$a00,$a01]}}\" >> \"$D/logs/windows.jsonl\"\n",
     "  echo \"{\\\"win\\\":\\\"$W\\\",\\\"secs\\\":$((WEND-WSTART)),\\\"codex_rc\\\":\\\"$(cat \"$D/$W/codex/rc.txt\")\\\",\\\"b0_rc\\\":$(cat \"$D/$W/agentB0/g1/cli_rc.txt\"),\\\"b1_rc\\\":$(cat \"$D/$W/agentB1/g1/cli_rc.txt\"),\\\"ranges\\\":{\\\"codex\\\":[$c0,$c1],\\\"b0\\\":[$a00,$a01],\\\"b1\\\":[$a10,$a11]}}\" >> \"$D/logs/windows.jsonl\"\n"),
    # 先写后跑闸: 臂集 3 / require 18 / 两臂剂量键显式且取值 0 vs 1 (单变量)
    ('assert set(d["arms"]) == {"C1", "R566B0"}, sorted(d["arms"])\nassert len(d["evidence_scope"]["require"]) == 12, d["evidence_scope"]["require"]\n',
     'assert set(d["arms"]) == {"C1", "R566B0", "R566B1"}, sorted(d["arms"])\nassert len(d["evidence_scope"]["require"]) == 18, d["evidence_scope"]["require"]\n'),
    ('_dose = [k for k in d["arms"]["R566B0"]["env"] if "MAX_" in k or "EARLY_STOP" in k]\nassert not _dose, ("R566B0 自称为产品默认档但带剂量键", _dose)\n',
     '_doses = {a: {k: v for k, v in d["arms"][a]["env"].items() if "MAX_" in k or "EARLY_STOP" in k}\n'
     '          for a in ("R566B0", "R566B1")}\n'
     'assert set(_doses["R566B0"]) == {"AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"}, _doses\n'
     'assert set(_doses["R566B1"]) == {"AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"}, _doses\n'
     'assert int(_doses["R566B0"]["AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"]) == 0, _doses\n'
     'assert int(_doses["R566B1"]["AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"]) == 1, _doses\n'),
    ('print("[先写后跑闸] prereg ok: arms=%s require=%d dose_keys=%s" % (\n    sorted(d["arms"]), len(d["evidence_scope"]["require"]), _dose))\n',
     'print("[先写后跑闸] prereg ok: arms=%s require=%d doses=%s" % (\n    sorted(d["arms"]), len(d["evidence_scope"]["require"]), _doses))\n'),
    ('"arm_env": {k: pre["arms"][k].get("env") for k in ("R566B0",)}}\n',
     '"arm_env": {k: pre["arms"][k].get("env") for k in ("R566B0", "R566B1")}}\n'),
    # ingest: 第三臂 spec + 汇总打印
    ('    spec = [("C1", "codex", "codex", rng(a.codex_range)),\n            ("R566B0", "agent", "agentB0", rng(a.b0_range)),\n]\n',
     '    spec = [("C1", "codex", "codex", rng(a.codex_range)),\n            ("R566B0", "agent", "agentB0", rng(a.b0_range)),\n            ("R566B1", "agent", "agentB1", rng(a.b1_range)),\n]\n'),
    ('    ap.add_argument("--b0-range", default="0,0")\n',
     '    ap.add_argument("--b0-range", default="0,0")\n    ap.add_argument("--b1-range", default="0,0")\n'),
    ('    for arm in ("C1", "R566B0"):\n        v = rec["arms"][arm]\n',
     '    for arm in ("C1", "R566B0", "R566B1"):\n        v = rec["arms"][arm]\n'),
    ('               "note": "快照 = snapshots/<win>/{C1,agentB0}/g1/**; 判分脚本 cases/run_cases_r521.py"},\n',
     '               "note": "快照 = snapshots/<win>/{C1,R566B0,R566B1}/g1/**; 判分脚本 cases/run_cases_r521.py"},\n'),
    # matrix: 三臂 + 判分工作目录默认值 (禁指向轮根)
    ('     "arms": ["C1", "R566B0"], "reports": "eval/rover/r566/evidence/windows"},\n',
     '     "arms": ["C1", "R566B0", "R566B1"], "reports": "eval/rover/r566/evidence/windows"},\n'),
    # adjudicate: 三臂
    ('ARMS = ["C1", "R566B0"]\n', 'ARMS = ["C1", "R566B0", "R566B1"]\n'),
    # kpi: 汇总打印三臂
    ('    for arm in ("C1", "R566B0"):\n        d = per.get(arm)\n',
     '    for arm in ("C1", "R566B0", "R566B1"):\n        d = per.get(arm)\n'),
]


def main():
    os.makedirs(DST, exist_ok=True)
    table = []
    for src, dst in MAP.items():
        s = io.open(os.path.join(SRC, src), encoding="utf-8").read()
        t = port(s)
        n_patch = 0
        for old, new in ARM_PATCHES:
            old_p = port(old)
            new_p = port(new)
            if old_p in t:
                t = t.replace(old_p, new_p)
                n_patch += 1
        io.open(os.path.join(DST, dst), "w", encoding="utf-8").write(t)
        table.append((dst, n_patch))
    for d, n in table:
        print("%-26s patched=%d" % (d, n))
    # 反向核验: 未替换到的补丁块必须为 0
    leftover = 0
    for src, dst in (("run_r565.sh", "run_r566.sh"), ("ingest_r565.py", "ingest_r566.py"),
                     ("matrix_r565.py", "matrix_r566.py"), ("kpi_r565.py", "kpi_r566.py"),
                     ("adjudicate_r565.py", "adjudicate_r566.py")):
        txt = io.open(os.path.join(DST, dst), encoding="utf-8").read()
        for pat in ("R566B0\",)", "agentB1", "R566B1"):
            pass
    # 关键命中核验
    run = io.open(os.path.join(DST, "run_r566.sh"), encoding="utf-8").read()
    checks = {
        "win0_125": 'WIN0=${WIN0:-125}' in run,
        "port_49446": 'PORT=${PORT:-49446}' in run,
        "three_arms_in_loop": 'run_agent R566B1 "$W" agentB1 1' in run,
        "require_18": 'len(d["evidence_scope"]["require"]) == 18' in run,
        "dose_pair": 'int(_doses["R566B0"]["AGENTFRAMEWORK_R1_MAX_EXEC_REPAIR"]) == 0' in run,
        "prev_postcheck_r565": 'eval/rover/r565/gate-postcheck-r565.json' in run,
        "b1_range": '--b1-range "$a10,$a11"' in run,
        "snap_b1": '"$PDIR/snapshots/$W/R566B1/g1/"' in run,
        "no_stale_arms": 'R566B0/unset' not in run,
    }
    ing = io.open(os.path.join(DST, "ingest_r566.py"), encoding="utf-8").read()
    checks["ingest_three"] = '("R566B1", "agent", "agentB1", rng(a.b1_range))' in ing
    mt = io.open(os.path.join(DST, "matrix_r566.py"), encoding="utf-8").read()
    checks["matrix_three"] = '"arms": ["C1", "R566B0", "R566B1"]' in mt
    checks["matrix_work_default"] = '/tmp/r566/pc' in mt
    adj = io.open(os.path.join(DST, "adjudicate_r566.py"), encoding="utf-8").read()
    checks["adj_three"] = 'ARMS = ["C1", "R566B0", "R566B1"]' in adj
    kp = io.open(os.path.join(DST, "kpi_r566.py"), encoding="utf-8").read()
    checks["kpi_three"] = '("C1", "R566B0", "R566B1")' in kp
    bad = [k for k, v in checks.items() if not v]
    for k, v in checks.items():
        print("  [check] %-22s %s" % (k, "OK" if v else "FAIL"))
    print("PATCH_FAIL=%d" % len(bad))
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
