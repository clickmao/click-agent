using System;
using System.Collections.Generic;
using System.Globalization;
using System.Numerics;

namespace agent.rover.formal;

public static class FormalParser
{
    private enum Tk { Num, Ident, Plus, Minus, Star, Le, Lt, Ge, Gt, Eq, Ne, LP, RP, And, Or, Not, End }

    private readonly struct Tok
    {
        public readonly Tk K; public readonly string S; public readonly Int128 N;
        public Tok(Tk k, string s, Int128 n) { K = k; S = s; N = n; }
    }

    public static F Parse(string expr)
    {
        var toks = Lex(expr);
        int i = 0;
        var f = ParseOr(toks, ref i);
        if (toks[i].K != Tk.End) throw new FormatException($"expr_unexpected_token: {toks[i].K} '{toks[i].S}'");
        return f;
    }

    private static List<Tok> Lex(string s)
    {
        var ts = new List<Tok>();
        int i = 0;
        while (i < s.Length)
        {
            char c = s[i];
            if (char.IsWhiteSpace(c)) { i++; continue; }
            if (char.IsDigit(c))
            {
                int j = i; while (j < s.Length && char.IsDigit(s[j])) j++;
                ts.Add(new Tok(Tk.Num, s.Substring(i, j - i), Int128.Parse(s.Substring(i, j - i), CultureInfo.InvariantCulture)));
                i = j; continue;
            }
            if (char.IsLetter(c) || c == '_')
            {
                int j = i; while (j < s.Length && (char.IsLetterOrDigit(s[j]) || s[j] == '_' || s[j] == '.')) j++;
                string w = s.Substring(i, j - i);
                ts.Add(w switch { "and" => new Tok(Tk.And, w, 0), "or" => new Tok(Tk.Or, w, 0), "not" => new Tok(Tk.Not, w, 0), _ => new Tok(Tk.Ident, w, 0) });
                i = j; continue;
            }
            if (i + 1 < s.Length)
            {
                string two = s.Substring(i, 2);
                Tk? k2 = two switch { "<=" => Tk.Le, ">=" => Tk.Ge, "==" => Tk.Eq, "!=" => Tk.Ne, "&&" => Tk.And, "||" => Tk.Or, _ => null };
                if (k2.HasValue) { ts.Add(new Tok(k2.Value, two, 0)); i += 2; continue; }
            }
            Tk k = c switch { '+' => Tk.Plus, '-' => Tk.Minus, '*' => Tk.Star, '<' => Tk.Lt, '>' => Tk.Gt, '(' => Tk.LP, ')' => Tk.RP, '!' => Tk.Not, _ => throw new FormatException($"expr_bad_char: '{c}' @{i}") };
            ts.Add(new Tok(k, c.ToString(), 0)); i++;
        }
        ts.Add(new Tok(Tk.End, "<eof>", 0));
        return ts;
    }

    private static F ParseOr(List<Tok> t, ref int i)
    {
        var first = ParseAnd(t, ref i);
        if (t[i].K != Tk.Or) return first;
        var o = new F.Or(); o.Items.Add(first);
        while (t[i].K == Tk.Or) { i++; o.Items.Add(ParseAnd(t, ref i)); }
        return o;
    }

    private static F ParseAnd(List<Tok> t, ref int i)
    {
        var first = ParseUnary(t, ref i);
        if (t[i].K != Tk.And) return first;
        var a = new F.And(); a.Items.Add(first);
        while (t[i].K == Tk.And) { i++; a.Items.Add(ParseUnary(t, ref i)); }
        return a;
    }

    private static F ParseUnary(List<Tok> t, ref int i)
    {
        if (t[i].K == Tk.Not) { i++; return Negate(ParseUnary(t, ref i)); }
        if (t[i].K == Tk.LP)
        {
            i++;
            var inner = ParseOr(t, ref i);
            if (t[i].K != Tk.RP) throw new FormatException("expr_missing_rparen");
            i++;
            return inner;
        }
        return ParseCmp(t, ref i);
    }

    private static F ParseCmp(List<Tok> t, ref int i)
    {
        var l = ParseLin(t, ref i);
        var op = t[i].K;
        if (op is not (Tk.Le or Tk.Lt or Tk.Ge or Tk.Gt or Tk.Eq or Tk.Ne))
            throw new FormatException($"expr_expected_comparison: got {op} '{t[i].S}'");
        i++;
        var r = ParseLin(t, ref i);
        var d = l.Sub(r); // 比较两侧归零: d op 0
        string origin = $"{l} {OpName(op)} {r}";
        return op switch
        {
            Tk.Le => new F.Atom(Constraint.FromNonNeg(d.Neg(), false, origin)),                          // d <= 0  ⇒ -d >= 0
            Tk.Lt => new F.Atom(Constraint.FromNonNeg(d.Neg(), true, origin)),                           // d < 0   ⇒ -d > 0
            Tk.Ge => new F.Atom(Constraint.FromNonNeg(d, false, origin)),                                // d >= 0
            Tk.Gt => new F.Atom(Constraint.FromNonNeg(d, true, origin)),                                 // d > 0
            Tk.Eq => And(new F.Atom(Constraint.FromNonNeg(d, false, origin)), new F.Atom(Constraint.FromNonNeg(d.Neg(), false, origin))),
            _ => Or(new F.Atom(Constraint.FromNonNeg(d, true, origin + " (>)")), new F.Atom(Constraint.FromNonNeg(d.Neg(), true, origin + " (<)"))),
        };
    }

    private static string OpName(Tk k) => k switch { Tk.Le => "<=", Tk.Lt => "<", Tk.Ge => ">=", Tk.Gt => ">", Tk.Eq => "==", _ => "!=" };

    private static F And(F a, F b) { var x = new F.And(); if (a is F.And aa) x.Items.AddRange(aa.Items); else x.Items.Add(a); if (b is F.And bb) x.Items.AddRange(bb.Items); else x.Items.Add(b); return x; }

    private static F Or(F a, F b) { var x = new F.Or(); if (a is F.Or ao) x.Items.AddRange(ao.Items); else x.Items.Add(a); if (b is F.Or bo) x.Items.AddRange(bo.Items); else x.Items.Add(b); return x; }

    private static LinTerm ParseLin(List<Tok> t, ref int i)
    {
        var acc = ParseTerm(t, ref i);
        while (t[i].K is Tk.Plus or Tk.Minus)
        {
            bool plus = t[i].K == Tk.Plus; i++;
            var rhs = ParseTerm(t, ref i);
            acc = plus ? acc.Add(rhs) : acc.Sub(rhs);
        }
        return acc;
    }

    private static LinTerm ParseTerm(List<Tok> t, ref int i)
    {
        var acc = ParseFactor(t, ref i);
        while (t[i].K == Tk.Star)
        {
            i++;
            var rhs = ParseFactor(t, ref i);
            if (acc.IsConst) acc = rhs.Scale(acc.Const);
            else if (rhs.IsConst) acc = acc.Scale(rhs.Const);
            else throw new FormatException("expr_nonlinear: 变量*变量 不在可判定片段内");
        }
        return acc;
    }

    private static LinTerm ParseFactor(List<Tok> t, ref int i)
    {
        if (t[i].K == Tk.Minus) { i++; return ParseFactor(t, ref i).Neg(); }
        if (t[i].K == Tk.Plus) { i++; return ParseFactor(t, ref i); }
        if (t[i].K == Tk.Num) { var n = t[i].N; i++; return LinTerm.Const0(n); }
        if (t[i].K == Tk.Ident) { var s = t[i].S; i++; return LinTerm.Var(s); }
        throw new FormatException($"expr_expected_operand: got {t[i].K} '{t[i].S}'");
    }

    /// <summary>否定下推 (NNF): 否定只落在比较上, 且 != / == 的否定在布尔层展开, 保证原子皆无析取。</summary>
    public static F Negate(F f) => f switch
    {
        F.True => new F.False(),
        F.False => new F.True(),
        F.Atom a => a.C.Strict
            ? new F.Atom(new Constraint(Flip(a.C.Coeffs), -a.C.Rhs, false, "!¬" + a.C.Origin))
            : new F.Atom(new Constraint(Flip(a.C.Coeffs), -a.C.Rhs, true, "!" + a.C.Origin)),
        F.And a => OrItems(a.Items),
        F.Or o => AndItems(o.Items),
        _ => throw new FormatException("negate_unsupported"),
    };

    private static Dictionary<string, Int128> Flip(Dictionary<string, Int128> c)
    {
        var d = new Dictionary<string, Int128>(StringComparer.Ordinal);
        foreach (var kv in c) if (kv.Value != 0) d[kv.Key] = -kv.Value;
        return d;
    }

    private static F OrItems(List<F> items) { var x = new F.Or(); foreach (var it in items) x.Items.Add(Negate(it)); return x; }
    private static F AndItems(List<F> items) { var x = new F.And(); foreach (var it in items) x.Items.Add(Negate(it)); return x; }

    /// <summary>把公式展成 DNF 案例集 (每个案例 = 约束合取)。超上限则返回 null (⇒ Unknown, 不做猜测)。</summary>
    public static List<List<Constraint>>? ToDnf(F f, int cap = 4096)
    {
        switch (f)
        {
            case F.True: return new List<List<Constraint>> { new() };
            case F.False: return new List<List<Constraint>>();
            case F.Atom a: return new List<List<Constraint>> { new() { a.C } };
            case F.Or o:
                {
                    var outp = new List<List<Constraint>>();
                    foreach (var it in o.Items)
                    {
                        var sub = ToDnf(it, cap);
                        if (sub == null) return null;
                        outp.AddRange(sub);
                        if (outp.Count > cap) return null;
                    }
                    return outp;
                }
            case F.And a:
                {
                    var acc = new List<List<Constraint>> { new() };
                    foreach (var it in a.Items)
                    {
                        var sub = ToDnf(it, cap);
                        if (sub == null) return null;
                        var next = new List<List<Constraint>>();
                        foreach (var c1 in acc)
                            foreach (var c2 in sub)
                            {
                                var merged = new List<Constraint>(c1); merged.AddRange(c2);
                                next.Add(merged);
                                if (next.Count > cap) return null;
                            }
                        acc = next;
                    }
                    return acc;
                }
            default: return null;
        }
    }

    public static void CollectVars(F f, HashSet<string> into)
    {
        switch (f)
        {
            case F.Atom a: foreach (var k in a.C.Coeffs.Keys) into.Add(k); break;
            case F.And a: foreach (var i in a.Items) CollectVars(i, into); break;
            case F.Or o: foreach (var i in o.Items) CollectVars(i, into); break;
        }
    }
}
