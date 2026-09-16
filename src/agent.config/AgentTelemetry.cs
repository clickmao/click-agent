
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
    // 而 reply 完整的假阴性候选机制)。改: 先缓存 (ring 上限 256), Configure 后 flush, 丢失可见。
    // v0.11.0 R133b: 上限 32→256 — 测试并行 (xUnit 多类并发) 下 ContextAssembler phase_timing
    // 打点 + tendency 写入可轻松 >32, 挤掉 TelemetryPendingTests 的 pre_boot_probe 断言
    // → 全仓测试间歇 flaky (实证 5/6 失败)。
    // R498 候选② (真缺陷 88, 本类唯一改动): **满环时淘汰最旧, 而不是丢弃最新** ——
    // 旧策略恰好打掉 R121 想保的那一条: Configure 紧前发出的点 (启动路径探针/末位启动事件)
    // 是 ring 里**最新**的一条, 满环时第一个被丢弃 ⇒ "不静默丢失"的语义被上限反向破掉。
    // 证据 (本轮同网格单变量对照): eval/rover/r498/telemetry-ring-before-after.log —
    // 满环 + 紧前探针, 旧策略 RED (探针缺席), 新策略 GREEN (探针在位)。
    // 口径: _droppedTotal 只计**真丢失** (淘汰即真丢失; 进环不再计数 —— 旧写法把"已缓存"也计进
    // DroppedTotal, 指标自报假形态)。新增 PendingEvictions 单列淘汰数。
    private static readonly List<string> _pendingBeforeConfigure = new();
    private static long _droppedTotal;
    private static long _pendingEvictions;
    private static long _pendingBuffered;

    /// <summary>Configure 前点位缓存上限 (R498: 满环 ⇒ 淘汰最旧, 不再是丢最新; 测试需读 ⇒ 公开常量)。</summary>
    public const int PendingCapacity = 256;

    /// <summary>R498: 当前 pending 环中的点位数 (测试/诊断用; 观测不改状态)。</summary>
    public static int PendingCount
    {
        get { lock (Lock) return _pendingBeforeConfigure.Count; }
    }

    /// <summary>R498: 因环满被 FIFO 淘汰 (真丢失) 的点位数 —— 与 <see cref="DroppedTotal"/> 同向。</summary>
    public static long PendingEvictions => Interlocked.Read(ref _pendingEvictions);

    /// <summary>R498: 累计进入过 pending 环的点位数 (含其后被淘汰者) —— 判「满环发生过」可机检。</summary>
    public static long PendingBuffered => Interlocked.Read(ref _pendingBuffered);

    /// <summary>
    /// R498 候选② (测试隔离接缝): 把**进程共享**的静态态清回未 Configure 的初态 ——
    /// writer 释放并清空 / configured=false / enabled=true / session 复位 / 空环。
    /// **累计计数器 (DroppedTotal / WriterNullDrops / PendingEvictions) 不复位** —— 它们是进程级累计
    /// 指标, 复位会让并发断言的读数变成假形态。
    /// 只由测试调用 (InternalsVisibleTo: agentframework.tests); 生产路径不调用。
    /// </summary>
    internal static void ResetForTests()
    {
        lock (Lock)
        {
            try { _writer?.Dispose(); } catch { /* 释放失败不影响复位 */ }
            _writer = null;
            _configured = false;
            _enabled = true;
            _sessionId = "default";
            _pendingBeforeConfigure.Clear();
        }
    }

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
                _writer = new StreamWriter(path, append: true, new System.Text.UTF8Encoding(false)) { AutoFlush = true };
                _configured = true;
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
    private static bool _configured;

    public static void Emit(string point, string module, params (string Key, object? Value)[] kv)
    {
        if (!_enabled)
            return;
        if (_writer is null && _configured)
        {
            // R305: Configure 已成功但 writer 丢失 (批测中并行 build 撞文件锁等) —
            // 不再静默, 计数可见 (进程退出前宿主可上报)。未 Configure 的路径走下方 R121 pending。
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
                    // Configure 前的点位: 缓存待 flush。
                    // R498 候选②: 满环 ⇒ **淘汰最旧** (FIFO)。旧策略 `if (Count < 256) Add(...)` 丢弃的是
                    // **最新**一条 —— 而 Configure 紧前发出的那条恰恰是 R121 要保的启动路径探针。
                    if (_pendingBeforeConfigure.Count >= PendingCapacity)
                    {
                        _pendingBeforeConfigure.RemoveAt(0);        // 满环 ⇒ FIFO 淘汰最旧 (旧策略丢最新 = 真缺陷 88)
                        Interlocked.Increment(ref _pendingEvictions);
                        Interlocked.Increment(ref _droppedTotal);   // 淘汰 = 真丢失 (口径见字段注释)
                    }
                    _pendingBeforeConfigure.Add(sb.ToString());
                    Interlocked.Increment(ref _pendingBuffered);
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
