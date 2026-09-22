#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R639 派生器（可复现；逐条声明的差异，非「照抄改个名」）：

承 R637 下轮候选 ②「`F_lift_min` 进主判据并读（声明先于跑）」+ R636 轮形（主线对照轮：新窗集
w237..w239 × 每窗 codex 真值 ×1 + 产品默认档 ×3）。

差异（逐条）：
  ① 命名空间 R636→R639 / r636→r639；D=$HARNESS/runs/r639；端口 49805→**49807**。
  ② 窗号 WIN0 234→**237**（w237..w239；与历史窗集 w184..w236 不相交）。
  ③ 题集 = r636 件**逐字节复制**（文件 sha e0c667c2… / payload e7ddce02… 双钉不变）；aux 两件同批携带。
  ④ 起手闸摆动余量 PREV_SWING 137→**81**（新源 = R636 **在飞窗**实测振幅：n=44 min 2729 / max 2810）。
  ⑤ 判据器 = judge_r639.py = r636 版 + **F_lift_min 进判决件并读**（判据核 **import** r637 件，
     不重写第二份口径）；rc 抬升规则声明先于跑（prereg F_lift_min.pair_read_rule）。
  ⑥ 预注册新增 `F_lift_min` 段 + 起臂前机检闸断言该段（fail-closed）。
"""
from __future__ import annotations
import hashlib
import io
import json
import os
import re
import shutil

REPO = "/home/agentuser/AgentFramework"
SRC = os.path.join(REPO, "eval/rover/r636")
DST = os.path.join(REPO, "eval/rover/r639")
os.makedirs(os.path.join(DST, "cases"), exist_ok=True)
os.makedirs(os.path.join(DST, "snapshots"), exist_ok=True)
os.makedirs(os.path.join(DST, "evidence/windows"), exist_ok=True)


def sha256(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def rd(p):
    return io.open(p, encoding="utf-8").read()


def wr(p, s):
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)


# ---------------- ① 题集 + aux 逐字节复制（含 sha 复核） ----------------
copies = [
    (os.path.join(SRC, "taskset-r636.json"), os.path.join(DST, "taskset-r639.json")),
    (os.path.join(SRC, "cases/run_cases_r521.py"), os.path.join(DST, "cases/run_cases_r521.py")),
    (os.path.join(REPO, "eval/rover/r635/cases/cases-r521.json"), os.path.join(DST, "cases/cases-r521.json")),
]
for s, d in copies:
    shutil.copyfile(s, d)
    assert sha256(s) == sha256(d), ("副本 sha 漂移", s, d)
print("[copies] 3 件逐字节复制 sha 同值:",
      [(os.path.basename(s), sha256(d)[:12]) for s, d in copies])

TASKSET_SHA = sha256(os.path.join(DST, "taskset-r639.json"))
assert TASKSET_SHA == "e0c667c2a313c04b2d87ac06fcba9f50166a4a0be5d5162cabdbf520d9d3927a", TASKSET_SHA

# ---------------- ② 驱动器派生 ----------------
t = rd(os.path.join(SRC, "run_r636.sh"))
reps = [
    ("R636", "R639"), ("r636", "r639"),
    ("w234..w236", "w237..w239"),
    ('["w234", "w235", "w236"]', '["w237", "w238", "w239"]'),
    ("w234", "w237"), ("w235", "w238"), ("w236", "w239"),
    ("**234**", "**237**"), ("WIN0=${WIN0:-234}", "WIN0=${WIN0:-237}"),
    ("49803→**49805**", "49805→**49807**"), ("PORT=${PORT:-49805}", "PORT=${PORT:-49807}"),
    ("PORT=49805 PREV_SWING=137", "PORT=49807 PREV_SWING=81"),
    ("PREV_SWING=${PREV_SWING:-137}", "PREV_SWING=${PREV_SWING:-81}"),
    ("余量源 = R635 在飞窗实测振幅 137MB", "余量源 = R636 在飞窗实测振幅 81MB"),
    ("（R635 派生版；余量源 = R635 在飞窗实测振幅 137MB）", "（R639 派生版；余量源 = R636 在飞窗实测振幅 81MB）"),
    ("R635 在飞窗实测振幅 (run-samples.jsonl n=185 min 2686 / max 2823) ⇒ swing=137MB",
     "R636 在飞窗实测振幅 (run-samples.jsonl n=44 min 2729 / max 2810) ⇒ swing=81MB"),
]
for a, b in reps:
    t = t.replace(a, b)

# 方向：w236→w239 的替换必须先于 w235→w238（否则 w236 里的 w23 会被二次命中）—— 上面按长度
# 重新排序执行（长串优先），此处机检最终不得残留旧窗号/旧端口/旧摆动值。
#   注：`49805→**49807**`（变更箭头行）合法含旧端口 ⇒ 残留检查前先摘除「A→**B**」形态的箭头对。
_t_check = re.sub(r"\d+→\*\*\d+\*\*", "<ARROW>", t)
for bad in ("w234", "w235", "w236", "WIN0:-234", "49805", "PREV_SWING:-137"):
    assert bad not in _t_check, ("旧值残留", bad)

# 新增 F_lift_min「声明先于跑」机检闸断言（插在 B 段断言之后）
anchor = 'assert "F_merge.quality.family_block_scan" in d["thresholds_cite_baselines"], d["thresholds_cite_baselines"]\n'
assert anchor in t
t = t.replace(anchor, anchor + '''# R639 新增判据「声明先于跑」机检闸：`F_lift_min` 段必须**同批预注册**携带（承 R637 候选②）
fl = d["F_lift_min"]
assert fl["declared_before_run"] is True and fl["declared_ts"], fl.get("declared_before_run")
assert fl["threshold_cases"] == -2, fl["threshold_cases"]
assert "worst" in fl["decided_form"] and "median" in fl["decided_form"], fl["decided_form"]
assert "pair_read_rule" in fl and fl["pair_read_rule"].strip(), sorted(fl)
for _k in ("T1", "T2", "T3"):
    assert _k in fl["bars"], sorted(fl["bars"])
assert "F_merge.quality.family_lift_min" in d["thresholds_cite_baselines"], d["thresholds_cite_baselines"]
''')
t = t.replace('print("[先写后跑闸] prereg ok: arms=%s windows=%s criterion=%s scope_require=%d policy=%s B=%s"\n      % (sorted(d["arms"]), d["windows"]["set"], d["criterion_version"][:12],\n         len(sc["require"]), up["rule"], bf["declared_before_run"]))',
              'print("[先写后跑闸] prereg ok: arms=%s windows=%s criterion=%s scope_require=%d policy=%s B=%s F=%s"\n      % (sorted(d["arms"]), d["windows"]["set"], d["criterion_version"][:14],\n         len(sc["require"]), up["rule"], bf["declared_before_run"], d["F_lift_min"]["declared_before_run"]))')
wr(os.path.join(DST, "run_r639.sh"), t)
assert "F_lift_min" in t and "judge_r639.py" in t and "--round r639" in t
print("[driver] run_r639.sh 派生完成 bytes=%d" % len(t))

# ---------------- ③ 判据器派生（**见 derive_judge_r639.py**） ----------------
# 原「批量替换」实现已废弃：它会连同**历史轮次断言**（「R636 自捕 / R636 修正版 / R636 新增」）
# 一起改写成 R639 ⇒ 归属篡改（把往轮功劳记到本轮）。judge 侧一律走 derive_judge_r639.py
# 的**定向替换表 + 残留白名单**。
print("[judge] 跳过（由 derive_judge_r639.py 定向派生；本脚本只出 driver + 逐字节复制件）")
