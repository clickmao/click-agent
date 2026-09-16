using System;
using System.Linq;
using Microsoft.Extensions.DependencyInjection;
using agent;
using agent.context;
using agent.intent;
using agent.registry;

// ── R391 真机挂载探针 (C7/C8): 用**生产组合根**装配, 不看源码猜 ──────────
var services = new ServiceCollection();
services.AddAgentFramework();
using var sp = services.BuildServiceProvider();

// C8: 插件在场性 ⇒ 静态前缀条件注入
var names = sp.GetServices<IResponseSegmentPlugin>().Select(p => p.Name).ToList();
var present = FormalPromptContract.IsPresent(names);
const string root = "/home/agentuser/AgentFramework";
var withContract = SessionBaseline.Build(root, present);
var without = SessionBaseline.Build(root, false);
Console.WriteLine($"A_plugins=[{string.Join("|", names)}]");
Console.WriteLine($"A_formal_present={present}");
Console.WriteLine($"A_prefix_has_clickproof={withContract.Contains(FormalPromptContract.FenceLanguage, StringComparison.Ordinal)}"
                + $" absent_has_clickproof={without.Contains(FormalPromptContract.FenceLanguage, StringComparison.Ordinal)}");
Console.WriteLine($"A_prefix_chars={without.Length}->{withContract.Length}"
                + $" delta_tokens_est={FormalPromptContract.EstimateTokens(withContract) - FormalPromptContract.EstimateTokens(without)}");

// C7 消费侧: 经 **DI 解析出的真实实例** 处理含围栏的模型回复 (恒等透传 + 本地裁决)
var plugin = sp.GetServices<IResponseSegmentPlugin>().OfType<ClickRoverSegmentPlugin>().Single();
var seg = new ResponseSegment { Kind = SegmentKind.Code, Content = "premise x >= 0\ngoal x > 0", Language = ClickProofFence.Language };
var back = await plugin.HandleAsync(seg);
Console.WriteLine($"B_segment_identity={back == seg.Content}"
                + $" reports={string.Join(",", plugin.DrainReports().Select(r => r.Verdict + "/allowed=" + r.Allowed))}");

// C7 编排侧: 真跑计划 —— 容器里**没有任何 LLM 调用面**, 若节点被误判远程必然硬失败
var plan = new TaskPlan { SourceText = "R391 真机挂载探针: 本地形式化验证链" };
var n1 = new PlanNode { Id = "n1", Text = "```clickproof\npremise x >= 0\npremise x <= 10\ngoal x <= 20\n```", Intent = IntentRecognizer.Intents.General };
var n2 = new PlanNode { Id = "n2", Text = "```clickproof\npremise x >= 0\ngoal x > 0\n```", Intent = IntentRecognizer.Intents.General };
n2.DependsOn.Add("n1");
// C7 路由侧: 走**真实路由函数** (机器可读围栏 ⇒ 判本地 formal.verify)
plan.Nodes.Add(n1);
plan.Nodes.Add(n2);
PlanRoutePolicy.Apply(plan);
foreach (var nd in plan.Nodes)
    Console.WriteLine($"C_route={nd.Id} intent={nd.Intent} location={nd.Location} exec={nd.LocalExecutorId ?? "-"}");

var run = await new PlanRunner(gate: () => true).RunAsync(plan, new LocalNodeContext());
Console.WriteLine($"C_run_state={run.State}");
foreach (var o in run.Outcomes)
    Console.WriteLine($"C_node={o.NodeId} loc={o.Location} exec={o.ExecutorId ?? "-"} state={o.State} tokens={o.Tokens}");
Console.WriteLine($"C_n1_proved={run.Outcomes.Any(o => o.NodeId == "n1" && o.State == PlanNodeState.Completed)}"
                + $" n2_blocked={run.Outcomes.Any(o => o.NodeId == "n2" && o.State == PlanNodeState.Failed)}"
                + $" total_llm_tokens={run.Outcomes.Sum(o => o.Tokens)}");
