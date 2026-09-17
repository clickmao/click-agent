using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;

namespace agent.skills;


/// <summary>STJ source-gen context (AOT: 无反射序列化)。</summary>
[JsonSerializable(typeof(ScriptTaskPayload))]
internal partial class ScriptPluginJsonCtx : JsonSerializerContext;
