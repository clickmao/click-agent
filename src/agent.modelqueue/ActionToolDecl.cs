using System;

namespace agent.modelqueue;


/// <summary>声明面: 工具名白名单 + Chat 形态工具 JSON (OpenAI function-calling)。
/// 单一事实源 (claude-fable-5.1 动因6): JSON 由 <see cref="ActionToolSpec.ChatToolsJson"/> 派生,
/// 此处不再复制字面量; 名称白名单与执行面同源 (R511); 顺序 = 字母序 (可 diff、可稳定缓存)。</summary>
public static class ActionToolDecl
{
    public const string DeleteFile = "delete_file";
    public const string ListDir = "list_dir";
    public const string ReadFile = "read_file";
    public const string RunCommand = "run_command";
    public const string WriteFile = "write_file";

    /// <summary>工具名白名单 (字母序; 与 ToolsJson 顺序逐项一致, 由 Fable51AlignmentTests 锁死)。</summary>
    public static readonly string[] Names = { DeleteFile, ListDir, ReadFile, RunCommand, WriteFile };

    /// <summary>Chat 形态声明 JSON (单源派生: 由 <see cref="ActionToolSpec.ChatToolsJson"/> 初始化,
    /// 不复制字面量)。字段形态保持不变 (公共 API 面基线逐行相等)。</summary>
    public static readonly string ToolsJson = ActionToolSpec.ChatToolsJson;

    /// <summary>名称是否在声明面白名单内 (执行面准入判定; 与 <see cref="Names"/> 同源)。</summary>
    public static bool IsDeclared(string name) => Array.IndexOf(Names, name) >= 0;
}
