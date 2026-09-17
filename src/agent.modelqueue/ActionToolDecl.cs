using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.Json;

namespace agent.modelqueue;


/// <summary>声明面: 工具 JSON (OpenAI function-calling 形态, 手写常量 —— 无反射、无生成)。</summary>
public static class ActionToolDecl
{
    public const string ListDir = "list_dir";
    public const string ReadFile = "read_file";
    public const string WriteFile = "write_file";
    public const string RunCommand = "run_command";

    /// <summary>R511: 删除类工具 (破坏性 ⇒ 执行面必须过人工审批门; 无审批通道 ⇒ fail-closed 拒绝)。</summary>
    public const string DeleteFile = "delete_file";

    /// <summary>工具名白名单 (声明面与执行面同源; 执行面拒绝表外名称)。</summary>
    public static readonly string[] Names = { ListDir, ReadFile, WriteFile, RunCommand, DeleteFile };

    public static bool IsDeclared(string name)
    {
        foreach (var n in Names)
            if (string.Equals(n, name, StringComparison.Ordinal)) return true;
        return false;
    }

    /// <summary>
    /// 声明文本。字段稳定 ⇒ 每次调用逐字节相同 (缓存前缀不动, R377 红线 ≥97%)。
    /// </summary>
    public static readonly string ToolsJson =
        """
        [{"type":"function","function":{"name":"list_dir","description":"列出工作区目录条目(相对路径/大小/类型)","parameters":{"type":"object","properties":{"path":{"type":"string","description":"相对工作区根的目录路径, 省略=根"}},"required":[]}}},
        {"type":"function","function":{"name":"read_file","description":"读取工作区文本文件","parameters":{"type":"object","properties":{"path":{"type":"string","description":"相对工作区根的文件路径"},"max_bytes":{"type":"integer","description":"最大字节数(默认8192)"}},"required":["path"]}}},
        {"type":"function","function":{"name":"write_file","description":"写入/覆盖工作区文本文件","parameters":{"type":"object","properties":{"path":{"type":"string","description":"相对工作区根的文件路径"},"content":{"type":"string","description":"文件内容"}},"required":["path","content"]}}},
        {"type":"function","function":{"name":"run_command","description":"在工作区根执行一条命令并返回 stdout/stderr/退出码","parameters":{"type":"object","properties":{"command":{"type":"string","description":"命令原文"},"timeout_ms":{"type":"integer","description":"超时毫秒(默认120000, 上限600000)"}},"required":["command"]}}},
        {"type":"function","function":{"name":"delete_file","description":"删除工作区内的文件或目录(需人工审批; 未接入审批通道时一律拒绝)","parameters":{"type":"object","properties":{"path":{"type":"string","description":"相对工作区根的文件/目录路径"}},"required":["path"]}}}]
        """;
}
