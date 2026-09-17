using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace agent.roles;


[JsonSerializable(typeof(LessonSnapshot))]
[JsonSerializable(typeof(LessonRecord))]
[JsonSerializable(typeof(List<LessonRecord>))]
internal sealed partial class LessonJsonContext : JsonSerializerContext;
