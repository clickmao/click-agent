using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using agent.exploration;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// R485 H1 机检: 分类器在**已录制真机流量**上逐条自足判定。
/// 语料 = eval/rover/r482/calls-Arole.jsonl (R482 Arole 臂 21 次远端调用, 与 R485 预注册同 pin)。
/// 判据 (prereg_r485.json H1): 微组 7/7 判 skip ∧ 主组 14/14 判 send。
/// fail-closed: 语料不可达 ⇒ **判红** (而非跳过); 语料形状 (21/7/14) 不符 ⇒ 判红 (pin 漂移即判红)。
/// 依赖 JSONL 的 messages[1] = 首条 user 消息 (微问询在该消息内以 '[微步骤隔离问询] ' 前缀包裹)。
/// </summary>
public class MicroStepGateTrafficTests
{
    private const string MicroPrefix = "[微步骤隔离问询]";
    private const int ExpectedTotal = 21;
    private const int ExpectedMicro = 7;
    private const int ExpectedMain = 14;

    /// <summary>从测试输出目录向上找仓库根 (以语料文件为锚, 不硬编码层级)。</summary>
    private static string CorpusPath()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var p = Path.Combine(dir.FullName, "eval", "rover", "r482", "calls-Arole.jsonl");
            if (File.Exists(p)) return p;
            dir = dir.Parent;
        }
        return string.Empty;
    }

    /// <summary>取包裹文本里的微问题原文 (前缀之后到首个换行为止)。</summary>
    private static string ExtractQuestion(string wrapper)
    {
        var i = wrapper.IndexOf(MicroPrefix, StringComparison.Ordinal);
        var s = wrapper[(i + MicroPrefix.Length)..].TrimStart();
        var nl = s.IndexOf('\n');
        if (nl >= 0) s = s[..nl];
        return s.Trim();
    }

    private static string Content(JsonElement msg)
    {
        if (msg.TryGetProperty("content", out var c) && c.ValueKind == JsonValueKind.String)
            return c.GetString() ?? string.Empty;
        return string.Empty;
    }

    [Fact]
    public void H1_RecordedTraffic_MicroGroupAllBlocked_MainGroupAllSent()
    {
        var path = CorpusPath();
        Assert.True(path.Length > 0,
            "语料缺失: eval/rover/r482/calls-Arole.jsonl 不可达 ⇒ H1 无法机检 (fail-closed 判红, 不得跳过)");

        int microTotal = 0, microBlocked = 0, mainTotal = 0, mainBlocked = 0;
        var reasons = new List<string>();
        var markers = new List<string>();

        foreach (var line in File.ReadAllLines(path))
        {
            if (line.Trim().Length == 0) continue;
            using var doc = JsonDocument.Parse(line);
            if (!doc.RootElement.TryGetProperty("messages", out var msgs) || msgs.ValueKind != JsonValueKind.Array)
            { Assert.Fail("语料形状不符: 缺 messages 数组"); return; }
            if (msgs.GetArrayLength() < 2)
            { Assert.Fail("语料形状不符: messages < 2 (无首条 user 消息)"); return; }

            var isMicro = false;
            var question = string.Empty;
            foreach (var m in msgs.EnumerateArray())
            {
                var c = Content(m);
                if (c.Contains(MicroPrefix, StringComparison.Ordinal))
                {
                    isMicro = true;
                    question = ExtractQuestion(c);
                    break;
                }
            }

            if (isMicro)
            {
                microTotal++;
                var d = MicroStepIsolationGate.Decide(question);
                if (!d.Send) { microBlocked++; reasons.Add(d.Reason); markers.Add(d.Marker); }
            }
            else
            {
                mainTotal++;
                if (!MicroStepIsolationGate.Decide(Content(msgs[1])).Send) mainBlocked++;
            }
        }

        Assert.Equal(ExpectedTotal, microTotal + mainTotal); // pin 形状守恒
        Assert.Equal(ExpectedMicro, microTotal);
        Assert.Equal(ExpectedMain, mainTotal);
        Assert.Equal(ExpectedMicro, microBlocked);   // 微组 7/7 判 skip
        Assert.Equal(0, mainBlocked);                // 主组 14/14 判 send (误伤 = 0)
        Assert.All(reasons, r => Assert.Equal("isolation_invalid_anaphora", r));
        Assert.All(markers, m => Assert.False(string.IsNullOrWhiteSpace(m))); // 归因可审计: 必须落到具体标记
    }

    /// <summary>R484 的语义判否锚点: 本地化被否, 残留候选 = 形态分流 —— 拦截面必须只覆盖回指形态。</summary>
    [Fact]
    public void H1_BlockedSet_IsExactlyAnaphoraShaped()
    {
        var path = CorpusPath();
        Assert.True(path.Length > 0, "语料缺失 (fail-closed 判红)");

        var microQuestions = new List<string>();
        foreach (var line in File.ReadAllLines(path))
        {
            if (line.Trim().Length == 0) continue;
            using var doc = JsonDocument.Parse(line);
            foreach (var m in doc.RootElement.GetProperty("messages").EnumerateArray())
            {
                var c = Content(m);
                if (c.Contains(MicroPrefix, StringComparison.Ordinal)) { microQuestions.Add(ExtractQuestion(c)); break; }
            }
        }

        Assert.Equal(ExpectedMicro, microQuestions.Count);
        // 每条都被拦 ⇒ 每条都必须至少含一个**已登记**标记 (可解释性: 拦截不得来自未登记规则)
        foreach (var q in microQuestions)
        {
            var hit = false;
            foreach (var mk in MicroStepIsolationGate.AnaphoraMarkers)
                if (mk.Length > 0 && q.Contains(mk, StringComparison.Ordinal)) { hit = true; break; }
            Assert.True(hit, $"被拦截但无登记标记解释: {q}");
        }
    }
}
