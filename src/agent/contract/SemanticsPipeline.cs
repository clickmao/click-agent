using System.Collections.Generic;
using System.IO;

namespace agent.contract;

/// <summary>
/// R1 管道准入闸（抽自 Claude-Fable-5.1 动因②「安全在每个能力边界再断言」）。
/// 闸序固定、fail-closed：硬闸 → 语义完整 → 非执行类 → 计划合法性 → 可执行。
/// 判定写在 Stage/Rc 上，不靠 grep 锚。
/// </summary>
public static class SemanticsPipeline
{
    private static readonly string[] Banned =
    {
        "sudo", "rm -rf /", "curl ", "wget ", "pip install", "apt-get", "git push",
        "chmod 777", "mkfs", "dd if=",
    };

    public static PipelineOutcome Gate(Semantics sem, string sandboxRoot)
    {
        if (sem.Refusal is not null)
        {
            return new PipelineOutcome(3, "hard_gate", "模型判定应拒答: " + sem.Refusal.Reason, true);
        }
        if (sem.MissingSlots.Count > 0 || sem.Ambiguities.Count > 0)
        {
            return new PipelineOutcome(2, "semantics_incomplete", "缺信息/有歧义 ⇒ 停下澄清", true);
        }
        if (sem.Intent != "code_task" && sem.Intent != "ops_task")
        {
            return new PipelineOutcome(0, "non_exec", "intent=" + sem.Intent + " 无需执行（信息类）", false);
        }

        var seen = new List<string>();
        foreach (var st in sem.Plan)
        {
            if (st.Tool != "write_file" && st.Tool != "run" && st.Tool != "none")
            {
                return new PipelineOutcome(4, "plan", "非白名单工具: " + st.Tool, true);
            }
            foreach (var d in st.DependsOn)
            {
                if (!seen.Contains(d))
                {
                    return new PipelineOutcome(4, "plan", "depends_on 引用不存在/后置: " + d + " (step " + st.Id + ")", true);
                }
            }
            if (st.Tool == "write_file")
            {
                var scope = ScopeError(st.Path, sandboxRoot);
                if (scope is not null)
                {
                    return new PipelineOutcome(4, "scope", scope, true);
                }
            }
            if (st.Tool == "run")
            {
                foreach (var b in Banned)
                {
                    if (st.Cmd.Contains(b, System.StringComparison.Ordinal))
                    {
                        return new PipelineOutcome(4, "plan", "命令含禁用片段 " + b, true);
                    }
                }
            }
            seen.Add(st.Id);
        }
        return new PipelineOutcome(0, "ready", "计划合法，可执行", false);
    }

    private static string? ScopeError(string path, string sandboxRoot)
    {
        if (string.IsNullOrEmpty(path))
        {
            return "空路径";
        }
        if (Path.IsPathRooted(path))
        {
            return "拒绝绝对路径: " + path;
        }
        var full = Path.GetFullPath(Path.Combine(sandboxRoot, path));
        var root = Path.GetFullPath(sandboxRoot);
        var sep = Path.DirectorySeparatorChar;
        if (full != root && !full.StartsWith(root + sep, System.StringComparison.Ordinal))
        {
            return "路径逃出沙箱: " + path;
        }
        return null;
    }
}
