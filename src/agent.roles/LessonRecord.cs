using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.roles;


/// <summary>
/// 统一教训记录 (exp5 §3.2)。
/// `Id` = FNV-1a 32(通用化后的 Kind + '\u0001' + Pattern) —— 语言/工具名不得进入指纹输入。
/// `Rev` = 该记录最后一次变更时的表版本号 (增量游标, A3)。
/// </summary>
public sealed record LessonRecord(
    string Id,
    string Kind,
    string Pattern,
    string? Precondition,
    string? Mechanism,
    string? Verify,
    int Count,
    long FirstSeenUnix,
    long LastSeenUnix,
    string? Solution,
    string Source,
    string Scope,
    int Rev,
    List<LessonInstance> Instances);
