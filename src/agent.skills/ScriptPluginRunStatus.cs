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


/// <summary>v0.17.2-b: 脚本插件执行结果状态。</summary>
public enum ScriptPluginRunStatus
{
    Completed,        // done 事件收到 (权威终态)
    Failed,           // error 事件 / 超时 / 协议违例 (无 done/error)
    RejectedInvalid,  // py_compile 验证拒绝 (未执行)
}
