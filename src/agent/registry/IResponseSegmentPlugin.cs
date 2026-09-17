using System.Text.RegularExpressions;

namespace agent.registry;


/// <summary>
/// 区段插件接口 (v7.11): 返回内容后处理不写死 — 按区段类型路由到注册的插件。
/// 插件可消费标记 (如 UI 高亮 html 段) 或触发服务 (代码段→审查服务)。
/// </summary>
public interface IResponseSegmentPlugin
{
    /// <summary>插件名 (DI 唯一, 审计用)</summary>
    string Name { get; }

    /// <summary>声明消费的区段类型</summary>
    IReadOnlySet<SegmentKind> Consumes { get; }

    /// <summary>
    /// 处理一个区段。返回值进最终输出 (恒等返回即可透传)。
    /// 异步签名: 插件内部可调外部服务 (审查/渲染), 由宿主控制超时。
    /// </summary>
    Task<string> HandleAsync(ResponseSegment segment, CancellationToken ct = default);
}
