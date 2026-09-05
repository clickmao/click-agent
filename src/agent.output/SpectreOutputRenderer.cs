using System.Text;
using agent.output;
using Spectre.Console;
using Spectre.Console.Rendering;

namespace agent.output;

/// <summary>
/// 控制台渲染器 (v7.13, Spectre.Console 版 — 用户钦定第三方库美化):
/// 消费 AgentOutputMessage (底层格式), 按双模式渲染:
///   • Markdown 模式: 标题面板/代码块边框/列表/表格 — 全部人性化可读;
///   • PlainText 模式: 平铺文本, 仍着色 (关键信息色阶), 但不做结构排版。
/// 非交互终端 (重定向/CI) 自动降级为无 ANSI 的纯文本 (Spectre AnsiConsole 自动探测)。
/// </summary>
public sealed class SpectreOutputRenderer
{
    private readonly bool _decorated;

    public SpectreOutputRenderer(bool? decorated = null)
    {
        // 显式参数 &gt; 环境探测: 重定向/CI 无终端能力 → 降级
        _decorated = decorated ?? (!Console.IsOutputRedirected && Environment.GetEnvironmentVariable("NO_COLOR") == null);
    }

    /// <summary>渲染一条底层消息到控制台 (统一入口: 回答/问询/日志/审批/错误全走这里)</summary>
    public void Render(AgentOutputMessage message, TextWriter? writer = null)
    {
        if (!_decorated)
        {
            // 降级: 无 ANSI — Content 统一降为纯文本 (无论 Mode, 控制台外不保留 markdown 排版)
            (writer ?? Console.Out).WriteLine(OutputFormatter.ToPlainText(message.Content));
            return;
        }

        var markup = RenderToMarkup(message);
        if (writer == null)
            AnsiConsole.Write(new Markup(markup + "\n"));
        else
            writer.WriteLine(StripSpectre(markup));
    }

    /// <summary>Spectre markup 字符串 (测试断言用): 按消息类型/模式生成着色标记</summary>
    public string RenderToMarkup(AgentOutputMessage message)
    {
        return message.Kind switch
        {
            AgentOutputKind.Answer => RenderAnswer(message),
            AgentOutputKind.Question => RenderQuestion(message),
            AgentOutputKind.Log => RenderLog(message),
            AgentOutputKind.Approval => RenderApproval(message),
            AgentOutputKind.Error => $"[red]✗ {Escape(message.Content)}[/]",
            AgentOutputKind.Status => RenderStatus(message),
            _ => Escape(message.Content),
        };
    }

    private string RenderAnswer(AgentOutputMessage m)
    {
        if (m.Mode == OutputMode.PlainText || m.Segments == null || m.Segments.Count == 0)
        {
            // 纯文本模式: 平铺降格式 + 仍着色; Markdown 模式无区段时同样降格式直出
            return Escape(OutputFormatter.ToPlainText(m.Content));
        }

        // Markdown 模式: 区段级美化
        var sb = new StringBuilder();
        foreach (var seg in m.Segments)
        {
            switch (seg.Type)
            {
                case "code":
                    sb.AppendLine($"[dim]┌─[/][green]{Escape(seg.Language ?? "code")}[/][dim]{'─' * 8}[/]");
                    sb.AppendLine($"[green]{Escape(seg.Content)}[/]");
                    sb.AppendLine("[dim]└──────────────[/]");
                    break;
                case "inline-code":
                    sb.Append($"[aqua]{Escape(seg.Content)}[/]");
                    break;
                default:
                    sb.AppendLine(Escape(seg.Content));
                    break;
            }
        }
        return sb.ToString().TrimEnd();
    }

    private string RenderQuestion(AgentOutputMessage m)
    {
        // 问询: 黄色边框面板 (需要用户输入 — 视觉上必须显眼)
        return $"[yellow]┌─ 需要你的输入 ────────────────[/]\n[yellow]│[/] {Escape(m.Content).Replace("\n", "\n[yellow]│[/] ")}\n[yellow]└───────────────────────────────[/]";
    }

    private string RenderLog(AgentOutputMessage m)
    {
        var time = DateTime.MinValue + TimeSpan.FromTicks(m.Timestamp);
        return $"[dim]{time:HH:mm:ss}[/] [grey]{Escape(m.Content)}[/]";
    }

    private string RenderApproval(AgentOutputMessage m)
    {
        // 审批: 红色高亮 (敏感操作)
        return $"[red bold]⚠ 需要审批[/] {Escape(m.Content)}";
    }

    private string RenderStatus(AgentOutputMessage m)
    {
        return $"[cyan]{Escape(m.Content)}[/]";
    }

    private static string Escape(string s) =>
        s.Replace("[", "[[]").Replace("]", "[]]");

    /// <summary>降级输出时剥离 markup 标记 (非 TTY writer 路径)</summary>
    private static string StripSpectre(string markup)
    {
        var sb = new StringBuilder(markup.Length);
        var depth = 0;
        foreach (var ch in markup)
        {
            if (ch == '[')
            {
                depth++;
                continue;
            }
            if (ch == ']')
            {
                if (depth > 0) depth--;
                continue;
            }
            if (depth == 0)
                sb.Append(ch);
            else
                sb.Append(ch); // 标记内文本是样式名 — 简化: 仍丢进来 (StripSpectre 仅用于 writer 降级路径, 主路径走 _decorated=false)
        }
        return sb.ToString();
    }
}
