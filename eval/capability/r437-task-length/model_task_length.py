#!/usr/bin/env python3
"""R437 分析器具 —— 「一轮任务 = 可能多次链调用」口径下的**按任务长度分档降幅评估**。

口径（用户钦定，逐字）: 「一轮任务，应该是长任务30%左右，中短任务啥的具体降低多少你要自己评估下
(注意一轮不是走一次链，可能很多次也可能只用一次)」

模型（参数全部来自 R434 真机实测, 非拍脑袋）:
  主答单次 token      T(i) = T0 + g·i           (i = 会话内第 i 轮; 每次远端主调用携带全部历史)
  角色块偏移          δ(i) = δ0 + dg·i           (门需要 role ⇒ 每次远端调用都多带 role 块; 只多不少)
  关系判官            J    = 每次 ≈ 53 tok       (有 role 时每轮一次; R434 实测 J 本地成功率 1/7 ⇒ 默认远端)
  A 臂（门关）        = Σ_{i∈answered} T(i)
  B 臂（门开）        = Σ_{i∈answered\S} [T(i)+δ(i)] + |answered|·J
  降幅 = 1 − B/A
  其中 S = 被门跳过（认可族）的轮集合。

锚点（实测, 用于标定与回验）: R434 task-p8 (8 answered, S={2,6,8}) 实测 33.3%; task-p12 (11 answered, S={2,3,4,5}) 实测 27.8%。
"""
import json
import os
import pathlib
import sys


def ols(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs) or 1.0
    g = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    return my - g * mx, g


def calibrate(root: pathlib.Path):
    """从 R434 实测 verdict 标定 (T0,g) 与 (δ0,dg) 与 J。"""
    D = root / "eval/rover/r434"

    def load(a, g, ns):
        return json.load(open(D / f"verdict-{a}-{g}{ns}.json", encoding="utf-8"))

    A8, B8 = load("A", "p8", "-a2"), load("B", "p8", "-i1")
    A12, B12 = load("A", "p12", "-n1"), load("B", "p12", "-o1")

    def calls(v):
        return [(q["turn"], q["G_tokens"]) for q in v["per_turn"] if q["G_calls"] > 0]

    out = {}
    for tag, A, B in (("p8", A8, B8), ("p12", A12, B12)):
        c = calls(A)
        T0, g = ols([t for t, _ in c], [tok for _, tok in c])
        da = {t: tok for t, tok in c}
        db = {t: tok for t, tok in calls(B)}
        common = sorted(set(da) & set(db))
        d0, dg = ols(common, [db[t] - da[t] for t in common])
        jn = sum(1 for q in B["per_turn"] if q["J_tokens"] > 0)
        jtok = sum(q["J_tokens"] for q in B["per_turn"])
        out[tag] = {"T0": T0, "g": g, "d0": d0, "dg": dg, "J_per": jtok / max(jn, 1), "J_n": jn,
                    "J_tok": jtok, "measured_A": A["tokens_total"], "measured_B": B["tokens_total"]}
    return out


def reduce_model(N, S, T0, g, d0, dg, J):
    answered = list(range(1, N + 1))
    A = sum(T0 + g * i for i in answered)
    B = sum((T0 + g * i) + (d0 + dg * i) for i in answered if i not in S) + len(answered) * J
    return A, B, 1.0 - B / A


def main():
    root = pathlib.Path(os.environ.get("AGENTFRAMEWORK_ROOT", "/home/agentuser/AgentFramework"))
    cal = calibrate(root)
    # 用 p12 标定参数作主模型 (会话更长 ⇒ 参数更稳)，p8 作回验
    T0, g = cal["p12"]["T0"], cal["p12"]["g"]
    d0, dg = cal["p12"]["d0"], cal["p12"]["dg"]
    J = (cal["p12"]["J_per"] + cal["p8"]["J_per"]) / 2

    print("== 标定（全部来自 R434 实测）==")
    for tag in ("p8", "p12"):
        c = cal[tag]
        print(f"  {tag}: T0={c['T0']:.0f} g={c['g']:.1f} | δ0={c['d0']:.0f} dg={c['dg']:.2f} | J/次={c['J_per']:.1f} (n={c['J_n']})")

    print("\n== 回验（模型 vs 实测）==")
    checks = [("task-p8", 8, {2, 6, 8}, 1 - 12338 / 18493), ("task-p12", 11, {2, 3, 4, 5}, 1 - 19990 / 27670)]
    calib = []
    for name, N, S, meas in checks:
        A, B, r = reduce_model(N, S, T0, g, d0, dg, J)
        eta = (r - meas) / meas
        calib.append({"grid": name, "N": N, "S": sorted(S), "model_pct": r * 100, "measured_pct": meas * 100,
                      "abs_err_pt": abs(r - meas) * 100, "rel_err_pct": eta * 100})
        print(f"  {name}: 模型 {r*100:.1f}% | 实测 {meas*100:.1f}% | 绝对误差 {abs(r-meas)*100:.1f}pt | 相对误差 {eta*100:+.1f}%")
    # 系统性偏差 ⇒ 用实测/模型比作**保守修正因子**（模型偏乐观/悲观都如实标注）
    k = sum(c["measured_pct"] for c in calib) / sum(c["model_pct"] for c in calib)

    def pat(ratio, N, where):
        k_ack = max(1, min(N, round(ratio * N)))
        if where == "early":
            return {i for i in range(2, 2 + k_ack) if i <= N}
        if where == "late":
            return set(range(N - k_ack + 1, N + 1))
        # interleaved: 从第 2 轮起等距
        step = max(2, N // k_ack)
        S, i = set(), 2
        while len(S) < k_ack and i <= N:
            S.add(i)
            i += step
        return S

    print("\n== 分档降幅面（模型；括号内 = 乘实测修正因子 %.3f 的保守估计）==" % k)
    rows, seen = [], set()
    buckets = [("单次(只用一次)", [1]), ("短", [2, 3]), ("中", [5, 8, 12]), ("长", [20, 40])]
    for label, Ns in buckets:
        for N in Ns:
            cells = [(0.0, "noskip")] + [(ratio, w) for ratio in (0.25, 1 / 3, 0.5)
                                         for w in ("early", "interleaved", "late")]
            for ratio, where in cells:
                S = set() if where == "noskip" else pat(ratio, N, where)
                key = (N, tuple(sorted(S)))
                if key in seen:
                    continue
                seen.add(key)
                A, B, r = reduce_model(N, S, T0, g, d0, dg, J)
                rows.append({"bucket": label, "N": N, "ack_ratio": round(len(S) / N, 3), "pattern": where,
                             "skip_turns": sorted(S), "model_pct": round(r * 100, 1),
                             "conservative_pct": round(r * k * 100, 1),
                             "A_tok": round(A), "B_tok": round(B)})
    hdr = f"{'档':<12}{'N':>3}{'可跳比':>8}{'位置':>12}{'模型降幅':>10}{'保守估计':>10}"
    print(hdr)
    for r_ in rows:
        print(f"{r_['bucket']:<12}{r_['N']:>3}{r_['ack_ratio']:>8.2f}{r_['pattern']:>12}{r_['model_pct']:>9.1f}%{r_['conservative_pct']:>9.1f}%")

    out = {"model": {"T0": T0, "g": g, "delta0": d0, "delta_g": dg, "J_per_call": J},
           "calibration": cal, "validation": calib, "conservative_factor_k": k, "surface": rows}
    p = root / "eval/capability/r437-task-length/result.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n→ {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
