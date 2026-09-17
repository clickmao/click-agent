using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace agent.skills;


/// <summary>运行级验证结果 (结构化, 可序列化/可台账化)。</summary>
public sealed record PythonRunResult(
    bool Ran,
    int ExitCode,
    string StdOut,
    string StdErr,
    long ElapsedMs,
    bool TimedOut,
    bool OutputTruncated,
    string Detail,
    string Interpreter = "");
