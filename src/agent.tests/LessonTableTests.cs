using System;
using System.Collections.Generic;
using System.IO;
using agent.roles;
using Xunit;

namespace agent.tests;

/// <summary>
/// exp5 (L3e) 教训表 单测 —— 验收断言 A1/A2/A3/A4/A5/A8 (docs/plans/v0.22.0-exp5-lesson-table.md §5)。
/// 铁律: 通用化机检必须能**拒收**语言专名 (A8 负断言); 指纹必须跨进程/跨实现稳定 (A2); 无 role 不落盘 (A4)。
/// </summary>
public class LessonTableTests : IDisposable
{
    private readonly string _root;

    public LessonTableTests()
    {
        _root = Path.Combine(Path.GetTempPath(), "lessons_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_root);
    }

    public void Dispose()
    {
        try { if (Directory.Exists(_root)) Directory.Delete(_root, recursive: true); } catch { /* 清理失败不影响断言 */ }
    }

    private static LessonRecord Rec(
        string pattern,
        string kind = "Failure",
        string scope = "Project",
        string? solution = null,
        List<LessonInstance>? instances = null,
        string source = "unit-test")
        => new(string.Empty, kind, pattern, null, null, null, 1, 0, 0, solution, source, scope, 0,
               instances ?? new List<LessonInstance>());

    private static LessonInstance Inst(string lang, string tool, string evidence)
        => new(lang, tool, evidence, 1700000000000);

    private const string GenericA = "静态语法校验不覆盖运行期语义, 交付前须补运行级验证";
    private const string GenericB = "共享可变容器在多线程下须整体加锁, 否则数据竞争";

    [Fact]  // A1
    public void A1_同一通用模式三次命中_归并为一条并累加计数与Solution升级()
    {
        var t = new LessonTable();

        var r1 = t.Submit(Rec(GenericA), 1_000);
        var r2 = t.Submit(Rec(GenericA), 2_000);
        var r3 = t.Submit(Rec(GenericA, solution: "补运行级冒烟: 真跑产物并断言退出码"), 3_000);

        Assert.True(r1.Accepted);
        Assert.Equal(1, r1.Count);
        Assert.Equal(2, r2.Count);
        Assert.Equal(3, r3.Count);
        Assert.Equal(1, t.Count);                                  // 表内只有 1 条
        var only = Assert.Single(t.All());
        Assert.Equal(3, only.Count);
        Assert.NotNull(only.Solution);
        Assert.Equal(1_000, only.FirstSeenUnix);                    // 首次看到时间保留
        Assert.Equal(3_000, only.LastSeenUnix);
        Assert.Equal(r1.Id, r3.Id);
    }

    [Fact]  // A2 (跨实现锁死: 期望值由独立 Python FNV-1a 实现算出, 见轮次报告)
    public void A2_指纹跨进程跨实现稳定_硬编码常量锁死()
    {
        Assert.Equal("8DC87C80", LessonTable.Fingerprint("Failure", GenericA));
        Assert.Equal("4C978D98", LessonTable.Fingerprint("Failure", "x"));
        Assert.Equal("848BBBB7", LessonTable.Fingerprint("Execution", "共享可变容器在多线程下须整体加锁"));
        // 归一化: 首尾/连续空白不影响指纹
        Assert.Equal(LessonTable.Fingerprint("Failure", GenericA), LessonTable.Fingerprint("Failure", "  " + GenericA + "  "));
    }

    [Fact]  // A3
    public void A3_版本号单调递增_增量查询只拉到新记录()
    {
        var t = new LessonTable();
        var a = t.Submit(Rec(GenericA), 1_000);
        var b = t.Submit(Rec(GenericB), 2_000);

        Assert.Equal(1, a.Version);
        Assert.Equal(2, b.Version);
        Assert.Equal(2, t.Query(0).Count);          // since=0 → 全量
        var delta = t.Query(a.Version);             // since=1 → 只有之后变更的
        var one = Assert.Single(delta);
        Assert.Equal(b.Id, one.Id);
        Assert.Null(t.Detail("不存在"));
    }

    [Fact]  // A4 + A5①
    public void A4_落盘在data_roles下_且运行后用户项目目录零新增()
    {
        var dataDir = Path.Combine(_root, "data");
        var projectDir = Path.Combine(_root, "user-project");
        Directory.CreateDirectory(projectDir);
        File.WriteAllText(Path.Combine(projectDir, "Program.cs"), "// user code\n");
        var beforeProject = Directory.GetFileSystemEntries(projectDir, "*", SearchOption.AllDirectories).Length;
        var beforeData = Directory.Exists(dataDir)
            ? Directory.GetFileSystemEntries(dataDir, "*", SearchOption.AllDirectories).Length : 0;

        var lessons = new RoleLessons("skeptic", dataDir);
        var res = lessons.Submit(Rec(GenericA), 5_000);

        Assert.True(res.Accepted);
        var expected = Path.Combine(dataDir, "roles", "skeptic.lessons.json");
        Assert.Equal(expected, lessons.StoragePath);
        Assert.True(File.Exists(expected), "教训必须落在 data/roles/{roleId}.lessons.json");
        Assert.False(File.Exists(expected + ".tmp"), "原子写不得残留 tmp");

        var afterProject = Directory.GetFileSystemEntries(projectDir, "*", SearchOption.AllDirectories).Length;
        Assert.Equal(beforeProject, afterProject);                       // 负断言①: 用户项目目录零新增
        Assert.True(Directory.GetFileSystemEntries(dataDir, "*", SearchOption.AllDirectories).Length > beforeData);
    }

    [Fact]  // A5②
    public void A5_跨role隔离_roleA的教训不出现在roleB()
    {
        var dataDir = Path.Combine(_root, "data");
        var a = new RoleLessons("role-a", dataDir);
        var b = new RoleLessons("role-b", dataDir);

        a.Submit(Rec(GenericA), 1_000);
        b.Submit(Rec(GenericB), 1_000);

        var qa = a.Query(0);
        var qb = b.Query(0);
        Assert.Single(qa);
        Assert.Single(qb);
        Assert.DoesNotContain(qa, r => r.Pattern == GenericB);
        Assert.DoesNotContain(qb, r => r.Pattern == GenericA);
    }

    [Fact]  // A8 正断言
    public void A8_同一通用模式的两个语言实例_归并为一条且Instances双语可溯()
    {
        var t = new LessonTable();
        var py = Rec(GenericA, instances: new List<LessonInstance>
        {
            Inst("python", "py_compile", "只做语法编译检查, 未真跑产物"),
        });
        var cpp = Rec(GenericA, instances: new List<LessonInstance>
        {
            Inst("c++", "-fsyntax-only", "编译通过但未运行可执行文件"),
        });

        t.Submit(py, 1_000);
        var merged = t.Submit(cpp, 2_000);

        var one = Assert.Single(t.All());
        Assert.Equal(2, one.Count);
        Assert.Equal(2, one.Instances.Count);
        Assert.Equal(merged.Count, one.Count);
        Assert.Contains(one.Instances, i => i.Lang == "python" && i.Tool == "py_compile");
        Assert.Contains(one.Instances, i => i.Lang == "c++" && i.Tool == "-fsyntax-only");
        // 同实例重复提交不重复累积 (去重)
        t.Submit(py, 3_000);
        Assert.Equal(2, Assert.Single(t.All()).Instances.Count);
    }

    [Fact]  // A8 负断言
    public void A8负断言_Pattern含语言或工具专名_必须拒收入库()
    {
        var t = new LessonTable();

        var bad1 = t.Submit(Rec("py_compile 只到语法级, 不算验证"), 1_000);
        Assert.False(bad1.Accepted);
        Assert.False(bad1.Recorded);
        Assert.Contains("未通用化", bad1.Rejected);
        Assert.Contains("py_compile", bad1.Rejected);

        var bad2 = t.Submit(Rec("在 C# 里 List 成员要加锁"), 1_000);
        Assert.False(bad2.Accepted);

        var bad3 = t.Submit(Rec("检查 .cs 文件的语法"), 1_000);
        Assert.False(bad3.Accepted);

        Assert.Equal(0, t.Count);          // 拒收 → 表零增长
        Assert.Equal(0, t.Version);
    }

    [Fact]
    public void 黑名单边界_不误杀普通词汇且大小写不敏感()
    {
        Assert.True(LessonGeneralization.IsGeneralized("算法复杂度与输入规模相关, 须用稳定哈希避免随机化"));
        Assert.True(LessonGeneralization.IsGeneralized("javaxxx 不是语言专名"));   // 边界: 不匹配子串
        Assert.False(LessonGeneralization.IsGeneralized("使用 PYTHON 脚本"));
        Assert.Contains("python", LessonGeneralization.Screen("使用 PYTHON 脚本"));
    }

    [Fact]
    public void 落盘往返_版本计数与实例保持_无tmp残留()
    {
        var path = Path.Combine(_root, "data", "roles", "skeptic.lessons.json");
        var t = new LessonTable();
        t.Submit(Rec(GenericA, instances: new List<LessonInstance> { Inst("python", "py_compile", "e1") }), 1_000);
        t.Submit(Rec(GenericB), 2_000);
        var written = t.Save(path);

        Assert.True(written > 0);
        Assert.False(File.Exists(path + ".tmp"));

        var back = LessonTable.Load(path);
        Assert.Equal(t.Version, back.Version);
        Assert.Equal(t.Count, back.Count);
        var rows = back.Query(0, kind: "Failure", scope: "Project");
        Assert.Equal(2, rows.Count);
        var a = Assert.Single(rows, r => r.Pattern == GenericA);
        Assert.Single(a.Instances);
        Assert.Equal("python", a.Instances[0].Lang);
        Assert.Equal(t.Query(0).Count, back.Query(0).Count);
    }

    [Fact]
    public void 无role_不落盘且显式回报_不静默()
    {
        var dataDir = Path.Combine(_root, "data");
        var none = new RoleLessons(null, dataDir);

        Assert.False(none.Enabled);
        Assert.Null(none.StoragePath);
        var res = none.Submit(Rec(GenericA), 1_000);
        Assert.False(res.Recorded);
        Assert.Contains("无 role", res.Rejected);
        Assert.Empty(none.Query(0));
        Assert.Null(none.Detail("x"));
        Assert.False(Directory.Exists(Path.Combine(dataDir, "roles")), "无 role 时不得创建 role 数据目录");
    }

    [Fact]
    public void 字段校验_Kind为空或Scope非法_拒收()
    {
        var t = new LessonTable();
        Assert.False(t.Submit(Rec(GenericA, kind: "  "), 1_000).Accepted);
        Assert.False(t.Submit(Rec(GenericA, scope: "Global"), 1_000).Accepted);
        Assert.True(t.Submit(Rec(GenericA, scope: "Session"), 1_000).Accepted);
        Assert.Equal(1, t.Count);
    }
}
