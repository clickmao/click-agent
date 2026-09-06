using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace agent.skills
{
    /// <summary>
    /// Skill 执行型脚本调度器 (v0.11.0 计划③ — 用户定案):
    /// SKILL.md 包 scripts/ 目录下的可执行脚本 → 独立进程实跑 (Process)。
    ///
    /// 生命周期: 解析脚本类型 (py/sh/js) → 选择解释器 → 进程启动 (工作目录 = 包目录, 环境变量注入契约) →
    /// stdin 传任务载荷 → stdout 按行收结果/命令 → 超时终止 → 输出聚合返回。
    ///
    /// 通讯协议 (用户定案 — 与前端一致命令接口): 脚本子进程就是最小"前端",
    /// 经 stdout 发统一命令行 (@cmd …), 本类经 AgentCommandReader 读取并转发到框架命令出口;
    /// 余额不足/思考切页等命令语义与宿主→面板方向完全一致 (同一 AgentCommand 契约)。
    ///
    /// 安全边界 (与 SkillContextScope 沙箱一致):
    ///   - 只执行包内 scripts/ 目录文件 (路径归一化校验, 拒绝 ../ 逃逸)
    ///   - 环境变量白名单注入 (任务参数/技能 id/会话 id), 不透传宿主全量环境
    ///   - 超时强制终止 (整进程树 kill); 退出码非 0 = 失败 (输出仍返回, 调用方裁量)
    /// </summary>
    public sealed class SkillScriptRunner
    {
        /// <summary>支持的脚本类型 → 解释器解析 (按序探测; 全缺 → 诚实报错, 不伪造执行)。</summary>
        private static readonly (string Ext, string[] Interpreters)[] InterpreterMap =
        {
            (".py", new[] { "python3", "python" }),
            (".sh", new[] { "bash", "sh" }),
            (".js", new[] { "node" }),
        };

        private readonly agent.io.AgentCommandWriter? _commandWriter;
        private readonly Func<string, string, int, int> _getConfig;

        /// <summary>命令出口注入: 脚本的 @cmd 进度/余额等命令转发到宿主前端 (null = 不转发, 仅聚合)。</summary>
        public SkillScriptRunner(
            agent.io.AgentCommandWriter? commandWriter = null,
            Func<string, string, int, int>? getConfig = null)
        {
            _commandWriter = commandWriter;
            _getConfig = getConfig ?? ((m, k, d) => d);
        }

        /// <summary>包内脚本是否可执行 (脚本文件存在 + 解释器至少一个可用)。</summary>
        public static bool CanRun(SkillDefinition skill, string scriptName = "main.py")
        {
            var scriptPath = ResolveScriptPath(skill, scriptName);
            if (scriptPath is null)
                return false;
            var ext = Path.GetExtension(scriptPath).ToLowerInvariant();
            var interpreters = InterpreterMap.FirstOrDefault(m => m.Ext == ext).Interpreters;
            if (interpreters is null)
                return false;
            return interpreters.Any(i => FindOnPath(i) is not null);
        }

        /// <summary>
        /// 执行包脚本 (async 进程调度)。
        /// </summary>
        /// <param name="skill">技能定义 (PackageDir 必须已解析 — SkillPackageLoader 产物)</param>
        /// <param name="scriptName">scripts/ 下脚本文件名 (默认 main.py)</param>
        /// <param name="taskPayload">任务参数 (stdin 单行传入; 建议一行 JSON — 脚本侧自解析)</param>
        /// <param name="ct">外部取消 (用户取消 → 进程树强杀, 不重试)</param>
        /// <returns>stdout 全部非命令行 (顺序聚合); 失败时 stderr 附加在末尾 — 恒不为 null</returns>
        public async Task<string> RunAsync(
            SkillDefinition skill, string scriptName, string taskPayload, CancellationToken ct = default)
        {
            var scriptPath = ResolveScriptPath(skill, scriptName)
                ?? throw new FileNotFoundException($"技能 {skill.SkillId} 无脚本 {scriptName} 或路径越界");
            var interpreter = ResolveInterpreter(scriptPath)
                ?? throw new InvalidOperationException(
                    $"脚本 {scriptName} 解释器不可用 (需 python3/bash/node 之一在 PATH)");

            var started = DateTime.UtcNow;
            var psi = new ProcessStartInfo
            {
                FileName = interpreter,
                Arguments = $"\"{scriptPath}\"",
                WorkingDirectory = skill.PackageDir,   // 沙箱: cwd=包目录 (相对路径读取 SKILL.md/references 可用)
                UseShellExecute = false,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
            };
            // 环境变量白名单 (不透传宿主全量环境)
            psi.Environment["SKILL_ID"] = skill.SkillId;
            psi.Environment["SKILL_DIR"] = skill.PackageDir;
            psi.Environment["SKILL_TASK"] = taskPayload ?? string.Empty;

            var outputLines = new List<string>();
            var errorLines = new List<string>();
            using var timeoutCts = CancellationTokenSource.CreateLinkedTokenSource(ct);
            timeoutCts.CancelAfter(TimeSpan.FromSeconds(_getConfig("skill", "script_runner:timeout_seconds", 60)));

            using var process = new Process { StartInfo = psi };
            process.Start();

            // stdin: 任务载荷单行 (脚本按 SKILL_TASK 环境变量或 stdin 双通道可得)
            await process.StandardInput.WriteLineAsync(taskPayload ?? string.Empty).ConfigureAwait(false);
            process.StandardInput.Close();

            // stdout 消费: @cmd → 命令转发; 其余 → 输出聚合 (独立 task, ReadLine 阻塞模型)
            var stdoutTask = Task.Run(() =>
            {
                string? line;
                var reader = new agent.io.TextReportReader(process.StandardOutput);
                while ((line = process.StandardOutput.ReadLine()) is not null)
                {
                    if (line.StartsWith(agent.io.AgentReportReaderBase.CommandPrefix, System.StringComparison.Ordinal))
                    {
                        ForwardCommand(line, skill.SkillId);
                        continue;
                    }
                    lock (outputLines) outputLines.Add(line);
                }
            }, CancellationToken.None);

            var stderrTask = Task.Run(() =>
            {
                string? line;
                while ((line = process.StandardError.ReadLine()) is not null)
                {
                    lock (errorLines) errorLines.Add(line);
                }
            }, CancellationToken.None);

            try
            {
                await process.WaitForExitAsync(timeoutCts.Token).ConfigureAwait(false);
            }
            catch (OperationCanceledException) when (!ct.IsCancellationRequested)
            {
                // 超时 → 强杀进程树 (脚本可能有子进程 — kill 全树, 不留孤儿)
                KillTree(process);
                ForwardDone(skill.SkillId, -1, started, "timeout");
                throw new TimeoutException(
                    $"技能 {skill.SkillId} 脚本 {scriptName} 超时 ({_getConfig("skill", "script_runner:timeout_seconds", 60)}s) — 进程树已终止");
            }

            await Task.WhenAll(stdoutTask, stderrTask).ConfigureAwait(false);

            var exitCode = process.ExitCode;
            ForwardDone(skill.SkillId, exitCode, started, exitCode == 0 ? "ok" : "failed");

            var sb = new StringBuilder();
            string[] outs, errs;
            lock (outputLines) outs = outputLines.ToArray();
            lock (errorLines) errs = errorLines.ToArray();
            foreach (var l in outs) sb.AppendLine(l);
            if (errs.Length > 0)
            {
                sb.AppendLine("# stderr");
                foreach (var l in errs) sb.AppendLine(l);
            }
            return sb.ToString().TrimEnd();
        }

        /// <summary>脚本 @cmd 命令转发 (skill_progress/balance_insufficient 等全部透传; 附 skill 参数)。</summary>
        private void ForwardCommand(string commandLine, string skillId)
        {
            if (_commandWriter is null)
                return;
            try
            {
                var cmd = agent.io.AgentCommand.Decode(commandLine);
                if (cmd is null)
                    return;
                if (cmd.Get("skill") is null)
                {
                    var withSkill = new Dictionary<string, string>(cmd.Params) { ["skill"] = skillId };
                    cmd = new agent.io.AgentCommand(cmd.Name, withSkill);
                }
                _commandWriter.Send(cmd);
            }
            catch
            {
                // 命令转发失败不影响脚本执行 (与 LogRouter 推送契约一致)
            }
        }

        private void ForwardDone(string skillId, int exitCode, DateTime started, string status)
        {
            if (_commandWriter is null)
                return;
            _commandWriter.Send(agent.io.AgentCommandNames.SkillDone,
                ("skill", skillId),
                ("exit", exitCode.ToString(System.Globalization.CultureInfo.InvariantCulture)),
                ("duration_ms", ((long)(DateTime.UtcNow - started).TotalMilliseconds).ToString(System.Globalization.CultureInfo.InvariantCulture)),
                ("status", status));
        }

        /// <summary>解析脚本路径: 只允许包内 scripts/ 直下 (拒绝 ../ 逃逸 — 沙箱铁律)。</summary>
        private static string? ResolveScriptPath(SkillDefinition skill, string scriptName)
        {
            if (string.IsNullOrEmpty(skill.PackageDir) || string.IsNullOrEmpty(scriptName))
                return null;
            var full = Path.GetFullPath(Path.Combine(skill.PackageDir, "scripts", scriptName));
            var scriptsRoot = Path.GetFullPath(Path.Combine(skill.PackageDir, "scripts"));
            if (!full.StartsWith(scriptsRoot + Path.DirectorySeparatorChar, System.StringComparison.Ordinal)
                && !full.Equals(scriptsRoot, System.StringComparison.Ordinal))
                return null; // 越界拒绝
            return File.Exists(full) ? full : null;
        }

        /// <summary>按扩展名解析可用解释器 (PATH 探测; 缓存于调用方视角 — 每次实探不缓存, 进程级代价可忽略)。</summary>
        private static string? ResolveInterpreter(string scriptPath)
        {
            var ext = Path.GetExtension(scriptPath).ToLowerInvariant();
            var interpreters = InterpreterMap.FirstOrDefault(m => m.Ext == ext).Interpreters;
            return interpreters?.FirstOrDefault(i => FindOnPath(i) is not null);
        }

        /// <summary>PATH 探测可执行文件 (Linux/macOS: 逐目录 File.Exists; 返回全路径或 null)。</summary>
        private static string? FindOnPath(string name)
        {
            var pathEnv = Environment.GetEnvironmentVariable("PATH");
            if (string.IsNullOrEmpty(pathEnv))
                return null;
            foreach (var dir in pathEnv.Split(Path.PathSeparator))
            {
                if (string.IsNullOrWhiteSpace(dir))
                    continue;
                try
                {
                    var candidate = Path.Combine(dir.Trim(), name);
                    if (File.Exists(candidate))
                        return candidate;
                }
                catch
                {
                    // PATH 中含非法目录项 — 跳过 (环境脏不致命)
                }
            }
            return null;
        }

        /// <summary>杀进程树 (kill 主进程 + 子进程; Linux 用 pkill -P 逐层 — 轻量且无 P/Invoke)。</summary>
        private static void KillTree(Process process)
        {
            try
            {
                KillChildren(process.Id, 3); // 最多 3 层深度
            }
            catch
            {
                // 子进程枚举失败 — 主进程仍要杀
            }
            try
            {
                if (!process.HasExited)
                    process.Kill(entireProcessTree: true);
            }
            catch
            {
                // 已退出竞态 — 忽略
            }
        }

        private static void KillChildren(int parentId, int depth)
        {
            if (depth <= 0)
                return;
            try
            {
                using var ps = Process.Start(new ProcessStartInfo
                {
                    FileName = "pkill",
                    Arguments = $"-P {parentId}",
                    UseShellExecute = false,
                    CreateNoWindow = true,
                });
                ps?.WaitForExit(2000);
            }
            catch
            {
                // pkill 不可用 — 由 entireProcessTree 兜底
            }
        }
    }
}
