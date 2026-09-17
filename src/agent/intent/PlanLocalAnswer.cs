using System.Text;
using System.Linq;

namespace agent.intent;


/// <summary>
/// 本地子请求结论渲染 (v0.22.0 exp9 D4b)。
///
/// 谁的用户可见结论被扣减了, 谁就必须出现在回复里 —— 否则等于"框架把用户的问题删了还不回答"。
/// 渲染是**确定性字符串拼接** (零反射, AOT 安全): 成功给结论, 失败给真实原因 (不静默)。
/// </summary>
public static class PlanLocalAnswer
{
    internal const int MaxRequestChars = 60;
    internal const int MaxNoteChars = 200;

    public static string Render(IReadOnlyList<LocalAnswerItem> items)
    {
        if (items is null || items.Count == 0)
            return string.Empty;

        var sb = new StringBuilder();
        foreach (var it in items)
        {
            if (string.IsNullOrWhiteSpace(it.Request))
                continue;
            if (sb.Length == 0)
                sb.Append("\n\n[框架本地执行 (零 token)]");
            sb.Append("\n- ").Append(Clip(it.Request, MaxRequestChars)).Append(" ⇒ ");
            if (it.Ok && !string.IsNullOrWhiteSpace(it.Note))
                sb.Append(Clip(it.Note!.Replace('\n', ' ').Trim(), MaxNoteChars));
            else if (!it.Ok)
                sb.Append("本地执行未成功: ").Append(Clip((it.Note ?? "无错误信息").Replace('\n', ' ').Trim(), MaxNoteChars));
            else
                sb.Append("(本地执行完成, 无结论文本)");
        }

        return sb.ToString();
    }

    private static string Clip(string s, int n) => s.Length <= n ? s : s[..n] + "…";
}
