namespace agent.output;


/// <summary>
/// 底层输出模式 (v7.13, 用户钦定): LLM 返回经内部管道处理后有两种呈现模式。
/// 内部管道只流转 AgentOutputMessage (结构化底层格式), 呈现层按 Mode 渲染。
/// </summary>
public enum OutputMode
{
    /// <summary>
    /// Markdown 模式: 全部人性化可读格式 — 标题/列表/粗体/代码围栏/表格,
    /// 文件日志与富界面 (支持 markdown 的通道) 用此模式。
    /// </summary>
    Markdown,

    /// <summary>
    /// 纯文本模式: 去格式化的直接文本 (无围栏/标题符/表格线),
    /// 控制台窄屏/管道/纯终端会话用此模式 — 控制台仍会着色, 只是排版降为平铺。
    /// </summary>
    PlainText,
}
