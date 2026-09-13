using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using agent.registry;
using Xunit;

namespace agent.tests;

/// <summary>
/// R371 D4-b: **无围栏代码块**的确定性识别。
/// 背景(真机): 模型有时不给 ```python 围栏 (3 次复跑仅 1 次带围栏) → artifact 链(落盘/编译/运行)永不触发。
/// 原则: 宁可漏提升, 不可误判 (把散文当代码落盘/编译 = 假证据)。
/// </summary>
public class UnfencedCodeDetectionTests : IDisposable
{
    private readonly string _dir;

    public UnfencedCodeDetectionTests()
    {
        _dir = Path.Combine(Path.GetTempPath(), "unfenced_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_dir);
    }

    public void Dispose()
    {
        try { if (Directory.Exists(_dir)) Directory.Delete(_dir, true); } catch { /* 清理失败不影响断言 */ }
    }

    /// <summary>与真机产物同型的实现 (含 shebang/注释/文档串/空行/缩进 —— 全都不得打断整段)。</summary>
    private static readonly string PyBody = string.Join("\n", new[]
    {
        "#!/usr/bin/env python3",
        "# -*- coding: utf-8 -*-",
        "\"\"\"贪吃蛇 (单文件, 逻辑/渲染分离)。\"\"\"",
        "import sys",
        "",
        "UP, DOWN = (0, -1), (0, 1)",
        "",
        "",
        "class SnakeLogic:",
        "    \"\"\"纯逻辑: 无 IO, 可无头驱动。\"\"\"",
        "",
        "    def __init__(self, w=20, h=15):",
        "        self.w = w",
        "        self.h = h",
        "        self.body = [(w // 2, h // 2)]",
        "        self.dead = False",
        "",
        "    def step(self, direction):",
        "        x, y = self.body[0]",
        "        nx, ny = x + direction[0], y + direction[1]",
        "        if not (0 <= nx < self.w and 0 <= ny < self.h):",
        "            self.dead = True",
        "            return",
        "        self.body.insert(0, (nx, ny))",
        "        self.body.pop()",
        "",
        "",
        "def selftest():",
        "    g = SnakeLogic()",
        "    g.step(DOWN)",
        "    if g.dead:",
        "        return False",
        "    return True",
        "",
        "",
        "if __name__ == \"__main__\":",
        "    print(\"PASS\" if selftest() else \"FAIL\")",
    }) + "\n";


    [Fact]
    public void 无围栏的完整实现_识别为python代码段_且全文可原样重建()
    {
        var reply = "已确认需求，直接给出单文件实现（逻辑/渲染分离）。\n\n" + PyBody;

        var segs = ResponseSegmenter.Segment(reply);
        var code = segs.Where(s => s.Kind == SegmentKind.Code).ToList();

        var one = Assert.Single(code);
        Assert.Equal("python", one.Language);
        Assert.Contains("class SnakeLogic", one.Content);
        Assert.Contains("def selftest", one.Content);
        Assert.Contains("__main__", one.Content);          // 注释/文档串/空行未截断整段
        Assert.Equal(reply, string.Concat(segs.Select(s => s.Content)));   // 区段拼回 == 原文 (恒等)
    }

    [Fact]
    public async Task 无围栏实现_经路由器后_真落盘且py_compile通过()
    {
        var ledger = new PythonArtifactLedger();
        var router = new ResponseSegmentRouter(new IResponseSegmentPlugin[]
        {
            new PythonArtifactPlugin(ledger, _dir),
        });
        var reply = "实现如下：\n\n" + PyBody;

        var output = await router.ProcessAsync(reply);

        // 段内容未被插件改写 (恒等), 但**渲染层**会给代码段补围栏 → 用户看到的输出被规范化
        Assert.Contains("```python", output);
        Assert.Contains("class SnakeLogic", output);
        Assert.Equal(reply.TrimEnd(), output.Replace("```python\n", "").Replace("\n```", "").TrimEnd());
        var r = Assert.Single(ledger.Snapshot());
        Assert.True(r.CompileValid, r.Detail);             // 真实 py_compile
        Assert.Equal("python", r.Language);
        Assert.True(File.Exists(r.Path), r.Path);
    }

    [Fact]
    public void 纯散文含括号与等号_不得被判为代码()
    {
        var prose = string.Join("\n", Enumerable.Range(1, 14).Select(i =>
            $"第 {i} 点：成本（tokens）与轮数需要对比，方案 A = 更稳妥（推荐），方案 B = 更激进。"));

        var segs = ResponseSegmenter.Segment(prose);

        Assert.DoesNotContain(segs, s => s.Kind == SegmentKind.Code);
    }

    [Fact]
    public void 短代码片段_不足八行_不得提升()
    {
        var shortCode = "import os\nimport sys\n\n\ndef f():\n    return 1\n\n\nprint(f())\n";
        var segs = ResponseSegmenter.Segment(shortCode);
        Assert.DoesNotContain(segs, s => s.Kind == SegmentKind.Code);
    }

    [Fact]
    public void 已带围栏_不触发回退_且只有一段代码()
    {
        var fenced = "给你脚本：\n```python\nprint('hi')\n```\n直接跑。";
        var segs = ResponseSegmenter.Segment(fenced);
        var code = segs.Where(s => s.Kind == SegmentKind.Code).ToList();
        var one = Assert.Single(code);
        Assert.Equal("python", one.Language);
        Assert.Equal("print('hi')\n", one.Content.Replace("\r\n", "\n"));
    }

    [Fact]
    public void 散文加代码混合_代码段从首个代码行起算_散文后置不并入()
    {
        var reply = "先说明思路：把逻辑与渲染分开，便于无头自测。\n\n" + PyBody + "\n运行方法：python3 game.py --selftest\n";

        var segs = ResponseSegmenter.Segment(reply);
        var code = segs.Where(s => s.Kind == SegmentKind.Code).ToList();

        var one = Assert.Single(code);
        Assert.StartsWith("#!/usr/bin/env python3", one.Content);
        Assert.DoesNotContain("运行方法", one.Content);     // 尾部散文不并入代码段
        Assert.Equal(reply, string.Concat(segs.Select(s => s.Content)));
    }
// ── R371 D4-b v2: 字符串字面量感知 + 机制归因 (真机 RUN3 实证驱动) ──────────────

    /// <summary>与真机 RUN3 同型的**文档健全**实现: 中文 docstring 占比高 (旧闸门判 47% 散文 → 放弃提升)。</summary>
    private static readonly string DocBody = string.Join("\n", new[]
    {
        "#!/usr/bin/env python3",
        "# -*- coding: utf-8 -*-",
        "\"\"\"终端贪吃蛇（文本渲染）。",
        "",
        "设计要点",
        "--------",
        "* 核心逻辑 :class:`SnakeGame` 完全不碰终端（无 print / 无 input），可无头测试。",
        "* 渲染     :class:`TerminalRenderer` 只读取状态、产出字符串，无副作用。",
        "* 输入     :class:`Input` 负责跨平台非阻塞单键读取。",
        "",
        "用法::",
        "",
        "    python3 game.py                 # 开始游戏（WASD / 方向键移动，q 退出）",
        "    python3 game.py --speed 12      # 调整速度（每秒步数）",
        "    python3 game.py --selftest      # 无头自测，打印 PASS 或 FAIL",
        "\"\"\"",
        "",
        "from __future__ import annotations",
        "",
        "import argparse",
        "import sys",
        "",
        "UP = (0, -1)",
        "",
        "",
        "class SnakeGame:",
        "    \"\"\"纯逻辑贪吃蛇：不读键盘、不写终端，方便无头自测。\"\"\"",
        "",
        "    def __init__(self, width: int = 20, height: int = 15):",
        "        self.width = width",
        "        self.height = height",
        "",
        "    def step(self, direction):",
        "        return direction",
        "",
        "",
        "def selftest():",
        "    assert SnakeGame().step(UP) == UP",
        "    print(\"PASS\")",
        "    return True",
        "",
        "",
        "if __name__ == \"__main__\":",
        "    selftest()",
    }) + "\n";

    [Fact]
    public void 文档健全的python_串内散文不算散文_仍被提升()
    {
        var reply = "说明如下：\n\n" + DocBody;

        var segs = ResponseSegmenter.Segment(reply);
        var one = Assert.Single(segs, s => s.Kind == SegmentKind.Code);

        Assert.Equal("python", one.Language);
        Assert.True(one.Promoted, "无围栏 → 必须标记为启发式提升, 否则真机 KPI 无法归因");
        Assert.StartsWith("#!/usr/bin/env python3", one.Content);
        Assert.DoesNotContain("说明如下", one.Content);
        Assert.Equal(reply, string.Concat(segs.Select(s => s.Content)));
    }

    [Fact]
    public void 归因字段_fenced段为假_启发式段为真()
    {
        var fenced = Assert.Single(
            ResponseSegmenter.Segment("```python\nprint(1)\n```\n"), s => s.Kind == SegmentKind.Code);
        Assert.False(fenced.Promoted);

        var promoted = Assert.Single(
            ResponseSegmenter.Segment(DocBody), s => s.Kind == SegmentKind.Code);
        Assert.True(promoted.Promoted);
    }

    [Fact]
    public void 被预算截断的半份实现_仍能入库_由截断检测另报()
    {
        var truncated = DocBody[..(DocBody.Length * 3 / 4)];   // 断在半行 (真机 RUN3 形态: 代码已开始后被裁)

        var one = Assert.Single(ResponseSegmenter.Segment(truncated), s => s.Kind == SegmentKind.Code);

        Assert.Equal("python", one.Language);
        Assert.StartsWith("#!/usr/bin/env python3", one.Content);
    }
}
