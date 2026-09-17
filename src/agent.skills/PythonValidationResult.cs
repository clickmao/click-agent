using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
using System.Threading.Tasks;

namespace agent.skills;


/// <summary>v0.17.2-b: py_compile 验证结果。</summary>
public sealed record PythonValidationResult(bool Valid, string Detail, int ExitCode);
