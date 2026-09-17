namespace agent.llamacpp;


/// <summary>会话轮次（本地 prompt 渲染的输入单位；裸 prompt 不再进入生成热路径）。</summary>
public sealed record ChatTurn(string Role, string Content);
