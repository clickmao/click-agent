using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using agent.skills;

namespace agent.registry;


/// <summary>
/// Python 产物报告 (审计/前端/教训复用; 单行可序列化)。
/// </summary>
public sealed record PythonArtifactReport(
    string Path,
    string Language,
    int Bytes,
    string Sha256Short,
    bool CompileValid,
    int ExitCode,
    string Detail,
    long AtUnixMs,
    bool Ran = false,          // L5: 是否真的执行过 (运行级验证)
    int RunExitCode = -1,
    long RunElapsedMs = 0,
    bool RunTimedOut = false,
    // R374: 校验/运行输出摘要 (尾部保留) — 让"失败原因"成为可观测事实, 而非只有一个 exit 码。
    string OutputExcerpt = "");
