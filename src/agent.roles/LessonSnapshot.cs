using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.roles;


/// <summary>落盘封装 (STJ 源生成; AOT 安全)。</summary>
public sealed record LessonSnapshot(string Schema, long Version, List<LessonRecord> Lessons);
