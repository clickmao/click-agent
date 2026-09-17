using System.Text;
using System.Text.Json;

namespace agent.frontendapi;


/// <summary>
/// menu 问询单题 (R375 · exp2 P0-3): 选项/数据类型/多选/默认值必须**进通道**,
/// 不得只拼进 Display 文本 (旧实现把菜单拼进 DisplayName, 前端无法渲染)。
/// </summary>
public sealed record AskQuestion(
    string Key,
    string Display,
    bool Required,
    bool Sensitive,
    string DataType,
    bool MultiSelect,
    IReadOnlyList<AskOption> Options,
    string? DefaultValue);
