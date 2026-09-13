using System.Text;

namespace agent.rover.token;

/// <summary>对话消息 (R400 支持子集: system / user / assistant-纯文本)。</summary>
public sealed record ChatMessage(string Role, string Content);

/// <summary>
/// DeepSeek chat template 渲染器 (支持子集), 与 GGUF 内嵌模板 + jinja2 渲染结果逐字节对齐。
/// 权威依据: eval/rover/tokref/chat_template.jinja (sha256 登记于 tables/meta.json) 与 eval/rover/tokref/chat_golden.jsonl。
/// 不支持的分支 (tool_calls / tool 角色) 一律显式抛 NotSupportedException —— 不静默降级 (R400 计划 §3 排除项)。
/// </summary>
public static class ChatTemplate
{
    public const string Bos = "<｜begin▁of▁sentence｜>";

    public const string Eos = "<｜end▁of▁sentence｜>";

    public const string UserTag = "<｜User｜>";

    public const string AssistantTag = "<｜Assistant｜>";

    public const string ToolOutputsEnd = "<｜tool▁outputs▁end｜>";

    private const string SystemSeparator = "\n\n";

    /// <summary>golden 夹具条数 (eval/rover/tokref/chat_golden.jsonl)。</summary>
    public const int GoldenCount = 12;

    /// <summary>
    /// 渲染对话为 prompt 字符串。
    /// 规则 (与模板逐条对应):
    ///   ① 全部 system 消息以 "\n\n" 连接后紧跟 bos;
    ///   ② user → "<｜User｜>{内容}<｜Assistant｜>" 且 is_last_user=true;
    ///   ③ assistant(纯文本) → "{内容}<｜end▁of▁sentence｜>" 且 is_last_user=false;
    ///   ④ addGenerationPrompt 时, 末尾未以 user 结束时补 "<｜Assistant｜>"。
    /// </summary>
    public static string Render(IReadOnlyList<ChatMessage> messages, bool addGenerationPrompt)
    {
        StringBuilder sys = new();
        bool first = true;
        foreach (ChatMessage m in messages)
        {
            if (m.Role != "system")
            {
                continue;
            }

            if (!first)
            {
                sys.Append(SystemSeparator);
            }

            sys.Append(m.Content);
            first = false;
        }

        StringBuilder sb = new();
        sb.Append(Bos).Append(sys);
        bool isLastUser = false;
        foreach (ChatMessage m in messages)
        {
            switch (m.Role)
            {
                case "system":
                    break;
                case "user":
                    sb.Append(UserTag).Append(m.Content).Append(AssistantTag);
                    isLastUser = true;
                    break;
                case "assistant":
                    sb.Append(m.Content).Append(Eos);
                    isLastUser = false;
                    break;
                case "tool":
                    throw new NotSupportedException("chat_template: role=tool 分支未实现 (R400 排除项, 见计划 §3)");
                default:
                    throw new NotSupportedException($"chat_template: 未知 role={m.Role}");
            }
        }

        if (addGenerationPrompt && !isLastUser)
        {
            sb.Append(AssistantTag);
        }

        return sb.ToString();
    }

    /// <summary>
    /// 模板驱动渲染 (R406): 用 GGUF 内嵌 `tokenizer.chat_template` **原文**渲染, 不写死任何模型。
    /// messages 映射为 jinja 的 [{'role','content'}] 列表; 未提供的字段 (tool_calls/reasoning_content)
    /// 在模板内表现为宽松 Undefined (假值) —— 与「无工具调用」语义一致。
    /// </summary>
    public static string RenderFromTemplate(string template, IReadOnlyList<ChatMessage> messages, bool addGenerationPrompt, string bosToken, JinjaOptions? options = null)
    {
        ArgumentNullException.ThrowIfNull(template);
        ArgumentNullException.ThrowIfNull(messages);
        List<JinjaValue> list = new(messages.Count);
        foreach (ChatMessage m in messages)
        {
            Dictionary<string, JinjaValue> item = new(StringComparer.Ordinal)
            {
                ["role"] = JinjaValue.Of(m.Role),
                ["content"] = JinjaValue.Of(m.Content),
            };
            list.Add(JinjaValue.Dict(item));
        }

        Dictionary<string, JinjaValue> ctx = new(StringComparer.Ordinal)
        {
            ["messages"] = JinjaValue.Of(list),
            ["add_generation_prompt"] = JinjaValue.Of(addGenerationPrompt),
            ["bos_token"] = JinjaValue.Of(bosToken),
        };
        return JinjaTemplate.Render(template, JinjaValue.Dict(ctx), options);
    }

    /// <summary>模板来自 GGUF 的入口: 缺失/空 ⇒ 显式抛 (不静默回退到下面的 DeepSeek 专用路径)。</summary>
    public static string RenderFromModelTemplate(string? ggufTemplate, IReadOnlyList<ChatMessage> messages, bool addGenerationPrompt, string bosToken, JinjaOptions? options = null)
    {
        if (string.IsNullOrEmpty(ggufTemplate))
        {
            throw new NotSupportedException("该模型 GGUF 无 tokenizer.chat_template ⇒ 模板驱动渲染不可用 (不静默回退)");
        }

        return RenderFromTemplate(ggufTemplate, messages, addGenerationPrompt, bosToken, options);
    }

    /// <summary>自检: 常量标签与资产表一致 (防止与生成资产漂移)。</summary>
    public static bool SelfCheck(out string detail)
    {
        (string name, string value)[] tags =
        [
            ("bos", Bos),
            ("eos", Eos),
            ("user", UserTag),
            ("assistant", AssistantTag),
            ("tool_outputs_end", ToolOutputsEnd),
        ];
        foreach ((string name, string value) in tags)
        {
            if (!TokenizerAssets.SplitTokens.Contains(value))
            {
                detail = $"模板标签 {name}={value} 不在切分集 (资产漂移)";
                return false;
            }
        }

        if (!TokenizerAssets.SpecialTokens.Contains(Bos) || !TokenizerAssets.SpecialTokens.Contains(Eos))
        {
            detail = "bos/eos 不在特殊符号表";
            return false;
        }

        detail = "5 个模板标签均在切分集内, bos/eos 在特殊符号表内";
        return true;
    }
}
