#!/usr/bin/env python3
"""R439 预注册预测器 — ≥30% 降幅的**域扩展**验证（长任务 V20 + p8 复测）。

口径（R413 用户令不变）: 降幅 = 1 − Σ_远端(BRJ) / Σ_远端(A)。判官 J 在 BRJ 臂完全本地 ⇒ 0 远端 token。

结构模型（三项，全部由磁盘档案程序化标定，**无手打常数**）:
  ① 逐调用基线   A(i)      = 该网格 **A 臂实测** 第 i 轮 prompt+completion est（门关 ⇒ 不受修复影响）
                              若某网格 A 臂尚未跑（V20 预注册时）⇒ 用 p12 实测二次拟合外推（标记 extrapolated）
  ② 角色块偏移   δ(i)      = d0 + d1·i        （门要吃 role ⇒ 每次远端调用多带 role 块；A/BRJ 同轮差验证）
  ③ 跳过轮块质量 m(t)      = 条目级实测中位数插值（后期调用历史里 `[本轮参考上下文]` 之后字符数 //2）
  BRJ(i) = A(i) + δ(i) − Σ_{t∈S, t<i} m(t)    （S = 该网格设计跳集；修复 = 跳过轮的块**不再回放**）
  降幅 = 1 − Σ_{i∉S} BRJ(i) / Σ_{i=1..N} A(i)

**样本内验证（模型可信度前提，报告必须带）**: 用同一模型回算
  · p12 修复后 BRJ（实测 17319）  · p8 修复前 BRJ（实测 12122，无移除项）
  两者均须 ≤1% 偏差；否则模型作废。

用法: python3 predict_r439.py [pre|anchor]   → eval/rover/r439/predict-r439{,-anchor}.json
"""
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
R438, R436, OUT = ROOT / "eval/rover/r438", ROOT / "eval/rover/r436", ROOT / "eval/rover/r439"
MARK = "[本轮参考上下文]"
MODE = (sys.argv[1] if len(sys.argv) > 1 else "pre").strip()


def rows(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()] if os.path.exists(p) else []


def est(c):
    return int(c.get("prompt_tokens_est") or 0) + int(c.get("completion_tokens_est") or 0)


def umsgs(c):
    return [str(m.get("content") or "") for m in (c.get("messages") or []) if str(m.get("role")) == "user"]


def lastu(c):
    u = umsgs(c)
    return u[-1] if u else ""


def pre_of(s):
    i = s.find(MARK)
    return (s[:i], s[i:]) if i >= 0 else (s, "")


def ols(xs, ys, deg=1):
    n = deg + 1
    M = [[sum(x ** (i + j) for x in xs) for j in range(n)] for i in range(n)]
    v = [sum(y * x ** i for x, y in zip(xs, ys)) for i in range(n)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(M[r][i]))
        M[i], M[p], v[i], v[p] = M[p], M[i], v[p], v[i]
        for r in range(i + 1, n):
            f = M[r][i] / M[i][i] if M[i][i] else 0.0
            for c2 in range(i, n):
                M[r][c2] -= f * M[i][c2]
            v[r] -= f * v[i]
    co = [0.0] * n
    for i in reversed(range(n)):
        co[i] = (v[i] - sum(M[i][j] * co[j] for j in range(i + 1, n))) / (M[i][i] or 1.0)
    return co


GRID = {}
for g in ("p8", "p12", "V20"):
    for base in (R438 / "grid", ROOT / "eval/rover/r439/grid"):
        f = base / f"task-{g}.json"
        if f.exists():
            GRID[g] = json.load(open(f, encoding="utf-8"))["turns"]
            break
TURNS = {g: {t.strip(): i + 1 for i, t in enumerate(ts)} for g, ts in GRID.items()}


def turn_of(g, text):
    return TURNS[g].get(text.strip())


# ---- ① 各网格 A 臂实测逐轮 ----
arch = {"p12": R438, "p8": R436, "V20": OUT}
A_meas = {}
for g in ("p8", "p12", "V20"):
    d = {}
    for c in rows(arch[g] / f"calls-A-{g}.jsonl"):
        t = turn_of(g, pre_of(lastu(c))[0])
        if t:
            d[t] = est(c)
    A_meas[g] = dict(sorted(d.items()))

# p12 二次拟合（V20 预注册外推用）
ax, ay = list(A_meas["p12"]), [A_meas["p12"][k] for k in A_meas["p12"]]
quad = ols(ax, ay, deg=2)
A_fit = lambda i: quad[0] + quad[1] * i + quad[2] * i * i  # noqa: E731

# ---- ③ 条目级块质量 m(t)（中位数 + 线性插值/外推）----
obs = {}
for g, p in ((("p12"), R438 / "calls-A-p12.jsonl"), ("p12", R438 / "calls-BRJ-p12.jsonl"),
             ("p8", R436 / "calls-A-p8.jsonl"), ("p8", R436 / "calls-BRJ-p8.jsonl"), ("p8", R436 / "calls-BP-p8.jsonl")):
    for c in rows(p):
        for s in umsgs(c):
            pre, blk = pre_of(s)
            t = turn_of(g, pre)
            if t and blk:
                obs.setdefault(t, []).append(len(blk) // 2)
m_obs = {t: sorted(v)[len(v) // 2] for t, v in sorted(obs.items())}
ks = sorted(m_obs)


def mof(t):
    if not ks:
        return 93.0
    if t <= ks[0]:
        return float(m_obs[ks[0]])
    if t >= ks[-1]:
        slope = (m_obs[ks[-1]] - m_obs[ks[-2]]) / (ks[-1] - ks[-2]) if len(ks) > 1 else 0.0
        return float(m_obs[ks[-1]] + slope * (t - ks[-1]))
    for a, b in zip(ks, ks[1:]):
        if a <= t <= b:
            return float(m_obs[a] + (m_obs[b] - m_obs[a]) * (t - a) / (b - a))
    return 93.0


# ---- ② δ(i) 由 p12 修复后 A/BRJ 同轮差 − 被移除块质量 ----
S12 = [2, 3, 4, 5]
brj12 = {}
for c in rows(R438 / "calls-BRJ-p12.jsonl"):
    t = turn_of("p12", pre_of(lastu(c))[0])
    if t:
        brj12[t] = est(c)
d_obs = {t: brj12[t] - A_meas["p12"][t] + sum(mof(x) for x in S12 if x < t) for t in sorted(set(brj12) & set(A_meas["p12"]))}
d_co = ols(list(d_obs), [d_obs[k] for k in d_obs], deg=1)
delta = lambda i: d_co[0] + d_co[1] * i  # noqa: E731


def aof(g, i, extrapolate):
    if i in A_meas[g] and not (g == "V20" and MODE == "pre"):
        return A_meas[g][i]
    if extrapolate:
        return A_fit(i)
    return None


A_CALLS = {g: sorted(A_meas[g]) for g in A_meas}


def calls_for(g, S, nominal_from):
    """真实调用轮集: 有 A 臂实测 ⇒ 用实测(剔 S); 否则用名义补集。
    校准事实: 每网格各有 1 轮**两臂皆无远端调用**(p12 t7 / p8 t4, 产品 ask 消费 ⇒ `asks:2`), 属器具固有, 与处理无关。"""
    meas = A_CALLS.get(g) or []
    if meas:
        return [i for i in meas if i not in S]
    return [i for i in range(1, nominal_from + 1) if i not in S]


def score(g, S, N, extrapolate):
    S = sorted(S)
    calls = calls_for(g, S, N)
    a_tot = (sum(A_meas[g].values()) if A_CALLS.get(g)
             else sum(A_fit(i) for i in range(1, N + 1)))
    removed = sum(mof(t) * len([i for i in calls if i > t]) for t in S)
    brj = sum(((A_meas[g][i] if i in A_meas[g] else A_fit(i)) + delta(i)) for i in calls) - removed
    return {"grid": g, "N": N, "S": S, "A_total": round(a_tot, 1), "BRJ_total": round(brj, 1),
            "calls": calls, "removed_mass_tok": round(removed, 1), "drop_pct": round(100 * (1 - brj / a_tot), 4)}


# ---- 口径: 分母/分子均取**G(远端生成) token**; 判官 J 单列(R439 起 J 全本地 ⇒ 0 远端)。
# R436 p8 报告口径含 1 次远端判官调用(155) ⇒ 本表按 G 口径复算 35.25%(原 34.41% 属口径含 J)。
# ---- 样本内验证（调用轮集一律取**实测**; 名义补集会混入 ask 消费轮 ⇒ 曾误判 13% 偏差）----
v12 = score("p12", [2, 3, 4, 5], 12, True)
meas12 = 17319.0      # verdict-BRJ-p12.json (R438, G_tokens)
meas8_pre = 11967.0   # verdict-BRJ-p8.json (R436, G_tokens; J 155 单列)
model8_pre = round(sum(A_meas["p8"][i] + delta(i) for i in A_CALLS["p8"] if i not in (2, 6, 8)), 1)
in_sample = {
    "p12_postfix": {"model_BRJ": v12["BRJ_total"], "measured_BRJ": meas12,
                    "dev_pct": round(100 * abs(v12["BRJ_total"] - meas12) / meas12, 4)},
    "p8_prefix": {"model_BRJ": model8_pre, "measured_BRJ": meas8_pre,
                  "dev_pct": round(100 * abs(model8_pre - meas8_pre) / meas8_pre, 4)},
}
_dev = max(in_sample["p12_postfix"]["dev_pct"], in_sample["p8_prefix"]["dev_pct"])
in_sample["verdict"] = "OK(<=1%)" if _dev <= 1.0 else "FAIL ⇒ 模型作废"
in_sample["p8_prefix_drop_pct_G口径"] = round(100 * (1 - meas8_pre / 18481), 4)

# ---- p8 复测：实测 A(冻结) − 修复移除项 (R439 修复: 跳过轮块不再回放; J 全本地) ----
p8 = score("p8", [2, 6, 8], 9, False)
p8["pre_fix_measured_BRJ"] = meas8_pre
p8["pre_fix_measured_drop_pct"] = round(100 * (1 - meas8_pre / p8["A_total"]), 4)

# ---- V20 ----
v20 = score("V20", [2, 5, 8, 11, 14, 17, 20], 20, True)
v20["A_source"] = "measured(A-V20 已跑)" if A_meas["V20"] else "extrapolated(p12 二次拟合)"
v20["calls_source"] = "measured(A-V20)" if A_meas["V20"] else "nominal(假设无 ask 消费轮)"

out = {
    "round": "R439", "kind": f"pre_registered_prediction:{MODE}", "mode": MODE,
    "ts": subprocess.run(["date", "-Iseconds"], capture_output=True, text=True).stdout.strip(),
    "target": "drop >= 30.0%", "tolerance_pt": 3.0,
    "model": {
        "p12_A_quadratic": {"a0": round(quad[0], 4), "a1": round(quad[1], 4), "a2": round(quad[2], 6),
                            "fit_vs_meas_p12_A": [round(sum(A_fit(i) for i in range(1, 12)), 1), sum(ay)]},
        "delta_role_offset": {"d0": round(d_co[0], 4), "d1": round(d_co[1], 4), "observed": d_obs},
        "block_mass_medians": m_obs, "J_remote_tokens_in_BRJ": 0, "estimator": "chars//2 (stub_openai.py)",
        "A_measured_per_turn": A_meas,
    },
    "in_sample_validation": in_sample,
    "predictions": {"p8_rerun": p8, "V20": v20},
    "falsification": "实测降幅落在预测 ±3.0 pt 之外 ⇒ 判「外推失效」(非机制失效): 须重标定并披露, 不得沿用本节因果叙述。",
    "assumptions": ["V20 轮文本较 p12 长 5…9 字符/轮 ⇒ 一阶抵消于比值", "m(t) 由 p12/p8 条目级中位数插值, t>12 用末段斜率外推",
                    "p8 A 臂第 4 轮无调用(与 BRJ 臂同, 属器具固有), 已按实测排除"],
}
json.dump(out, open(OUT / f"predict-r439{'-anchor' if MODE == 'anchor' else ''}.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("mode:", MODE, "| in-sample:", in_sample["p12_postfix"]["dev_pct"], "%,",
      in_sample["p8_prefix"]["dev_pct"], "%", "->", in_sample["verdict"])
print("p8  rerun pred:", p8)
print("V20 pred      :", v20)
