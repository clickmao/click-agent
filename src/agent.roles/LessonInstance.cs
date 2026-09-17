using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.roles;


/// <summary>
/// 教训实例 (唯一允许出现语言/工具专名的地方; exp5 §3.2 R369 口径)。
/// </summary>
public sealed record LessonInstance(string Lang, string Tool, string Evidence, long SeenAtUnix);
