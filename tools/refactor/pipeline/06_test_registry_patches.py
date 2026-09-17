#!/usr/bin/env python3
"""R526 流水线: 因单文件结构变化而必须同步的测试/登记修正 (幂等)。"""
import io, os, json, re

ROOT = "/home/agentuser/AgentFramework"
os.chdir(ROOT)


def sub(path, old, new, must=True):
    t = io.open(path, encoding="utf-8").read()
    if new in t and old not in t:
        print(f"  = 已是目标态: {path}")
        return
    if old not in t:
        if must:
            print(f"  !! 未匹配: {path} :: {old[:60]!r}")
        return
    io.open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new, 1))
    print(f"  ✓ {path}")


# ① FlatDir helper + C2 目录级扫描
p = "src/agent.tests/EmptyBodyDiagnosisTests.cs"
t = io.open(p, encoding="utf-8").read()
if "FlatDir" not in t:
    sub(p, """    private static string Flat(params string[] relative)""",
        """    /// <summary>目录级扫描 (R526: 单类型单文件后, 逻辑层不再等于单一文件)。</summary>
    private static string FlatDir(params string[] relative)
    {
        var dir = Path.Combine(new[] { RepoRoot() }.Concat(relative).ToArray());
        var files = Directory.EnumerateFiles(dir, "*.cs", SearchOption.AllDirectories)
            .Where(f => !f.Contains($"{Path.DirectorySeparatorChar}obj{Path.DirectorySeparatorChar}")
                     && !f.Contains($"{Path.DirectorySeparatorChar}bin{Path.DirectorySeparatorChar}"))
            .OrderBy(f => f, StringComparer.Ordinal);
        return string.Join(' ', files.SelectMany(f =>
            File.ReadAllText(f).Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries)));
    }

    private static string Flat(params string[] relative)""")

sub(p, """        Assert.Contains("public string RequestId { get; set; }",
            Flat("src", "agent.modelqueue", "ModelQueueRouter.cs"));
        Assert.Contains("(\\"request_id\\", resp.RequestId)",
            Flat("src", "agent.modelqueue", "ModelQueueRouter.cs"));""",
    """        Assert.Contains("public string RequestId { get; set; }",
            FlatDir("src", "agent.modelqueue"));
        Assert.Contains("(\\"request_id\\", resp.RequestId)",
            FlatDir("src", "agent.modelqueue"));""")

# ② 指纹四层落点
sub("src/agent.tests/DecisionPromptFingerprintTests.cs",
    '"src/agent.modelqueue/LocalGenerationPort.cs",',
    '"src/agent.modelqueue/LocalGenerationOutcome.cs",   // R526: 原 LocalGenerationPort.cs 多类型已单文件化')

# ③ 计划链断言覆盖全部 partial
sub("src/agent.tests/PlanRoutingExecutionTests.cs",
    'var src = File.ReadAllText(Path.Combine(RepoRoot, "src", "agent", "IndustrialAgentV2.cs"));',
    '''// R526: 该类已按职责拆为多 partial 文件 (IndustrialAgentV2*.cs) — 断言覆盖全部片段
        var src = string.Join("\\n", Directory.EnumerateFiles(Path.Combine(RepoRoot, "src", "agent"), "IndustrialAgentV2*.cs")
            .OrderBy(f => f, StringComparer.Ordinal)
            .Select(File.ReadAllText));''')

# ④ 登记表: 插件实现单文件化后的 covers
reg = "docs/verification-registry.json"
d = json.load(open(reg, encoding="utf-8"))
hit = 0
for r in d["rows"]:
    if r.get("id") == "segment.plugin.router":
        c = [x for x in (r.get("covers") or []) if "(CodeReviewPlugin)" not in x]
        if "src/agent/registry/CodeReviewPlugin.cs" not in c:
            c.append("src/agent/registry/CodeReviewPlugin.cs")
            hit += 1
        r["covers"] = c
if hit:
    io.open(reg, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
print(f"  ✓ 登记表 covers 更新 {hit} 行")
print("测试/登记修正完成")
