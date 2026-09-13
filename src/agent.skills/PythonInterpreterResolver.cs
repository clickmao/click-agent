using System;
using System.IO;
using System.Linq;

namespace agent.skills;

/// <summary>
/// 解析出的 python 解释器 + **来源标签** (T4 决策 v0.22.0 exp9 §11)。
/// 来源必须可对账: "产物跑过了" 这句话只有在知道"跑在哪个解释器上"时才成立。
/// </summary>
public sealed record PythonInterpreter(string Exe, string Source);

/// <summary>
/// python 解释器解析 (确定性顺序, 纯函数可注入 → 可单测)。
///
/// 顺序与理由:
///   ① 显式指定 (`AGENTFRAMEWORK_PY_EXE` / `AGENTFRAMEWORK_PYTHON` / 参数) —— 调用方说了算
///   ② 仓库固定记录 `tools/py/interpreter.txt` (scripts/fetch-py-tool.sh 写入) —— 本机可复现的"测试用 py tool"
///   ③ uv 托管解释器目录 (版本降序) —— 有固定版本但没有记录文件时的兜底
///   ④ PATH 上的 python3/python —— 最后兜底 (诚实标注 source=path: 不可复现)
///
/// 不变量: 返回的 Exe 一定存在 (fileExists 判定); 返回 null = 任何一层都没有 → 调用方按"不可用"处理, 不许瞎猜路径。
/// </summary>
public static class PythonInterpreterResolver
{
    /// <summary>显式指定解释器 (规范名)</summary>
    public const string ExeEnvName = "AGENTFRAMEWORK_PY_EXE";

    /// <summary>历史别名 (产物插件先于本解析器存在, 保留兼容)</summary>
    public const string LegacyExeEnvName = "AGENTFRAMEWORK_PYTHON";

    /// <summary>固定解释器记录文件 (相对仓库根; 本机产物, 不入库)</summary>
    public const string PinRecordRelativePath = "tools/py/interpreter.txt";

    /// <summary>记录文件里允许的解释器文件名 (按优先级)</summary>
    private static readonly string[] BinNames = ["python3", "python3.12", "python"];

    public static PythonInterpreter? Resolve(
        string? explicitExe = null,
        string? repoRoot = null,
        Func<string, bool>? fileExists = null,
        Func<string, bool>? dirExists = null,
        string? envValue = null,
        string? legacyEnvValue = null,
        string? managedRoot = null,
        Func<string?>? pathProbe = null)
    {
        var exists = fileExists ?? File.Exists;

        // ① 显式 (参数 / 规范 env / 历史 env)
        foreach (var candidate in new[]
                 {
                     explicitExe,
                     envValue ?? Environment.GetEnvironmentVariable(ExeEnvName),
                     legacyEnvValue ?? Environment.GetEnvironmentVariable(LegacyExeEnvName),
                 })
        {
            if (!string.IsNullOrWhiteSpace(candidate) && exists(candidate!))
                return new PythonInterpreter(candidate!, "explicit");
        }

        // ② 仓库固定记录 (测试用 py tool)
        var record = Path.Combine(repoRoot ?? Environment.CurrentDirectory, PinRecordRelativePath);
        if (exists(record))
        {
            try
            {
                var pinned = File.ReadAllText(record).Trim();
                if (pinned.Length > 0 && exists(pinned))
                    return new PythonInterpreter(pinned, "pinned");
            }
            catch (IOException)
            {
                // 记录文件读不了 → 继续往下兜底, 不因为一个记录文件让闸门失效
            }
        }

        // ③ uv 托管解释器 (版本降序 = 取最高; 记录文件缺失时的兜底)
        var root = managedRoot ?? Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
            ".local", "share", "uv", "python");
        if ((dirExists ?? Directory.Exists)(root))
        {
            foreach (var dir in Directory.GetDirectories(root).OrderByDescending(static d => d, StringComparer.Ordinal))
            {
                foreach (var bin in BinNames)
                {
                    var p = Path.Combine(dir, "bin", bin);
                    if (exists(p))
                        return new PythonInterpreter(p, "managed");
                }
            }
        }

        // ④ PATH 兜底
        var onPath = (pathProbe ?? (() => PythonScriptValidator.ResolvePython(null)))();
        return string.IsNullOrWhiteSpace(onPath) ? null : new PythonInterpreter(onPath!, "path");
    }

    /// <summary>
    /// 是否有"固定解释器" (pinned / managed / explicit) —— 真跑闸门默认值据此判定。
    /// T4 口径: **装了 py tool 才默认真跑**, 只有 PATH 兜底解释器时保持旧的"默认不跑",
    /// 免得把"某个恰好存在的 python"当成结论来源 (不可复现的通过比不通过更危险)。
    /// </summary>
    public static bool HasPinnedInterpreter(
        string? repoRoot = null,
        Func<string, bool>? fileExists = null,
        Func<string, bool>? dirExists = null)
        => Resolve(repoRoot: repoRoot, fileExists: fileExists, dirExists: dirExists)
           is { Source: "explicit" or "pinned" or "managed" };
}
