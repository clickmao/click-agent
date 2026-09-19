#!/usr/bin/env python3
"""R579-tick 机检器: RF0002 §3 验收面②③④ 的**可测化**契约与零回归闸。

判据 (来自 prereg-r579tick.json, 单源; 不在本器内重定义):
  P1 生产面 `ShapeCounters` 消费者计数 (非测试 vs 测试) — 复现 F1。
  P2 前态锚有牙: 同一契约在 **前态提交字节** 上必须判红 (打点点位缺失), 现盘判绿。
  P3 打点契约: 键集 == prereg 声明集 ∧ 点位在 `LearnOnSuccess` 之后。
  P4 零行为改动: 冻结源 (判定链) 逐位不变 ∧ 目标文件新增行删除数 == 0。
rc: 0 全过 / 1 被测契约面不符 / 2 器具缺陷(fail-closed) / 3 输入缺失。
用法: python3 eval/rover/r579-tick/shape_kpi_face_check.py --pre-sha <sha> [--out <json>]
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TARGET = "src/agent/IndustrialAgentV2.cs"
POINT = 'Emit("nlp_shape"'
ANCHORS = [  # 判定链冻结面 (P4): 本 tick 声称零行为改动 ⇒ 必须逐位不变
    "src/agent.nlp/NlpGate.cs",
    "src/agent.modelqueue/TurnGateJudge.cs",
    "src/agent.modelqueue/LocalParaphraseChannel.cs",
    "src/agent.modelqueue/ModelQueueRouter.cs",
    "src/agent.modelqueue/ModelQueueRouter.Call.cs",
    "src/agent.modelqueue/ModelQueueRouter.Catalog.cs",
    "src/agent.modelqueue/ModelQueueRouter.LocalChannel.cs",
    "src/agent.modelqueue/TurnGateCounters.cs",
]


def sh(args, **kw):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, **kw)


def prereg():
    p = ROOT / "eval/rover/r579-tick/prereg-r579tick.json"
    if not p.exists():
        fail(3, "prereg 缺失", {})
    return json.loads(p.read_text(encoding="utf-8"))


def fail(rc, why, out):
    out.update({"rc": rc, "verdict": why})
    print(json.dumps(out, ensure_ascii=False, indent=1))
    if out.get("_out"):
        Path(out["_out"]).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.exit(rc)


def scan_shape_consumers():
    """P1: 生产面/测试面 `ShapeCounters` 引用点 (排除 bin/obj/archive)。"""
    prod, tests = [], []
    for p in sorted((ROOT / "src").rglob("*.cs")):
        s = str(p)
        if "/bin/" in s or "/obj/" in s:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if "ShapeCounters" not in line:
                continue
            (tests if "/agent.tests/" in s else prod).append(
                f"{p.relative_to(ROOT)}:{i}: {line.strip()[:110]}")
    return prod, tests


def emission_block(src):
    """返回 `Emit("nlp_shape"` 起、到该语句结束 (右括号+分号) 的文本窗口。
    键集扫描窗口**跳过点位名与模块名** (那两项是 Emit 的形参, 不是 kv 键)。"""
    i = src.find(POINT)
    if i < 0:
        return None, -1
    j = src.find(");", i)
    blk = src[i:j if j > 0 else i + 2000]
    mod = blk.find('"IndustrialAgentV2"')
    return (blk[mod:] if mod > 0 else blk), i


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pre-sha", required=True, help="前态提交 (不可变; 禁写 HEAD)")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    out = {"round": "R579-tick", "pre_sha": a.pre_sha, "_out": a.out}
    pr = prereg()

    # ---- 输入闸 (fail-closed) ----
    if not (ROOT / TARGET).exists():
        fail(3, f"目标文件不存在: {TARGET}", out)
    anc = sh(["git", "merge-base", "--is-ancestor", a.pre_sha, "HEAD"])
    if anc.returncode != 0:
        fail(3, f"前态锚 {a.pre_sha} 不是 HEAD 祖先 (不可作对照)", out)
    pre = sh(["git", "show", f"{a.pre_sha}:{TARGET}"])
    if pre.returncode != 0:
        fail(3, f"git show {a.pre_sha}:{TARGET} 失败: {pre.stderr.strip()[:200]}", out)
    head = sh(["git", "rev-parse", "HEAD"]).stdout.strip()
    out["head"] = head
    if a.pre_sha == head:
        out["note_prestate_equals_head"] = "前态锚 == HEAD (对照物会随提交前进而失效; 本轮 pre 提交即改动前)"

    # ---- P1: 生产面消费者计数 (只读, 复现 F1) ----
    prod, tests = scan_shape_consumers()
    # 前态读数 (同一器具路径): 目标文件取**前态字节**, 其余文件取现盘 ⇒ F1 的对照面
    prod_pre = [x for x in prod if not x.startswith(TARGET + ":")]
    pre_lines = pre.stdout.splitlines()
    prod_pre += [f"{TARGET}:{i}: {ln.strip()[:110]}"
                 for i, ln in enumerate(pre_lines, 1) if "ShapeCounters" in ln]
    out["P1_shape_consumers"] = {
        "production_n_prestate": len(prod_pre), "production_n": len(prod),
        "test_n": len(tests),
        "production_prestate": prod_pre, "production": prod, "tests": tests,
        "source": "src/**/*.cs (排除 bin/obj), substring ShapeCounters; 前态面 = 目标文件前态字节 + 其余现盘",
    }

    src = (ROOT / TARGET).read_text(encoding="utf-8", errors="replace")
    block, pos = emission_block(src)

    # ---- P2: 前态锚有牙 (同一契约在前态字节上必须判红) ----
    pre_block, _ = emission_block(pre.stdout)
    out["P2_prestate_teeth"] = {
        "pre_has_point": pre_block is not None,
        "now_has_point": block is not None,
        "pre_sha256": __import__("hashlib").sha256(pre.stdout.encode()).hexdigest()[:16],
        "now_sha256": __import__("hashlib").sha256(src.encode()).hexdigest()[:16],
        "pass": (pre_block is None and block is not None),
    }
    if not out["P2_prestate_teeth"]["pass"]:
        fail(1, "P2 前态锚无牙 (前态已含点位 或 现盘缺点位)", out)

    # ---- P3: 打点契约 (键集 == prereg 声明集 ∧ 位置) ----
    need = set()
    for f in pr.get("predicates", {}).values():
        for m in re.finditer(r"\{(route, shape, face, basis, hits, learned, shapes, msg_sha16)\}", str(f)):
            need |= {t.strip() for t in m.group(1).split(",")}
    if not need:
        fail(2, "P3 契约集无法从 prereg 派生 (器具读法错, fail-closed)", out)
    present = set(re.findall(r'\("([a-z0-9_]+)"\s*,', block or ""))
    learn_at = src.find("TurnGateJudge.LearnOnSuccess(message.Content, llmResponse.Success)")
    out["P3_emission_contract"] = {
        "required_keys": sorted(need), "present_keys": sorted(present),
        "missing": sorted(need - present), "extra": sorted(present - need),
        "position_after_learn": (pos > learn_at >= 0), "learn_at": learn_at, "point_at": pos,
    }
    if (out["P3_emission_contract"]["missing"] or out["P3_emission_contract"]["extra"]
            or not out["P3_emission_contract"]["position_after_learn"]):
        fail(1, "P3 契约不符 (键缺失 或 点位早于回补)", out)

    # ---- P4: 零行为改动 (冻结源逐位不变 ∧ 目标文件删除行数 == 0) ----
    frozen = {}
    for rel in ANCHORS:
        p = ROOT / rel
        cur = p.read_text(encoding="utf-8", errors="replace") if p.exists() else None
        old = sh(["git", "show", f"{a.pre_sha}:{rel}"]).stdout
        frozen[rel] = {
            "exists": cur is not None,
            "identical": cur is not None and cur == old,
        }
    ns = sh(["git", "diff", "--numstat", a.pre_sha, "--", TARGET]).stdout.split()
    added = int(ns[0]) if len(ns) >= 2 and ns[0].isdigit() else None
    removed = int(ns[1]) if len(ns) >= 2 and ns[1].isdigit() else None
    out["P4_zero_behavior_change"] = {
        "frozen_chain": frozen,
        "frozen_all_identical": all(v["identical"] for v in frozen.values()),
        "target_added": added, "target_removed": removed,
    }
    if not out["P4_zero_behavior_change"]["frozen_all_identical"] or (removed or 0) != 0:
        fail(1, "P4 越界 (判定链被改 或 目标文件有删除行)", out)

    out["rc"] = 0
    out["verdict"] = "P1..P4 PASS (P5 由 dotnet 定向+形式校验承担; P6 诚实体界)"
    print(json.dumps(out, ensure_ascii=False, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
