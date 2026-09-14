#!/usr/bin/env python3
"""R440 预注册预测器 — **长度分档梯** V1/V2/V4/V5 的降幅预测（跑测**之前**落盘）。

口径（R413 用户令不变）: 降幅 = 1 − Σ_远端(B_arm) / Σ_远端(A_arm)。
  分档定义（R437 用户口径澄清令: 「一轮任务…可能很多次也可能只用一次」）:
    V1 = N=1 单次真诉求  V2 = N=3 短(可跳 1/3 早)
    V4 = N=20 长(可跳 7/20 晚簇)  V5 = N=20 零可跳(全真诉求)

结构模型（三项，全部由磁盘档案**程序化标定**，无手打常数；与 R439 同式）:
  ① 逐调用基线 A(i)   = 该网格 A 臂实测（门关 ⇒ 不受 R438 修复影响）
                         本网格无 A 实测 ⇒ 用**同长度**已测网格代理（标记 proxy:*，属预注册假设）
  ② 角色块偏移 δ(i)   = d0 + d1·i   （由 p12 修复后 A/BRJ 同轮差 − 被移除块质量 反解）
  ③ 跳过轮块质量 m(t) = 条目级实测中位数插值（跳过轮的块**不再回放** ⇒ 后期调用被扣减）
  BRJ(i) = A(i) + δ(i) − Σ_{t∈S, t<i} m(t)

**模型可信度前提（样本内验证，必须 ≤1% 偏差，否则模型作废）**:
  · p12 修复后 BRJ 实测 17319   · p8 修复前 BRJ 实测 11967（无移除项）

判伪（预注册）: 实测降幅落在预测 ±3.0 pt 之外 ⇒ 判「外推失效」（非机制失效），须重标定并披露。
用法: python3 predict_r440.py            → eval/rover/r440/predict-r440-pre.json
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
R436, R438, R439, OUT = ROOT / "eval/rover/r436", ROOT / "eval/rover/r438", ROOT / "eval/rover/r439", ROOT / "eval/rover/r440"
MARK = "[本轮参考上下文]"


def rows(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()] if pathlib.Path(p).exists() else []


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


GRID_PATHS = {"p8": R436 / "grid/task-p8.json", "p12": R438 / "grid/task-p12.json",
              "V20": R439 / "grid/task-V20.json", "V1": OUT / "grid/task-V1.json",
              "V2": OUT / "grid/task-V2.json", "V4": OUT / "grid/task-V4.json", "V5": OUT / "grid/task-V5.json"}
GRID = {g: json.load(open(p, encoding="utf-8"))["turns"] for g, p in GRID_PATHS.items() if p.exists()}
TURNS = {g: {t.strip(): i + 1 for i, t in enumerate(ts)} for g, ts in GRID.items()}
def turn_of(g, text):
    return TURNS.get(g, {}).get((text or "").strip())


# ---- ① A 臂实测逐轮（p8=R436, p12=R438, V20=R439; 门关 ⇒ 与 R438 修复无关）----
arch = {"p8": R436, "p12": R438, "V20": R439}
A_meas = {}
for g, d0 in arch.items():
    d = {}
    for c in rows(d0 / f"calls-A-{g}.jsonl"):
        t = turn_of(g, pre_of(lastu(c))[0])
        if t:
            d[t] = est(c)
    A_meas[g] = dict(sorted(d.items()))

ax, ay = list(A_meas["p12"]), [A_meas["p12"][k] for k in A_meas["p12"]]
quad = ols(ax, ay, deg=2)
A_fit = lambda i: quad[0] + quad[1] * i + quad[2] * i * i  # noqa: E731

# ---- ③ 条目级块质量 m(t) ----
obs = {}
for g, p in (("p12", R438 / "calls-A-p12.jsonl"), ("p12", R438 / "calls-BRJ-p12.jsonl"),
             ("p8", R436 / "calls-BRJ-p8.jsonl"), ("p8", R436 / "calls-BP-p8.jsonl")):
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

# ---- ② δ(i): p12 修复后同轮差 − 被移除块质量 ----
S12 = [2, 3, 4, 5]
brj12 = {}
for c in rows(R438 / "calls-BRJ-p12.jsonl"):
    t = turn_of("p12", pre_of(lastu(c))[0])
    if t:
        brj12[t] = est(c)
d_obs = {t: brj12[t] - A_meas["p12"][t] + sum(mof(x) for x in S12 if x < t) for t in sorted(set(brj12) & set(A_meas["p12"]))}
d_co = ols(list(d_obs), [d_obs[k] for k in d_obs], deg=1)
delta = lambda i: d_co[0] + d_co[1] * i  # noqa: E731

# ---- 样本内验证（模型可信度前提）----
v12 = round(sum(A_meas["p12"][i] + delta(i) for i in A_meas["p12"] if i not in S12) - sum(mof(t) * len([i for i in A_meas["p12"] if i not in S12 and i > t]) for t in S12), 1)
model8_pre = round(sum(A_meas["p8"][i] + delta(i) for i in A_meas["p8"] if i not in (2, 6, 8)), 1)
in_sample = {
    "p12_postfix": {"model_BRJ": v12, "measured_BRJ": 17319.0, "dev_pct": round(100 * abs(v12 - 17319.0) / 17319.0, 4)},
    "p8_prefix": {"model_BRJ": model8_pre, "measured_BRJ": 11967.0, "dev_pct": round(100 * abs(model8_pre - 11967.0) / 11967.0, 4)},
}
_dev = max(x["dev_pct"] for x in in_sample.values())
in_sample["verdict"] = "OK(<=1%)" if _dev <= 1.0 else "FAIL ⇒ 模型作废"


# ---- 分档预测 ----
def predict(grid, S, proxy, note):
    S = sorted(S)
    turns = GRID[grid]
    N = len(turns)
    A = {}
    for i in range(1, N + 1):
        if grid in A_meas and i in A_meas[grid]:
            A[i] = A_meas[grid][i]
        else:
            # 同长度代理: 先按文本匹配已测网格, 再退化为逐轮下标代理
            # 逐轮下标优先（成本由历史长度/位置决定）; 文本匹配仅作参考记录
            A[i] = A_meas[proxy][i] if i in A_meas[proxy] else A_fit(i)
    calls = [i for i in range(1, N + 1) if i not in S]
    a_tot = sum(A.values())
    removed = sum(mof(t) * len([i for i in calls if i > t]) for t in S)
    brj = sum(A[i] + delta(i) for i in calls) - removed
    return {"grid": grid, "N": N, "S": S, "calls": calls, "A_total": round(a_tot, 1), "BRJ_total": round(brj, 1),
            "removed_mass_tok": round(removed, 1), "pred_drop_pct": round(100 * (1 - brj / a_tot), 4),
            "A_source": "measured" if grid in A_meas else f"proxy({proxy}) by turn index",
            "A_per_turn": {k: round(v, 1) for k, v in sorted(A.items())}, "note": note}


PREDS = {
    "V1": predict("V1", [], "p8", "N=1 单次真诉求: 期望净亏(负降幅) = 角色块 + 门成本 / 单次基线"),
    "V2": predict("V2", [2], "p8", "N=3 短, 可跳 1/3 早位置"),
    "V4": predict("V4", list(range(14, 21)), "V20", "N=20 长, 可跳 35% **晚簇** (与 V20 同文本/同认可轮数 ⇒ 单变量=位置)"),
    "V5": predict("V5", [], "V20", "N=20 零可跳 ⇒ 期望净亏; 新增 7 条文本未经 r1 实测(fn 风险)"),
}
# R437 旧模型（解析式分档）对应格, 供对照（程序化读取, 缺失记 null）
r437p = ROOT / "eval/capability/r437-task-length/result.json"
r437 = json.load(open(r437p, encoding="utf-8")) if r437p.exists() else {}
def r437_cell(*keys):
    cur = r437
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur
for g, k in (("V1", ("single",)), ("V2", ("short",)), ("V4", ("long",))):
    PREDS[g]["r437_old_model_anchor"] = r437_cell("cells", k) if r437 else None

out = {
    "round": "R440", "kind": "pre_registered_prediction", "ts": subprocess.run(["date", "-Iseconds"], capture_output=True, text=True).stdout.strip(),
    "target": "分档降幅(非单一 ≥30%): V1 期望<0, V2 ~25-35%, V4 ≥30%, V5 期望<0",
    "tolerance_pt": 3.0, "deltas_margin_pt": 3.0,
    "model": {"delta_role_offset": {"d0": round(d_co[0], 4), "d1": round(d_co[1], 4)}, "block_mass_medians": m_obs,
              "A_measured_per_turn": A_meas, "p12_A_quadratic": [round(x, 4) for x in quad]},
    "in_sample_validation": in_sample, "predictions": PREDS,
    "falsification": "各档 |实测 − 预测| > 3.0 pt ⇒ 该档外推失效, 须重标定并披露, 不得沿用本节因果叙述。",
    "assumptions": ["A 分母代理取**逐轮下标**匹配（v1 逐文本匹配曾取错位置: 单轮网格拿到带历史成本 ⇒ V1 净亏被低估）; 未匹配者用 p12 二次拟合 ⇒ 分母误差直接进降幅",
                    "V5 含 7 条未经 r1 实测的新文本 ⇒ 门若误跳真诉求则 fn>0, 判据 C-fn 失败",
                    "δ(i) 由 p12 反解, 位置 i>12 属线性外推", "m(t) 由 p12/p8 条目级中位数插值"],
}
json.dump(out, open(OUT / "predict-r440-pre.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("in-sample:", json.dumps(in_sample, ensure_ascii=False), "| delta:", round(d_co[0], 3), round(d_co[1], 4))
for g, p in PREDS.items():
    print(f"  {g}: A={p['A_total']} BRJ={p['BRJ_total']} pred_drop={p['pred_drop_pct']}% S={p['S']} src={p['A_source']}")
print("wrote", OUT / "predict-r440-pre.json")
