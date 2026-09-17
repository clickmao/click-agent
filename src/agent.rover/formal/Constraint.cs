using System.Collections.Generic;
using System.Numerics;
using System.Text;

namespace agent.rover.formal;


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
