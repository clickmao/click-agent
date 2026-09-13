using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using agent.registry;
using agent.templates;
using Xunit;

namespace agent.tests;

/// <summary>
/// R374 (D3): 运行结果回流闭环 — "产物机器校验失败 → 失败输出回灌模型 → 有界修复 → 复检"。
///
/// 断言绑定**真实行为**(不是"模型说修好了"): 真实落盘 + 真实 py_compile 结论 + 真实磁盘新产物;
/// 负向控制: 通过态不得产生任何额外调用 (证明这些用例能抓回归)。
/// </summary>
public class ArtifactRepairTests : IDisposable
{
    private readonly string _dir;

    public ArtifactRepairTests()
    {
        _dir = Path.Combine(Path.GetTempPath(), "artrepair_" + Guid.NewGuid().ToString("N"));
    }

    public void Dispose()
    {
        try { if (Directory.Exists(_dir)) Directory.Delete(_dir, recursive: true); } catch { /* 清理失败不影响断言 */ }
    }

    private static string Fence(string code) => "```python\n" + code + "\n```";

    private (ResponseSegmentRouter Router, PythonArtifactLedger Ledger) Setup(bool run)
    {
        var ledger = new PythonArtifactLedger();
        var plugin = new PythonArtifactPlugin(ledger, _dir, runGate: () => run);
        var router = new ResponseSegmentRouter(new IResponseSegmentPlugin[] { plugin });
        return (router, ledger);
    }

    /// <summary>脚本化 LLM 端口: 记录每次调用 (含提示词全文, 供"事实是否真回灌"断言)。</summary>
    private sealed class ScriptedCaller : ILLMCaller
    {
        private readonly Queue<string> _replies;
        public List<Prompt> Prompts { get; } = new();
        public int Calls => Prompts.Count;

        public ScriptedCaller(params string[] replies) => _replies = new Queue<string>(replies);

        public Task<LLMResponse> CallAsync(Prompt prompt, CancellationToken ct = default)
        {
            Prompts.Add(prompt);
            var reply = _replies.Count > 0 ? _replies.Dequeue() : Fence("print('no-scripted-reply')");
            return Task.FromResult(new LLMResponse { Content = reply, Success = true, TokensUsed = 123 });
        }
    }

    [Fact]
    public async Task 编译失败_失败事实回灌模型_复检通过后正文替换为修复版()
    {
        var (router, ledger) = Setup(run: false);
        var broken = Fence("print('oops'");                 // 真实语法错误 (缺右括号)
        var first = await router.ProcessAsync(broken);      // 主链第一步: 落盘 + py_compile → 结论入队
        var caller = new ScriptedCaller(Fence("print('fixed')"));
        var loop = new ArtifactRepairLoop(router, caller, gate: () => true);

        var res = await loop.RunAsync(first);

        Assert.True(res.Attempted);
        Assert.True(res.Fixed, res.Detail);
        Assert.Equal("compile", res.ErrorKind);
        Assert.Equal(1, caller.Calls); // 有界: 只修一轮
        var p = caller.Prompts[0];
        Assert.Contains("未通过机器校验", p.UserMessage);
        Assert.Contains("print('oops'", p.UserMessage);                 // 失败脚本原样回灌
        Assert.Contains("SyntaxError", p.UserMessage);                  // py_compile 真实错误输出
        Assert.Equal("code_generation", p.Intent);                      // R373 首轮预算策略联动 (给足输出预算)
        // 复检 = 磁盘证据: 两个产物, 后一个通过校验且路径不同 (内容寻址 → 不同内容)
        var reports = ledger.Snapshot();
        Assert.Equal(2, reports.Count);
        Assert.NotEqual(reports[0].Path, reports[1].Path);
        Assert.True(reports[1].CompileValid);
        Assert.Contains("fixed", res.Content);
    }

    [Fact]
    public async Task 修复轮仍失败_只修一轮且如实标记未修好_不改写正文()
    {
        var (router, _) = Setup(run: false);
        var broken = Fence("print('oops'");
        var first = await router.ProcessAsync(broken);
        var caller = new ScriptedCaller(Fence("print('still broken'"));   // 仍然语法错
        var loop = new ArtifactRepairLoop(router, caller, gate: () => true);

        var res = await loop.RunAsync(first);

        Assert.True(res.Attempted);
        Assert.False(res.Fixed);
        Assert.Equal(1, res.Attempts);
        Assert.Equal(1, caller.Calls);              // 声称"再试一次"而不受界 = 回归
        Assert.Equal(first, res.Content);           // 诚实: 未修好 → 不伪装成修复版
        Assert.Contains("仍未通过", res.Detail);
    }

    [Fact]
    public async Task 修复轮回吐同一份失败脚本_不得判定为修好()
    {
        var (router, _) = Setup(run: false);
        var broken = Fence("print('oops'");
        var first = await router.ProcessAsync(broken);
        var caller = new ScriptedCaller(Fence("print('oops'"));            // 与失败脚本逐字一致
        var loop = new ArtifactRepairLoop(router, caller, gate: () => true);

        var res = await loop.RunAsync(first);

        // 同内容 → 内容寻址同路径 → "没有新代码" ≠ "修好了"
        Assert.False(res.Fixed);
        Assert.Contains("未变", res.Detail);
    }

    [Fact]
    public async Task 通过态零触发_不产生额外调用_正文不变_负向控制()
    {
        var (router, _) = Setup(run: false);
        var good = Fence("print('ok')");
        var first = await router.ProcessAsync(good);
        var caller = new ScriptedCaller();
        var loop = new ArtifactRepairLoop(router, caller, gate: () => true);

        var res = await loop.RunAsync(first);

        Assert.False(res.Attempted);
        Assert.False(res.Fixed);
        Assert.Equal(0, caller.Calls);   // 通过态多一次调用 = 白烧 token = 回归
        Assert.Equal(first, res.Content);
    }

    [Fact]
    public async Task 运行失败_退出码与stderr回灌_复检通过()
    {
        if (agent.skills.PythonScriptValidator.ResolvePython() is null)
            return; // 本机无 python3 → 运行级验证不可能成立 (其余用例只依赖编译级)

        var (router, ledger) = Setup(run: true);
        var failing = Fence("import sys\nprint('hi')\nsys.exit(3)");
        var first = await router.ProcessAsync(failing);
        var caller = new ScriptedCaller(Fence("print('hi')"));
        var loop = new ArtifactRepairLoop(router, caller, gate: () => true);

        var res = await loop.RunAsync(first);

        Assert.Equal("run", res.ErrorKind);
        Assert.True(res.Fixed, res.Detail);
        Assert.Contains("退出码=3", caller.Prompts[0].UserMessage);
        var reports = ledger.Snapshot();
        Assert.True(reports[^1].Ran);
        Assert.Equal(0, reports[^1].RunExitCode);
    }

    [Fact]
    public async Task 同一文件重跑变通过_不算修复_必须由修复轮产出新产物()
    {
        // 非确定性场景 (超时/环境抖动): 同一份脚本第二次跑就成功。
        // 若复检丢掉"必须是新产物路径"这条判据 → 原地重试会被误判为"已修复" (KPI 虚高)。
        if (agent.skills.PythonScriptValidator.ResolvePython() is null)
            return;

        var (router, ledger) = Setup(run: true);
        var flaky = Fence(
            "import os, sys\n" +
            "mark = os.path.join(os.path.dirname(__file__), 'mark.txt')\n" +
            "if not os.path.exists(mark):\n" +
            "    open(mark, 'w').write('1')\n" +
            "    sys.exit(5)\n" +
            "print('ok')");
        var first = await router.ProcessAsync(flaky);
        var caller = new ScriptedCaller(flaky);   // 模型原样回吐 (未改动任何代码)
        var loop = new ArtifactRepairLoop(router, caller, gate: () => true);

        var res = await loop.RunAsync(first);

        Assert.Equal("run", res.ErrorKind);
        Assert.False(res.Fixed);
        Assert.Contains("未变", res.Detail);
        // 事实仍如实落库: 同一路径的第二次结论是"通过" (可观测, 不隐藏)
        var reports = ledger.Snapshot();
        Assert.Equal(2, reports.Count);
        Assert.True(reports[^1].Ran);
        Assert.Equal(0, reports[^1].RunExitCode);
    }

    [Fact]
    public void 提示词构造函数_含类别退出码与输出尾部_且按上限截断()
    {
        var longCode = new string('x', ArtifactRepairPolicy.MaxCodeChars + 500);
        var longOut = new string('e', ArtifactRepairPolicy.MaxOutputChars + 500);
        var check = new ArtifactCheck("p.py", "python", longCode, CompileValid: false, ExitCode: 1,
            Ran: true, RunExitCode: 7, RunTimedOut: false, Output: longOut);

        var prompt = ArtifactRepairPolicy.BuildPrompt(check);

        Assert.Contains("失败类别=compile", prompt);
        Assert.Contains("运行退出码=7", prompt);
        Assert.Contains("已截断", prompt);                                  // 超限必截断 (否则爆预算)
        Assert.True(prompt.Length < ArtifactRepairPolicy.MaxCodeChars + ArtifactRepairPolicy.MaxOutputChars + 3000);
        Assert.Contains("```python", prompt);                               // 围栏纪律 (机器链唯一入口)
    }

    [Fact]
    public void 判据真值表_编译失败_运行失败_超时_未跑均不得判定为通过()
    {
        Assert.True(new ArtifactCheck("p", "python", "c", true, 0, false, -1, false, "").Passed);
        Assert.True(new ArtifactCheck("p", "python", "c", true, 0, true, 0, false, "").Passed);

        var compileFail = new ArtifactCheck("p", "python", "c", false, 1, false, -1, false, "SyntaxError: x");
        Assert.False(compileFail.Passed);
        Assert.Equal("compile", compileFail.ErrorKind);

        var runFail = new ArtifactCheck("p", "python", "c", true, 0, true, 3, false, "traceback");
        Assert.False(runFail.Passed);
        Assert.Equal("run", runFail.ErrorKind);

        var timeout = new ArtifactCheck("p", "python", "c", true, 0, true, -1, true, "timeout");
        Assert.False(timeout.Passed);
        Assert.Equal("timeout", timeout.ErrorKind);
    }

    [Fact]
    public void 提示词_含闸门契约与未通过用例摘要_并写明最小改动约束()
    {
        // 真机事实 (R374 B 臂): 闸门对含 --selftest 的产物以 `python3 -I <文件> --selftest` 判定成败,
        // 失败判据是产物自带自测的退出码 —— 契约与"未通过用例"必须显式回灌, 否则模型无从对症。
        var outText = string.Join("\n", new[]
        {
            "[PASS] 吃食物增长得分",
            "[FAIL] 尾格让位不误判: 进入即将让位的尾格不应死亡",
            "FAIL",
        });
        var code = "if __name__ == '__main__':\n    main()  # --selftest\n";
        var check = new ArtifactCheck("p.py", "python", code, true, 0, true, 1, false, outText);

        var prompt = ArtifactRepairPolicy.BuildPrompt(check);

        Assert.Contains("python3 -I", prompt);                       // 闸门调用方式
        Assert.Contains("--selftest", prompt);                       // 闸门选参 (与插件同源判据)
        Assert.Contains("退出码 0", prompt);                          // 判据: 退出码, 不是"看起来对"
        Assert.Contains("尾格让位不误判", prompt);                     // 未通过用例摘要 (原文, 不改写)
        Assert.Contains("最小改动", prompt);                          // 防大改引入回归
        Assert.Contains("不得回退", prompt);
        Assert.True(check.SelfTestAvailable);
        Assert.False(new ArtifactCheck("p", "python", "print(1)", true, 0, false, -1, false, "").SelfTestAvailable);
    }

    [Fact]
    public void 未通过用例摘要_只摘原文行_有界且不臆造()
    {
        var lines = new List<string> { "[FAIL] case0", "[PASS] 应当被排除", "Traceback (most recent call last):" };
        for (var i = 1; i < 40; i++) lines.Add($"[FAIL] case{i}");
        var check = new ArtifactCheck("p", "python", "c", false, 1, false, -1, false, string.Join("\n", lines));

        var summary = ArtifactRepairPolicy.FailedCases(check);

        Assert.Equal(ArtifactRepairPolicy.MaxFailedCases, summary.Split('\n').Length);  // 有界
        Assert.DoesNotContain("应当被排除", summary);                                     // 只摘失败行
        Assert.Contains("case0", summary);                                              // 原文, 不臆造
        Assert.Contains("Traceback", summary);                                          // 摘要在上限内先到先得
        Assert.DoesNotContain("case39", summary);                                       // 超上限的行不进摘要
        Assert.Empty(ArtifactRepairPolicy.FailedCases(
            new ArtifactCheck("p", "python", "c", true, 0, false, -1, false, "")));
    }
}
