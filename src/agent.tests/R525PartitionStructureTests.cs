using System.Text.RegularExpressions;
using agent.context;
using Xunit;

namespace agent.tests;

/// <summary>
/// R525 分区常量前缀结构锁 —— 依据 (用户 2026-09-17 令):
///   「根据它的提示词 [外部真值 Fable 5.1 泄露 system: 274,608 字符 / 270 个顶级段 / 逐字节恒定前缀] 重构我们当前 agent 系统」。
/// 落点: `SessionBaseline` 由"九个中文数字段"改为**固定顺序的 §1..§11 命名常量分区** (每段一个主题),
///      段头形如 `## §N 名称`, 机检可枚举、可排序、可跨窗口比对。
/// 四条锁:
///   ① 段头序列恒为 §1..§11 升序且各出现一次 (顺序漂移 = 前缀字节漂移);
///   ② 段集合跨构建/跨工作区恒定 (只允许 §8 工作区快照的内容随根变, 段头不变);
///   ③ 旧基线全部纪律零丢失 (逐条关键句仍在);
///   ④ 按运行变化的材料 (遥测/工作区文件 dump) 不得出现在常量前缀内。
/// </summary>
public sealed class R525PartitionStructureTests
{
    private static readonly string[] ExpectedSections =
    {
        "§1 身份与目标",
        "§2 安全与诚实底线 (违反即返工)",
        "§3 记忆与召回规则 (常量规则; 材料一律只追加尾部)",
        "§4 行为与输出纪律",
        "§5 工程与执行纪律 (违反即返工)",
        "§6 工具协议",
        "§7 技能菜单与按需加载",
        "§8 环境与工作区 (会话首轮快照)",
        "§9 常见失败模式与自检 (历史实证, 逐条自查)",
        "§10 汇报格式 (约定)",
        "§11 关键模块地图 (本仓库实况, 便于定位改动点)",
    };

    private static string RepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !Directory.Exists(Path.Combine(dir.FullName, "src"))) dir = dir.Parent;
        Assert.NotNull(dir);
        return dir!.FullName;
    }

    private static List<string> Headers(string baseline) =>
        Regex.Matches(baseline, @"(?m)^## §(\d+) (.+)$")
            .Select(m => "§" + m.Groups[1].Value + " " + m.Groups[2].Value.Trim())
            .ToList();

    private static string Baseline(string root, bool formal = false)
    {
        SessionBaseline.ResetForTests();
        return SessionBaseline.Build(root, formal);
    }

    [Fact]
    public void 分区段头序列为1到11升序各一次()
    {
        var headers = Headers(Baseline(RepoRoot()));
        Assert.Equal(ExpectedSections.Length, headers.Count);
        for (var i = 0; i < ExpectedSections.Length; i++)
            Assert.Equal(ExpectedSections[i], headers[i]);
    }

    [Fact]
    public void 段集合跨构建与跨工作区恒定()
    {
        var a = Headers(Baseline(RepoRoot()));
        var b = Headers(Baseline(RepoRoot()));           // 同根重算
        Assert.Equal(a, b);
        var alt = Path.Combine(Path.GetTempPath(), "r525-alt-root");
        Directory.CreateDirectory(alt);
        var c = Headers(Baseline(alt));                  // 换工作区根: 段头必须不变
        Assert.Equal(a, c);
    }

    [Fact]
    public void 旧基线纪律零丢失()
    {
        var t = Baseline(RepoRoot());
        string[] must =
        {
            "禁止伪代码、TODO 占位", "没测到 ≠ 测过通过", "凭据卫生", "绝不用编造的输出冒充真实结果",
            "--selftest", "一律用绝对路径", "不用 shell 字符串拼接执行命令", "长任务放后台并登记通知",
            "技能优先于通用做法", "子任务的自述结果不等于已验证事实", "先确认问题本身",
            "拆前提、拆定义、拆边界", "关键模块地图", "SessionInjectionPlanner", "汇报格式",
            "空心断言", "假红", "未验证即宣称",
        };
        foreach (var m in must) Assert.Contains(m, t, StringComparison.Ordinal);
    }

    [Fact]
    public void 动态材料不得出现在常量前缀()
    {
        var t = Baseline(RepoRoot());
        Assert.DoesNotContain("data/activity", t, StringComparison.Ordinal);
        Assert.DoesNotContain("prompt_audit", t, StringComparison.Ordinal);
        Assert.DoesNotContain("[工作区文件", t, StringComparison.Ordinal);
        Assert.Contains("只允许**追加在尾部**", t, StringComparison.Ordinal);
    }

    [Fact]
    public void 每段体量有界_便于保持碎片化()
    {
        var t = Baseline(RepoRoot());
        var idx = Regex.Matches(t, @"(?m)^## §\d+ ").Select(m => m.Index).ToArray();
        Assert.Equal(ExpectedSections.Length, idx.Length);
        for (var i = 0; i < idx.Length; i++)
        {
            var end = i + 1 < idx.Length ? idx[i + 1] : t.Length;
            var size = end - idx[i];
            Assert.InRange(size, 40, 4000);
        }
    }

    [Fact]
    public void 常量前缀不含易变的确定性来源路径()
    {
        var t = Baseline(RepoRoot());
        // §8 工作区快照允许出现根路径, 但**不得**包含运行产物目录 (宿主自身产物会逐轮变化)
        Assert.DoesNotContain("data/telemetry/host.jsonl\"", t, StringComparison.Ordinal);
        Assert.True(t.Length is > 3000 and < 40000, $"基线体量异常: {t.Length}");
    }
}
