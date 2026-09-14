using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using agent.llamacpp;
using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// R413 单组件探针 —— 回答"1.5b r1 能否输出**格式化**判别结果"（而不是自由文本）。
///
/// 背景（真机实证，2026-09-14）: 生产门用自由生成 + 只输出一个字母 ⇒ 思考链把小
/// 预算吃光、字母从未出现，解析只能去推理正文里猜 = 空心。本探针直接测 5 种出参格式，
/// 逐条落盘**完整原文**（不经过遥测，避免任何截断），再判"格式是否合法"。
///
/// 纪律:
///   - 门控: 仅当 AGENTFRAMEWORK_R413_PROBE=1 时真跑（否则 0 成本跳过）。
///   - 进出都是**标准 chat template**（经 ILocalPromptRenderer，由端口保证）；探针不自行拼模板。
///   - 外部真值 = 落盘文件 eval/rover/r413/probe-struct.jsonl（不信自报计数）。
///   - 测量期间不做别的吃 CPU 的活（R407 纯净纪律）。
/// </summary>
public sealed class LocalTurnGateProbeTests
{
    private static bool Enabled =>
        Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R413_PROBE") == "1";

    private static readonly string[] Messages =
    {
        "好，知道了。",                                                   // chat (应本地消化)
        "另外，测试命令呢？",                                              // ask  (需远端)
        "收到，谢谢。",                                                   // chat
        "不对，你上一条回答不准确，请重新确认后再回答一次。",                 // llm/correct (需远端)
        "嗯。",                                                          // chat
        "现在把结论压缩成一行给我。",                                       // llm (需远端)
    };

    [Fact]
    public async Task Probe_结构化出参能力_五变体()
    {
        if (!Enabled) return;

        var model = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R413_MODEL")
                    ?? "/tmp/models/r1-distill-qwen-1.5b-q4km.gguf";
        var bin = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_LLAMA_BIN") ?? string.Empty;
        var outPath = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_R413_PROBE_OUT")
                      ?? "/home/agentuser/AgentFramework/eval/rover/r413/probe-struct.jsonl";

        var opts = new LlamaCppGeneratorOptions
        {
            ModelPath = model,
            BinaryPath = bin,
            ContextSize = 4608,
            Threads = 2,
            StartTimeoutMs = 240_000,
            AllowRestart = false,
            MaxTokens = 192,
        };

        await using var port = new LlamaCppLocalGenerationPort(opts);
        Assert.True(port.IsAvailable, $"本地端口不可用 (model={model}, bin={bin})");

        // 五个变体: (名字, 提示构造, 尾接 assistant 前缀, 上限)
        var variants = new (string Name, Func<string, string> Build, string? Prefill, int MaxTokens)[]
        {
            ("V1_free_sp", m => agent.modelqueue.TurnGateJudge.BuildPrompt(m, null, null), null, 192),
            ("V2_json_noprefill", BuildJsonPrompt, null, 192),
            ("V3_json_prefill", BuildJsonPrompt, "{\"kind\":\"", 48),
            ("V4_label_prefill", BuildLabelPrompt, "分类：", 24),
            ("V5_label_noprefill", BuildLabelPrompt, null, 24),
        };

        var sb = new StringBuilder();
        var sw = Stopwatch.StartNew();
        var rows = 0;
        (string Name, int Valid, int Rows, long Gen, long Ms)[] summary =
            new (string, int, int, long, long)[variants.Length];

        for (var vi = 0; vi < variants.Length; vi++)
        {
            var v = variants[vi];
            var valid = 0; var gen = 0L; var ms = 0L; var n = 0;
            foreach (var m in Messages)
            {
                var turns = new List<LocalChatTurn> { new("user", v.Build(m)) };
                if (v.Prefill is not null) turns.Add(new("assistant", v.Prefill));

                var o = await port.GenerateAsync(new LocalGenerationRequest
                {
                    SessionKey = "r413:probe:" + v.Name,
                    TurnIndex = 1,
                    Turns = turns,
                    MaxTokens = v.MaxTokens,
                }, CancellationToken.None);

                var ok = o.Success && o.AccountingConsistent;
                var content = o.Content ?? string.Empty;
                var verdict = ok ? Judge(content, v.Name) : "-";
                if (ok && verdict != "-") valid++;
                n++; gen += o.GeneratedTokens; ms += o.ElapsedMs;

                sb.Append('{')
                  .Append("\"variant\":\"").Append(v.Name).Append("\",")
                  .Append("\"msg\":\"").Append(Esc(m)).Append("\",")
                  .Append("\"ok\":").Append(ok ? "true" : "false").Append(',')
                  .Append("\"error\":\"").Append(Esc(o.Error ?? string.Empty)).Append("\",")
                  .Append("\"accounting\":").Append(o.AccountingConsistent ? "true" : "false").Append(',')
                  .Append("\"gen_tokens\":").Append(o.GeneratedTokens).Append(',')
                  .Append("\"prompt_total\":").Append(o.TokensEvaluated).Append(',')
                  .Append("\"cache_n\":").Append(o.CachedTokens).Append(',')
                  .Append("\"elapsed_ms\":").Append(o.ElapsedMs).Append(',')
                  .Append("\"has_think_tag\":").Append(content.Contains(ThinkClose).ToString().ToLowerInvariant()).Append(',')
                  .Append("\"content_len\":").Append(content.Length).Append(',')
                  .Append("\"verdict\":\"").Append(Esc(verdict)).Append("\",")
                  .Append("\"content_full\":\"").Append(Esc(content)).Append("\"}")
                  .Append('\n');
            }
            summary[vi] = (v.Name, valid, n, gen, ms);
        }

        sw.Stop();
        File.WriteAllText(outPath, sb.ToString(), new UTF8Encoding(false));

        var head = new StringBuilder();
        head.Append("探针落盘: ").Append(outPath).Append('\n');
        head.Append("wall=").Append(sw.ElapsedMilliseconds).Append("ms\n");
        foreach (var s in summary)
            head.Append($"{s.Name,-20} 合法={s.Valid}/{s.Rows} 生成tok={s.Gen} 均延迟={(s.Rows > 0 ? s.Ms / s.Rows : 0)}ms\n");
        Console.WriteLine(head.ToString());
        File.WriteAllText(outPath + ".summary.txt", head.ToString(), new UTF8Encoding(false));
    }

    /// <summary>JSON 出参: 只认一行合法 JSON 且 kind 在允许集合内、new_info 为布尔。</summary>
    private static string Judge(string content, string variant)
    {
        if (string.IsNullOrWhiteSpace(content)) return "-";
        var text = content.Trim();
        if (text.Contains(ThinkClose)) text = text[(text.LastIndexOf(ThinkClose, StringComparison.Ordinal) + ThinkClose.Length)..].Trim();

        if (variant.StartsWith("V1", StringComparison.Ordinal))
        {
            var m = Regex.Match(text, @"(?<![A-Za-z])([SPsp])(?![A-Za-z])");
            return m.Success ? (m.Value.Equals("S", StringComparison.OrdinalIgnoreCase) ? "SKIP" : "PASS") : "-";
        }
        if (variant.StartsWith("V2", StringComparison.Ordinal) || variant.StartsWith("V3", StringComparison.Ordinal))
        {
            var m = Regex.Match(text, "\"kind\"\\s*:\\s*\"(ask|tool|llm|chat)\"", RegexOptions.IgnoreCase);
            var ni = Regex.Match(text, "\"new_info\"\\s*:\\s*(true|false)", RegexOptions.IgnoreCase);
            if (!m.Success || !ni.Success) return "-";
            return m.Groups[1].Value.ToUpperInvariant() + "/" + ni.Groups[1].Value.ToLowerInvariant();
        }
        var w = Regex.Match(text, "(?<![A-Za-z])(ASK|TOOL|LLM|CHAT)(?![A-Za-z])", RegexOptions.IgnoreCase);
        return w.Success ? w.Value.ToUpperInvariant() : "-";
    }

    /// <summary>思考链闭合标记 (转义写, 防写入通道吃掉尖括号)。</summary>
    private const string ThinkClose = "\u003c/think\u003e";

    private const string JsonRules =
        "你是轮次路由器。对用户消息做一次分类，只输出一行 JSON，不要解释、不要思考过程。\n" +
        "字段: \"kind\" ∈ {ask(问询/提问), tool(要求执行工具或命令), llm(要求生成内容), chat(仅认可/寒暄/确认, 无新诉求)}; \"new_info\" ∈ {true,false}。\n" +
        "示例: {\"kind\":\"chat\",\"new_info\":false}\n";

    private static string BuildJsonPrompt(string msg) =>
        JsonRules + "用户消息: " + msg + "\n输出:";

    private static string BuildLabelPrompt(string msg) =>
        "判断用户消息要求什么动作，只输出一个词: ASK / TOOL / LLM / CHAT。\n" +
        "用户消息: " + msg + "\n分类：";

    private static string Esc(string s)
    {
        var b = new StringBuilder(s.Length + 16);
        foreach (var c in s)
        {
            switch (c)
            {
                case '"': b.Append("\\\""); break;
                case '\\': b.Append("\\\\"); break;
                case '\n': b.Append("\\n"); break;
                case '\r': b.Append("\\r"); break;
                case '\t': b.Append("\\t"); break;
                default:
                    if (c < ' ') b.Append("\\u").Append(((int)c).ToString("x4"));
                    else b.Append(c);
                    break;
            }
        }
        return b.ToString();
    }
}
