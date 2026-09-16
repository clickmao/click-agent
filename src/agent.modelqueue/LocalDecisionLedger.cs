using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace agent.modelqueue;

/// <summary>
/// R495: 本地决策台账**挂载块** (实发面 + 落盘面 + 打点面共用的同一份结构量)。
/// 挂载轴 = <see cref="LocalDecisionLedger.MountEnvName"/> (默认关; 关 ⇒ <see cref="Off"/> ⇒ 旧行为逐字节不变)。
/// </summary>
/// <param name="Text">挂载文本 (§尾追加的 system 消息; 关时 = 空串)</param>
/// <param name="N">渲染时该会话的台账条数 (关时 = 0)</param>
/// <param name="Code">渲染时该会话的核对码 (关时 = 空串)</param>
/// <param name="Session8">会话指纹 (sha256 前 8 位; 关时 = 空串)</param>
public sealed record LedgerMount(string Text, int N, string Code, string Session8)
{
    /// <summary>挂载关 / 无会话 ⇒ 一个字节都不加 (与 R490..R494 逐字节同形)。</summary>
    public static readonly LedgerMount Off = new(string.Empty, 0, string.Empty, string.Empty);

    public bool On => Text.Length > 0;
}

/// <summary>
/// R495: 本地决策台账 (r1 侧真值的**落盘**面 + 可挂载引用面)。
///
/// 动机 (R413 验收③「r1 对管道有可测增益」的直接抓手):
///   链自己做过哪些本地决策 (闸判 pass/skip 及依据) —— 这是**上游永远看不到**的事实。
///   把它落盘成台账, 再把台账的**核对码**挂进发往远端的提示尾部, 就得到一个可判族:
///     · 问「本会话核对码是什么」⇒ 只有挂载臂答得出真码 (真值 = 台账字节的可复算摘要);
///     · 未挂载臂只能拒答或**编一个码** ⇒ 幻觉可机检 (编的码不在台账的任何 n 位前缀上)。
///   反向 (用户抛一个假码问「对吧」) ⇒ 挂载臂可核并否定。
///
/// 铁律:
///   1) 确定性: 核对码 = sha256(session + "|" + 台账规范行按序 \n 连接) 的前 12 位小写十六进制,
///      前缀 "LCM-"。同字节输入 ⇒ 同码 (跨进程可复算; 判据器/复核器用同一配方, 见 ledger 文件的 `canon` 字段)。
///   2) 零反射: 手写 JSON 行 (STJ 反射在 AOT 禁用); 文件写侧 UTF8Encoding(false) (去 BOM)。
///   3) 单点挂载: 只由 ModelQueueAdapter 在**远端**调用前渲染 (本地 r1 通道不消费 ⇒ 闸的输入面逐字节不变,
///      保证「挂载」是单变量而不是同时改了闸的判据输入)。
///   4) 幂等: 同 (turn, kind, chars) 重复到达 (重试/重放) 只记一条 ⇒ 台账不膨胀、码不漂移。
///   5) 失败可见: 落盘异常只置 <see cref="FileErrors"/> 计数, 不抛 (链不能被台账拖死)。
/// </summary>
public static class LocalDecisionLedger
{
    /// <summary>挂载轴 (默认关; "1"/"true" 才开)。</summary>
    public const string MountEnvName = "AGENTFRAMEWORK_LOCAL_DECISION_MOUNT";

    /// <summary>台账落盘路径轴 (.jsonl 文件, 或以 / 结尾的目录 ⇒ 目录下 local-decisions.jsonl; 未设 ⇒ 只内存不落盘)。</summary>
    public const string PathEnvName = "AGENTFRAMEWORK_LOCAL_DECISION_LEDGER";

    public const string CodePrefix = "LCM-";
    public const int CodeHexLen = 12;

    /// <summary>挂载块首行前缀 —— 判据器用它机检「实发面有没有挂上」(常量, 非用户话术)。</summary>
    public const string MountHeader = "[本地决策台账-链自持]";

    private static readonly object Sync = new();
    private static readonly Dictionary<string, List<string>> Rows = new(StringComparer.Ordinal);

    /// <summary>累计落盘条数 (打点/自检用)。</summary>
    public static long Recorded { get; private set; }

    /// <summary>落盘成功次数。</summary>
    public static long FileWrites { get; private set; }

    /// <summary>落盘异常次数 (失败可见)。</summary>
    public static long FileErrors { get; private set; }

    public static bool EnvOn(string name)
    {
        var v = Environment.GetEnvironmentVariable(name);
        return v == "1" || string.Equals(v, "true", StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>挂载轴是否开 (默认关 ⇒ 与 R490..R494 逐字节同形)。</summary>
    public static bool IsEnabled() => EnvOn(MountEnvName);

    /// <summary>落盘路径 (未设 ⇒ null ⇒ 不落盘)。</summary>
    public static string? LedgerPath()
    {
        var v = Environment.GetEnvironmentVariable(PathEnvName);
        if (string.IsNullOrWhiteSpace(v)) return null;
        return v.EndsWith("/", StringComparison.Ordinal) || v.EndsWith("\\", StringComparison.Ordinal)
            ? Path.Combine(v, "local-decisions.jsonl")
            : v;
    }

    private static string Key(string? sessionId) => string.IsNullOrWhiteSpace(sessionId) ? "" : sessionId!;

    public static string Sha8(string s)
    {
        var h = SHA256.HashData(Encoding.UTF8.GetBytes(s));
        return Convert.ToHexString(h).ToLowerInvariant()[..8];
    }

    /// <summary>台账规范行 (判据器复算配方的最小单位): "turn|kind|chars"。</summary>
    public static string Canon(int turn, string kind, int chars) =>
        turn.ToString(CultureInfo.InvariantCulture) + "|" + kind + "|" + chars.ToString(CultureInfo.InvariantCulture);

    /// <summary>核对码: sha256(session + "|" + 规范行按序 "\n" 连接) 前 12 位小写十六进制, 前缀 LCM-。</summary>
    public static string CodeOf(string sessionId, IReadOnlyList<string> canonRows)
    {
        var sb = new StringBuilder();
        sb.Append(sessionId).Append('|');
        for (var i = 0; i < canonRows.Count; i++)
        {
            if (i > 0) sb.Append('\n');
            sb.Append(canonRows[i]);
        }
        var h = SHA256.HashData(Encoding.UTF8.GetBytes(sb.ToString()));
        return CodePrefix + Convert.ToHexString(h).ToLowerInvariant()[..CodeHexLen];
    }

    /// <summary>按会话复算核对码 (n = 前 n 条; n &lt;= 0 亦给码 —— 空台账也有码, 保证「挂载 ⇒ 一定有码」)。</summary>
    public static string CheckCode(string? sessionId, int n = -1)
    {
        var key = Key(sessionId);
        lock (Sync)
        {
            if (!Rows.TryGetValue(key, out var list)) return CodeOf(key, Array.Empty<string>());
            var take = n < 0 || n > list.Count ? list.Count : n;
            return CodeOf(key, take == list.Count ? list : list.GetRange(0, take));
        }
    }

    public static int Count(string? sessionId)
    {
        lock (Sync)
            return Rows.TryGetValue(Key(sessionId), out var list) ? list.Count : 0;
    }

    /// <summary>最近一次记入的规范行 (判据器/自检用; 未记入 ⇒ 空串)。</summary>
    public static string LastCanon(string? sessionId)
    {
        lock (Sync)
            return Rows.TryGetValue(Key(sessionId), out var list) && list.Count > 0 ? list[^1] : string.Empty;
    }

    /// <summary>
    /// 记一条本地决策 (闸判定 / 本地消化产出)。返回记账后的核对码。
    /// kind 取结构量 ("pass"/"skip"/...) —— 判据器只吃这些常量, 不引入任何用户话术特征。
    /// </summary>
    public static string Record(string? sessionId, int turn, string kind, string? basis)
    {
        var key = Key(sessionId);
        if (key.Length == 0) return string.Empty;
        var chars = basis is null ? 0 : basis.Length;
        var canon = Canon(turn, kind, chars);
        lock (Sync)
        {
            if (!Rows.TryGetValue(key, out var list))
            {
                list = new List<string>();
                Rows[key] = list;
            }
            // 幂等: 同 (turn, kind, chars) 重复到达只记一条
            var dup = false;
            foreach (var row in list)
                if (string.Equals(row, canon, StringComparison.Ordinal)) { dup = true; break; }
            if (!dup)
            {
                list.Add(canon);
                Recorded++;
            }
            var code = CodeOf(key, list);
            if (!dup) WriteLine(key, turn, kind, chars, list.Count, code, canon);
            return code;
        }
    }

    /// <summary>
    /// 渲染挂载块。挂载轴关 / 无会话 ⇒ <see cref="LedgerMount.Off"/> (零字节)。
    /// 文本形状固定 (逐行常量 + 数值), 尾部追加 ⇒ 前缀 system/context/history/user 逐字节不变。
    /// </summary>
    public static LedgerMount RenderMount(string? sessionId)
    {
        if (!IsEnabled()) return LedgerMount.Off;
        var key = Key(sessionId);
        if (key.Length == 0) return LedgerMount.Off;
        string code;
        int n;
        string last;
        lock (Sync)
        {
            if (!Rows.TryGetValue(key, out var list)) list = new List<string>();
            n = list.Count;
            code = CodeOf(key, list);
            last = n > 0 ? list[^1] : "(无)";
        }
        var sb = new StringBuilder();
        sb.Append(MountHeader).Append(" session=").Append(Sha8(key))
          .Append(" n=").Append(n.ToString(CultureInfo.InvariantCulture))
          .Append(" code=").Append(code).Append('\n');
        sb.Append("最近本地决策: ").Append(last).Append('\n');
        sb.Append("口径: 该码 = 本会话本地决策台账的确定性摘要, 只可能出现在链自己发往模型的请求里; 用户无法从别处得到。");
        return new LedgerMount(sb.ToString(), n, code, Sha8(key));
    }

    /// <summary>测试用: 清空内存态 (不动文件)。</summary>
    public static void ResetForTests()
    {
        lock (Sync)
        {
            Rows.Clear();
            Recorded = 0;
            FileWrites = 0;
            FileErrors = 0;
        }
    }

    private static void WriteLine(string sessionId, int turn, string kind, int chars, int n, string code, string canon)
    {
        var path = LedgerPath();
        if (path is null) return;
        try
        {
            var dir = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
            var ts = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds().ToString(CultureInfo.InvariantCulture);
            var line = new StringBuilder();
            line.Append("{\"schema\":\"local-decisions/1\",\"ts\":").Append(ts)
                .Append(",\"session\":\"").Append(Escape(sessionId))
                .Append("\",\"turn\":").Append(turn.ToString(CultureInfo.InvariantCulture))
                .Append(",\"kind\":\"").Append(Escape(kind))
                .Append("\",\"chars\":").Append(chars.ToString(CultureInfo.InvariantCulture))
                .Append(",\"n\":").Append(n.ToString(CultureInfo.InvariantCulture))
                .Append(",\"code\":\"").Append(code)
                .Append("\",\"canon\":\"").Append(Escape(canon))
                .Append("\"}\n");
            File.AppendAllText(path, line.ToString(), new UTF8Encoding(false));
            FileWrites++;
        }
        catch (Exception)
        {
            // 落盘失败不拖死链 (计数可见即可)
            FileErrors++;
        }
    }

    /// <summary>零反射手写转义 (STJ 反射在 AOT 被禁)。</summary>
    private static string Escape(string s)
    {
        var sb = new StringBuilder(s.Length + 8);
        foreach (var c in s)
        {
            switch (c)
            {
                case '"': sb.Append("\\\""); break;
                case '\\': sb.Append("\\\\"); break;
                case '\n': sb.Append("\\n"); break;
                case '\r': sb.Append("\\r"); break;
                case '\t': sb.Append("\\t"); break;
                default:
                    if (c < 0x20) sb.Append("\\u").Append(((int)c).ToString("x4", CultureInfo.InvariantCulture));
                    else sb.Append(c);
                    break;
            }
        }
        return sb.ToString();
    }
}
