using System;
using System.Collections.Generic;
using System.Numerics;

namespace agent.rover.formal;

/// <summary>精确可行性判定 (Fourier–Motzkin 消元, 全整数 Int128 无浮点)。
/// 契约: 只可能「判定成功」或「放弃(Unknown)」——绝不在未证明时报 Proved/Refuted。
/// 反例模型一律**精确复核**后才返回。</summary>
public static class FourierMotzkin
{
    public const int MaxVars = 12;
    public const int MaxCons = 512;

    public sealed class Unsupported : Exception { public Unsupported(string m) : base(m) { } }

    public enum Sat { Sat, Unsat, Unknown }

    /// <summary>整数语义下的可满足性。有理数可行 ⇒ 再尝试**精确整数补全** (外框外扩、框内穷举, 仅当框可穷举时)。
    /// 只返回 Sat(附精确模型) / Unsat / Unknown —— Unsat 只在「外框为空」或「框内穷举完毕无解」时给出。</summary>
    public static Sat Satisfiable(List<Constraint> input, out Dictionary<string, Int128>? model)
    {
        model = null;
        // (c) 健全整数必要条件: 显式等式 a·x = b 且 gcd(a_i) ∤ b ⇒ **无整数解** (有理可行但整数不可行)。
        // 例: 3x-3y=1 (g=3∤1) / 2x=2y+1 (g=2∤1)。只可能新增 Unsat, 且该条件为必要条件 ⇒ 不产生假 Unsat。
        if (HasGcdInfeasibleEquality(input)) return Sat.Unsat;
        if (!Feasible(input, out var m)) return Sat.Unsat;          // 有理数不可行 ⇒ 整数必不可行
        if (m != null) { model = m; return Sat.Sat; }
        // (a)(b) 取点播种: 加宽窗口 + 精确外框角点 + 等式代入点。
        // 每个候选点都逐约束 Int128 精确复核 ⇒ 只可能把 Unknown 提升为 Sat, 绝不产生假 Sat。
        if (TrySeededModel(input, out var seeded)) { model = seeded; return Sat.Sat; }
        var box = ExactBox(input);
        if (box == null) return Sat.Unknown;
        var (lo, hi, vars) = box.Value;
        Int128 total = 1;
        foreach (var v in vars)
        {
            var w = hi[v] - lo[v] + 1;
            if (w <= 0) return Sat.Unsat;                            // 外框为空 ⇒ 无整数解
            total = checked(total * w);
            if (total > MaxEnumerate) return Sat.Unknown;
        }
        var pick = new Dictionary<string, Int128>(StringComparer.Ordinal);
        foreach (var v in vars) pick[v] = lo[v];
        while (true)
        {
            bool ok = true;
            foreach (var c in input)
            {
                Int128 lhs = 0;
                foreach (var kv in c.Coeffs) lhs = checked(lhs + checked(kv.Value * pick[kv.Key]));
                if (c.Strict ? !(lhs < c.Rhs) : !(lhs <= c.Rhs)) { ok = false; break; }
            }
            if (ok) { model = new Dictionary<string, Int128>(pick, StringComparer.Ordinal); return Sat.Sat; }
            int i = vars.Count - 1;
            while (i >= 0)
            {
                if (pick[vars[i]] < hi[vars[i]]) { pick[vars[i]]++; break; }
                pick[vars[i]] = lo[vars[i]]; i--;
            }
            if (i < 0) return Sat.Unsat;                             // 框内穷举完毕, 无整数解
        }
    }

    public const long MaxEnumerate = 100000;

    /// <summary>精确整数外框 (含所有实解 ⇒ 必含所有整数解)。任一分量无界 ⇒ null (⇒ Unknown)。</summary>
    private static (Dictionary<string, Int128> Lo, Dictionary<string, Int128> Hi, List<string> Vars)? ExactBox(List<Constraint> cons)
    {
        var vars = new List<string>();
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var c in cons) foreach (var k in c.Coeffs.Keys) if (seen.Add(k)) vars.Add(k);
        if (vars.Count == 0) return null;
        if (vars.Count > MaxVars) return null;

        var lo = new Dictionary<string, Int128>(StringComparer.Ordinal);
        var hi = new Dictionary<string, Int128>(StringComparer.Ordinal);
        var hasLo = new Dictionary<string, bool>(StringComparer.Ordinal);
        var hasHi = new Dictionary<string, bool>(StringComparer.Ordinal);
        foreach (var v in vars) { hasLo[v] = false; hasHi[v] = false; }

        for (int it = 0; it < 32; it++)
        {
            bool changed = false;
            foreach (var c in cons)
            {
                foreach (var v in vars)
                {
                    if (!c.Coeffs.TryGetValue(v, out var cv) || cv == 0) continue;
                    Int128 rest = 0; bool ok = true;
                    foreach (var kv in c.Coeffs)
                    {
                        if (kv.Key == v || kv.Value == 0) continue;
                        if (kv.Value > 0) { if (!hasLo[kv.Key]) { ok = false; break; } rest = checked(rest + checked(kv.Value * lo[kv.Key])); }
                        else { if (!hasHi[kv.Key]) { ok = false; break; } rest = checked(rest + checked(kv.Value * hi[kv.Key])); }
                    }
                    if (!ok) continue;
                    Int128 r = c.Rhs; if (c.Strict) r = checked(r - 1);      // 整数化: E < r ⇔ E <= r-1
                    Int128 slack = checked(r - rest);
                    if (cv > 0)
                    {
                        var ub = FloorDiv(slack, cv);
                        if (!hasHi[v] || ub < hi[v]) { hi[v] = ub; hasHi[v] = true; changed = true; }
                    }
                    else
                    {
                        var lb = -FloorDiv(slack, -cv);
                        if (!hasLo[v] || lb > lo[v]) { lo[v] = lb; hasLo[v] = true; changed = true; }
                    }
                }
            }
            if (!changed) break;
        }
        foreach (var v in vars)
        {
            if (!hasLo[v] || !hasHi[v]) return null;                      // 无界 ⇒ 放弃 (Unknown)
            if (checked(hi[v] - lo[v] + 1) <= 0) return (lo, hi, vars);   // 空框 ⇒ Unsat (调用方处理)
        }
        return (lo, hi, vars);
    }

    private static Int128 FloorDiv(Int128 a, Int128 b)   // b > 0, 向下取整 (Euclid)
    {
        Int128 q = a / b, r = a % b;
        if (r != 0 && a < 0) q -= 1;
        return q;
    }

    /// <summary>判定约束合取是否可满足。可行时尽量给出精确模型 (给不出则 model=null, 调用方应降级 Unknown)。</summary>
    public static bool Feasible(List<Constraint> input, out Dictionary<string, Int128>? model)
    {
        model = null;
        var cons = new List<Constraint>();
        foreach (var c in input)
        {
            var d = Clean(c);
            if (d.Coeffs.Count == 0)
            {
                if (d.Strict ? d.Rhs <= 0 : d.Rhs < 0) return false;   // 0 < rhs / 0 <= rhs 不成立 ⇒ 不可满足
                continue;
            }
            cons.Add(d);
        }
        var eliminated = Eliminate(cons);
        var m = TryModel(input);
        model = m;
        return eliminated;
    }

    private static Constraint Clean(Constraint c)
    {
        var d = new Dictionary<string, Int128>(StringComparer.Ordinal);
        foreach (var kv in c.Coeffs) if (kv.Value != 0) d[kv.Key] = kv.Value;
        return new Constraint(d, c.Rhs, c.Strict, c.Origin);
    }

    /// <summary>返回 true=可满足, false=不可满足; 超规模抛 Unsupported。</summary>
    private static bool Eliminate(List<Constraint> cons)
    {
        var vars = new HashSet<string>(StringComparer.Ordinal);
        foreach (var c in cons) foreach (var k in c.Coeffs.Keys) vars.Add(k);
        if (vars.Count > MaxVars) throw new Unsupported($"vars>{MaxVars}");
        if (cons.Count > MaxCons) throw new Unsupported($"constraints>{MaxCons}");

        var cur = cons;
        foreach (var v in vars)
        {
            var pos = new List<Constraint>();
            var neg = new List<Constraint>();
            var keep = new List<Constraint>();
            foreach (var c in cur)
            {
                // 关键: 系数为 0 的约束「不含变量 v」⇒ 必须保留(keep), 否则会被当成 neg 参与消元,
                // 令 Combine 的乘子 al=-a2=0 —— 把另一条 strict 约束乘 0 后仍继承 strict 标志, 凭空产出 0<0 假矛盾。
                if (!c.Coeffs.TryGetValue(v, out var a) || a == 0) { keep.Add(c); continue; }
                if (a > 0) pos.Add(c); else neg.Add(c);
            }
            var next = new List<Constraint>(keep);
            foreach (var c1 in pos)
                foreach (var c2 in neg)
                {
                    if (next.Count > MaxCons) throw new Unsupported("blowup");
                    next.Add(Combine(c1, c2, v));
                }
            cur = next;
            foreach (var c in cur)
                if (BaseUnsat(c)) return false;
        }
        foreach (var c in cur)
            if (BaseUnsat(c)) return false;
        return true;
    }

    /// <summary>「基础矛盾」: 所有系数为 0 的约束 (0 ≤ r / 0 < r) 不成立。用「系数全零」而非 Count==0,
    /// 以捕获 Combine 残留的零系数条目。</summary>
    private static bool BaseUnsat(Constraint c)
    {
        foreach (var kv in c.Coeffs) if (kv.Value != 0) return false;
        return c.Strict ? c.Rhs <= 0 : c.Rhs < 0;
    }

    /// <summary>α·c1 + β·c2, 其中 α=-a2&gt;0, β=a1&gt;0 ⇒ 消去 v 且不改变解集 (Fourier–Motzkin 投影)。</summary>
    private static Constraint Combine(Constraint c1, Constraint c2, string v)
    {
        Int128 a1 = c1.Coeffs[v], a2 = c2.Coeffs[v];
        Int128 al = -a2, be = a1;
        // 不变式: 乘子必须严格为正, 否则 c1/c2 中至少一条其实不含 v (系数 0) ⇒ 该对不是合法的 FM 消元对。
        if (al <= 0 || be <= 0) throw new Unsupported($"combine_nonpositive_multiplier({a1},{a2})");
        var d = new Dictionary<string, Int128>(StringComparer.Ordinal);
        foreach (var kv in c1.Coeffs) { if (kv.Key == v) continue; var x = checked(kv.Value * al); if (x != 0) d[kv.Key] = x; }
        foreach (var kv in c2.Coeffs) { if (kv.Key == v) continue; var x = checked(kv.Value * be); if (x == 0) continue; d[kv.Key] = d.TryGetValue(kv.Key, out var p) ? checked(p + x) : x; }
        // 规范化: 累加后归零的系数必须删除, 否则 {y:0} 这类残渣既逃过「空约束 ⇒ 基础矛盾」检查,
        // 又会在后续轮次被当作真实系数参与分配 (即本次 UNSAT 假阳的次要成因)。
        if (d.Count > 0)
        {
            var zeros = new List<string>();
            foreach (var kv in d) if (kv.Value == 0) zeros.Add(kv.Key);
            foreach (var z in zeros) d.Remove(z);
        }
        Int128 rhs = checked(checked(al * c1.Rhs) + checked(be * c2.Rhs));
        return new Constraint(d, rhs, c1.Strict || c2.Strict, $"{c1.Origin} & {c2.Origin}");
    }

    // ── R388 整数完备性补强: 三条来自**真装配 DCR 评测**的弃权缺口 ─────────────────────
    //  (a) 等式系统前提 (x+y==10 ∧ z==x+y): 外框无界 ⇒ Unknown, 而它对「目标是否恒真」是决定性的
    //  (b) 反例域落在取点窗口外 (0<=x, x<=1e6, x>=5e5): 窗口钳制把真解顶掉 ⇒ Unknown, 而它本可给出反例
    //  (c) 整数同余不可行 (3x-3y==1): 有理可行但整数无解 ⇒ Unknown, 而它应判 Unsat
    // 三条修法都**只新增可精确复核的结论**: Sat 一律附逐约束 Int128 复核过的点;
    // Unsat 只来自健全必要条件 (gcd | b) 或既有精确消元 ⇒ 不放松任何既有判据。

    /// <summary>范式下「等式」的唯一来源: 系数向量互为相反数、rhs 互为相反数的两条非严格约束 ⇒ a·x = b。</summary>
    public static List<(Dictionary<string, Int128> Coeffs, Int128 Rhs, string Origin)> DetectEqualities(List<Constraint> input)
    {
        var res = new List<(Dictionary<string, Int128>, Int128, string)>();
        var byKey = new Dictionary<string, List<int>>(StringComparer.Ordinal);
        for (int i = 0; i < input.Count; i++)
        {
            var c = input[i];
            if (c.Strict || c.Coeffs.Count == 0) continue;
            var k = CoeffKey(c.Coeffs, false);
            if (!byKey.TryGetValue(k, out var l)) { l = new List<int>(); byKey[k] = l; }
            l.Add(i);
        }
        for (int i = 0; i < input.Count; i++)
        {
            var c = input[i];
            if (c.Strict || c.Coeffs.Count == 0) continue;
            if (!byKey.TryGetValue(CoeffKey(c.Coeffs, true), out var cands)) continue;
            foreach (var j in cands)
            {
                if (j <= i) continue;                                   // 每个无序对只报一次
                var d = input[j];
                if (d.Strict || d.Rhs != -c.Rhs) continue;
                res.Add((c.Coeffs, c.Rhs, $"{c.Origin} = {d.Origin}"));
                break;
            }
        }
        return res;
    }

    /// <summary>健全必要条件: 等式 a·x = b 有整数解 ⇒ gcd(|a_i|) 整除 b; 逆否即不可行。
    /// 覆盖 3x-3y=1 (g=3∤1)、2x=2y+1 (g=2∤1) 这类「有理可行/整数无解」。</summary>
    public static bool HasGcdInfeasibleEquality(List<Constraint> input)
    {
        foreach (var eq in DetectEqualities(input))
        {
            Int128 g = 0;
            foreach (var kv in eq.Coeffs) g = GcdOf(g, kv.Value);
            if (g != 0 && eq.Rhs % g != 0) return true;
        }
        return false;
    }

    private static Int128 GcdOf(Int128 a, Int128 b)
    {
        if (a < 0) a = -a;
        if (b < 0) b = -b;
        while (b != 0) { var t = a % b; a = b; b = t; }
        return a;
    }

    private static string CoeffKey(Dictionary<string, Int128> c, bool negate)
    {
        var keys = new List<string>(c.Keys);
        keys.Sort(StringComparer.Ordinal);
        var sb = new System.Text.StringBuilder();
        foreach (var k in keys) sb.Append(k).Append('=').Append(negate ? -c[k] : c[k]).Append(';');
        return sb.ToString();
    }

    /// <summary>取点播种 (加宽窗口 + 精确外框角点 + 等式代入点)。所有候选点逐约束 Int128 精确复核,
    /// 因此**只可能把 Unknown 提升为 Sat**, 绝不产生假 Sat。</summary>
    public static bool TrySeededModel(List<Constraint> input, out Dictionary<string, Int128>? model)
    {
        model = null;
        var vars = new List<string>();
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var c in input) foreach (var k in c.Coeffs.Keys) if (seen.Add(k)) vars.Add(k);
        if (vars.Count == 0) { model = new Dictionary<string, Int128>(StringComparer.Ordinal); return true; }

        var cands = new List<Dictionary<string, Int128>>();

        // (b) 加宽窗口: 反例域下界常在 1e5~1e9 量级, 小窗口会被 Math.Min/Max 钳回边界而丢解
        foreach (var w in new[] { 65536.0, 2000000.0, 1000000000.0 })
        {
            var m = TryModelWindow(input, w);
            if (m != null) cands.Add(m);
        }

        // (b') 精确外框三角点: 反例域被下界顶住时, lo 角点往往就是真反例
        var box = ExactBox(input);
        if (box != null)
        {
            var (lo, hi, bvars) = box.Value;
            for (int which = 0; which < 3; which++)
            {
                var m = new Dictionary<string, Int128>(StringComparer.Ordinal);
                foreach (var v in bvars)
                    m[v] = which == 0 ? lo[v] : which == 1 ? hi[v] : checked(lo[v] + (hi[v] - lo[v]) / 2);
                cands.Add(m);
            }
        }

        // (a) 等式代入点: 对每条等式的**每个 |系数|=1 候选主元**都代入一遍 (不做单点启发式挑选), 主元之外按 0/1/-1 策略赋值。
        // 例1 (x+y==10 ∧ z-x-y==0) ⇒ 主元 x/z ⇒ {x:10,y:0,z:10}; 主元必须避开已占用变量, 否则 z 永远解不出来。
        // 例2 (a+b+c+d==20 ∧ a>=0 ∧ a>=5) ⇒ 主元必须含 a 才能取到反例 {a:20,0,0,0} —— 单主元启发式在此**必然失效**
        // (它挑"出现次数最少"的 b, 于是 a 永远停在策略值上, 反例取不到 ⇒ 弃权)。
        var counts = new Dictionary<string, int>(StringComparer.Ordinal);
        foreach (var c in input) foreach (var k in c.Coeffs.Keys) counts[k] = counts.TryGetValue(k, out var n) ? n + 1 : 1;
        var eqs = DetectEqualities(input);
        const int MaxEqCands = 64;
        var eqCands = new List<Dictionary<string, Int128>>();
        foreach (var strat in new[] { (Int128)0, (Int128)1, (Int128)(-1) })
        {
            var m0 = new Dictionary<string, Int128>(StringComparer.Ordinal);
            foreach (var v in vars) m0[v] = strat;
            ExpandEq(0, m0, new HashSet<string>(StringComparer.Ordinal));
        }
        foreach (var m in eqCands) cands.Add(m);

        void ExpandEq(int idx, Dictionary<string, Int128> m, HashSet<string> used)
        {
            if (eqCands.Count >= MaxEqCands) return;
            if (idx >= eqs.Count) { eqCands.Add(new Dictionary<string, Int128>(m, StringComparer.Ordinal)); return; }
            var eq = eqs[idx];
            var picks = new List<KeyValuePair<string, Int128>>();
            foreach (var kv in eq.Coeffs) if (kv.Value == 1 || kv.Value == -1) picks.Add(kv);
            picks.Sort((p, q) =>
            {
                bool pu = used.Contains(p.Key), qu = used.Contains(q.Key);
                if (pu != qu) return pu ? 1 : -1;                              // 未被占用的主元优先
                int pc = counts.TryGetValue(p.Key, out var c1) ? c1 : int.MaxValue;
                int qc = counts.TryGetValue(q.Key, out var c2) ? c2 : int.MaxValue;
                if (pc != qc) return pc.CompareTo(qc);                         // 出现次数少的优先 (更可能解出"自由"变量)
                return string.CompareOrdinal(p.Key, q.Key);
            });
            if (picks.Count == 0) { ExpandEq(idx + 1, m, used); return; }
            foreach (var pk in picks)
            {
                var m2 = new Dictionary<string, Int128>(m, StringComparer.Ordinal);
                Int128 rhs = eq.Rhs;                                           // v = coef * (rhs - Σ_{k≠v} a_k x_k), 其中 coef = ±1
                foreach (var kv in eq.Coeffs) if (kv.Key != pk.Key) rhs = checked(rhs - checked(kv.Value * m2[kv.Key]));
                m2[pk.Key] = checked(pk.Value * rhs);
                var u2 = new HashSet<string>(used, StringComparer.Ordinal) { pk.Key };
                ExpandEq(idx + 1, m2, u2);
                if (eqCands.Count >= MaxEqCands) return;
            }
        }

        foreach (var m in cands)
        {
            bool ok = true;
            foreach (var c in input)
            {
                Int128 lhs = 0;
                foreach (var kv in c.Coeffs) lhs = checked(lhs + checked(kv.Value * m[kv.Key]));
                if (c.Strict ? !(lhs < c.Rhs) : !(lhs <= c.Rhs)) { ok = false; break; }
            }
            if (ok) { model = m; return true; }
        }
        return false;
    }

    /// <summary>候选模型生成 (浮点近似仅用于**取点**, 取到后逐约束 Int128 精确复核; 复核不过 ⇒ 返回 null)。</summary>
    public static Dictionary<string, Int128>? TryModel(List<Constraint> cons) => TryModelWindow(cons, 65536.0);

    /// <summary>同上, 但取点窗口可变: 真解域落在 [−w, w] 之外时, 小窗口会被 Math.Min/Max 钳回边界而丢解
    /// (实测: x ≥ 500000 在 65536 窗口下被钳成 65536 ⇒ 弃权)。放宽窗口只影响**取点**, 不影响复核 ⇒ 安全。</summary>
    public static Dictionary<string, Int128>? TryModelWindow(List<Constraint> cons, double window)
    {
        var vars = new List<string>();
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var c in cons) foreach (var k in c.Coeffs.Keys) if (seen.Add(k)) vars.Add(k);
        if (vars.Count == 0) return new Dictionary<string, Int128>(StringComparer.Ordinal);

        var lo = new Dictionary<string, double>(StringComparer.Ordinal);
        var hi = new Dictionary<string, double>(StringComparer.Ordinal);
        foreach (var v in vars) { lo[v] = -window; hi[v] = window; }

        for (int it = 0; it < 96; it++)
        {
            foreach (var c in cons)
            {
                foreach (var v in vars)
                {
                    if (!c.Coeffs.TryGetValue(v, out var cv) || cv == 0) continue;
                    double rest = (double)c.Rhs;
                    double slack = 0;
                    foreach (var kv in c.Coeffs)
                    {
                        if (kv.Key == v) continue;
                        double k = (double)kv.Value;
                        double b = k > 0 ? (lo.TryGetValue(kv.Key, out var l) ? l : -window) : (hi.TryGetValue(kv.Key, out var h) ? h : window);
                        rest -= k * b;
                        slack += Math.Abs(k) * 1.0;
                    }
                    double bound = (rest + (c.Strict ? -0.5 : 0.0)) / (double)cv;
                    if (cv > 0) { if (bound < hi[v]) hi[v] = Math.Max(bound, lo[v]); }
                    else { if (bound > lo[v]) lo[v] = Math.Min(bound, hi[v]); }
                }
            }
        }

        var cand = new List<Dictionary<string, Int128>>();
        var mid = new Dictionary<string, Int128>(StringComparer.Ordinal);
        var lowp = new Dictionary<string, Int128>(StringComparer.Ordinal);
        var hip = new Dictionary<string, Int128>(StringComparer.Ordinal);
        foreach (var v in vars)
        {
            double m = (lo[v] + hi[v]) / 2.0;
            if (double.IsNaN(m) || double.IsInfinity(m)) m = 0;
            mid[v] = Clamp(m); lowp[v] = Clamp(Math.Ceiling(lo[v])); hip[v] = Clamp(Math.Floor(hi[v]));
        }
        cand.Add(mid); cand.Add(lowp); cand.Add(hip);
        var zero = new Dictionary<string, Int128>(StringComparer.Ordinal);
        foreach (var v in vars) zero[v] = 0;
        cand.Add(zero);
        var one = new Dictionary<string, Int128>(StringComparer.Ordinal);
        foreach (var v in vars) one[v] = 1;
        cand.Add(one);
        var negOne = new Dictionary<string, Int128>(StringComparer.Ordinal);
        foreach (var v in vars) negOne[v] = -1;
        cand.Add(negOne);

        foreach (var m in cand)
        {
            bool ok = true;
            foreach (var c in cons)
            {
                Int128 lhs = 0;
                foreach (var kv in c.Coeffs) lhs = checked(lhs + checked(kv.Value * m[kv.Key]));
                if (c.Strict ? !(lhs < c.Rhs) : !(lhs <= c.Rhs)) { ok = false; break; }
            }
            if (ok) return m;
        }
        return null;
    }

    private static Int128 Clamp(double d)
    {
        if (double.IsNaN(d) || double.IsInfinity(d)) return 0;
        if (d > 1e15) return Int128.Parse("1000000000000000");
        if (d < -1e15) return Int128.Parse("-1000000000000000");
        return (Int128)Math.Round(d);
    }
}
