#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R419 多轮探针**判据检查器** (预注册判据在下方, 改判据必须同时改这里的断言)。

用法: python3 eval/rover/r419/check_multiturn.py [--probe-dir data/probe] [--ns <批次后缀>]

臂归属 = **文件名里的 tag 前缀** (r419bctlpos / r419bctlneg / r419bagent), 不用 solver
(同 solver 跨臂必然撞名)。每个前缀取**最新一份**(mtime), 并断言三臂批次后缀相同 ——
后缀不同即「不同批混读」判弃权。(命名空间碰撞是真实事件: 同仓两个执行体会写同一 tag
⇒ 本条不变式是唯一的防混读闸。)

判据 (预注册, 不得为了让脚本变绿而放宽):
  A. 正控 `ctlpos` (缺陷解: 第 1 轮浅解 / 第 2 轮真解)
     ⇒ `fix_rate == 1.0` ∧ `first_try_rate_whole == 0.0` ∧ 轮数实到 == 期望。
     意义: **仪器必须能记到一次修复** —— 无此正控时「仪器坏」与「题太难」不可区分 (R415 教训)。
  B. 负控 `ctlneg` (两轮同浅解, 不回修正)
     ⇒ `fix_rate == 0.0`。意义: 不许把「没修」读成「修了」(空心闸门同族)。
  C. 真机臂 `agent`
     ⇒ `turns_arg == 2` ∧ 轮数实到 == 期望 ∧ 判据「首次通过率 < 两轮合并整题全对率」,
       若两值相等 ⇒ 必须 `saturated is True` (题集饱和), 不得两值相等又不标饱和。

退出码: 0 全过 / 2 断言失败 / 3 测量或环境失败 (臂缺失 / 混批 / 字段缺失 —— 弃权不判红)
"""
import argparse
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ARMS = (("ctlpos", "r419bctlpos"), ("ctlneg", "r419bctlneg"), ("agent", "r419bagent"))


def tag_of(base, prefix):
    """probe-<solver>-seed<N>-<prefix>[-<suffix>]-t<K>.json → `<suffix>` (无后缀则 '')"""
    stem = base[:-5] if base.endswith(".json") else base
    i = stem.find("-" + prefix)
    if i < 0:
        return None
    rest = stem[i + 1 + len(prefix):].lstrip("-")
    parts = [p for p in rest.split("-") if p]
    if parts and parts[-1].startswith("t") and parts[-1][1:].isdigit():
        parts = parts[:-1]
    return "-".join(parts)


def load(probe_dir):
    """按臂前缀取**最新**多轮运行; 单轮运行(turns_arg<=1)一律不计入。"""
    found = {}
    for name, prefix in ARMS:
        cands = []
        for path in sorted(glob.glob(os.path.join(probe_dir, "probe-*.json"))):
            base = os.path.basename(path)
            if prefix not in base:
                continue
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    d = json.load(fh)
            except Exception as e:                  # 解析失败必须出声, 不静默跳过
                print("  [parse-error] %s: %s" % (base, e))
                continue
            if not isinstance(d, dict) or not d.get("turns_arg") or d["turns_arg"] <= 1:
                continue
            cands.append((os.path.getmtime(path), base, d))
        if not cands:
            continue
        cands.sort()
        mt, base, d = cands[-1]
        found[name] = {"file": base, "mtime": mt, "tag": tag_of(base, prefix),
                       "n_candidates": len(cands), "d": d}
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-dir", default=os.path.join(ROOT, "data", "probe"))
    ap.add_argument("--ns", default="", help="期望批次后缀 (空=不校验, 仍打印)")
    a = ap.parse_args()

    found = load(a.probe_dir)
    miss = [name for name, _ in ARMS if name not in found]
    print("| 臂 | 文件 | 批次后缀 | 轮数(实/期) | 首次通过率 | 两轮整题全对率 | 修复率 | 饱和 |")
    print("|---|---|---|---|---|---|---|---|")
    for name, _ in ARMS:
        if name not in found:
            print("| `%s` | (缺) | | | | | | |" % name)
            continue
        f = found[name]
        d = f["d"]
        print("| `%s` | %s | `%s` | %s/%s | %s | %s | %s | %s |" % (
            name, f["file"], f["tag"], d.get("rounds_observed"), d.get("rounds_expected"),
            d.get("first_try_rate_whole"), d.get("final_rate_whole"), d.get("fix_rate"),
            d.get("saturated")))

    if miss:
        print("MISSING_ARMS=%s ⇒ 测量/环境失败, 不下断言结论" % ",".join(miss))
        print("R419_EXIT=3")
        return 3

    # 混批闸: 三臂批次后缀必须一致 (命名空间碰撞 ⇒ 不可比)
    suffixes = {name: found[name]["tag"] for name, _ in ARMS}
    if len(set(suffixes.values())) != 1:
        print("MIXED_BATCH suffixes=%s ⇒ 三臂不同批 (命名空间碰撞), 判弃权, 不判红绿" % suffixes)
        print("R419_EXIT=3")
        return 3
    if a.ns and suffixes["agent"] != a.ns:
        print("NS_MISMATCH 期望 %r 实得 %r ⇒ 弃权" % (a.ns, suffixes["agent"]))
        print("R419_EXIT=3")
        return 3

    d = found["ctlpos"]["d"]
    d2 = found["ctlneg"]["d"]
    dag = found["agent"]["d"]
    # 弃权闸 (三态判决): 关键判据字段缺失 ⇒ 测量失败(3), 绝不因 None 让合取式"真空通过"
    for name, _ in ARMS:
        dd = found[name]["d"]
        if dd.get("fix_rate") is None and not (name == "agent" and dd.get("saturated") is True):
            print("MISSING_KEYS %s.fix_rate=None (无待修题? 且非饱和真机臂) ⇒ 测量失败, 不下断言结论" % name)
            print("R419_EXIT=3")
            return 3
    if dag.get("first_try_rate_whole") is None or dag.get("final_rate_whole") is None:
        print("MISSING_KEYS agent.first_try_rate_whole/final_rate_whole ⇒ 测量失败")
        print("R419_EXIT=3")
        return 3

    fails = []

    def chk(name, cond, extra=""):
        print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, extra))
        if not cond:
            fails.append(name)

    for name, _ in ARMS:
        dd = found[name]["d"]
        chk("%s: 轮数实到 == 期望" % name, dd.get("rounds_observed") == dd.get("rounds_expected"),
            "实=%s 期=%s 缺=%s" % (dd.get("rounds_observed"), dd.get("rounds_expected"), dd.get("rounds_missing")))
    chk("正控: 第 2 轮真解 ⇒ 修复率 == 1.0 (仪器能记到修复)", d.get("fix_rate") == 1.0,
        "fix=%s" % d.get("fix_rate"))
    chk("正控: 第 1 轮浅解 ⇒ 首次通过率 == 0.0", d.get("first_try_rate_whole") == 0.0,
        "first=%s" % d.get("first_try_rate_whole"))
    chk("负控: 两轮同浅解 ⇒ 修复率 == 0.0 (没修不许读成修了)", d2.get("fix_rate") == 0.0,
        "fix=%s" % d2.get("fix_rate"))
    chk("真机: turns_arg == 2", dag.get("turns_arg") == 2, str(dag.get("turns_arg")))
    fw, ww = dag.get("first_try_rate_whole"), dag.get("final_rate_whole")
    fx, rg = dag.get("fix_rate"), dag.get("regressed")
    chk("真机: 修正轮触发条件 == onfail (前提下真)", dag.get("correction_mode") == "onfail",
        str(dag.get("correction_mode")))
    if dag.get("saturated") is True:
        print("  [NOTE] 真机臂首轮即全对 (饱和) ⇒ 修复率 n/a, 本轮对真机无分辨力 (如实标注, 非失败)")
    else:
        # C1 只允增益 (硬): 修正轮只对首轮未过题发 ⇒ 两轮合并必 >= 首轮
        chk("真机 C1 非回归: 两轮合并整题全对率 >= 首次通过率",
            ww is not None and fw is not None and ww >= fw, "first=%s whole=%s" % (fw, ww))
        # C2 回归计数必须为 0 (缺陷锁: onfail 下若 >0 ⇒ 仪器把已过题也发了修正轮)
        chk("真机 C2 回归计数 == 0", rg == 0, "regressed=%s" % rg)
        # C3 增益与账本一致 (成对): 有增益必须记到修复; 无增益必须记修复率 0
        chk("真机 C3 增益/账本一致", (fw is not None and ww is not None) and (
            ((ww > fw) and fx is not None and fx > 0) or ((ww == fw) and fx == 0)),
            "first=%s whole=%s fix=%s" % (fw, ww, fx))

    print("fails=%d" % len(fails))
    print("R419_EXIT=%d" % (2 if fails else 0))
    return 2 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
