using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using agent.config;
using agent.registry;
using agent.skills;

namespace agent.intent;


/// <summary>远程生成窗口 (主链事实: 调用方在模型调用前后各取一次单调时刻)</summary>
public readonly record struct RemoteWindow(long StartedUs, long ReadyUs)
{
    public long WaitUs => Math.Max(0, ReadyUs - StartedUs);

    public long WaitMs => WaitUs / 1000;
}
