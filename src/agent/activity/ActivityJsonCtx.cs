using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;

namespace agent.activity;


/// <summary>STJ source-gen context (AOT)。</summary>
[JsonSerializable(typeof(ActivityEntry))]
internal partial class ActivityJsonCtx : JsonSerializerContext;
