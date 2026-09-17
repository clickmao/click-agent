using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace agent.modelqueue;

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
///   1) R496 **不可复算真值** (R495 教训): 核对码 = HMAC-SHA256(进程密钥, session + "|" + 台账规范行按序 \n 连接)
///      的前 12 位小写十六进制, 前缀 "LCM-"。进程密钥 = 启动时 CSPRNG 取 32 字节, **只存内存**, 从不写文件/环境/挂载文本。
///      ⇒ 落盘面 (ledger) + 打点面 (telemetry) + 任何可读文件都**推不出**真值; 同字节输入在不同进程**不同码**。
///      (R495 的旧配方 sha256(session|canon) 是公开可复算的 ⇒ 「关轴不可知」被证伪; 本轮把配方换成密钥化的
///       HMAC, 并把落盘/打点字段从 `code` 换成**指纹** `code8` / `key_id`, 使「真值只在内存 + 只在线上」成立。)
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

    /// <summary>
    /// R496 进程密钥 (32 字节 CSPRNG, 只在内存): 真值的唯一不可读来源。
    /// 反例防护: 不得来自环境变量 (会落进 runner 的 flags/日志 ⇒ 又变成可读配方)。
    /// </summary>
    private static byte[] _key = RandomNumberGenerator.GetBytes(32);

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

    /// <summary>R496: 真值配方主体 (判据器**不可复算**的最小说明单位): session + "|" + 规范行按序 "\n" 连接。</summary>
    public static string Compose(string sessionId, IReadOnlyList<string> canonRows)
    {
        var sb = new StringBuilder();
        sb.Append(sessionId).Append('|');
        for (var i = 0; i < canonRows.Count; i++)
        {
            if (i > 0) sb.Append('\n');
            sb.Append(canonRows[i]);
        }
        return sb.ToString();
    }

    /// <summary>核对码: HMAC-SHA256(进程密钥, 配方主体) 前 12 位小写十六进制, 前缀 LCM-。</summary>
    public static string CodeOf(string sessionId, IReadOnlyList<string> canonRows)
        => CodeOfWithKey(KeySnapshot(), sessionId, canonRows);

    /// <summary>指定密钥的复算入口 (测试/自检用; 生产路径无密钥来源 ⇒ 不可复算)。</summary>
    internal static string CodeOfWithKey(byte[] key, string sessionId, IReadOnlyList<string> canonRows)
    {
        using var h = new HMACSHA256(key);
        var d = h.ComputeHash(Encoding.UTF8.GetBytes(Compose(sessionId, canonRows)));
        return CodePrefix + Convert.ToHexString(d).ToLowerInvariant()[..CodeHexLen];
    }

    private static byte[] KeySnapshot()
    {
        lock (Sync) return _key;
    }

    /// <summary>测试用: 安装固定密钥 (生产路径从不调用 —— 生产密钥只能来自进程内 CSPRNG)。</summary>
    public static void SetKeyForTests(byte[] key)
    {
        lock (Sync) _key = key.Length == 0 ? RandomNumberGenerator.GetBytes(32) : key;
    }

    /// <summary>密钥指纹 (非密钥本身): 判据器可核「同进程内码同源」而**无法回推密钥/真值**。</summary>
    public static string KeyId() => Sha8(Convert.ToHexString(KeySnapshot()).ToLowerInvariant());

    /// <summary>码指纹 (非码本身): 落盘面/打点面只存它 ⇒ 由实发面可核一致, 但**推不回真值**。</summary>
    public static string Code8(string code) => Sha8(code);

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
        // R496 (候选①, R495 反向诊断): 旧口径「用户无法从别处得到」被挂载臂读成**金丝雀** ⇒
        // 问核对码时防御性拒答 (治疗向判据全红)。新口径 = **显式授权复述**: 该码是链自持摘要, 不是密钥,
        // 用户问到就照原样复述 —— 把「有权限说」这件事写进挂载文本本身。
        sb.Append("口径: 该码 = 本会话本地决策台账摘要 (链自持的核对码, 非密钥、非保密标记); ");
        sb.Append("用户若问到核对码或台账条数, 就按上面这行**原样直接复述**, 不要拒答、不要改写、不要额外推测。");
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
                // R496: 落盘面**不再含真值** —— 只留指纹 (code8 = sha8(code), key_id = sha8(keyhex))。
                // R495 的 `"code":"LCM-…"` 是「读文件即得真值」的通道 (B 臂 34 次调用里 25/26 两条正是照抄它);
                // 换成指纹后: 判据器仍可核「实发码 ↔ 落盘行 ↔ 打点面」三面一致, 但**无法回推码**。
                .Append(",\"code8\":\"").Append(Code8(code))
                .Append("\",\"key_id\":\"").Append(KeyId())
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
