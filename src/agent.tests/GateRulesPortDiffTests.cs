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

    /// <summary>语料声明的补丁面 ⇒ C# 侧补丁集合 (签名只在 C# 侧算; 端口按行内 `patch` 声明同构判定)。</summary>
    private static HashSet<string> PatchesOf(IEnumerable<JsonElement> rows)
    {
        var set = new HashSet<string>(StringComparer.Ordinal);
        foreach (var r in rows)
        {
            if (!r.TryGetProperty("patch", out var p)) continue;
            var face = p.GetString() ?? "";
            if (face.Length == 0) continue;
            set.Add(agent.nlp.NlpGate.Key(face, agent.nlp.NlpGate.SignatureOf(r.GetProperty("text").GetString() ?? "")));
        }
        return set;
    }

    /// <summary>「无补丁」的确定性形态 (显式空集, 不读进程级回补库 ⇒ 与执行顺序无关)。</summary>
    private static readonly HashSet<string> NoPatches = new(StringComparer.Ordinal);

    /// <summary>产品侧标签: 与前置门链同序 (MechanicalPass → 纯复述 → 同义改写 → 认可族 → 残余带)。</summary>
    private static string ProductLabel(string text, IReadOnlyCollection<string> patches)
    {
        if (TurnGateJudge.MechanicalPass(text)) return "pass";
        if (TurnGateJudge.IsPureRepeat(text, patches)) return "repeat";
        if (LocalParaphraseChannel.IsPureParaphrase(text, patches)) return "para";
        if (TurnGateJudge.MechanicalAck(text)) return "ack";
        return "other";
    }

    [Fact]
    public void Port_Corpus_Labels_Match_Product_Judges()
    {
        var rows = LoadCorpus();
        Assert.True(rows.Count >= 300, $"语料过窄: {rows.Count} 行 (<300)");
        var patches = PatchesOf(rows);                      // R575: 补丁面由语料声明 (repeat/para)
        var mismatch = new List<string>();
        var patched = 0;
        foreach (var r in rows)
        {
            var text = r.GetProperty("text").GetString() ?? "";
            var portLabel = r.GetProperty("class").GetString();
            if (r.TryGetProperty("patch", out _)) patched++;
            var prodLabel = ProductLabel(text, patches);
            if (portLabel != prodLabel)
                mismatch.Add($"[{portLabel}≠{prodLabel}] {text.Substring(0, Math.Min(40, text.Length))}");
        }
        Assert.True(patched >= 8, $"补丁面覆盖不足 ({patched} 行) ⇒ 回补面未被差分校验覆盖");
        Assert.True(mismatch.Count == 0,
            $"端口与产品判据不一致 {mismatch.Count}/{rows.Count} 条 (前 8): " + string.Join(" | ", mismatch.GetRange(0, Math.Min(8, mismatch.Count))));
    }

    [Fact]
    public void Corpus_Covers_Archive_And_Repeat_And_Pass_Families()
    {
        var rows = LoadCorpus();
        var classes = new HashSet<string>();
        foreach (var r in rows) classes.Add(r.GetProperty("class").GetString() ?? "");
        foreach (var need in new[] { "pass", "ack", "repeat", "para", "other" })
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
            if (TurnGateJudge.IsPureRepeat(text, NoPatches) || TurnGateJudge.MechanicalAck(text)) skipFace++;
        }
        Assert.True(real >= 300, $"真实语料过窄: {real}");
        Assert.Equal(0, skipFace);
    }
}
