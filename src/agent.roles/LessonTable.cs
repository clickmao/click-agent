using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.roles;

/// <summary>
/// role 模块的教训表 (exp5 L1/L4; R369 用户钦定归属 role 模块)。
///
/// 语义: 去重 (按通用 Id 归并计数) / 版本号单调 (增量拉取游标) / 原子落盘 /
///       **通用化机检拒收** (语言/工具专名不得进入 Id/Pattern)。
/// 诚实边界: 只做"表格 + 读写面", 不做自动向量检索 (exp5 §6 排除项), 不迁移既有 6 个存储。
/// </summary>
public sealed class LessonTable
{
    public const string Schema = "role-lessons/v1";

    private readonly object _gate = new();
    private readonly Dictionary<string, LessonRecord> _byId = new(StringComparer.Ordinal);
    private long _version;

    public long Version { get { lock (_gate) return _version; } }
    public int Count { get { lock (_gate) return _byId.Count; } }

    /// <summary>FNV-1a 32bit (R365 算法; 跨进程/跨 locale 稳定, 禁用 string.GetHashCode)。</summary>
    public static string Fingerprint(string kind, string pattern)
    {
        var text = LessonGeneralization.Normalize(kind) + "\u0001" + LessonGeneralization.Normalize(pattern);
        unchecked
        {
            var hash = 0x811C9DC5u;
            foreach (var b in System.Text.Encoding.UTF8.GetBytes(text))
            {
                hash ^= b;
                hash *= 0x01000193u;
            }
            return hash.ToString("X8");
        }
    }

    /// <summary>
    /// 提交 (模块内唯一写入口)。同一通用 Pattern 第 N 次命中 → Count 累加, Instances 归并,
    /// Solution 非空即升级, Rev 前移到当前版本; 未通用化 → 拒收 (A8 负断言)。
    /// </summary>
    public LessonSubmitResult Submit(LessonRecord incoming, long nowUnix)
    {
        ArgumentNullException.ThrowIfNull(incoming);

        var violation = LessonGeneralization.Violation(incoming.Pattern)
                        ?? LessonGeneralization.Violation(incoming.Kind);
        if (violation is not null)
            return new LessonSubmitResult(false, false, incoming.Id, 0, Version, violation);

        if (string.IsNullOrWhiteSpace(incoming.Kind))
            return new LessonSubmitResult(false, false, incoming.Id, 0, Version, "Kind 不能为空 (Execution|Failure|Guardrail|Correction)");
        if (string.IsNullOrWhiteSpace(incoming.Pattern))
            return new LessonSubmitResult(false, false, incoming.Id, 0, Version, "Pattern 不能为空");
        if (incoming.Scope is not ("Project" or "Session"))
            return new LessonSubmitResult(false, false, incoming.Id, 0, Version, "Scope 只能是 Project|Session");

        var pattern = LessonGeneralization.Normalize(incoming.Pattern);
        var id = Fingerprint(incoming.Kind, pattern);

        lock (_gate)
        {
            _version++;
            var rev = checked((int)_version);
            var addCount = incoming.Count <= 0 ? 1 : incoming.Count;

            if (_byId.TryGetValue(id, out var exist))
            {
                var merged = Merge(exist, incoming, pattern, rev, addCount, nowUnix);
                _byId[id] = merged;
                return new LessonSubmitResult(true, true, id, merged.Count, _version, null);
            }

            var fresh = incoming with
            {
                Id = id,
                Pattern = pattern,
                Count = addCount,
                FirstSeenUnix = incoming.FirstSeenUnix > 0 ? incoming.FirstSeenUnix : nowUnix,
                LastSeenUnix = nowUnix,
                Rev = rev,
                Instances = Dedupe(incoming.Instances),
            };
            _byId[id] = fresh;
            return new LessonSubmitResult(true, true, id, fresh.Count, _version, null);
        }
    }

    private static LessonRecord Merge(LessonRecord exist, LessonRecord incoming, string pattern, int rev, int addCount, long nowUnix)
    {
        var instances = new List<LessonInstance>(exist.Instances);
        foreach (var inst in Dedupe(incoming.Instances))
        {
            var dup = false;
            foreach (var e in instances)
            {
                if (string.Equals(e.Lang, inst.Lang, StringComparison.OrdinalIgnoreCase) &&
                    string.Equals(e.Tool, inst.Tool, StringComparison.OrdinalIgnoreCase) &&
                    string.Equals(e.Evidence, inst.Evidence, StringComparison.Ordinal))
                {
                    dup = true;
                    break;
                }
            }
            if (!dup) instances.Add(inst);
        }

        var firstSeen = exist.FirstSeenUnix;
        if (incoming.FirstSeenUnix > 0 && (firstSeen == 0 || incoming.FirstSeenUnix < firstSeen)) firstSeen = incoming.FirstSeenUnix;

        return exist with
        {
            Pattern = pattern,
            Precondition = Coalesce(exist.Precondition, incoming.Precondition),
            Mechanism = Coalesce(exist.Mechanism, incoming.Mechanism),
            Verify = Coalesce(exist.Verify, incoming.Verify),
            Solution = Coalesce(exist.Solution, incoming.Solution),   // 非空即升级
            Count = exist.Count + addCount,
            FirstSeenUnix = firstSeen,
            LastSeenUnix = nowUnix > exist.LastSeenUnix ? nowUnix : exist.LastSeenUnix,
            Rev = rev,
            Instances = instances,
        };
    }

    private static string? Coalesce(string? a, string? b)
        => string.IsNullOrWhiteSpace(a) ? (string.IsNullOrWhiteSpace(b) ? a : b) : a;

    private static List<LessonInstance> Dedupe(List<LessonInstance>? src)
    {
        var list = new List<LessonInstance>();
        if (src is null) return list;
        foreach (var i in src)
        {
            if (i is null) continue;
            list.Add(i);
        }
        return list;
    }

    /// <summary>增量拉取: since&lt;=0 → 全量; 否则只返回 Rev &gt; since 的记录。</summary>
    public IReadOnlyList<LessonRecord> Query(long since = 0, string? kind = null, string? scope = null, int limit = 100)
    {
        var list = new List<LessonRecord>();
        lock (_gate)
        {
            foreach (var r in _byId.Values)
            {
                if (since > 0 && r.Rev <= since) continue;
                if (kind is not null && !string.Equals(r.Kind, kind, StringComparison.OrdinalIgnoreCase)) continue;
                if (scope is not null && !string.Equals(r.Scope, scope, StringComparison.OrdinalIgnoreCase)) continue;
                list.Add(r);
            }
        }
        list.Sort(static (a, b) =>
        {
            var c = b.LastSeenUnix.CompareTo(a.LastSeenUnix);
            return c != 0 ? c : string.CompareOrdinal(a.Id, b.Id);
        });
        return limit > 0 && list.Count > limit ? list.GetRange(0, limit) : list;
    }

    public LessonRecord? Detail(string id)
    {
        if (string.IsNullOrWhiteSpace(id)) return null;
        lock (_gate) return _byId.TryGetValue(id, out var r) ? r : null;
    }

    public IReadOnlyList<LessonRecord> All() => Query(0, null, null, 0);

    /// <summary>原子落盘 (tmp + rename; 同 .rbin 先例)。返回字节数, 0 = 空表未写。</summary>
    public int Save(string path)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);
        var dir = Path.GetDirectoryName(Path.GetFullPath(path));
        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);

        LessonSnapshot snap;
        lock (_gate)
        {
            snap = new LessonSnapshot(Schema, _version, QueryLocked());
        }

        var json = JsonSerializer.Serialize(snap, LessonJsonContext.Default.LessonSnapshot);
        var tmp = path + ".tmp";
        File.WriteAllText(tmp, json);
        File.Move(tmp, path, overwrite: true);
        return json.Length;
    }

    private List<LessonRecord> QueryLocked()
    {
        var list = new List<LessonRecord>(_byId.Values);
        list.Sort(static (a, b) => string.CompareOrdinal(a.Id, b.Id));
        return list;
    }

    public static LessonTable Load(string path)
    {
        var table = new LessonTable();
        if (string.IsNullOrWhiteSpace(path) || !File.Exists(path)) return table;

        var json = File.ReadAllText(path);
        if (string.IsNullOrWhiteSpace(json)) return table;
        var snap = JsonSerializer.Deserialize(json, LessonJsonContext.Default.LessonSnapshot);
        if (snap?.Lessons is null) return table;

        lock (table._gate)
        {
            table._version = snap.Version;
            foreach (var r in snap.Lessons)
            {
                if (r is null || string.IsNullOrWhiteSpace(r.Id)) continue;
                table._byId[r.Id] = r;
            }
        }
        return table;
    }
}
