using System.Text;
using System.Text.Json;

namespace agent.frontendapi;


/// <summary>ask.reply / ask.cancel 的解析结果 (answers=null 且 Cancel=true 表示取消)。</summary>
public sealed record AskReply(string AskId, Dictionary<string, string>? Answers, bool Cancel);
