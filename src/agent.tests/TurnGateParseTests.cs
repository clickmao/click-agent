using agent.modelqueue;
using Xunit;
namespace agent.tests;

/// <summary>
/// R449 — 门判解析器 (TurnGateJudge.Parse) 跨语言同位夹具.
/// 与 eval/rover/r449/real_gate_probe.py `--selftest` 的 13 条用例**逐条同形** (同一批输入, 两侧必须同判).
/// 说明: 真实生成文本可以不含思考区开头 (模板把思考开在助手头部) ⇒ "[t2]" 类用例即此形态.
/// </summary>
public class TurnGateParseTests
{
    // 尖括号字面量一律按码点构造 (R413 铁律: 源码里的 < > 会被静默替换)
    static readonly string TO = ((char)60) + "think" + ((char)62);
    static readonly string TC = ((char)60) + "/think" + ((char)62);

    static (string? Letter, string? Reason) Run(string raw)
    {
        var o = TurnGateJudge.Parse(raw);
        return (o.Decided ? o.Verdict.ToString()! : null, o.Decided ? "ok" : (o.Error ?? "empty"));
    }

    static void Case(string name, string raw, string? letter, string reason)
    {
        var (l, r) = Run(raw);
        Assert.True(l == letter && r == reason, $"{name}: 实际 letter={l} reason={r}, 期望 letter={letter} reason={reason}");
    }

    [Fact]
    public void Empty()
    {
        Case("empty", "", null, "empty");
        Case("blank", "   \n ", null, "empty");
    }

    [Fact]
    public void ThinkingTruncated()
        => Case("truncated", TO + "用户说好", null, "thinking_truncated");

    [Fact]
    public void LetterAfterThinkBlock()
    {
        Case("skip", TO + "分析" + TC + "\nS", "Skip", "ok");
        Case("pass", TO + "分析" + TC + "\nP", "Pass", "ok");
    }

    [Fact]
    public void WordMarkers()
    {
        // 词表移除后 (2026-09-19): 本地裁决只认**字母标记** (S/P/A/C/N) — 中文词标记不再本地裁决,
        // 一律 no_marker ⇒ 交 LLM (本地不做词面猜测)。旧期望 (词面 ⇒ Skip/Pass) 来自已删词表。
        Case("word_ack", TO + "分析" + TC + "\n纯认可", null, "no_marker");
        Case("word_new", TO + "分析" + TC + "\n有新增诉求", null, "no_marker");
    }

    [Fact]
    public void LastPositionWins()
    {
        Case("last_wins_b", TO + "分析" + TC + "\nS 然后 P", "Pass", "ok");
        Case("last_wins_a", TO + "分析" + TC + "\nP 然后 S", "Skip", "ok");
    }

    [Fact]
    public void TailWindowWithoutThinkBlock()
    {
        Case("tail64_no_think", "纯认可", null, "no_marker");   // 词表已删: 无字母标记 ⇒ 不本地裁决
        Case("empty_conclusion", TO + "分析" + TC, null, "empty_conclusion");
        Case("no_marker", TO + "分析" + TC + "\n没有标记", null, "no_marker");
    }

    [Fact]
    public void AstralCharKeepsLetter()
    {
        // emoji 为代理对: 结论区取窗必须按 UTF-16 码元 (与 .NET 索引口径一致)
        Case("astral", TO + "分析" + TC + "\n\U0001F600S", "Skip", "ok");
    }
}
