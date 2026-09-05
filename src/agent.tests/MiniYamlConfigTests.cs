using agent.config;
using Xunit;

namespace agent.tests;

/// <summary>
/// v7.15 配置体系测试: MiniYaml 子集解析 + ConfigSnapshot 四层覆盖 (base←env←modules←runtime)。
/// 契约: base 被同名 module 配置增量覆盖, 未定义字段继承低层 (规范 §3.2)。
/// </summary>
public class MiniYamlConfigTests
{
    [Fact]
    public void Parse_Nested_Scalars_And_Comments()
    {
        var yaml = """
# 顶部注释
runtime:
  # 行内注释
  default_token_budget: 8192
  enable_metrics: true
  ratio: 0.85
  name: MainAgent
  empty_value:
""";
        var d = MiniYaml.Parse(yaml);
        var rt = Assert.IsType<Dictionary<string, object?>>(d["runtime"]);
        Assert.Equal(8192L, rt["default_token_budget"]);
        Assert.Equal(true, rt["enable_metrics"]);
        Assert.Equal(0.85, rt["ratio"]);
        Assert.Equal("MainAgent", rt["name"]);
        Assert.Null(rt["empty_value"]);
    }

    [Fact]
    public void Parse_List_Of_Scalars_And_Maps()
    {
        var yaml = """
skills:
  - a
  - b
items:
  - name: x
    priority: 10
  - name: y
    priority: 20
""";
        var d = MiniYaml.Parse(yaml);
        var skills = Assert.IsType<List<object?>>(d["skills"]);
        Assert.Equal(2, skills.Count);
        Assert.Equal("a", skills[0]);
        var items = Assert.IsType<List<object?>>(d["items"]);
        var first = Assert.IsType<Dictionary<string, object?>>(items[0]);
        Assert.Equal("x", first["name"]);
        Assert.Equal(10L, first["priority"]);
    }

    [Fact]
    public void Parse_Quoted_String_With_Hash()
    {
        var yaml = "key: \"value # not comment\"";
        var d = MiniYaml.Parse(yaml);
        Assert.Equal("value # not comment", d["key"]);
    }

    [Fact]
    public void Snapshot_Module_Overrides_Base_And_Inherits_Undeclared()
    {
        var root = Path.Combine(Path.GetTempPath(), "cfgtest_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(Path.Combine(root, "base"));
        Directory.CreateDirectory(Path.Combine(root, "modules"));
        File.WriteAllText(Path.Combine(root, "base", "m.yaml"),
            "m:\n  threshold: 0.85\n  name: base_name\n  nested:\n    a: 1\n    b: 2\n");
        File.WriteAllText(Path.Combine(root, "modules", "m.yaml"),
            "m:\n  threshold: 0.95\n  nested:\n    a: 11\n");
        try
        {
            var s = new ConfigSnapshot(root);
            // L3 覆盖 L1
            Assert.Equal(0.95, s.Get<double>("m", "threshold", 0.0));
            // 未覆盖字段继承 base
            Assert.Equal("base_name", s.Get("m", "name", ""));
            // 深合并: nested.a 被覆盖, nested.b 继承
            var nested = s.GetSection("m")["nested"] as Dictionary<string, object?>;
            Assert.NotNull(nested);
            Assert.Equal(11L, nested!["a"]);
            Assert.Equal(2L, nested["b"]);
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    [Fact]
    public void Snapshot_Missing_File_Falls_Back_To_Defaults()
    {
        var root = Path.Combine(Path.GetTempPath(), "cfgtest_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root); // 空目录: 无任何 yaml
        try
        {
            var s = new ConfigSnapshot(root);
            Assert.Equal(42, s.Get("nope", "anything", 42));
            Assert.Equal("dft", s.Get("nope", "anything", "dft"));
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    [Fact]
    public void Snapshot_Invalid_Yaml_Skips_File_Not_Crash()
    {
        var root = Path.Combine(Path.GetTempPath(), "cfgtest_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(Path.Combine(root, "base"));
        File.WriteAllText(Path.Combine(root, "base", "bad.yaml"),
            "key_no_colon_is_invalid\n  broken\n");
        try
        {
            var s = new ConfigSnapshot(root); // 不应抛
            Assert.Equal(1, s.Get("bad", "k", 1));
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }
}
