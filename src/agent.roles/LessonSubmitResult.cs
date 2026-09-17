using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.roles;


/// <summary>提交结果: 明确区分"已入库/被拒绝/无 role 未记录", 不静默。</summary>
public sealed record LessonSubmitResult(bool Accepted, bool Recorded, string Id, int Count, long Version, string? Rejected);
