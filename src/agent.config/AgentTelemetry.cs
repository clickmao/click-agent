
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Threading;

namespace agent.config;

/// <summary>
/// v0.11.0 功能有效性打点层 (PGO 式阶段点位):
/// 全功能不同阶段的结构化点位输出 — 用于"对比数据判断是否需要改进" (用户钦定评测闭环)。
/// 8 类点位: intent / subtask / assembly / llm_call / skill / subagent / prompt_user / loop_turn
/// JSONL 追加写 data/telemetry/{session}.jsonl; 每行 {"ts","point","module","kv"}。
/// 设计约束: 静态门面 (零 DI 侵入) / 锁内单写 / 手写 JSON 转义 (AOT 安全) /
/// AGENTFRAMEWORK_TELEMETRY=off 关闭 / 打点失败绝不影响主链路 (catch-all 吞)。
/// </summary>
public static class AgentTelemetry
{
    private static readonly object Lock = new();
    private static StreamWriter? _writer;
    private static string _sessionId = "default";
    private static bool _enabled = true;
    private static long _seq;

    /// <summary>会话启动时调用: 设定 telemetry 输出流 (data/telemetry/{sessionId}.jsonl)</summary>
    public static void Configure(string sessionId, string telemetryDir)
    {
        lock (Lock)
        {
            try
            {
                var env = Environment.GetEnvironmentVariable("AGENTFRAMEWORK_TELEMETRY");
                _enabled = !string.Equals(env, "off", StringComparison.OrdinalIgnoreCase);
                if (!_enabled)
                    return;
                _sessionId = Sanitize(sessionId);
                Directory.CreateDirectory(telemetryDir);
                _writer?.Dispose();
                var path = Path.Combine(telemetryDir, _sessionId + ".jsonl");
                _writer = new StreamWriter(path, append: true, Encoding.UTF8) { AutoFlush = true };
            }
            catch
            {
                // 打点失败绝不影响主链路
                _writer = null;
            }
        }
    }

    /// <summary>单点位: point=点位类型, module=发起模块, kv=度量键值 (数值/字符串/时间戳由调用方给原始值)</summary>
    public static void Emit(string point, string module, params (string Key, object? Value)[] kv)
    {
        if (!_enabled)
            return;
        try
        {
            var sb = new StringBuilder(256);
            sb.Append("{\"ts\":\"").Append(DateTime.UtcNow.ToString("o", CultureInfo.InvariantCulture));
            sb.Append("\",\"seq\":").Append(Interlocked.Increment(ref _seq));
            sb.Append(",\"session\":\"").Append(Escape(_sessionId));
            sb.Append("\",\"point\":\"").Append(Escape(point));
            sb.Append("\",\"module\":\"").Append(Escape(module));
            if (kv is { Length: > 0 })
            {
                sb.Append("\",\"kv\":{");

                for (var i = 0; i < kv.Length; i++)
                {
                    if (i > 0)
                        sb.Append(',');
                    sb.Append('"').Append(Escape(kv[i].Key)).Append("\":");
                    var v = kv[i].Value;
                    switch (v)
                    {
                        case null:
                            sb.Append("null");
                            break;
                        case bool b:
                            sb.Append(b ? "true" : "false");
                            break;
                        case int or long or double or float:
                            sb.Append(Convert.ToString(v, CultureInfo.InvariantCulture));
                            break;
                        default:
                            sb.Append('"').Append(Escape(v.ToString())).Append('"');
                            break;
                    }
                }
                sb.Append('}');
            }
            sb.Append("}\n");
            lock (Lock)
            {
                _writer?.Write(sb.ToString());
            }
        }
        catch
        {
            // 打点失败绝不影响主链路
        }
    }

    private static string Sanitize(string s)
    {
        var b = new StringBuilder(s.Length);
        foreach (var c in s)
            b.Append(char.IsLetterOrDigit(c) || c is '-' or '_' ? c : '_');
        return b.Length == 0 ? "default" : b.ToString();
    }

    private static string Escape(string? s)
    {
        if (string.IsNullOrEmpty(s))
            return string.Empty;
        var b = new StringBuilder(s.Length + 8);
        foreach (var c in s)
        {
            switch (c)
            {
                case '"':
                    b.Append("\\\"");
                    break;
                case '\\':
                    b.Append("\\\\");
                    break;
                case '\n':
                    b.Append("\\n");
                    break;
                case '\r':
                    b.Append("\\r");
                    break;
                case '\t':
                    b.Append("\\t");
                    break;
                default:
                    if (c < 0x20)
                        b.Append("\\u").Append(((int)c).ToString("x4", CultureInfo.InvariantCulture));
                    else
                        b.Append(c);
                    break;
            }
        }
        return b.ToString();
    }
}
