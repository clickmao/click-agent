namespace agent.frontendapi;


/// <summary>ask.reply / ask.cancel 的消费面 (由 FrontendPromptService 实现; 路由层只依赖该接口)。</summary>
public interface IAskReplySink
{
    AskReplyOutcome Complete(string askId, Dictionary<string, string>? answers);
}
