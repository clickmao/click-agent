using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Numerics;
using System.Text;

namespace agent.rover.formal;

public enum Verdict { Proved, Refuted, Vacuous, Unknown, Malformed }

/// <summary>形式化验证内核: 对「前提 ⇒ 目标」在可判定片段内做**本地零 token 裁决**。
/// 输入是 agent 返回的符号附图 (premise/goal 行), 输出是机器可判的裁决 + 证据。
/// 诚实边界: 只覆盖线性整数算术 + 命题逻辑; 片段外一律 Unknown (绝不放行成"已证明")。</summary>
public static class FormalKernel
{
    public const string Engine = "rover-fm-v1";

    public sealed class Result
    {
        public Verdict Verdict;
        public List<string> Premises = new();
        public string Goal = "";
        public int Vars;
        public int Cases;
        public Dictionary<string, Int128>? Counterexample;
        public string Note = "";
        public double Ms;
        public int ExitCode => Verdict switch { Verdict.Proved => 0, Verdict.Refuted => 1, Verdict.Vacuous => 2, Verdict.Unknown => 3, _ => 4 };
    }

    public sealed class ParseError : Exception { public ParseError(string m) : base(m) { } }

    public static List<(string Name, F Formula)> ParsePremises(string text)
    {
        var list = new List<(string, F)>();
        int n = 0;
        foreach (var raw in text.Split('\n'))
        {
            var line = raw.Trim();
            if (line.Length == 0 || line.StartsWith("#") || line.StartsWith("//")) continue;
            if (line.StartsWith("goal")) continue;   // 目标行由 ParseGoal 处理
            if (line.StartsWith("premise ") || line.StartsWith("let "))
            {
                var body = line.StartsWith("premise ") ? line.Substring(8).Trim() : line.Substring(4).Trim();
                string name = $"p{++n}";
                int colon = body.IndexOf(':');
                if (colon > 0 && !body.Substring(0, colon).Contains(' ') && !body.Substring(0, colon).Contains('<') && !body.Substring(0, colon).Contains('>') && !body.Substring(0, colon).Contains('='))
                { name = body.Substring(0, colon).Trim(); body = body.Substring(colon + 1).Trim(); }
                list.Add((name, FormalParser.Parse(body)));
            }
            else throw new ParseError($"unknown_directive: {line}");
        }
        return list;
    }

    public static (string Raw, F Formula) ParseGoal(string text)
    {
        foreach (var raw in text.Split('\n'))
        {
            var line = raw.Trim();
            if (line.StartsWith("goal ") || line.StartsWith("goal:"))
            {
                var body = line.StartsWith("goal:") ? line.Substring(5).Trim() : line.Substring(5).Trim();
                return (body, FormalParser.Parse(body));
            }
        }
        throw new ParseError("missing_goal");
    }

    /// <summary>核心裁决。premisesAndGoal: 前提公式列表 + 目标公式。</summary>
    public static Result Check(List<F> premises, F goal)
    {
        var sw = Stopwatch.StartNew();
        var r = new Result { Goal = goal.ToString() ?? string.Empty };
        var vars = new HashSet<string>(StringComparer.Ordinal);
        foreach (var p in premises) FormalParser.CollectVars(p, vars);
        FormalParser.CollectVars(goal, vars);
        r.Vars = vars.Count;

        try
        {
            // ① 前提自洽性: 前提不可满足 ⇒ 空前提 ⇒ Vacuous (任何结论都"成立"但无意义)
            var pre = new F.And(); pre.Items.AddRange(premises);
            var preDnf = FormalParser.ToDnf(pre);
            if (preDnf == null) { r.Verdict = Verdict.Unknown; r.Note = "premise_dnf_cap"; return Finish(r, sw); }
            r.Cases = preDnf.Count;
            bool preSat = false, preUnknown = false;
            foreach (var c in preDnf)
            {
                var s = FourierMotzkin.Satisfiable(c, out _);
                if (s == FourierMotzkin.Sat.Sat) { preSat = true; break; }
                if (s == FourierMotzkin.Sat.Unknown) preUnknown = true;
            }
            if (!preSat && preUnknown) { r.Verdict = Verdict.Unknown; r.Note = "premise_decision_unknown"; return Finish(r, sw); }
            if (!preSat) { r.Verdict = Verdict.Vacuous; r.Note = "premises_unsat_over_integers"; return Finish(r, sw); }

            // ② 反驳搜索: 前提 ∧ ¬目标 可满足 ⇒ 目标不成立 (附精确复核过的反例)
            var neg = new F.And(); neg.Items.AddRange(premises); neg.Items.Add(FormalParser.Negate(goal));
            var negDnf = FormalParser.ToDnf(neg);
            if (negDnf == null) { r.Verdict = Verdict.Unknown; r.Note = "refute_dnf_cap"; return Finish(r, sw); }
            bool negUnknown = false;
            foreach (var c in negDnf)
            {
                var s = FourierMotzkin.Satisfiable(c, out var model);
                if (s == FourierMotzkin.Sat.Sat)
                {
                    r.Verdict = Verdict.Refuted; r.Counterexample = model!; r.Note = "exact_model_verified";
                    return Finish(r, sw);
                }
                if (s == FourierMotzkin.Sat.Unknown) negUnknown = true;
            }

            // ③ 前提 ∧ ¬目标 不可满足 ⇒ Proved (精确消元/整数补全, 非启发式)
            if (negUnknown) { r.Verdict = Verdict.Unknown; r.Note = "refute_decision_unknown"; return Finish(r, sw); }
            r.Verdict = Verdict.Proved; r.Note = "premises_and_not_goal_unsat";
            return Finish(r, sw);
        }
        catch (FourierMotzkin.Unsupported u) { r.Verdict = Verdict.Unknown; r.Note = "fragment_limit:" + u.Message; return Finish(r, sw); }
        catch (OverflowException) { r.Verdict = Verdict.Unknown; r.Note = "int128_overflow"; return Finish(r, sw); }
    }

    private static Result Finish(Result r, Stopwatch sw) { sw.Stop(); r.Ms = sw.Elapsed.TotalMilliseconds; return r; }

    public static string Json(Result r)
    {
        var sb = new StringBuilder();
        sb.Append('{');
        sb.Append("\"engine\":\"").Append(Engine).Append("\",");
        sb.Append("\"verdict\":\"").Append(r.Verdict.ToString()).Append("\",");
        sb.Append("\"exit_code\":").Append(r.ExitCode).Append(',');
        sb.Append("\"vars\":").Append(r.Vars).Append(',');
        sb.Append("\"cases\":").Append(r.Cases).Append(',');
        sb.Append("\"goal\":").Append(Esc(r.Goal)).Append(',');
        sb.Append("\"note\":").Append(Esc(r.Note)).Append(',');
        sb.Append("\"ms\":").Append(r.Ms.ToString("F3")).Append(',');
        sb.Append("\"tokens\":0,");
        sb.Append("\"counterexample\":");
        if (r.Counterexample == null) sb.Append("null");
        else
        {
            sb.Append('{');
            bool first = true;
            foreach (var kv in r.Counterexample) { if (!first) sb.Append(','); sb.Append(Esc(kv.Key)).Append(':').Append(kv.Value); first = false; }
            sb.Append('}');
        }
        sb.Append('}');
        return sb.ToString();
    }

    private static string Esc(string s) => "\"" + s.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";

    /// <summary>
    /// 解析失败分类 (v0.23.0 exp12 S2 修正): **片段外 ⇒ Unknown(诚实弃权)**, 真正的语法错 ⇒ Malformed。
    /// 二者绝不可混算 —— 否则"本语言不可判定"被记成"畸形/违规", DCR 口径被自身片段限制污染
    /// (实测曾把 `x * x == 4` 判成 Malformed)。
    /// </summary>
    private static Result FromParseFailure(string note)
    {
        var outOfFragment = note.StartsWith("expr_nonlinear", StringComparison.Ordinal)
                            || note.Contains("不在可判定片段内", StringComparison.Ordinal);
        return new Result
        {
            Verdict = outOfFragment ? Verdict.Unknown : Verdict.Malformed,
            Note = outOfFragment ? "fragment_limit:" + note : note,
        };
    }

    /// <summary>从「断言文件全文」一路到裁决 (premise/goal 行)。</summary>
    public static Result CheckText(string text)
    {
        try
        {
            var pre = ParsePremises(text);
            var (_, goal) = ParseGoal(text);
            var fs = new List<F>();
            foreach (var p in pre) fs.Add(p.Formula);
            return Check(fs, goal);
        }
        catch (ParseError e) { return FromParseFailure(e.Message); }
        catch (FormatException e) { return FromParseFailure(e.Message); }
    }
}
