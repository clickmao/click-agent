using System.Text.Json;
using agent.intent;
using Xunit;

namespace agent.tests;

/// <summary>
/// v7.15 开发计划防漂移测试 (PlanNode.DocRef 落地验证):
/// docs/plans/v715_dev_plan.taskplan.json 中的计划节点必须与其 DocRef 指向的文档同在,
/// 防止文档被删/改名后计划节点变成无锚孤儿。
/// </summary>
public class DevPlanDocRefTests
{
    private static readonly string RepoRoot = FindRepoRoot();

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "agent.sln")))
            dir = dir.Parent;
        return dir?.FullName ?? ".";
    }

    [Fact]
    public void DevPlan_Json_Exists_And_Valid()
    {
        var path = Path.Combine(RepoRoot, "docs", "plans", "v715_dev_plan.taskplan.json");
        Assert.True(File.Exists(path), $"开发计划文件缺失: {path}");
        var doc = JsonDocument.Parse(File.ReadAllText(path));
        Assert.Equal("devplan715", doc.RootElement.GetProperty("PlanId").GetString());
        Assert.True(doc.RootElement.GetProperty("Nodes").GetArrayLength() >= 4,
            "开发计划至少应含 4 个模块节点 (并发化/重试/模型队列/隔离任务)");
    }

    [Fact]
    public void DevPlan_EveryNode_HasValidDocRef()
    {
        var path = Path.Combine(RepoRoot, "docs", "plans", "v715_dev_plan.taskplan.json");
        using var doc = JsonDocument.Parse(File.ReadAllText(path));
        foreach (var node in doc.RootElement.GetProperty("Nodes").EnumerateArray())
        {
            var docRef = node.GetProperty("DocRef").GetString();
            Assert.False(string.IsNullOrWhiteSpace(docRef),
                $"节点 {node.GetProperty("Id").GetString()} 缺 DocRef — 开发计划任务必须标注文档");
            var abs = Path.Combine(RepoRoot, docRef!.Replace('/', Path.DirectorySeparatorChar));
            Assert.True(File.Exists(abs), $"节点 {node.GetProperty("Id").GetString()} 的 DocRef 指向不存在的文档: {docRef}");
            // 文档必须含状态行 (待开发/已完成) — 防空壳文档
            var content = File.ReadAllText(abs);
            Assert.True(content.Contains("状态:"), $"{docRef} 缺少「状态:」行");
        }
    }

    [Fact]
    public void PlanNode_DocRef_Serializes_InTaskPlanJson()
    {
        // DocRef 参与 TaskPlan source-gen JSON 往返 (AOT 面)
        var node = new PlanNode { Id = "t1", Text = "测试任务", DocRef = "docs/plan_x.md" };
        var json = JsonSerializer.Serialize(node, TaskPlanJsonContext.Default.PlanNode);
        Assert.Contains("DocRef", json);

        var back = JsonSerializer.Deserialize(json, TaskPlanJsonContext.Default.PlanNode);
        Assert.NotNull(back);
        Assert.Equal("docs/plan_x.md", back!.DocRef);
    }
}
