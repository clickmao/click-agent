
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
    // v0.11.0 R121 (真缺陷 51 防御): Configure 前发射的点位原为静默丢失 (mass_151 C03 llm_calls=0
    // 而 reply 完整的假阴性候选机制)。改: 先缓存 (ring 上限 32), Configure 后 flush, 丢失可见。
    private static readonly List<string> _pendingBeforeConfigure = new();
    private static long _droppedTotal;

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
                // v0.11.0 R110 (fix#42): env 指定绝对目录时覆写默认 dir — 批测每用例独立打点文件,
                // 根除共享单文件的删除/追加时序竞争 (mass_99 系间歇 llm_calls=0 误判根因)。
                if (!string.IsNullOrWhiteSpace(env) && !string.Equals(env, "on", StringComparison.OrdinalIgnoreCase))
                    telemetryDir = env;
                Directory.CreateDirectory(telemetryDir);
                _writer?.Dispose();
                var path = Path.Combine(telemetryDir, _sessionId + ".jsonl");
                _writer = new StreamWriter(path, append: true, Encoding.UTF8) { AutoFlush = true };
                // R121: flush Configure 前缓存的点位 (保持 seq 原序)
                if (_pendingBeforeConfigure.Count > 0)
                {
                    foreach (var line in _pendingBeforeConfigure)
                        _writer.Write(line);
                    _pendingBeforeConfigure.Clear();
                }
            }
            catch
            {
                // 打点失败绝不影响主链路
                _writer = null;
            }
        }
    }

    /// <summary>单点位: point=点位类型, module=发起模块, kv=度量键值 (数值/字符串/时间戳由调用方给原始值)</summary>
    /// <summary>R305 (真缺陷 71 根因): writer 创建失败的静默丢弃计数 — 批测中并行 build
    /// 会让 Configure 撞文件锁 → _writer=null → 后续 Emit 全丢 (C08 intent=None/llm_calls=0 假象)。</summary>
    public static long WriterNullDrops => Interlocked.Read(ref _writerNullDrops);
    private static long _writerNullDrops;

    public static void Emit(string point, string module, params (string Key, object? Value)[] kv)
    {
        if (!_enabled)
            return;
        if (_writer is null)
        {
            // Configure 失败 (_writer=null) 时不再静默 — 计数可见 (进程退出前宿主可上报)。
            Interlocked.Increment(ref _writerNullDrops);
            return;
        }
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
                if (_writer is not null)
                    _writer.Write(sb.ToString());
                else
                {
                    // Configure 前的点位: 缓存待 flush (上限 256, 超出丢弃并计数 — 可见化)。
                    // v0.11.0 R133b: 上限 32→256 — 测试并行 (xUnit 多类并发) 下 ContextAssembler
                    // phase_timing 打点 + tendency 写入可轻松 >32, 挤掉 TelemetryPendingTests 的
                    // pre_boot_probe 断言 → 全仓测试间歇 flaky (实证 5/6 失败)。产品运行时 Configure
                    // 在进程启动即调用, ring 极少超 32; 放宽只影响极端并发, 丢点计数仍可见。
                    if (_pendingBeforeConfigure.Count < 256)
                        _pendingBeforeConfigure.Add(sb.ToString());
                    _droppedTotal++;
                }
            }
        }
        catch
        {
            // 打点失败绝不影响主链路
            Interlocked.Increment(ref _droppedTotal);
        }
    }

    /// <summary>R121: 已丢弃点位总数 (Emit 在 Configure 前 / 写盘异常) — 诊断用, 不影响主链路</summary>
    public static long DroppedTotal => Interlocked.Read(ref _droppedTotal);

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
