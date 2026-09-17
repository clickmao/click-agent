using System.Text;
using System.Linq;

namespace agent.intent;


/// <summary>一条本地子请求的结论 (请求原文片段 + 本地执行结论 + 是否成功)</summary>
public sealed record LocalAnswerItem(string Request, string? Note, bool Ok);
