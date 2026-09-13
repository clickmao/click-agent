using System;
using System.Collections.Generic;
using System.IO;

namespace agent.roles;

/// <summary>
/// role 模块的教训读写门面 (exp5 §3.3; R369 用户钦定: 表本体 + 提交 API + 读取面全部归 role 模块)。
///
/// 落盘: `{dataDir}/roles/{roleId}.lessons.json` (与 failureClusters.json / {id}.growth.json 同域)。
/// 无 role (`ActiveRole=null`): 按 exp5 §8-7 推荐口径 ① —— **不落盘、不注入**, 结果显式回报 (不静默)。
/// 宿主/CLI/前端只依赖本类, 不直连教训文件。
/// </summary>
public sealed class RoleLessons
{
    private readonly object _gate = new();
    private readonly string? _roleId;
    private LessonTable? _table;

    public RoleLessons(string? roleId, string dataDir = "data")
    {
        DataDir = dataDir;
        _roleId = string.IsNullOrWhiteSpace(roleId) ? null : roleId.Trim();
        StoragePath = _roleId is null ? null : Path.Combine(dataDir, "roles", _roleId + ".lessons.json");
    }

    public string DataDir { get; }

    /// <summary>null = 无 role (教训表在该会话内完全不可用)。</summary>
    public string? StoragePath { get; }

    public bool Enabled => StoragePath is not null;

    private LessonTable Table
    {
        get
        {
            lock (_gate)
            {
                return _table ??= LessonTable.Load(StoragePath!);
            }
        }
    }

    public long Version => Enabled ? Table.Version : 0;
    public int Count => Enabled ? Table.Count : 0;

    /// <summary>唯一写入口: 去重/计数/通用化机检在表内完成; 接受即原子落盘。</summary>
    public LessonSubmitResult Submit(LessonRecord record, long nowUnix)
    {
        ArgumentNullException.ThrowIfNull(record);
        if (!Enabled)
            return new LessonSubmitResult(false, false, record.Id, 0, 0,
                "无 role (ActiveRole=null): 教训不落盘不注入 (exp5 §8-7 口径①)");

        var result = Table.Submit(record, nowUnix);
        if (result.Accepted) Table.Save(StoragePath!);
        return result;
    }

    public IReadOnlyList<LessonRecord> Query(long since = 0, string? kind = null, string? scope = null, int limit = 100)
        => Enabled ? Table.Query(since, kind, scope, limit) : Array.Empty<LessonRecord>();

    public LessonRecord? Detail(string id) => Enabled ? Table.Detail(id) : null;
}
