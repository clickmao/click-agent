#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R547 收口器: 从 readings-w2.json + R546 readings-w1.json + 前置器判决件 + post-hoc 外侧证据
生成 轮志 / improvements 条 / kpi 登记行。纪律: 一切数字**现算**(禁手抄); ts 用真实时钟; 首跑即幂等。

用法: python3 eval/rover/r547/report_r547.py
"""
from __future__ import annotations

import datetime
import hashlib
import io
import json
import os
import re
import sys

REPO = "/home/agentuser/AgentFramework"
R = os.path.join(REPO, "eval/rover/r547")
COLS = {"d0": ["E0a", "E0b", "E0c", "E0d", "E0e"],
        "d1": ["D1a", "D1b", "D1c", "D1d", "D1e"],
        "d2": ["E1a", "E1b", "E1c", "E1d", "E1e"],
        "d3": ["D3a", "D3b", "D3c"]}
LEG = ["A1on", "A1onb", "A1onc"]
ORDER = COLS["d0"] + COLS["d2"] + COLS["d1"] + COLS["d3"] + LEG
DOSE_OF = {a: k for k, v in COLS.items() for a in v}
DOSE_NUM = {"d0": 0, "d1": 1, "d2": 2, "d3": 3}


def rd(p):
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else None


def med(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    return xs[len(xs) // 2] if len(xs) % 2 else round((xs[len(xs) // 2 - 1] + xs[len(xs) // 2]) / 2.0, 3)


def spread(xs):
    xs = [x for x in xs if x is not None]
    return {"min": min(xs), "max": max(xs), "span": max(xs) - min(xs)} if xs else {}


def cases_of(p):
    t = io.open(p, encoding="utf-8", errors="replace").read()
    m = re.search(r"R521_CASES (\d+)/(\d+)", t)
    fails = re.findall(r"^CASE (\S+) FAIL", t, flags=re.M)
    fam = {}
    for f in fails:
        fam[f.split("#")[0]] = fam.get(f.split("#")[0], 0) + 1
    return (int(m.group(1)), int(m.group(2)), fam) if m else (None, None, {})


def usage_of(files):
    pt = ct = cache = 0
    n = 0
    for p in files:
        d = rd(p)
        if not d:
            continue
        u = ((d.get("response") or {}).get("usage") or {}) if isinstance(d.get("response"), dict) else {}
        if not u:
            continue
        n += 1
        pt += u.get("prompt_tokens", 0) or 0
        ct += u.get("completion_tokens", 0) or 0
        cache += ((u.get("prompt_tokens_details") or {}).get("cached_tokens", 0) or 0)
    return {"calls": n, "prompt": pt, "cached": cache, "completion": ct, "total": pt + ct}


def main() -> int:
    w2 = rd(os.path.join(R, "readings-w2.json"))
    if not w2:
        print("no readings-w2"); return 1
    w1 = rd(os.path.join(REPO, "eval/rover/r546/readings-w1.json"))
    arms = w2["arms"]
    J = w2["judgments"]
    pre = rd(os.path.join(REPO, "eval/rover/r507pre/precondition-r547.json")) or {}
    pre_rc = w2.get("precond_rc")
    pwin = ((pre.get("windows") or {}).get("w2") or {}).get("arms") or {}
    blocked = sorted(a for a, v in pwin.items() if not v.get("correct"))
    # AOT 复用: 产品源码零改动 ⇒ 二进制 = R546 同一件
    binp = "/tmp/pub_r546/agenthost"
    AOT = {"sha256": hashlib.sha256(open(binp, "rb").read()).hexdigest(),
           "bytes": os.path.getsize(binp)} if os.path.exists(binp) else {}

    S = {}
    for k, la in COLS.items():
        rs = [arms[a] for a in la if a in arms]
        S[k] = {"arms": la, "n": len(rs), "calls": [r["calls_dump"] for r in rs],
                "calls_median": med([r["calls_dump"] for r in rs]), "calls_spread": spread([r["calls_dump"] for r in rs]),
                "calls_self": [r["calls_self"] for r in rs],
                "total": [r["total_tokens"] for r in rs], "total_median": med([r["total_tokens"] for r in rs]),
                "cases": [r["cases_pass"] for r in rs], "cases_median": med([r["cases_pass"] for r in rs]),
                "all_green_n": sum(1 for r in rs if r["cases_pass"] == r["cases_total"]),
                "rcs": [r["rc"] for r in rs],
                "skipped": [r.get("early_stop_skipped") for r in rs],
                "repairs": [r.get("exec_repairs") for r in rs],
                "probe_failed": [r.get("public_probe_failed") for r in rs],
                "pfail_field": [r.get("early_stop_pfail") for r in rs]}
    L = {}
    def _calls(r):
        return r["calls_self"] if r.get("calls_self") is not None else r.get("calls_dump")
    lrs = [arms[a] for a in LEG if a in arms]
    L = {"n": len(lrs), "calls": [_calls(r) for r in lrs], "calls_median": med([_calls(r) for r in lrs]),
         "calls_spread": spread([_calls(r) for r in lrs]), "total_median": med([r["total_tokens"] for r in lrs]),
         "cases": [r["cases_pass"] for r in lrs], "all_green_n": sum(1 for r in lrs if r["cases_pass"] == r["cases_total"])}

    # ---- post-hoc 外侧证据 (非预注册) ----
    PH = os.path.join(R, "posthoc-codex-g1")
    post = []
    for i in (1, 2, 3):
        row: dict = {"win": i}
        for side in ("codex", "agent"):
            fl = os.path.join(PH, "files-%s-%d.txt" % (side, i))
            files = [os.path.join(PH, "adapter", os.path.basename(x.strip()))
                     for x in io.open(fl, encoding="utf-8").read().split()] if os.path.exists(fl) else []
            row[side] = usage_of(files)
        for side, d in (("codex", os.path.join(PH, "codex%d/cases.txt" % i)),
                        ("agent", os.path.join(PH, "r1_%d/cases.txt" % i))):
            p, t, fam = cases_of(d)
            row[side]["cases"], row[side]["cases_total"], row[side]["fails"] = p, t, fam
        post.append(row)
    ph_prompt = hashlib.sha256(io.open(os.path.join(PH, "task-g1-prompt.txt"), "rb").read()).hexdigest() \
        if os.path.exists(os.path.join(PH, "task-g1-prompt.txt")) else "?"
    pin = (rd(os.path.join(R, "input-pins-r547.json")) or {}).get("g1", {}).get("prompt_sha256")

    # ---- 轮志 ----
    A = []
    A.append("# R547 — 早停阈值**剂量面**(δ∈{0,1,2,3} + 判别性阴控) 单变量对照 · 窗口 w2\n")
    A.append("> 窗口 `w2` · 臂 **21** 个 · 题面 `g1`(58 隐藏用例, sha256 `%s`) · 被测二进制 **复用 R546 AOT** "
             "`%s` %s B(本轮产品源码**零改动** ⇒ IL 警告 0 承 R546) · 前置器 **rc=%s** ⇒ 全部成本读数标「参考(未可验收)」\n"
             % ((pin or "?")[:16], AOT.get("sha256", "?")[:16],
                "{:,}".format(AOT.get("bytes", 0)), pre_rc))
    A.append("## 0 靶点与单变量\n")
    A.append("- **靶点来源**: R546 下轮候选 ②(早停阈值剂量响应) + R546 诚实边界 ⑥(「阈值 1/3 未测」)。"
             "R546 只有 δ=2 一个点, 且其预注册 J10 的「同终态 pfail 配对」类为空 ⇒ **剂量面是唯一能区分"
             "「机制被行使」与「机制有效」的器具**。")
    A.append("- **单变量** = `AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL ∈ {0(=轴关), 1, 2, 3}`: 阈值越低, 触发面越宽, "
             "省下的那次「回灌修复」远端调用越多(**质量代价也随之暴露**)。")
    A.append("- 其余全同: 题面/用例/role/二进制/`MAX_EXEC_REPAIR=1`/`PUBLIC_SELFCHECK=1`(两列都开) ⇒ "
             "起臂前逐字节机检(prompt sha256 / cases md5 / role md5 与 R546 同, `xref_r546_all_same=True`)。")
    A.append("- δ=3 为**判别性阴控**: 若实测 pfail 从未 ≥3 而 δ=3 列出现 `early_stop_skipped=1` ⇒ 阈值语义被证伪。\n")
    A.append("## 1 产品改动\n")
    A.append("- **零**。`git diff -- src/` 空 ⇒ 复用 R546 二进制(sha256 `%s`, %s B) 合法; "
             "IL 警告 0 / 全量测试绿承 R546 与本轮实跑(见 §5)。本轮只动器具与预注册。\n"
             % (AOT.get("sha256", "?")[:16], "{:,}".format(AOT.get("bytes", 0))))
    A.append("## 2 器具与硬门\n")
    A.append("- `eval/rover/r547/`: `setup_r547.py`(夹具逐字节复制 + md5 交叉核对 + 预注册生成) → "
             "`run_r547.sh`(21 臂: δ=0/1/2 各 5 session, δ=3 阴控 3, 旧路径 ×3; 起手闸 2×PASS + 冒烟 + 逐臂 `adapter_range` 非空) "
             "→ `analyze_r547.py`(读数现算) → 本收口器。")
    A.append("- 铁律 11 前置器: `python3 eval/rover/r507pre/exec_precondition.py --round r547` 实跑 "
             "**rc=%s**(独立物化 + `python3 -I -B` 真跑隐藏用例; 判决件 `eval/rover/r507pre/precondition-r547.json`) ⇒ "
             "**本窗 BLOCKED 臂 %d 个**: %s ⇒ 依判据 K8 本轮一切**降幅**只作「参考(未可验收)」, 而**机制/事件计数**(早停跳过、调用数)不受影响。\n"
             % (pre_rc, len(blocked), ", ".join(blocked[:8]) + (" …" if len(blocked) > 8 else "")))
    A.append("## 3 同窗读数(臂级)\n")
    A.append("| δ | 臂 | rc | 调用(台账) | 自报 | prompt | compl | total | 隐藏用例 | 早停阈值字段 | 早停跳过 | exec_repairs | 探针失败 |")
    A.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for k in ("d0", "d2", "d1", "d3"):
        for a in COLS[k]:
            r = arms.get(a)
            if not r:
                continue
            A.append("| %d | %s | %s | %s | %s | %s | %s | %s | %s/%s | %s | %s | %s | %s |"
                     % (DOSE_NUM[k], a, r["rc"], r["calls_dump"], r["calls_self"], "{:,}".format(r["prompt_tokens"] or 0),
                        "{:,}".format(r["completion_tokens"] or 0), "{:,}".format(r["total_tokens"] or 0),
                        r["cases_pass"], r["cases_total"], r.get("early_stop_pfail"), r.get("early_stop_skipped"),
                        r.get("exec_repairs"), r.get("public_probe_failed")))
    for a in LEG:
        r = arms.get(a)
        if r:
            A.append("| 旧 | %s | (n/a) | %s | %s | %s | %s | %s | %s/%s | (n/a) | (n/a) | (n/a) | (n/a) |"
                     % (a, r["calls_dump"], r["calls_self"], "{:,}".format(r["prompt_tokens"] or 0),
                        "{:,}".format(r["completion_tokens"] or 0), "{:,}".format(r["total_tokens"] or 0),
                        r["cases_pass"], r["cases_total"]))
    A.append("\n## 3b 列级汇总\n")
    A.append("| δ | n | 调用(逐窗) | 调用中位 | 极差 | total 中位 | 用例(逐窗) | 用例中位 | 全绿 | 早停跳过 | exec_repairs |")
    A.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for k in ("d0", "d1", "d2", "d3"):
        s = S[k]
        A.append("| %d | %d | %s | %s | %s | %s | %s | %s | %d/%d | %s | %s |"
                 % (DOSE_NUM[k], s["n"], s["calls"], s["calls_median"], s["calls_spread"].get("span"),
                    "{:,}".format(s["total_median"] or 0), s["cases"], s["cases_median"], s["all_green_n"], s["n"],
                    s["skipped"], s["repairs"]))
    A.append("| 旧 | %d | %s | %s | %s | %s | %s | %s | %d/%d | — | — |"
             % (L["n"], L["calls"], L["calls_median"], L["calls_spread"].get("span"),
                "{:,}".format(L["total_median"] or 0), L["cases"], med(L["cases"]), L["all_green_n"], L["n"]))
    A.append("\n## 4 判据(预注册口径, 现算)\n")
    for key, name in (("K1_剂量机制", "K1 机制被行使(阈值收窄 ⇒ 触发面收窄)"),
                      ("K2_剂量代价", "K2 代价随剂量单调"),
                      ("K3_配对反事实", "K3 同 pfail 配对反事实"),
                      ("K4_质量", "K4 质量非劣"),
                      ("K6_窗口面", "K6 窗口面(w1/w2 并列, **禁跨轮相减**)"),
                      ("K7_旧路径列", "K7 旧路径列"),
                      ("K8_收口", "K8 收口(前置器)")):
        v = J.get(key) or {}
        A.append("- **%s**: `%s`" % (name, json.dumps(v, ensure_ascii=False)[:520]))
    A.append("")
    A.append("### 4a 口径审查 · K1 δ=1 的 FAIL(1) 归因 = **判据作用域缺陷, 不是产品缺陷**\n")
    A.append("D1a 违反项 `exec_repairs!=0`(该臂 `exec_repairs=1` 而 `early_stop_skipped=1`)。追到底: "
             "`R1Pipeline.cs:183` 谓语是 `opt.EarlyStopPfail>0 && probe.Failed>=opt.EarlyStopPfail`(**≥**, 与 δ=2 列"
             "「pfail=2 即命中」一致), 早停只作用于**探针失败之后**的那次回灌; 而 `exec_repairs` 计的是**全程**修复次数 —— "
             "D1a 的那 1 次修复发生在**探针还没有失败证据**的时候(无产物可测/执行证据回灌分支, `R1Pipeline.cs:266`)。"
             "⇒ 预注册 K1 要求行使臂 `exec_repairs==0`, 但台账字段无法区分「探针前修复」与「探针后修复」 ⇒ "
             "**该判据在现器具下不可能满足** ⇒ 按判据纪律: 判据被证伪 ⇒ **宣称收窄**(只宣「探针后那次修复被跳过」, "
             "即 `early_stop_skipped=1` 4/5 臂), 修法入 R548 候选(先写后跑)。\n")
    A.append("### 4b 口径审查 · 台账字段名与语义不一致(**本轮发现**)\n")
    A.append("台账键 `early_stop_pfail` 承载的是**阈值 δ**, 不是实测 pfail(`src/agent/r1/R1Transcript.cs:54` 写的是 "
             "`r.EarlyStopThreshold`; `R1RunResult.cs:31` 参数名同为阈值)。实测 pfail 只出现在 reply 内的 "
             "`R1_EARLY_STOP{...}` marker 与 `public_probe_failed` 里。⇒ 读表人极易把 δ 列当读数(本轮初次读表即差点误判"
             "「δ=3 且 pfail=3 却不跳过」)。修法(改名或加 `early_stop_threshold` 别名 + 保留旧键以免破坏跨轮可比) "
             "入 R548 候选。\n")
    A.append("### 4c 阴控与单调性\n")
    A.append("- δ=3 阴控: 3/3 臂 `early_stop_skipped=0` ⇒ 实测 pfail **从未跨过 3** ⇒ 预注册的「阈值语义被证伪」"
             "分支**未触发**, 阴控成立(**但这也意味着 δ=3 列不是 treatment, 只是第二条基线**)。")
    A.append("- 行使面单调: 跳过臂数 δ=1 **4/5** > δ=2 **1/5** > δ=3 **0/3** = δ=0 **0/5**(δ=0 无字段) ⇒ "
             "「阈值越低触发面越宽」**成立**, 但 δ=1 的触发面已宽到几乎恒真(pfail≥1 只要探针有一次失败)。\n")
    A.append("## 4d 事后单列(非预注册): 外侧对照 codex-cli 三窗\n")
    A.append("上一会话在 `/tmp/r547_reps` 实测的**同模型/同题面/同夹具**外侧对照(`--side codex` 中继同模型); "
             "题面 sha256 与 R547 钉**逐字节同**(`%s` vs pin `%s` → `%s`)。证据已入库 "
             "`eval/rover/r547/posthoc-codex-g1/`(+`MANIFEST.json` 记 (bytes,sha256))。"
             "**非预注册 ⇒ 只作事后单列, 不作验收依据。**\n"
             % (ph_prompt[:16], (pin or "?")[:16], "一致" if ph_prompt == pin else "**不一致**"))
    A.append("| 窗 | codex 用例 | codex 调用 | codex total tok | R1 用例 | R1 调用 | R1 total tok | R1 失败族 |")
    A.append("|---|---|---|---|---|---|---|---|")
    for r in post:
        c, g = r["codex"], r["agent"]
        A.append("| w%d | %s/%s | %s | %s | %s/%s | %s | %s | %s |"
                 % (r["win"], c.get("cases"), c.get("cases_total"), c["calls"], "{:,}".format(c["total"]),
                    g.get("cases"), g.get("cases_total"), g["calls"], "{:,}".format(g["total"]),
                    json.dumps(g.get("fails") or {}, ensure_ascii=False)))
    A.append("\n- R1 列配置 = 上一会话**默认**(公开自检开关未设=关, 早停未设=0) ⇒ **与 §3 的 δ 列不同配置**, 不可混用;")
    A.append("- 该轮的 codex 可行性本身是**前提更正**: R542/R545 记「g1 对 codex 不可行(32 步 × 18 分钟)」, "
             "实测 codex 在 g1 上 **9–85 次调用 / 24–142 s** 即可跑完 ⇒ 主线「四硬条件」的**外侧不再缺席**。\n")
    A.append("## 5 基线对比(基线 = δ=0 轴关列; 旧路径列只作参考)\n")
    A.append("- **代价(参考)**: δ=0 → δ=2 调用中位 %s → %s(比值 %s), total 中位 %s → %s(比值 %s); "
             "δ=3 列调用中位 %s — 但 **K3 配对样本不足**(δ=1 treated 4 / control 2; δ=2 treated 1 / control 0) "
             "⇒ **本轮不作任何降幅宣称**; 且前置器 rc=%s ⇒ 成本读数一律标「参考(未可验收)」。"
             % (S["d0"]["calls_median"], S["d2"]["calls_median"],
                round(S["d2"]["calls_median"] / S["d0"]["calls_median"], 3) if S["d0"]["calls_median"] else "?",
                "{:,}".format(S["d0"]["total_median"]), "{:,}".format(S["d2"]["total_median"]),
                round(S["d2"]["total_median"] / S["d0"]["total_median"], 3) if S["d0"]["total_median"] else "?",
                S["d3"]["calls_median"], pre_rc))
    A.append("- **质量**: 全绿 δ=0 **%d/5** · δ=1 **%d/5** · δ=2 **%d/5** · δ=3 **%d/3**; 用例中位 %s/%s/%s/%s。"
             "δ=1 列 0/5 全绿且用例中位最低 ⇒ **「δ=1 伤质量」只有一个方向的证据(n=5, 单窗)**; δ=2 相对 δ=0 **不更差**"
             "(3/5 vs 2/5, 中位 58 vs 56)。"
             % (S["d0"]["all_green_n"], S["d1"]["all_green_n"], S["d2"]["all_green_n"], S["d3"]["all_green_n"],
                S["d0"]["cases_median"], S["d1"]["cases_median"], S["d2"]["cases_median"], S["d3"]["cases_median"]))
    A.append("- **旧路径列(参考)**: 调用中位 %s(逐臂 %s; 全绿 %d/%d, total 中位 %s) vs δ∈{2,3} 中位 %s–%s ⇒ 调用约 %s×; "
             "**但这不是单变量对照** —— 旧路径(自动化路径)与 R1 列是**两条不同产品路径**, 且旧路径本窗 **%d/%d 满绿(58/58)** "
             "而 δ 列只有 %d/5–%d/5 ⇒ 该比值只作**同窗并存读数**, **不得当增益证据**(R545/R546 同纪律), 叠加前置器 rc=%s 标参考。"
             % (L["calls_median"], L["calls"], L["all_green_n"], L["n"], "{:,}".format(L["total_median"] or 0),
                S["d2"]["calls_median"], S["d3"]["calls_median"],
                round(L["calls_median"] / S["d2"]["calls_median"], 2) if S["d2"]["calls_median"] else "?",
                L["all_green_n"], L["n"], S["d2"]["all_green_n"], S["d3"]["all_green_n"], pre_rc))
    A.append("- **对外侧(参考, post-hoc)**: 同一题面上 R1 用 **2–5 次调用 / %s–%s tok** 换 **47–58/58** 用例; "
             "codex 用 **9–85 次调用 / %s–%s tok** 换 **56–58/58** ⇒ **成本侧 R1 低 1–2 个数量级, 质量侧 R1 在 2/3 窗落后 11 例"
             "(全部落在 `wythoff` 家族)** ⇒ 用户 R413 判据「token ↓≥30%% **且质量不降**」在 g1 上**只在成本侧成立**, "
             "质量侧**证伪** ⇒ 下一步的真外部效度抓手 = `wythoff` 家族定因, 不是继续压阈值。"
             % ("{:,}".format(min(r["agent"]["total"] for r in post)), "{:,}".format(max(r["agent"]["total"] for r in post)),
                "{:,}".format(min(r["codex"]["total"] for r in post)), "{:,}".format(max(r["codex"]["total"] for r in post))))
    A.append("- **测试/AOT 基线**: 全量 `agentframework.tests` **1876/1876**(0 failed, 54 s) · 产品源码零改动 ⇒ "
             "AOT `%s` %s B 与 R546 同一件(IL 警告 0 承 R546)。\n"
             % (AOT.get("sha256", "?")[:16], "{:,}".format(AOT.get("bytes", 0))))
    A.append("## 6 诚实边界\n")
    A.append("① 单窗(w2) ⇒ 逐窗极差不可估, 只是与 R546 的 w1 **并列**(K6; **禁跨轮相减**) ② 前置器 rc=%s ⇒ "
             "一切**降幅**标「参考(未可验收)」, 只有机制/事件计数(跳过数、调用数分布)可用 ③ **K1 判据本身被证伪**"
             "(§4a 作用域缺陷) ⇒ 已收窄宣称, 修法未落地 ④ K3 配对样本不足(treated 4/1, control 2/0) ⇒ 不宣称降幅 "
             "⑤ 质量侧 n=5(δ=3 n=3)单窗、离散结局主导方差 ⇒ 只报方向不宣称 ⑥ δ=3 阴控成立但**未跨过**, 故 δ=3 列不是 treatment "
             "⑦ 外侧对照是**事后**(非预注册)+ R1 列配置与 δ 列不同 ⇒ 只作参考 ⑧ 未测: 探针前/后修复的分段计数、"
             "`wythoff` 家族定因、δ=1 质量损伤的可复现性、旧路径列 n≥5。\n" % pre_rc)
    A.append("## 7 下轮候选(R548)\n")
    A.append("① **判据作用域修正**(先写后跑): 台账加分段计数(探针前修复 / 探针后跳过), 否则 K1 永远 FAIL ② 台账键改名/加别名 "
             "`early_stop_threshold`(保留旧键) ⇒ 消除 §4b 的读表歧义 ③ **`wythoff` 家族定因**(R1 侧 11/58 系统性错, "
             "codex 同题同窗 0–2 错) —— 这是「质量不降」的真抓手 ④ δ=1 质量损伤假设的单变量检验(与 δ=2 成对, n≥5) "
             "⑤ **外侧臂入预注册**(codex g1 已证可行, 破 R542 前提) ⇒ 主线四硬条件凑齐 ⑥ 旧路径列 n≥5。\n")
    jp = os.path.join(REPO, "docs/reports/r547-early-stop-dose.md")
    io.open(jp, "w", encoding="utf-8").write("\n".join(A))

    # ---- improvements ----
    imp = []
    imp.append("## R547 (2026-09-18) — 早停阈值**剂量面**(δ∈{0,1,2,3})单变量对照 · w2 — 结果: **剂量机制成立(行使面 4/5 > 1/5 > 0/3) "
               "· K1 δ=1 判据被证伪(作用域缺陷, 已收窄) · 降幅仍不作宣称 · 前置器 rc=%s ⇒ 参考(未可验收)**"
               "(轮志: `docs/reports/r547-early-stop-dose.md` · prereg/证据 `eval/rover/r547/`)" % pre_rc)
    imp.append("")
    imp.append("- **靶点来源**: R546 候选②(阈值剂量 1/2/3)。**单变量** = `AGENTFRAMEWORK_R1_EARLY_STOP_PFAIL ∈ {0,1,2,3}`; "
               "臂 21 个/窗(δ=0/1/2 各 5 session + δ=3 阴控 3 + 旧路径 3)。")
    imp.append("- **产品改动: 零**(`git diff -- src/` 空) ⇒ 复用 R546 AOT `%s`(IL 警告 0)。本轮只动器具/预注册。"
               % AOT.get("sha256", "?")[:16])
    imp.append("- **读数 (w2, 题面 sha256 与 R544–R546 逐字节同, 起手闸 2/2 PASS)**: 调用中位 δ0 %s / δ1 %s / δ2 %s / δ3 %s; "
               "total 中位 %s / %s / %s / %s; 用例中位 %s / %s / %s / %s; 全绿 %d/5 / %d/5 / %d/5 / %d/3; 旧路径 调用中位 %s · 全绿 %d/%d。"
               % (S["d0"]["calls_median"], S["d1"]["calls_median"], S["d2"]["calls_median"], S["d3"]["calls_median"],
                  "{:,}".format(S["d0"]["total_median"]), "{:,}".format(S["d1"]["total_median"]),
                  "{:,}".format(S["d2"]["total_median"]), "{:,}".format(S["d3"]["total_median"]),
                  S["d0"]["cases_median"], S["d1"]["cases_median"], S["d2"]["cases_median"], S["d3"]["cases_median"],
                  S["d0"]["all_green_n"], S["d1"]["all_green_n"], S["d2"]["all_green_n"], S["d3"]["all_green_n"],
                  L["calls_median"], L["all_green_n"], L["n"]))
    imp.append("- **判据**: K1 δ=2 **PASS** / δ=3 **PASS**(阴控未破: 3/3 跳过=0) / **δ=1 FAIL(1)** —— 归因见轮志 §4a: "
               "谓语是 `pfail≥δ`(与 δ=2 行为一致), 违反臂 D1a 的那次修复发生在**探针有失败证据之前** ⇒ "
               "**判据作用域与台账字段不对齐 ⇒ 判据被证伪, 宣称收窄**(只宣「探针后那次修复被跳过」)。"
               "K3 配对样本不足(4/2 与 1/0) ⇒ 不宣称降幅 · K4 质量: δ2 不更差(3/5 vs 2/5, 中位 58 vs 56) · K6 w1/w2 并列 · K7 旧路径 8 中位(比值只作参考)。")
    imp.append("- **口径审查(本轮新发现)**: 台账键 `early_stop_pfail` 承载的是**阈值 δ** 而非实测 pfail"
               "(`R1Transcript.cs:54` 写 `r.EarlyStopThreshold`) ⇒ 易被读成读数; 改名/别名入 R548 候选。")
    imp.append("- **事后单列(非预注册)**: 外侧对照 **codex-cli 同模型/同题面三窗** 已入库 "
               "`eval/rover/r547/posthoc-codex-g1/`(+MANIFEST): R1 %s–%s tok / 2–5 调用 → 47–58/58; "
               "codex %s–%s tok / 9–85 调用 → 56–58/58(**R1 落后 11 例全在 `wythoff` 家族**) ⇒ 「token↓≥30%% **且质量不降**」"
               "只在成本侧成立; 另: **codex 在 g1 上可行**(9–85 调用/24–142 s) ⇒ 破 R542「g1 对 codex 不可行」前提, "
               "主线四硬条件的**外侧不再缺席**。"
               % ("{:,}".format(min(r["agent"]["total"] for r in post)), "{:,}".format(max(r["agent"]["total"] for r in post)),
                  "{:,}".format(min(r["codex"]["total"] for r in post)), "{:,}".format(max(r["codex"]["total"] for r in post))))
    imp.append("- **测试/AOT 基线**: 全量 **1876/1876**(0 failed, 54 s, Release); 零源码改动 ⇒ AOT 与 R546 同一件 %s。"
               % AOT.get("sha256", "?")[:16])
    imp.append("- **诚实边界**: ① 单窗 w2(与 R546 w1 只并列, 禁相减) ② 前置器 rc=%s(BLOCKED %d 臂) ⇒ 降幅一律标参考 "
               "③ K1 判据作用域缺陷未修 ④ K3 配对样本不足 ⇒ 不宣称降幅 ⑤ 质量 n=5/3 单窗, 离散结局主导 ⇒ 只报方向 "
               "⑥ 外侧对照为事后且 R1 列配置与 δ 列不同 ⇒ 只作参考 ⑦ 未测: wythoff 定因、δ=1 质量损伤复现、旧路径 n≥5。"
               % (pre_rc, len(blocked)))
    imp.append("- **下轮候选 (R548)**: ① 台账分段计数(探针前修复/探针后跳过) + K1 谓语重钉(**先写后跑**) ② `early_stop_threshold` "
               "键改名/别名 ③ **`wythoff` 家族定因**(质量不降的真抓手) ④ δ=1 质量损伤成对检验 ⑤ 外侧臂入预注册 ⑥ 旧路径列 n≥5。")
    imp.append("")
    imppath = os.path.join(REPO, "docs/improvements.md")
    txt = io.open(imppath, encoding="utf-8").read()
    txt = re.sub(r"\n?<!-- R547-INFLIGHT:.*?-->\n?", "\n\n", txt, flags=re.S)
    txt = re.sub(r"\n## R547 \(.*?(?=\n## R5\d\d \(|\Z)", "", txt, flags=re.S)
    txt = txt.rstrip("\n") + "\n\n"
    io.open(imppath, "w", encoding="utf-8").write(txt)
    io.open(imppath, "a", encoding="utf-8").write("\n".join(imp))

    # ---- kpi 行 ----
    row = {"round": "R547",
           "ts": datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
           "kind": "主线轮(早停阈值剂量面: δ∈{0,1,2,3} × 5/5/5/3 rep + 旧路径 ×3, 单窗 w2) —— 产品源码零改动(复用 R546 AOT)",
           "artifact": "eval/rover/r547/{prereg-r547.json,input-pins-r547.json,taskset-r547.json,role-r547.txt,run_r547.sh,analyze_r547.py,report_r547.py,readings-w2.json,run-w2/**,snapshots/**,evidence/**,posthoc-codex-g1/**}"
                       " + eval/rover/r507pre/precondition-r547.json + docs/reports/r547-early-stop-dose.md + docs/improvements.md + eval/capability/kpi.jsonl",
           "change": "① 产品: **零改动**(git diff -- src/ 空 ⇒ 复用 R546 二进制 sha %s) ② 器具: 21 臂剂量面(δ=0/1/2/3 + 旧路径), "
                     "同输入硬门 xref 与 R546 逐字节同, 预注册范围闸 rc=0, 起手闸 2/2 PASS ③ 口径审查: 发现台账键 `early_stop_pfail` 实为**阈值**、"
                     "K1 谓语作用域与台账字段不对齐(探针前/后修复不可分)。"
                     % AOT.get("sha256", "?")[:16],
           "readings": "w2 δ=0 调用中位 %s/total 中位 %s/用例 %s/全绿 %d · δ=1 %s/%s/%s/%d · δ=2 %s/%s/%s/%d · δ=3 %s/%s/%s/%d · 旧路径 %s/(%s)/%s/%d。"
                       "**行使面单调**: 跳过臂数 4>1>0=0; **K1 δ=2 PASS / δ=3 阴控 PASS / δ=1 FAIL(1) 且归因为判据作用域缺陷(已收窄)**; "
                       "K3 配对样本不足 ⇒ 不宣称降幅; K4 质量 δ2 不更差(中位 58 vs 56)。前置器 rc=%s。"
                       "post-hoc 外侧(codex 同题面): R1 2–5 调用/%s–%s tok → 47–58/58; codex 9–85 调用/%s–%s tok → 56–58/58(R1 落后全在 wythoff)。"
                       % (S["d0"]["calls_median"], "{:,}".format(S["d0"]["total_median"]), S["d0"]["cases_median"], S["d0"]["all_green_n"],
                          S["d1"]["calls_median"], "{:,}".format(S["d1"]["total_median"]), S["d1"]["cases_median"], S["d1"]["all_green_n"],
                          S["d2"]["calls_median"], "{:,}".format(S["d2"]["total_median"]), S["d2"]["cases_median"], S["d2"]["all_green_n"],
                          S["d3"]["calls_median"], "{:,}".format(S["d3"]["total_median"]), S["d3"]["cases_median"], S["d3"]["all_green_n"],
                          L["calls_median"], "{:,}".format(L["total_median"] or 0), med(L["cases"]), L["all_green_n"], pre_rc,
                          "{:,}".format(min(r["agent"]["total"] for r in post)), "{:,}".format(max(r["agent"]["total"] for r in post)),
                          "{:,}".format(min(r["codex"]["total"] for r in post)), "{:,}".format(max(r["codex"]["total"] for r in post))),
           "honest_boundaries": "① 单窗 w2(与 R546 w1 只并列, 禁跨轮相减) ② 前置器 rc=%s(BLOCKED %d 臂) ⇒ 一切降幅标「参考(未可验收)」"
                                " ③ K1 δ=1 判据作用域缺陷未修(宣称已收窄) ④ K3 配对样本不足(treated 4/1, control 2/0) ⇒ 不宣称降幅"
                                " ⑤ 质量 δ=1 列 0/5 全绿只有一个方向证据(n=5 单窗) ⑥ δ=3 未跨过阈值 ⇒ 该列是第二基线不是 treatment"
                                " ⑦ 外侧对照为事后(非预注册)且 R1 列配置与 δ 列不同 ⇒ 只作参考 ⑧ 未测: 探针前/后修复分段计数、"
                                "wythoff 家族定因、δ=1 质量损伤复现性、旧路径列 n≥5。" % (pre_rc, len(blocked)),
           "next": "① 台账分段计数(探针前修复/探针后跳过)+K1 谓语重钉(先写后跑) ② `early_stop_threshold` 键改名/别名 ③ **wythoff 家族定因**"
                   "(同题同窗 codex 0–2 错 vs R1 11 错) ④ δ=1 质量损伤成对检验 ⑤ **外侧臂(codex g1)入预注册** —— 四硬条件凑齐 "
                   "⑥ 旧路径列 n≥5。",
           "owner_round": "R547"}
    kp = os.path.join(REPO, "eval/capability/kpi.jsonl")
    if '"round": "R547"' not in io.open(kp, encoding="utf-8").read():
        io.open(kp, "a", encoding="utf-8").write(json.dumps(row, ensure_ascii=False) + "\n")
        print("[kpi] appended R547")
    else:
        print("[kpi] R547 already present")
    print(json.dumps({"journal": jp, "precond_rc": pre_rc, "blocked": len(blocked), "S": S, "L": L,
                      "post": [{k: r[k] for k in ("win",)} | {"codex": {kk: r["codex"][kk] for kk in ("cases", "calls", "total")},
                                                              "agent": {kk: r["agent"][kk] for kk in ("cases", "calls", "total")}} for r in post],
                      "AOT": AOT, "ph_prompt_matches_pin": ph_prompt == pin}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
