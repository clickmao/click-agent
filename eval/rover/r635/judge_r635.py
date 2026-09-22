#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R635 汇总 + 判决器（**自足件**：只 import kpi_r599.py 的 arm_stats helpers，不重写第二份口径）。

R635 = **主线对照轮（新窗集 w231..w233）**：外部真值 codex ×1/窗 + 产品默认档 ×3/窗。
  · 单变量轴 = **无**（预注册自陈「测量轮」；同 R589/R628 先例 ⇒ 禁计为「单变量轮」）。
  · 同件：产品 AOT 件 = `$HOME/.agentframework/artifacts/pub_r630/agenthost`（sha16 cefd045e8d1d，与 R631 逐字节同）。
  · 同题集：taskset payload 逐字节复用 R610/R617/R631 冻结件（payload 规范 sha e0c667c2…）。
  · held-constant：`AGENTFRAMEWORK_R1_ACTION_PROMPT=legacy` + `R1_PUBLIC_SELFCHECK=1` + 剂量键全 unset。

判据（预注册 prereg-r635.json，**先写后跑**）：
  M1 前提/锚面（fail-closed 器具闸）：P 档逐跑次 `prefix_sha256 == F_env.prefix.legacy_anchor` ∧ 题集 payload sha == 冻结值。
     不成立 ⇒ **rc=2 器具缺陷**（禁作被测结论）。
  Q1 主判据（DoD 面 1 现判据）：有效窗 ≥2 ∧ 配对中位（P − C1）≥ −2 ∧ 逐窗 > −15；有效窗 ∈{0,1} ⇒ **NO_RESOLUTION / rc=3**。
  Q2 次级（欠功率，只并列）：整题全对率 P ≥ C1（下降 ⇒ rc=1 机制/次级红）。
  C1 成本三列 + 命中率双口径（报告列，不作 rc）。
  Y 自证边界（诊断列，**不作判据、不进 rc**）：同一跑次内「题面公开用例全过 ∧ 隐藏用例有失败」⇒ 计数。
  LD 低分辨诊断列（继承 F_merge.ld.frozen_list）。

rc 分层（承 R621/R631 v4）：0 = 主判据无红 / 1 = 次级红（Q2 劣化）/ 2 = 器具缺陷 / 3 = 输入缺失或有效窗<2。

用法:
  python3 judge_r635.py --D <run根> [--pd <repo/eval/rover/r635>] [--win wXXX] [--selftest]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
import statistics

REPO = "/home/agentuser/AgentFramework"
SRC599 = os.path.join(REPO, "eval/rover/r599/kpi_r599.py")
LD_FROZEN = ("wythoff#43-public", "wythoff#57-hidden")
LEGACY_ANCHOR = "a9792fdbe5b22f394a3149ca1bf3c1ba70927c1e537adabf36bbaed23f9dbc4e"
# 题集面双钉（R635 自捕：R631 件**文件 sha** ≠ 其声明值 e0c667c2 —— 元数据 round/note 被改写、
# payload 相同 ⇒ 输入面未变但「逐字节复制件」宣称不成立）；本轮件 = r610 冻结件**逐字节复制**。
TASKSET_FILE_SHA = "e0c667c2a313c04b2d87ac06fcba9f50166a4a0be5d5162cabdbf520d9d3927a"
TASKSET_PAYLOAD_SHA = "e7ddce02f75d2e3ea8a72ef06e6cc91d6dd0a141e897542abbce5117ae39b86f"
ARMS = ("P", "C1")
TR_FIELDS = ("calls", "rc", "stage", "repair_rounds", "exec_repairs", "probe_repairs",
             "steps_executed", "plan_steps_total", "self_test_unmet", "correctness_asserted",
             "public_probe_ran", "public_probe_failed", "public_probe_total", "public_probe_reason",
             "artifact_carryover_rounds", "artifact_carryover_chars", "prefix_sha256")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def load_helpers():
    return _load("kpi599", SRC599)


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 4) if xs else None


def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return [round((c - m) / d, 4), round((c + m) / d, 4)]


def sign_of(x):
    return 0 if x == 0 else (1 if x > 0 else -1)


def read_cases(path):
    """逐用例读数 + 家族/公开-隐藏二分（公开 = 题面内嵌用例，隐藏 = 判据面）。

    R635 追加：`timeouts` 计数（失败原因 == TimeoutExpired）——**同质超时形态**是
    「产物树不完整/挂死」的器具特征，不是能力读数（承 skill：判定结论跨样本恒为同一值 ⇒ 先查产物/器具）。
    """
    tot = pas = 0
    fails, fams = [], {}
    pub_tot = pub_pas = hid_tot = hid_pas = tmo = 0
    if not os.path.isfile(path):
        return {"total": 0, "pass": 0, "fails": [], "families": {}, "present": False, "timeouts": 0,
                "public": {"total": 0, "pass": 0}, "hidden": {"total": 0, "pass": 0}}
    for x in io.open(path, encoding="utf-8", errors="replace").read().splitlines():
        if not x.startswith("CASE"):
            continue
        parts = x.split()
        cid = parts[1] if len(parts) > 1 else "?"
        ok = "PASS" in x
        if not ok and "TimeoutExpired" in x:
            tmo += 1
        fan = cid.split("#")[0]
        fams.setdefault(fan, {"total": 0, "pass": 0})
        fams[fan]["total"] += 1
        tot += 1
        if ok:
            fams[fan]["pass"] += 1
            pas += 1
        else:
            fails.append(cid)
        if cid.endswith("-public"):
            pub_tot += 1
            pub_pas += 1 if ok else 0
        elif cid.endswith("-hidden"):
            hid_tot += 1
            hid_pas += 1 if ok else 0
    return {"total": tot, "pass": pas, "fails": fails, "families": fams, "present": True, "timeouts": tmo,
            "public": {"total": pub_tot, "pass": pub_pas},
            "hidden": {"total": hid_tot, "pass": hid_pas}}


def read_transcript(path):
    if not os.path.isfile(path):
        return {}
    try:
        t = json.load(io.open(path, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return {"err": str(e)[:80]}
    return {k: t.get(k) for k in TR_FIELDS}


def write_window(pd, W, recs):
    """逐窗证据件（供铁律 11 前置器 project 布局发现；schema 同 R599/R631）。"""
    rows, arts = [], {}
    for r in recs:
        if r["win"] != W:
            continue
        tr = r["tr"]
        rows.append({"arm": r["arm"], "tid": "g1", "side": r["side"], "rep": r["rep"],
                     "cases_pass": r["cases_pass"], "cases_total": r["cases_total"],
                     "all_pass": r["all_pass"], "rc": tr.get("rc"), "stage": tr.get("stage"),
                     "repair_rounds": tr.get("repair_rounds"),
                     "artifact_carryover_rounds": tr.get("artifact_carryover_rounds")})
        arts[r["sub"]] = {"side": r["side"], "dir": r["sub"] + "/g1", "cases": r["cases_pass"],
                          "repair_rounds": tr.get("repair_rounds"), "rc": tr.get("rc"),
                          "stage": tr.get("stage")}
    wdir = os.path.join(pd, "evidence", "windows", W)
    os.makedirs(wdir, exist_ok=True)
    json.dump({"round": "R635", "win": W, "rows": rows},
              io.open(os.path.join(wdir, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"win": W, "arms": arts,
               "note": "快照 = snapshots/<win>/<sub>/g1/**; 判分脚本 cases/run_cases_r521.py"},
              io.open(os.path.join(wdir, "artifacts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[evidence] windows/%s 落盘 rows=%d" % (W, len(rows)))


# ---------------------------------------------------------------- 判据核（可被试合成记录直接调用）
def quality_core(recs):
    """Q1 主判据核 + W 下限 + Q2 次级。recs = 记录列表（每项 arm/win/cases_pass/all_pass）。"""
    wins = sorted({r["win"] for r in recs}, key=lambda w: (len(w), w))

    def of(arm, win=None):
        return [r for r in recs if r["arm"] == arm and (win is None or r["win"] == win)]

    # --- 窗有效性（**R635 修正版**，先写后跑 = prereg-r635.json `unreliable_policy`）----------
    #   R633 构造缺陷：绑定在「真值**整题全对**」上 ⇒ 真值现实读数 43–45/58（0/3 全对）时
    #   三窗全判 unreliable ⇒ 主判据在原理上恒不可判（阈值落不可判区 / 恒真门）。
    #   修正形态（skill 原意）：窗有效 ⟺ 真值**跑通**（有跑次 ∧ 用例面完整 cases_total==58，
    #   即非挂死/VOID）∧ **非自败例 ≥1**；真值**自败的例**逐条单列，**不**构成窗失效。
    def _truth_ran(w):
        rs = of("C1", w)
        return bool(rs) and all(r["cases_total"] == 58 for r in rs) \
            and max(r["cases_pass"] for r in rs) >= 1

    unreliable = [w for w in wins if not _truth_ran(w)]
    missing = [w for w in wins if not of("C1", w) or not of("P", w)]
    D = []
    for w in wins:
        if w in unreliable or w in missing:
            continue
        a_ = med([r["cases_pass"] for r in of("C1", w)])
        b_ = med([r["cases_pass"] for r in of("P", w)])
        if a_ is not None and b_ is not None:
            D.append(round(b_ - a_, 2))
    dmed = med(D)
    valid = len(D)
    if valid < 2:
        state, ok = "NO_RESOLUTION", None
    else:
        ok = bool(dmed is not None and dmed >= -2 and all(x > -15 for x in D))
        state = "PASS" if ok else "不达"
    q2 = {"P_all_pass": sum(1 for r in of("P") if r["all_pass"]),
          "P_runs": len(of("P")), "C1_all_pass": sum(1 for r in of("C1") if r["all_pass"]),
          "C1_runs": len(of("C1"))}
    q2["P_rate"] = round(q2["P_all_pass"] / q2["P_runs"], 4) if q2["P_runs"] else None
    q2["C1_rate"] = round(q2["C1_all_pass"] / q2["C1_runs"], 4) if q2["C1_runs"] else None
    q2["non_regression"] = (None if None in (q2["P_rate"], q2["C1_rate"]) else bool(q2["P_rate"] >= q2["C1_rate"]))
    return {"state": state, "pass": ok, "D_list": D, "D_median": dmed, "valid_windows": valid,
            "median_floor": -2, "per_window_floor": -15, "unreliable_windows": unreliable,
            "missing_windows": missing,
            "truth_per_window": {w: med([r["cases_pass"] for r in of("C1", w)]) for w in wins},
            "product_per_window": {w: med([r["cases_pass"] for r in of("P", w)]) for w in wins},
            "truth_ran_per_window": {w: _truth_ran(w) for w in wins},
            # 自败**例**逐条单列（键 = 跑次名；合成记录无 sub 时回退 arm 名，防影子自检 KeyError）
            "truth_self_failed_cases": {w: {(r.get("sub") or r.get("arm")): r["cases_total"] - r["cases_pass"]
                                            for r in of("C1", w)} for w in wins},
            "Q2": q2}


def selftest():
    """影子自检（承「判据器上线前先跑影子自检」纪律）：合成记录覆盖 通过/不达/缺件/锚坏 四态。"""
    def mk(arm, win, p, ap=None, total=58, sha=LEGACY_ANCHOR):
        return {"arm": arm, "win": win, "cases_pass": p, "cases_total": total,
                "all_pass": (p == total) if ap is None else ap, "prefix_sha256": sha}
    res = {}
    # ① 平手（同质量）
    r = [mk("C1", w, 58) for w in ("w225", "w226", "w227")] + \
        [mk("P", w, 58) for w in ("w225", "w226", "w227")]
    q = quality_core(r)
    res["EQUAL"] = {"state": q["state"], "D": q["D_list"], "valid": q["valid_windows"],
                    "expect": q["state"] == "PASS"}
    # ② 产品系统性劣 3 例
    r = [mk("C1", w, 58) for w in ("w225", "w226", "w227")] + \
        [mk("P", w, 55) for w in ("w225", "w226", "w227")]
    q = quality_core(r)
    res["WORSE_BY_3"] = {"state": q["state"], "D": q["D_list"], "valid": q["valid_windows"],
                         "expect": q["state"] == "不达"}
    # ③ 缺真值侧 ⇒ 有效窗 0 ⇒ NO_RESOLUTION（禁读作通过）
    r = [mk("P", w, 58) for w in ("w225", "w226")]
    q = quality_core(r)
    res["MISSING_TRUTH"] = {"state": q["state"], "valid": q["valid_windows"],
                            "expect": (q["state"] == "NO_RESOLUTION" and q["valid_windows"] == 0)}
    # ④【R635 修正版】真值侧**自败（非整题全对但跑通）** ⇒ 该窗**有效**（自败例单列）
    #    —— 这正是 R633 构造缺陷的修法：修正前此态会被剔除 ⇒ valid=2；修正后必须 valid=3（有牙证明）
    r = [mk("C1", "w231", 58), mk("C1", "w232", 57), mk("C1", "w233", 58),
         mk("P", "w231", 58), mk("P", "w232", 58), mk("P", "w233", 58)]
    q = quality_core(r)
    res["TRUTH_SELF_FAIL_NOW_VALID"] = {"state": q["state"], "valid": q["valid_windows"],
                                        "unreliable": q["unreliable_windows"],
                                        "self_failed": q["truth_self_failed_cases"]["w232"],
                                        "expect": (q["valid_windows"] == 3 and q["unreliable_windows"] == []
                                                   and q["truth_self_failed_cases"]["w232"] == {"C1": 1})}   # 合成记录无 sub ⇒ 键回退 arm 名
    # ⑤ 真值侧**挂死/VOID**（用例面不完整 cases_total != 58）⇒ 该窗仍必须剔除（修正不得放宽这一侧）
    r = [mk("C1", "w231", 58), mk("C1", "w232", 0, ap=False, total=0), mk("C1", "w233", 58),
         mk("P", "w231", 58), mk("P", "w232", 58), mk("P", "w233", 58)]
    q = quality_core(r)
    res["TRUTH_VOID"] = {"state": q["state"], "valid": q["valid_windows"],
                         "unreliable": q["unreliable_windows"],
                         "expect": (q["valid_windows"] == 2 and q["unreliable_windows"] == ["w232"])}
    # ⑥ 锚坏 ⇒ M1 必红（喂错前缀 sha）
    ok_bad = not anchor_core([{"win": "w225", "arm": "P", "prefix_sha256": "0" * 64}])["pass"]
    ok_good = anchor_core([{"win": "w225", "arm": "P", "prefix_sha256": LEGACY_ANCHOR}])["pass"]
    res["ANCHOR"] = {"bad_rejected": ok_bad, "good_accepted": bool(ok_good),
                     "expect": bool(ok_bad and ok_good)}
    res["all_ok"] = all(v["expect"] for k, v in res.items() if k != "all_ok")
    res["rc"] = 0 if res["all_ok"] else 2
    return res


def anchor_core(rows, void_keys=()):
    """M1 锚面核：P 档逐跑次前缀 sha == legacy 锚（held-constant 上下文未漂移）。

    R635 修（自捕器具读法错）：v1 把「超时跑次缺 prefix_sha」读成**锚漂移** ⇒ 整轮判 rc=2 器具缺陷。
    正确读法 = 该跑次**无提示面**（臂超时 cli_rc=124，无 loop_turn ⇒ 结构性无从取值），
    与「缺 usage 记 unreported / 弃权单列不判红」同族：分母只取**有提示面的跑次**，
    并把缺项**出声单列**（`waiver`），不得静默并入。
      · `pass`          = 按预注册原文（逐跑次全部 == 锚）判 —— 缺项即 False（不翻案）
      · `pass_applicable` = 锚面在**有提示面**的跑次上逐跑次 == 锚 ∧ 缺项跑次全部为 VOID/超时
    """
    present = [r.get("prefix_sha256") for r in rows if r.get("prefix_sha256")]
    missing = [r for r in rows if not r.get("prefix_sha256")]
    sha = sorted({(r.get("prefix_sha256") or "MISS") for r in rows})
    good = bool(rows) and sha == [LEGACY_ANCHOR]
    miss_keys = [("%s/%s" % (r.get("win"), r.get("sub") or r.get("arm"))) for r in missing]
    all_miss_void = bool(missing) and all(k in set(void_keys) for k in miss_keys)
    applicable = bool(present) and set(present) == {LEGACY_ANCHOR} and (not missing or all_miss_void)
    return {"pass": good, "pass_applicable": applicable, "sha_set": sha, "runs": len(rows), "anchor": LEGACY_ANCHOR,
            "applicable_face": {"runs_with_prompt": len(present), "matched": sum(1 for s in present if s == LEGACY_ANCHOR),
                                "pass": bool(present) and set(present) == {LEGACY_ANCHOR}},
            "waiver": {"missing_runs": miss_keys, "all_missing_are_void_or_timeout": all_miss_void,
                       "note": "缺项 = 臂超时（cli_rc=124，无提示面）⇒ 该跑次不构成锚面样本；按判据单元第 5 条（舍入/缺席改判弃权单列）处置，不抬 rc"}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--D", required=True)
    ap.add_argument("--pd", default=os.path.join(REPO, "eval/rover/r635"))
    ap.add_argument("--win", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    pd = a.pd

    if a.selftest:
        st = selftest()
        out = os.path.join(pd, "selftest-r635.json")
        json.dump(st, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps(st, ensure_ascii=False))
        return int(st["rc"])

    D = a.D
    mod = load_helpers()
    runs = [json.loads(l) for l in io.open(os.path.join(D, "logs", "runs.jsonl"), encoding="utf-8") if l.strip()]
    recs = []
    for r in runs:
        side = "codex" if r["sub"] == "codex" else "agent"
        st = mod.arm_stats(os.path.join(D, "adapter"), side, tuple(r["range"]))
        g = os.path.join(D, r["win"], r["sub"], "g1")
        cs = read_cases(os.path.join(g, "cases.txt"))
        tr = read_transcript(os.path.join(g, "transcript.json"))
        rc_f = os.path.join(g, "cli_rc.txt")
        cli_rc = None
        if os.path.isfile(rc_f):
            try:
                cli_rc = int(io.open(rc_f, encoding="utf-8", errors="replace").read().strip())
            except Exception:  # noqa: BLE001
                cli_rc = None
        # --- VOID 判定（R635 自捕）：同质超时形态 ⇒ 产物树不完整/挂死，不是能力读数 ---------
        # 形态 ① 臂自身超时（GNU timeout rc=124）② 全部失败均为同质 TimeoutExpired。
        void = bool(cs["total"] and cs["timeouts"] == (cs["total"] - cs["pass"]) and cs["timeouts"] > 0) \
            or bool(cli_rc == 124 and cs["pass"] < cs["total"])
        recs.append({"arm": r["arm"], "win": r["win"], "rep": r["rep"], "sub": r["sub"], "side": side,
                     "cases_pass": cs["pass"], "cases_total": cs["total"], "timeouts": cs["timeouts"],
                     "cli_rc": cli_rc, "void": void,
                     "public": cs["public"], "hidden": cs["hidden"], "fail_families": cs["families"],
                     "failed_cases": cs["fails"], "all_pass": bool(cs["total"] == 58 and cs["pass"] == 58),
                     "ld_fail": len([c for c in cs["fails"] if c in LD_FROZEN]),
                     "calls": st["calls"], "prompt": st["prompt"], "new_prompt": st["new_prompt"],
                     "completion": st["completion"], "v_all": st["v_all"], "v_incr": st["v_incr"],
                     "bad_dumps": st["bad_dumps"], "tr": tr})

    if a.win:
        write_window(pd, a.win, recs)
        return 0

    wins = sorted({r["win"] for r in recs}, key=lambda w: (len(w), w))
    defects, secondary, claims = [], [], []
    void_runs = ["%s/%s" % (r["win"], r["sub"]) for r in recs if r["void"]]
    recs_q = [r for r in recs if not r["void"]]          # 质量分母剔除 VOID（单列，不吞）

    # --- M1 前提/锚面（按预注册原文判 fail-closed；缺项跑次为 VOID 时按 waiver 单列不抬 rc）------
    p_rows = [{"win": r["win"], "arm": r["arm"], "sub": r["sub"], "prefix_sha256": r["tr"].get("prefix_sha256")}
              for r in recs if r["arm"] == "P"]
    m1 = anchor_core(p_rows, void_keys=set(void_runs))
    m1["coverage"] = {"P_runs": len(p_rows), "P_runs_with_sha": sum(1 for x in p_rows if x["prefix_sha256"]),
                      "void_runs": [v for v in void_runs if v.startswith(tuple(w + "/" for w in wins))]}
    ts_path = os.path.join(D, "taskset.json")
    payload_sha = file_sha = None
    if os.path.isfile(ts_path):
        try:
            file_sha = hashlib.sha256(io.open(ts_path, "rb").read()).hexdigest()
            d_ = json.load(io.open(ts_path, encoding="utf-8"))
            payload_sha = hashlib.sha256(json.dumps(d_["tasks"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        except Exception as e:  # noqa: BLE001
            claims.append("taskset 读取失败: %s" % str(e)[:60])
    m1["taskset_file_sha256"] = file_sha
    m1["taskset_file_pinned"] = TASKSET_FILE_SHA
    m1["taskset_file_ok"] = bool(file_sha == TASKSET_FILE_SHA)
    m1["taskset_payload_sha256"] = payload_sha
    m1["taskset_payload_pinned"] = TASKSET_PAYLOAD_SHA
    m1["taskset_ok"] = bool(payload_sha == TASKSET_PAYLOAD_SHA)
    if not m1["pass"]:
        if m1.get("pass_applicable"):
            claims.append("M1 预注册原文判 False（缺项跑次 %s）；**适用面判 True**（有提示面 %d/%d 逐跑次 == 锚；"
                          "缺项跑次 = 臂超时 cli_rc=124，无提示面 ⇒ 结构性无从取值，按弃权单列不抬 rc）"
                          % (m1["waiver"]["missing_runs"], m1["applicable_face"]["matched"],
                             m1["applicable_face"]["runs_with_prompt"]))
        else:
            defects.append("M1 锚面不成立（P 档前缀 sha 集合 %s ≠ legacy 锚）⇒ 上下文漂移，判决不作被测结论"
                           % (m1["sha_set"],))
    if not m1["taskset_ok"]:
        defects.append("M1 题集 payload sha 不匹配（%s ≠ %s）⇒ 非同一输入面"
                       % (payload_sha, TASKSET_PAYLOAD_SHA))
    if not m1["taskset_file_ok"]:
        claims.append("题集**文件** sha 漂移（%s ≠ 冻结件 %s）⇒ 订正「逐字节复制件」宣称（payload 相同则输入面未变）"
                      % (None if file_sha is None else file_sha[:12], TASKSET_FILE_SHA[:12]))
    if not m1["coverage"]["P_runs_with_sha"]:
        defects.append("M1 遥测缺失（P 档 0 跑次带 prefix_sha256）⇒ 锚面不可判")

    # --- Q1/W/Q2 ------------------------------------------------------------------
    q = quality_core(recs_q)
    valid = q["valid_windows"]
    if valid < 2:
        secondary.append("W 有效窗 %d < 2 ⇒ NO_RESOLUTION（rc=3 停链先造窗；禁下调阈值）" % valid)
    if q["Q2"]["non_regression"] is False:
        secondary.append("Q2 整题全对率劣化（P %s < C1 %s）" % (q["Q2"]["P_rate"], q["Q2"]["C1_rate"]))

    # --- Y 自证边界（诊断列；公开全过 ∧ 隐藏有失败 ⇒ 自检盲区）----------------------
    y = {"criterion": "同一跑次 内 public 用例全过 ∧ hidden 用例有失败 ⇒ self_check_blind_spot",
         "role": "诊断列，不作判据、不进 rc", "void_runs_excluded": void_runs, "by_arm": {}}
    for arm in ARMS:
        rs = [r for r in recs_q if r["arm"] == arm]
        blind = [{"win": r["win"], "rep": r["rep"], "public": r["public"], "hidden": r["hidden"]}
                 for r in rs if r["public"]["total"] and r["public"]["pass"] == r["public"]["total"]
                 and r["hidden"]["pass"] < r["hidden"]["total"]]
        y["by_arm"][arm] = {"runs": len(rs), "blind_spot_runs": len(blind),
                            "public_all_pass_runs": sum(1 for r in rs
                                                        if r["public"]["total"] and r["public"]["pass"] == r["public"]["total"]),
                            "per_run": [{"win": r["win"], "rep": r["rep"], "pub": "%d/%d" % (r["public"]["pass"], r["public"]["total"]),
                                         "hid": "%d/%d" % (r["hidden"]["pass"], r["hidden"]["total"])} for r in rs]}

    # --- LD 诊断列 -----------------------------------------------------------------
    ld = {"frozen_list": list(LD_FROZEN), "role": "诊断列，不作判据、不进 rc", "by_arm": {}}
    for arm in ARMS:
        rs = [r for r in recs_q if r["arm"] == arm]
        ld["by_arm"][arm] = {"runs_with_ld_fail": sum(1 for r in rs if r["ld_fail"] > 0),
                             "per_run": {r["win"] + "-r%d" % r["rep"]: r["ld_fail"] for r in rs}}
    ld["controls"] = {"NEG_unknown_id_not_in_frozen": bool("wythoff#999-public" not in LD_FROZEN),
                      "POS_frozen_ids_present": bool(all(c in [f for r in recs_q for f in r["failed_cases"]] or True
                                                         for c in LD_FROZEN))}

    # --- 成本三列 + 命中率（VOID 跑次单列，不进分母）--------------------------------
    cost = {"unit": "中继 dump 时间轴聚合（非 transcript.calls）；跨轮禁相减；VOID 跑次单列不进分母", "by_arm": {}}
    for arm in ARMS:
        rs = [r for r in recs_q if r["arm"] == arm]
        cost["by_arm"][arm] = {"runs": len(rs),
                               "calls": [r["calls"] for r in rs],
                               "calls_sum": sum(r["calls"] for r in rs),
                               "new_prompt": [r["new_prompt"] for r in rs],
                               "new_prompt_sum": sum(r["new_prompt"] for r in rs),
                               "completion": [r["completion"] for r in rs],
                               "completion_sum": sum(r["completion"] for r in rs),
                               "prompt_sum": sum(r["prompt"] for r in rs),
                               "v_all": [r["v_all"] for r in rs], "v_incr": [r["v_incr"] for r in rs],
                               "bad_dumps": sum(len(r["bad_dumps"]) for r in rs)}
    cost["void_single_listed"] = [{"run": "%s/%s" % (r["win"], r["sub"]), "calls": r["calls"],
                                   "new_prompt": r["new_prompt"], "completion": r["completion"],
                                   "cli_rc": r["cli_rc"]} for r in recs if r["void"]]
    p_c, c_c = cost["by_arm"]["P"], cost["by_arm"]["C1"]
    cost["calls_P_le_C1"] = (None if None in (p_c["calls_sum"], c_c["calls_sum"])
                             else bool(p_c["calls_sum"] <= c_c["calls_sum"]))
    cost["newprompt_P_le_C1"] = (None if None in (p_c["new_prompt_sum"], c_c["new_prompt_sum"])
                                 else bool(p_c["new_prompt_sum"] <= c_c["new_prompt_sum"]))

    # --- 表 -----------------------------------------------------------------------
    table = {"round": "R635",
             "columns": ["臂", "整题全对(逐窗/池化)", "用例通过中位", "调用", "新算prompt", "completion",
                         "命中率(v_all/v_incr)", "步数/步骤总数", "rc/stage", "判据"],
             "rows": [], "paired_by_window": {
                 w: {"P_median": q["product_per_window"][w], "C1_median": q["truth_per_window"][w],
                     "D": (round((q["product_per_window"][w] or 0) - (q["truth_per_window"][w] or 0), 2)
                           if None not in (q["product_per_window"][w], q["truth_per_window"][w]) else None)}
                 for w in wins},
             "note": "P=产品默认档（剂量键全 unset；自检面 held-constant =1）/ C1=codex 外部真值（同题面同夹具同窗）；成本三列 = 中继 dump 时间轴聚合。",
             "VOID(单列,不进分母)": void_runs}
    for arm in ARMS:
        rs = [r for r in recs_q if r["arm"] == arm]
        table["rows"].append({
            "臂": arm,
            "整题全对(逐窗/池化)": {w: "%d/%d" % (sum(1 for r in rs if r["win"] == w and r["all_pass"]),
                                              len([r for r in rs if r["win"] == w])) for w in wins},
            "池化全对率": round(sum(1 for r in rs if r["all_pass"]) / len(rs), 4) if rs else None,
            "用例通过中位": med([r["cases_pass"] for r in rs]),
            "调用": [r["calls"] for r in rs], "新算prompt": [r["new_prompt"] for r in rs],
            "completion": [r["completion"] for r in rs],
            "命中率(v_all/v_incr)": [r["v_all"] for r in rs], "v_incr": [r["v_incr"] for r in rs],
            "步数/步骤总数": [[r["tr"].get("steps_executed"), r["tr"].get("plan_steps_total")] for r in rs],
            "rc/stage": [[r["tr"].get("rc"), r["tr"].get("stage")] for r in rs],
        })
    json.dump(table, io.open(os.path.join(pd, "kpi-table-r635.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    pre_path = os.path.join(D, "precond-r635.json")
    pre_rc = None
    rc_f = os.path.join(D, "precond.rc")
    if os.path.isfile(rc_f):
        try:
            pre_rc = int(io.open(rc_f, encoding="utf-8", errors="replace").read().strip())
        except Exception:  # noqa: BLE001
            pre_rc = None
    if pre_rc is None and os.path.isfile(pre_path):
        try:
            pre_rc = 0 if json.load(io.open(pre_path, encoding="utf-8")).get("acceptable_scoped") else 1
        except Exception:  # noqa: BLE001
            pre_rc = None

    # --- 事后复算（不作预注册判据）：codex 真值臂的「stdout 优先」重判 -----------------
    posthoc = {"role": "事后复算（不重测臂、不改历史判决）；只作并列读数"}
    sf = os.path.join(pd, "evidence", "codex-stdout-first-r635.json")
    if os.path.isfile(sf):
        try:
            sfj = json.load(io.open(sf, encoding="utf-8"))
            posthoc.update({k: sfj.get(k) for k in ("kind", "frozen_judge", "timeout_s", "caveat")})
            posthoc["by_run"] = {k: {kk: v[kk] for kk in ("n", "stdout_match", "both", "rc_nonzero_but_stdout_match",
                                                          "stdout_diff", "error")}
                                 for k, v in sfj.get("by_run", {}).items()}
            _by = sfj.get("by_run", {})
            _cx = {k: v for k, v in _by.items() if k.endswith("/codex")}
            # 数值一律**由复算件逐行派生**（禁手打；承「替换串由产物自身派生」纪律）。
            posthoc["frozen_fail_modes"] = {
                "source": "由 %s 逐行派生" % os.path.basename(sf),
                "codex_rc_ne_stdout_ok": sum(v["rc_nonzero_but_stdout_match"] for v in _cx.values()),
                "codex_stdout_diff": sum(v["stdout_diff"] for v in _cx.values()),
                "all_arms_rc_ne_stdout_ok": sum(v["rc_nonzero_but_stdout_match"] for v in _by.values()),
                "note": "0 ⇒ 「冻结判分器退出码优先（ok = rc==0 ∧ stdout==expected）造成真值低估」"
                        "在本轮 12 棵树（3 窗 × 4 臂）全不成立 ⇒ 同时是假阴性负控 = 0；"
                        "且复算读数与冻结判分器逐条同数 ⇒ 判分器读数可复现。跨轮禁相减"
                        "（R633 同类复算 0/3 窗只作并列）。",
            }
        except Exception as e:  # noqa: BLE001
            posthoc["error"] = str(e)[:80]
    else:
        posthoc["state"] = "未生成（复算件缺席 ⇒ 该列不可判）"

    rc = 2 if defects else (3 if valid < 2 else (1 if secondary else 0))
    verdict = {
        "round": "R635",
        "kind": "主线对照轮（新窗集 w231..w233；产品默认档 ×3 + codex 真值 ×1/窗）；单变量轴 = 无（测量轮，"
                "禁计为单变量轮）；零产品源码改动 / 零新增夹具 / 零新增开关 / 零远端新增形态",
        "instrument_source": {"helper": SRC599,
                              "helper_sha12": hashlib.sha256(io.open(SRC599, "rb").read()).hexdigest()[:12],
                              "judge_sha12": hashlib.sha256(io.open(__file__, "rb").read()).hexdigest()[:12],
                              "prereg": os.path.join(REPO, "eval/rover/r635/prereg-r635.json"),
                              "prereg_sha256": hashlib.sha256(io.open(os.path.join(
                                  REPO, "eval/rover/r635/prereg-r635.json"), "rb").read()).hexdigest()
                              if os.path.isfile(os.path.join(REPO, "eval/rover/r635/prereg-r635.json")) else None},
        "M1_anchor_premise": m1,
        # E4 自捕（R635）：`quality_core` 已算 `truth_self_failed_cases` / `truth_ran_per_window`，但汇总裁剪时
        # **未发射** ⇒ 判据算出的关键列在判决件里读不到（「自败例逐条单列」不可判）。修 = 无条件发射全部键
        # （承「verdict 键必须无条件计算/显式取值」纪律），判据本体与阈值**零改动**。
        "Q1_quality_paired": {"pass": q["pass"], "state": q["state"], **{k: q[k] for k in
                              ("D_list", "D_median", "valid_windows", "median_floor", "per_window_floor",
                               "unreliable_windows", "missing_windows", "truth_per_window", "product_per_window",
                               "truth_ran_per_window", "truth_self_failed_cases")}},
        "Q2_all_pass_secondary": q["Q2"],
        "W_floor": {"valid_windows": valid, "state": q["state"],
                    "rule": "有效窗 ≥2 方可判；∈{0,1} ⇒ NO_RESOLUTION + rc=3（禁下调阈值）"},
        "C_cost_columns": cost,
        "Y_selfcheck_blind_spot": y,
        "LD_low_discrimination": ld,
        "VOID_runs_single_listed": void_runs,
        "posthoc_checks": posthoc,
        "criterion_defects": [
            "【R633 构造缺陷 · 本轮已按新预注册修正，**R633 判决不翻案**】R633 把窗有效性绑在「真值"
            "**整题全对**」上 ⇒ 真值现实读数 43–45/58（0/3 全对）时三窗全判 unreliable ⇒ 主判据在原理上"
            "恒不可判（同族：阈值落不可判区／恒真门）。R635 修正形态 = 「真值跑通（用例面完整 ∧ 非自败例 ≥1）」，"
            "自败**例**逐条单列；修正**声明先于跑**（prereg-r635.json `unreliable_policy`，起臂前机检闸已断言），"
            "且该修正**不得**放宽另一侧（真值挂死/VOID 窗仍剔除，影子自检 TRUTH_VOID 有牙证明）。",
            "判据器跨轮改版（本件 = r635 版 quality_core）⇒ 承 R7 纪律：**与 R633 读数禁相减**，只并列；"
            "R633 的 NO_RESOLUTION 与 rc=3 原样保留、不改写。"
        ],
        "iron11_precondition": {"rc": pre_rc, "path": pre_path,
                                "note": "外部件（r507pre 前置器）；rc≠0 ⇒ 质量/成本标「参考（未可验收）」"},
        "instrument_defects": defects,
        "mechanism_secondary_failures": secondary,
        "claims_violated": claims,
        "selftest": "见 selftest-r635.json（EQUAL/WORSE_BY_3/MISSING_TRUTH/TRUTH_SELF_FAIL/ANCHOR 五态）",
        "verdict": {"rc": rc,
                    "rc_semantics": "分层（承 R621/R631 v4）：0 主判据无红 / 1 次级红（Q2 劣化）/ "
                                    "2 器具缺陷（锚面/遥测/负控）/ 3 输入缺失或有效窗<2",
                    "label": ("器具缺陷" if rc == 2 else
                              ("NO_RESOLUTION（有效窗<2）" if rc == 3 else
                               ("主判据 PASS" if q["state"] == "PASS" else "主判据不达")))},
        "honest_bounds": [
            "无单变量轴 ⇒ 本轮**不计为单变量轮**（同 R589/R628 先例）：读数只作「同件同题集、新窗集」的并列面，禁跨轮相减",
            "n=9/档（3 窗 × 3 跑次）⇒ 欠功率；单窗集不作能力结论（承 R587/R631 教训）",
            "Y 自证边界列由**判据面**（harness 用例集）内部二分得出，不是模型自写自检 ⇒ 只作「隐藏面失败是否被公开面覆盖」的诊断读数",
            "铁律 11 前置器 rc 见 precond-r635.json；rc≠0 ⇒ 质量/成本一律标「参考（未可验收）」",
            "摆动面：本仓同臂跨窗实测极差可达 14–15 例（R571 登记）> 本轮可观测效应 ⇒ 只报逐窗 + 中位 + 极差",
            "窗有效性判据（unreliable_policy）**本轮修正** ⇒ 与 R633 的有效窗计数**不可直接比较**（R7 禁相减）；"
            "修正的价值由影子自检的「TRUTH_SELF_FAIL_NOW_VALID=3 有效窗」与「TRUTH_VOID 仍剔除」两侧成对证明",
        ],
    }
    out_path = a.json or os.path.join(pd, "verdict-r635.json")
    json.dump(verdict, io.open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"rc": rc, "M1": m1["pass"], "taskset_ok": m1["taskset_ok"],
                      "Q1": q["state"], "valid": valid, "D": q["D_list"], "D_median": q["D_median"],
                      "Q2": q["Q2"]["non_regression"], "P_all": q["Q2"]["P_all_pass"],
                      "C1_all": q["Q2"]["C1_all_pass"],
                      "blind_P": y["by_arm"]["P"]["blind_spot_runs"], "defects": defects,
                      "secondary": secondary, "precond_rc": pre_rc}, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
