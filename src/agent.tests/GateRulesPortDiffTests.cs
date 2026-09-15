using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using agent.modelqueue;
using Xunit;

namespace agent.tests;

/// <summary>
/// R468: 门判规则 Python 端口 (`eval/rover/r468/gate_rules.py`) 与产品判据的**差分校验**。
/// 目的: 真实流量外部效度读数由该端口产出 ⇒ 端口必须与产品 `TurnGateJudge` 逐条一致,
/// 否则外部结论不成立 (器具镐: 源码派生器具须与产品逐位比对)。
/// 语料 `eval/rover/r468/real-traffic-corpus.jsonl` 由端口生成 (真实用户轮 + 网格 p12 + 产品 InlineData)。
/// 规则一旦在产品侧改变 ⇒ 本节必红 ⇒ 强制重生成语料 (证据↔器具版本绑定)。
/// </summary>
public class GateRulesPortDiffTests
{
    private static readonly string RepoRoot = FindRepoRoot();

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "agent.sln")))
            dir = dir.Parent;
        return dir?.FullName ?? ".";
    }

    private static List<JsonElement> LoadCorpus()
    {
        var path = Path.Combine(RepoRoot, "eval", "rover", "r468", "real-traffic-corpus.jsonl");
        Assert.True(File.Exists(path), $"R468 差分语料缺失: {path}");
        var rows = new List<JsonElement>();
        foreach (var line in File.ReadAllLines(path))
        {
            if (string.IsNullOrWhiteSpace(line)) continue;
            rows.Add(JsonDocument.Parse(line).RootElement.Clone());
        }
        return rows;
    }

    /// <summary>产品侧标签: 与前置门链同序 (MechanicalPass → 纯复述 → 认可族 → 残余带)。</summary>
    private static string ProductLabel(string text)
    {
        if (TurnGateJudge.MechanicalPass(text)) return "pass";
        if (TurnGateJudge.IsPureRepeat(text)) return "repeat";
        if (TurnGateJudge.MechanicalAck(text)) return "ack";
        return "other";
    }

    [Fact]
    public void Port_Corpus_Labels_Match_Product_Judges()
    {
        var rows = LoadCorpus();
        Assert.True(rows.Count >= 300, $"语料过窄: {rows.Count} 行 (<300)");
        var mismatch = new List<string>();
        foreach (var r in rows)
        {
            var text = r.GetProperty("text").GetString() ?? "";
            var portLabel = r.GetProperty("class").GetString();
            var prodLabel = ProductLabel(text);
            if (portLabel != prodLabel)
                mismatch.Add($"[{portLabel}≠{prodLabel}] {text.Substring(0, Math.Min(40, text.Length))}");
        }
        Assert.True(mismatch.Count == 0,
            $"端口与产品判据不一致 {mismatch.Count}/{rows.Count} 条 (前 8): {string.Join(" | ", mismatch.GetRange(0, Math.Min(8, mismatch.Count)))}");
    }

    [Fact]
    public void Corpus_Covers_Archive_And_Repeat_And_Pass_Families()
    {
        var rows = LoadCorpus();
        var classes = new HashSet<string>();
        foreach (var r in rows) classes.Add(r.GetProperty("class").GetString() ?? "");
        foreach (var need in new[] { "pass", "ack", "repeat", "other" })
            Assert.Contains(need, classes);
    }

    /// <summary>
    /// R468 外部效度断言: **真实用户轮**语料 (src=real) 上, 产品机械可跳面恒为 0。
    /// 即: 不存在既非 MechanicalPass 又 (纯复述 ∨ 认可族) 的真实轮。这是「网格降幅 ≠ 真实降幅」的机检锚。
    /// </summary>
    [Fact]
    public void RealTraffic_Rows_Have_Zero_Product_SkipFace()
    {
        var rows = LoadCorpus();
        int real = 0, skipFace = 0;
        foreach (var r in rows)
        {
            if (r.TryGetProperty("src", out _)) continue; // 网格/InlineData 行不计入真实面
            real++;
            var text = r.GetProperty("text").GetString() ?? "";
            if (TurnGateJudge.MechanicalPass(text)) continue;
            if (TurnGateJudge.IsPureRepeat(text) || TurnGateJudge.MechanicalAck(text)) skipFace++;
        }
        Assert.True(real >= 300, $"真实语料过窄: {real}");
        Assert.Equal(0, skipFace);
    }
}
