using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Xunit;
using agent.rover.token;

namespace agent.tests;

/// <summary>
/// R406 P0-2 · chat template **模板驱动**渲染对账 (oracle = jinja2 3.1.6, 独立实现)。
///
/// 判据 (预注册):
///   J1. 三套夹具共 32 例逐字节相等 (deepseek 12 + r1-distill 10 + qwen25-math 10), 且条数硬断言防夹具缩水;
///   J2. 每例同时校验 UTF-8 字节长度 (expected_len);
///   J3. 产品路径 (ChatMessage → RenderFromTemplate) 与原始 JSON 路径渲染结果一致。
/// 负控 (R399 判定器铁律: 无负控的通过率是空心指标):
///   N1. 模板互换 (R1 消息 × qwen 模板) 必须**判不过** —— 证明对账对模板敏感, 非恒真;
///   N2. 未实现构造 (macro/未知过滤器) 必须抛 JinjaUnsupportedException, 不静默降级;
///   N3. 块未闭合 / for 迭代 Undefined 必须抛 JinjaEvaluationException, 不静默空转;
///   N4. 空白控制与 keep_trailing_newline 开关各自可观测 (关掉即结果变化);
///   N5. 宽松 Undefined / namespace 跨循环写回 / 负下标 split 语义逐条固定。
/// </summary>
public class JinjaChatTemplateTests
{
    private static readonly (string Template, string Golden, string Name)[] Fixtures =
    [
        ("chat_template.jinja", "chat_golden.jsonl", "deepseek"),
        ("r1_chat_template.jinja", "r1_chat_golden.jsonl", "r1-distill-1.5b"),
        ("qwen25math_chat_template.jinja", "qwen25math_chat_golden.jsonl", "qwen2.5-math-1.5b"),
    ];

    private static string Root
    {
        get
        {
            DirectoryInfo? dir = new(AppContext.BaseDirectory);
            while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "eval", "rover", "tokref", "manifest.json")))
            {
                dir = dir.Parent;
            }

            return dir?.FullName ?? throw new InvalidOperationException("找不到仓库根 (eval/rover/tokref/manifest.json)");
        }
    }

    private static string Tokref(params string[] parts) => Path.Combine([Root, "eval", "rover", "tokref", .. parts]);

    private static List<JsonDocument> Rows(string file)
    {
        List<JsonDocument> rows = [];
        foreach (string line in File.ReadLines(file, Encoding.UTF8))
        {
            if (line.Trim().Length > 0) rows.Add(JsonDocument.Parse(line));
        }

        return rows;
    }

    private static string RenderRow(string template, JsonElement row)
    {
        Assert.True(row.TryGetProperty("messages", out JsonElement messages), "夹具缺 messages");
        Assert.True(row.TryGetProperty("add_generation_prompt", out JsonElement gen), "夹具缺 add_generation_prompt");
        Dictionary<string, JinjaValue> ctx = new(StringComparer.Ordinal)
        {
            ["messages"] = ToValue(messages),
            ["add_generation_prompt"] = JinjaValue.Of(gen.GetBoolean()),
            ["bos_token"] = JinjaValue.Of(row.TryGetProperty("bos_token", out JsonElement bos) ? bos.GetString()! : ChatTemplate.Bos),
        };
        return JinjaTemplate.Render(template, JinjaValue.Dict(ctx));
    }

    private static JinjaValue ToValue(JsonElement e)
    {
        switch (e.ValueKind)
        {
            case JsonValueKind.Object:
                {
                    Dictionary<string, JinjaValue> fields = new(StringComparer.Ordinal);
                    foreach (JsonProperty p in e.EnumerateObject()) fields[p.Name] = ToValue(p.Value);
                    return JinjaValue.Dict(fields);
                }

            case JsonValueKind.Array:
                {
                    List<JinjaValue> items = [];
                    foreach (JsonElement item in e.EnumerateArray()) items.Add(ToValue(item));
                    return JinjaValue.Of(items);
                }

            case JsonValueKind.String:
                return JinjaValue.Of(e.GetString()!);
            case JsonValueKind.Number:
                return e.TryGetInt64(out long l) ? JinjaValue.Of(l) : JinjaValue.Of(e.GetDouble());
            case JsonValueKind.True:
                return JinjaValue.True;
            case JsonValueKind.False:
                return JinjaValue.False;
            default:
                return JinjaValue.Null;
        }
    }

    [Fact]
    public void J1_三套夹具32例_与jinja2逐字节对齐()
    {
        Assert.Equal(3, Fixtures.Length);
        int total = 0;
        List<string> failures = [];
        foreach ((string templateFile, string goldenFile, string name) in Fixtures)
        {
            string template = File.ReadAllText(Tokref(templateFile), Encoding.UTF8);
            foreach (JsonDocument row in Rows(Tokref(goldenFile)))
            {
                total++;
                string expected = row.RootElement.GetProperty("rendered").GetString()!;
                string got = RenderRow(template, row.RootElement);
                string label = row.RootElement.TryGetProperty("name", out JsonElement nm)
                    ? nm.GetString()!
                    : row.RootElement.TryGetProperty("case", out JsonElement cs) ? cs.GetString()! : "?";
                if (!string.Equals(expected, got, StringComparison.Ordinal))
                {
                    failures.Add($"[{name}/{label}] 逐字节不等\n  exp={Escape(expected)}\n  got={Escape(got)}");
                    continue;
                }

                if (row.RootElement.TryGetProperty("error", out JsonElement err) && err.ValueKind != JsonValueKind.Null)
                {
                    failures.Add($"[{name}/{label}] 夹具自带 error 字段非空: {err}");
                }

                if (row.RootElement.TryGetProperty("rendered_sha256", out JsonElement sha))
                {
                    string digest = Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(got)));
                    if (!string.Equals(sha.GetString(), digest, StringComparison.OrdinalIgnoreCase))
                    {
                        failures.Add($"[{name}/{label}] sha256 不等: exp={sha.GetString()} got={digest}");
                    }
                }

                if (!row.RootElement.TryGetProperty("len_unit", out JsonElement unit) || unit.GetString() != "utf8_bytes")
                {
                    failures.Add($"[{name}] 夹具缺少 len_unit='utf8_bytes' (长度单位必须显式, 防单位漂移)");
                }

                if (row.RootElement.TryGetProperty("expected_len", out JsonElement len))
                {
                    int bytes = Encoding.UTF8.GetByteCount(got);
                    if (bytes != len.GetInt32()) failures.Add($"[{name}] 字节长度 {bytes} != expected_len {len.GetInt32()}");
                }
            }
        }

        Assert.True(failures.Count == 0, $"{failures.Count}/{total} 例失败:\n{string.Join("\n", failures)}");
        Assert.Equal(32, total);
    }

    [Fact]
    public void J3_产品路径ChatMessage_与原始JSON路径一致()
    {
        int total = 0;
        foreach ((string templateFile, string goldenFile, string name) in Fixtures)
        {
            string template = File.ReadAllText(Tokref(templateFile), Encoding.UTF8);
            foreach (JsonDocument row in Rows(Tokref(goldenFile)))
            {
                List<ChatMessage> messages = [];
                foreach (JsonElement m in row.RootElement.GetProperty("messages").EnumerateArray())
                {
                    messages.Add(new ChatMessage(m.GetProperty("role").GetString()!, m.GetProperty("content").GetString() ?? string.Empty));
                }

                string gen = row.RootElement.GetProperty("add_generation_prompt").GetBoolean() ? "gen" : "nogen";
                string viaApi = ChatTemplate.RenderFromTemplate(template, messages, row.RootElement.GetProperty("add_generation_prompt").GetBoolean(), ChatTemplate.Bos);
                string viaRaw = RenderRow(template, row.RootElement);
                Assert.True(string.Equals(viaApi, viaRaw, StringComparison.Ordinal), $"[{name}/{gen}] 产品路径与原始路径不一致");
                total++;
            }
        }

        Assert.Equal(32, total);
    }

    [Fact]
    public void N1_模板互换负控_必须判不过()
    {
        string r1Template = File.ReadAllText(Tokref("r1_chat_template.jinja"), Encoding.UTF8);
        string qwenTemplate = File.ReadAllText(Tokref("qwen25math_chat_template.jinja"), Encoding.UTF8);
        int mismatches = 0;
        int cases = 0;
        foreach (JsonDocument row in Rows(Tokref("r1_chat_golden.jsonl")))
        {
            cases++;
            string expected = row.RootElement.GetProperty("rendered").GetString()!;
            if (!string.Equals(RenderRow(qwenTemplate, row.RootElement), expected, StringComparison.Ordinal)) mismatches++;
        }

        Assert.Equal(10, cases);
        Assert.True(mismatches == cases, $"负控失效: 用 qwen 模板渲染 R1 夹具仅 {mismatches}/{cases} 不等 (对账对模板不敏感 ⇒ 空心)");

        // 反向: R1 模板渲染 qwen 夹具也必须全不等
        int reverse = 0;
        int reverseCases = 0;
        foreach (JsonDocument row in Rows(Tokref("qwen25math_chat_golden.jsonl")))
        {
            reverseCases++;
            string expected = row.RootElement.GetProperty("rendered").GetString()!;
            if (!string.Equals(RenderRow(r1Template, row.RootElement), expected, StringComparison.Ordinal)) reverse++;
        }

        Assert.Equal(10, reverseCases);
        Assert.True(reverse == reverseCases, $"负控失效: R1 模板渲染 qwen 夹具仅 {reverse}/{reverseCases} 不等");
    }

    [Fact]
    public void N2_未实现构造必须显式抛_不静默降级()
    {
        Assert.Throws<JinjaUnsupportedException>(() => Render("{% macro m() %}x{% endmacro %}"));
        Assert.Throws<JinjaUnsupportedException>(() => Render("{% include 'x.jinja' %}"));
        Assert.Throws<JinjaUnsupportedException>(() => Render("{{ 'a' | bogusfilter }}"));
        Assert.Throws<JinjaUnsupportedException>(() => Render("{{ 'a'.bogusmethod() }}"));
        Assert.Throws<JinjaUnsupportedException>(() => Render("{% for k, v in [1] %}{% endfor %}"));

        // 未走到的分支不得抛 (排除项按「是否被走到」判定, 而非按「模板里是否出现」)
        string r1Template = File.ReadAllText(Tokref("r1_chat_template.jinja"), Encoding.UTF8);
        string one = ChatTemplate.RenderFromTemplate(r1Template, [new ChatMessage("user", "hi")], true, ChatTemplate.Bos);
        Assert.Contains("hi", one, StringComparison.Ordinal);
    }

    [Fact]
    public void N3_块未闭合与未定义迭代必须抛()
    {
        Assert.Throws<JinjaEvaluationException>(() => Render("{% if true %}x"));
        Assert.Throws<JinjaEvaluationException>(() => Render("{% for x in [1] %}y"));
        Assert.Throws<JinjaEvaluationException>(() => Render("a{% endif %}"));
        Assert.Throws<JinjaEvaluationException>(() => Render("{% for x in nope %}{{x}}{% endfor %}"));
        Assert.Throws<JinjaEvaluationException>(() => Render("{{ 'a' + none }}"));
    }

    [Fact]
    public void N4_空白控制与末尾换行开关可观测()
    {
        Assert.Equal("ab", Render("a{{- 'b' }}"));
        Assert.Equal("ab", Render("a {{- 'b' }}"));
        Assert.Equal("ab", Render("a{{ 'b' -}} "));
        Assert.Equal("a b\n", Render("a {% if true %}b{% endif %}\n"));
        Assert.Equal("a\nb\n", Render("a\n{% if true %}b{% endif %}\n", new JinjaOptions { LStripBlocks = true }));

        string template = "x{{ 'y' }}\n";
        Assert.Equal("xy\n", JinjaTemplate.Render(template, JinjaValue.Dict()));
        Assert.Equal("xy", JinjaTemplate.Render(template, JinjaValue.Dict(), new JinjaOptions { KeepTrailingNewline = false }));

        // trim_blocks: 关掉保留块标签后的换行, 打开则吞掉
        string tpl2 = "a\n{% if true %}\nb{% endif %}\n";
        Assert.Equal("a\n\nb\n", Render(tpl2));
        Assert.Equal("a\nb", Render(tpl2, new JinjaOptions { TrimBlocks = true }));

        // lstrip_blocks: 关掉保留标签所在行缩进, 打开则删掉
        string tpl3 = "a\n  {% if true %}b{% endif %}\n";
        Assert.Equal("a\n  b\n", Render(tpl3));
        Assert.Equal("a\nb\n", Render(tpl3, new JinjaOptions { LStripBlocks = true }));
    }

    [Fact]
    public void N5_宽松Undefined与namespace与负下标语义()
    {
        Assert.Equal("", Render("{{ nope }}"));
        Assert.Equal("", Render("{{ nope.deep.deeper }}"));
        Assert.Equal("false", Render("{% if nope %}true{% else %}false{% endif %}"));
        Assert.Equal("false", Render("{% if nope is defined %}true{% else %}false{% endif %}"));
        Assert.Equal("true", Render("{% if nope is not defined %}true{% else %}false{% endif %}"));
        Assert.Equal("true", Render("{% if none is none %}true{% else %}false{% endif %}"));
        Assert.Equal("true", Render("{% if 'a' in 'bab' %}true{% else %}false{% endif %}"));
        Assert.Equal("true", Render("{% if 2 in [1,2,3] %}true{% else %}false{% endif %}"));
        Assert.Equal("b", Render("{{ 'a</think>b'.split('</think>')[-1] }}"));

        // namespace 跨循环写回 (jinja 语义: 循环作用域独立, 但 namespace 对象本身共享)
        string tpl = "{% set ns = namespace(n=0) %}{% for i in [1,2,3] %}{% set ns.n = ns.n + 1 %}{% endfor %}{{ ns.n }}";
        Assert.Equal("3", Render(tpl));

        // 普通 set 不跨循环泄漏 (jinja: 每次迭代独立作用域)
        string leak = "{% set x = 'outer' %}{% for i in [1,2] %}{% set x = 'inner' %}{% endfor %}{{ x }}";
        Assert.Equal("outer", Render(leak));

        // loop 变量
        Assert.Equal("3|3|3|", Render("{% for i in [1,2,3] %}{{ loop.length }}|{% endfor %}"));
        // 布尔渲染与 jinja 一致 = Python str(): True/False (不是 true/false)
        Assert.Equal("1True|2False|3False|", Render("{% for i in [1,2,3] %}{{ i }}{{ loop.first }}|{% endfor %}"));
        Assert.Equal("321", Render("{% for i in [1,2,3] %}{{ loop.revindex }}{% endfor %}"));
        Assert.Equal("empty", Render("{% for i in [] %}x{% else %}empty{% endfor %}"));

        // 未定义序列即使写了 else 也必须抛 (jinja 同样在迭代未定义时报错, 不静默走 else)
        Assert.Throws<JinjaEvaluationException>(() => Render("{% for i in nope2 %}x{% else %}empty{% endfor %}"));
    }

    private static string Render(string template) => JinjaTemplate.Render(template, JinjaValue.Dict());

    private static string Render(string template, JinjaOptions options) => JinjaTemplate.Render(template, JinjaValue.Dict(), options);

    private static string Escape(string s) => s.Replace("\n", "\\n", StringComparison.Ordinal).Replace("\r", "\\r", StringComparison.Ordinal);
}
