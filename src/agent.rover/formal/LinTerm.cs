using System.Collections.Generic;
using System.Numerics;
using System.Text;

namespace agent.rover.formal;

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
