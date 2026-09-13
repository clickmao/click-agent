using System.Collections.Generic;
using System.Numerics;
using System.Text;

namespace clickrover.formal;

/// <summary>线性表达式: sum(coeff_i * var_i) + const。系数用 Int128 精确整数 (无浮点 ⇒ 判定零误差)。</summary>
public sealed class LinTerm
{
    public readonly Dictionary<string, Int128> Coeffs = new(System.StringComparer.Ordinal);
    public Int128 Const;

    public static LinTerm Const0(Int128 c) { var t = new LinTerm(); t.Const = c; return t; }
    public static LinTerm Var(string n) { var t = new LinTerm(); t.Coeffs[n] = Int128.One; return t; }

    public LinTerm Clone()
    {
        var t = new LinTerm { Const = Const };
        foreach (var kv in Coeffs) t.Coeffs[kv.Key] = kv.Value;
        return t;
    }

    public LinTerm Add(LinTerm o)
    {
        var t = Clone();
        t.Const += o.Const;
        foreach (var kv in o.Coeffs) t.Coeffs[kv.Key] = t.Coeffs.TryGetValue(kv.Key, out var v) ? v + kv.Value : kv.Value;
        return t;
    }

    public LinTerm Neg() { var t = Clone(); t.Const = -t.Const; foreach (var k in new List<string>(t.Coeffs.Keys)) t.Coeffs[k] = -t.Coeffs[k]; return t; }
    public LinTerm Sub(LinTerm o) => Add(o.Neg());
    public LinTerm Scale(Int128 k) { var t = Clone(); t.Const *= k; foreach (var key in new List<string>(t.Coeffs.Keys)) { var v = t.Coeffs[key] * k; if (v == 0) t.Coeffs.Remove(key); else t.Coeffs[key] = v; } return t; }
    public bool IsConst => Coeffs.Count == 0;

    public override string ToString()
    {
        var sb = new StringBuilder();
        bool first = true;
        foreach (var kv in Coeffs)
        {
            if (!first) sb.Append(" + ");
            sb.Append(kv.Value).Append('*').Append(kv.Key);
            first = false;
        }
        if (Const != 0 || first) { if (!first) sb.Append(Const >= 0 ? " + " : " - "); sb.Append(Const >= 0 || first ? Const : -Const); }
        return sb.ToString();
    }
}

/// <summary>约束: sum(coeff_i*var_i) &lt;= rhs (strict ⇒ &lt;)。全部经此范式, 便于 Fourier–Motzkin 消元。</summary>
public readonly struct Constraint
{
    public readonly Dictionary<string, Int128> Coeffs;
    public readonly Int128 Rhs;
    public readonly bool Strict;
    public readonly string Origin;

    public Constraint(Dictionary<string, Int128> coeffs, Int128 rhs, bool strict, string origin)
    { Coeffs = coeffs; Rhs = rhs; Strict = strict; Origin = origin; }

    /// <summary>由 E &gt;= 0 (strict ⇒ E &gt; 0) 转成 E' &lt;= c 形式。</summary>
    public static Constraint FromNonNeg(LinTerm e, bool strict, string origin)
    {
        var d = new Dictionary<string, Int128>(System.StringComparer.Ordinal);
        foreach (var kv in e.Coeffs) if (kv.Value != 0) d[kv.Key] = -kv.Value;
        return new Constraint(d, e.Const, strict, origin);
    }

    public override string ToString() => $"{LinTermOf()}{(Strict ? " < " : " <= ")}{Rhs}  [{Origin}]";

    private string LinTermOf()
    {
        var t = new LinTerm();
        foreach (var kv in Coeffs) t.Coeffs[kv.Key] = kv.Value;
        return Coeffs.Count == 0 ? "0" : t.ToString();
    }
}
