using System;
using System.Collections.Generic;
using System.Text.Json;

namespace agent.skills;

/// <summary>
/// v0.17.2-b (R337, 用户钦定): 脚本插件事件类型 — 插件脚本 stdout **JSON Lines 事件流**的 type 字段。
/// 权威协议: docs/plans/v0.17.2-activity-script-plan.md §2。
/// </summary>
public enum ScriptPluginEventType
{
    Progress,
    Checkpoint,
    Heartbeat,
    Done,
    Error,
}

/// <summary>
/// v0.17.2-b: 单行事件解析产物。字段对应协议: done 带 summary/exit_code(顶层优先, data 兜底) +
/// data.outputs(产物路径数组); error 带 error 消息; heartbeat/progress 带 progress_pct。
/// </summary>
public sealed class ScriptPluginEvent
{
    public ScriptPluginEventType Type { get; set; }
    public long TsUnixMs { get; set; }
    public string Msg { get; set; } = string.Empty;
    public string? Summary { get; set; }
    public int? ExitCode { get; set; }
    public string? Error { get; set; }
    public List<string> Outputs { get; } = new();
    public double? ProgressPct { get; set; }
}

/// <summary>
/// v0.17.2-b: JSON Lines 事件流解析器/状态机 (纯逻辑, 时钟注入可测)。
/// 语义 (协议权威): type ∈ progress|checkpoint|heartbeat|done|error; 非 JSON/缺 type/未知 type 行 =
/// 调试噪声 (忽略, 计数打点); **done/error = 终态** (CLI 以事件为准, 进程退出码仅兜底);
/// 事件驱动 LastEvent 活性 → 超过 2×heartbeat 无事件 = 疑似挂起 (打点, 不杀)。
/// </summary>
public sealed class ScriptEventStreamParser
{
    private readonly Func<long> _nowMs;

    public ScriptEventStreamParser(Func<long>? nowMs = null)
    {
        _nowMs = nowMs ?? (() => DateTimeOffset.UtcNow.ToUnixTimeMilliseconds());
        LastEventUnixMs = _nowMs();
    }

    public long LastEventUnixMs { get; private set; }
    public bool TerminalReached { get; private set; }
    public ScriptPluginEventType? TerminalType { get; private set; }
    public ScriptPluginEvent? TerminalEvent { get; private set; }
    public int EventLines { get; private set; }
    public int NoiseLines { get; private set; }
    public int ProgressCount { get; private set; }
    public int HeartbeatCount { get; private set; }

    public long MsSinceLastEvent(long nowMs) => Math.Max(0, nowMs - LastEventUnixMs);

    /// <summary>疑似挂起: 未达终态且距最后事件 ≥ hangAfterMs。</summary>
    public bool IsSuspectedHang(long nowMs, long hangAfterMs)
        => !TerminalReached && MsSinceLastEvent(nowMs) >= hangAfterMs;

    /// <summary>喂一行 stdout。空行忽略 (python print() 常见, 不算噪声)。</summary>
    public void FeedLine(string? line)
    {
        if (string.IsNullOrEmpty(line))
            return;
        if (!TryParseEvent(line, out var ev, _nowMs()))
        {
            NoiseLines++;
            return;
        }
        EventLines++;
        if (ev.TsUnixMs > LastEventUnixMs)
            LastEventUnixMs = ev.TsUnixMs;
        switch (ev.Type)
        {
            case ScriptPluginEventType.Progress:
                ProgressCount++;
                break;
            case ScriptPluginEventType.Heartbeat:
                HeartbeatCount++;
                break;
            case ScriptPluginEventType.Done:
            case ScriptPluginEventType.Error:
                if (!TerminalReached)
                {
                    TerminalReached = true;
                    TerminalType = ev.Type;
                    TerminalEvent = ev;
                }
                break;
        }
    }

    /// <summary>解析单行事件。非 JSON / 非对象 / 缺 type / 未知 type / 损坏 → false (调用方计噪声)。</summary>
    public static bool TryParseEvent(string line, out ScriptPluginEvent ev, long? nowMs = null)
    {
        ev = new ScriptPluginEvent { TsUnixMs = nowMs ?? DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() };
        try
        {
            using var doc = JsonDocument.Parse(line);
            var root = doc.RootElement;
            if (root.ValueKind != JsonValueKind.Object || !root.TryGetProperty("type", out var t) || t.ValueKind != JsonValueKind.String)
                return false;
            var type = t.GetString() switch
            {
                "progress" => ScriptPluginEventType.Progress,
                "checkpoint" => ScriptPluginEventType.Checkpoint,
                "heartbeat" => ScriptPluginEventType.Heartbeat,
                "done" => ScriptPluginEventType.Done,
                "error" => ScriptPluginEventType.Error,
                _ => (ScriptPluginEventType?)null,
            };
            if (type is null)
                return false;
            ev.Type = type.Value;

            if (root.TryGetProperty("ts", out var ts) && ts.ValueKind == JsonValueKind.Number)
            {
                var v = ts.GetDouble();
                // 协议: ts = epoch 毫秒; 容忍 epoch 秒 (time.time(), ~1e9..1e12) → ×1000;
                // 小值 (<1e9) = 相对毫秒/测试值, 原样 (协议内 ts 建议 epoch ms, 脚本可用 time.time()*1000)
                ev.TsUnixMs = v >= 1_000_000_000d ? (long)(v < 1_000_000_000_000d ? v * 1000d : v) : (long)v;
            }
            ev.Msg = GetStr(root, "msg") ?? string.Empty;

            if (type == ScriptPluginEventType.Done || type == ScriptPluginEventType.Error)
            {
                ev.Summary = GetStr(root, "summary") ?? GetDataStr(root, "summary");
                var code = GetInt(root, "exit_code") ?? GetDataInt(root, "exit_code");
                if (type == ScriptPluginEventType.Done)
                {
                    ev.ExitCode = code ?? 0;
                    if (root.TryGetProperty("data", out var d) && d.ValueKind == JsonValueKind.Object
                        && d.TryGetProperty("outputs", out var outs) && outs.ValueKind == JsonValueKind.Array)
                    {
                        foreach (var o in outs.EnumerateArray())
                            if (o.ValueKind == JsonValueKind.String)
                                ev.Outputs.Add(o.GetString() ?? string.Empty);
                    }
                }
                else
                {
                    ev.ExitCode = code;
                    ev.Error = GetStr(root, "error") ?? GetDataStr(root, "error") ?? ev.Msg;
                }
            }
            if (type == ScriptPluginEventType.Heartbeat || type == ScriptPluginEventType.Progress)
                ev.ProgressPct = GetDbl(root, "progress_pct") ?? GetDataDbl(root, "progress_pct");
            return true;
        }
        catch (JsonException)
        {
            return false;
        }
    }

    private static string? GetStr(JsonElement root, string key)
        => root.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() : null;

    private static int? GetInt(JsonElement root, string key)
        => root.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.Number ? v.GetInt32() : null;

    private static double? GetDbl(JsonElement root, string key)
        => root.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.Number ? v.GetDouble() : null;

    private static JsonElement? Data(JsonElement root)
        => root.TryGetProperty("data", out var d) && d.ValueKind == JsonValueKind.Object ? d : null;

    private static string? GetDataStr(JsonElement root, string key)
    {
        var d = Data(root);
        return d is null ? null : GetStr(d.Value, key);
    }

    private static int? GetDataInt(JsonElement root, string key)
    {
        var d = Data(root);
        return d is null ? null : GetInt(d.Value, key);
    }

    private static double? GetDataDbl(JsonElement root, string key)
    {
        var d = Data(root);
        return d is null ? null : GetDbl(d.Value, key);
    }
}
