using agent.modelqueue;
using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Xunit;

namespace agentframework.tests;

/// <summary>
/// R450 — 门判实发 prompt 落盘闸。
/// 铁律: 默认(env 未设) = 完全关闭 ⇒ 零产品变更; 开启 = 逐位可核 (len/sha16/prompt 原文)。
/// </summary>
public class GatePromptDumpTests
{
    private const string Env = "AGENTFRAMEWORK_GATE_PROMPT_DUMP";

    private static string NewPath() =>
        Path.Combine(Path.GetTempPath(), "r450-dump-" + Guid.NewGuid().ToString("N")[..8] + ".jsonl");

    [Fact]
    public void 默认未设时_完全不落盘()
    {
        var path = NewPath();
        var prev = Environment.GetEnvironmentVariable(Env);
        try
        {
            Environment.SetEnvironmentVariable(Env, null);
            ModelQueueRouter.DumpGatePrompt("判别: 好的，明白。");
            Assert.False(File.Exists(path));
        }
        finally
        {
            Environment.SetEnvironmentVariable(Env, prev);
        }
    }

    [Fact]
    public void 仅空白串被当作关闭_带尾空格的路径按原样使用()
    {
        // 契约: 只有「未设 / 纯空白」= 关闭; 其余字符串一律按**原样路径**处理 (不做 trim 猜测)
        var path = NewPath();
        var prev = Environment.GetEnvironmentVariable(Env);
        try
        {
            Environment.SetEnvironmentVariable(Env, "   ");
            ModelQueueRouter.DumpGatePrompt("判别: 收到。");

            Environment.SetEnvironmentVariable(Env, path + " ");
            ModelQueueRouter.DumpGatePrompt("判别: 收到。");
            Assert.True(File.Exists(path + " "), "带尾空格的路径应被原样使用");
            Assert.False(File.Exists(path), "不得静默 trim 成另一条路径");
        }
        finally
        {
            Environment.SetEnvironmentVariable(Env, prev);
            try { File.Delete(path + " "); } catch { /* 清理尽力而为 */ }
        }
    }

    [Fact]
    public void Json转义_覆盖引号反斜杠与控制字符()
    {
        // AOT 下 STJ 反射序列化被禁用 ⇒ 必须零反射手写转义; 用标准解析器回读验证正确性
        var raw = "a\"b" + (char)92 + "c\nd\te" + (char)1 + "f【角色设定】";
        var esc = ModelQueueRouter.JsonEscape(raw);
        Assert.DoesNotContain("\n", esc);
        using var doc = JsonDocument.Parse("{\"p\":\"" + esc + "\"}");
        Assert.Equal(raw, doc.RootElement.GetProperty("p").GetString());
        Assert.Equal(8, ModelQueueRouter.JsonEscape("x" + (char)1 + "y").Length);   // \u0001 = 6 字符 + 2
    }

    [Fact]
    public void 开启时_落盘且len_sha16_原文逐位可核()
    {
        var path = NewPath();
        var prompt = "【角色设定】种子\n【Role 成长经历】g: 赏1/罚0\n【用户消息】好的，明白。\n答案:\n";
        var prev = Environment.GetEnvironmentVariable(Env);
        try
        {
            Environment.SetEnvironmentVariable(Env, path);
            ModelQueueRouter.DumpGatePrompt(prompt);
            ModelQueueRouter.DumpGatePrompt(prompt);

            var lines = File.ReadAllLines(path);
            Assert.Equal(2, lines.Length);
            var head = File.ReadAllBytes(path);
            Assert.False(head.Length >= 3 && head[0] == 0xEF && head[1] == 0xBB && head[2] == 0xBF,
                "JSONL 不得写 BOM (下游解析器会炸)");
            var expectSha = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(prompt)))[..16];
            foreach (var l in lines)
            {
                using var doc = JsonDocument.Parse(l);
                Assert.Equal(prompt, doc.RootElement.GetProperty("prompt").GetString());
                Assert.Equal(prompt.Length, doc.RootElement.GetProperty("len").GetInt32());
                Assert.Equal(expectSha, doc.RootElement.GetProperty("sha16").GetString());
            }
        }
        finally
        {
            Environment.SetEnvironmentVariable(Env, prev);
            try { File.Delete(path); } catch { /* 清理尽力而为 */ }
        }
    }
}
