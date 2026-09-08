# click-agent (v0.13.0-dev)

[![ci](https://github.com/clickmao/click-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/clickmao/click-agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![.NET](https://img.shields.io/badge/.NET-10.0-512BD4)
![Tests](https://img.shields.io/badge/tests-409%2F409-brightgreen)
![Eval](https://img.shields.io/badge/thousand--round%20eval-1034%2F1056-success)
![NativeAOT](https://img.shields.io/badge/NativeAOT-zero%20warnings-blueviolet)

> CI workflow file is ready (`.github/workflows/ci.yml`); badge activates once pushed with a `workflow`-scoped token.

C# agent framework built on Microsoft MAF (Microsoft Agent Framework) & WebReaper — full-scenario coverage, 100% managed code. net10.0 / NativeAOT zero warnings / 355 tests green.
Release line: v0.11.0 — unified @cmd command protocol + 3 transports / Skill executive scripts / vector-blended relevance scoring / 19-model catalog.

[🇨🇳 中文 → README.md](README.md)

---

### 🚧 v0.13.0/v0.13.1 In Development — Think-Chain Convergence / Progressive Exploration / Sticky Fallback Routing
- **Progressive exploration** (user-directed): ExplorationConfig (max steps per context-block/text/url/dir + global budget + URL depth) + ExplorationPlanner (priority queue; URL found in context outranks external directory) — 7 tests.
- **Think-chain T3** (user-directed): ComplexityGate + EvidenceScorer (multi-source required for high; single source capped medium) + ThinkMemory RAG association (preferentially browse high-confidence history links, +0.05 citation boost, negative-outcome penalty, 30d decay) + ThinkChainSession convergence criteria — 12 tests.
- **Sticky fallback routing v0.13.1** (user-directed): FallbackConfig (config switch, cost-quality order = auto-sourced ranking, per-fallback reply verification) + StickyRouteMemory (similar questions reuse the previously successful model; triple-gate: embedding similarity + intent + entity fingerprint; TTL 72h) — Router sequential fallback chain landed, 11 tests.
- Design docs: docs/plans/v0.13.0-progressive-exploration.md · v0.13.0-think-chain-convergence.md · v0.13.1-fallback-sticky-routing.md

### ✅ v0.12.0 Additions — Vision / Render Plugins / Convergence Loop (Accepted)
- **Vision chain**: CLI `-img` → data URL base64 → glm-5.3-flash v4 endpoint (1M ctx); text-only model auto-reroute + coding-endpoint rewrite (defects 63/64 fixed); OpenAIMultimodalMessage dual-form DTO (AOT-safe).
- **Live acceptance**: T-V01~T-V04 vision family first full-23 pass ALL GREEN (incl. negative bait: model rejected the false "apple at bottom-right" premise); four-question live verification; baseline doc docs/reports/v012-acceptance-baseline.md.
- **Image render plugin system** (user-directed): IImageRenderPlugin + SkiaSharpRenderPlugin (default, edge option -p:DisableSkiaRenderer=true) + SvgTextRenderPlugin (zero-dependency fallback) + Registry (no renderer → skip downstream); LocalSvgRenderer DSL.
- **Convergence loop E2E**: LLM DSL → render → 5.3-flash vision verification — one-round live PASS (1039ch DSL → 843ch SVG → 6/6 checks, 6.4s).
- **Capability matrix**: 25/25 models in models.yaml; CogViewClient retained (generation path deprecated per user directive).

### 📦 v0.11.0 R169-R204 Additions

Archived → [CHANGELOG-v0.11.0-R169-R185.md](docs/changelogs/CHANGELOG-v0.11.0-R169-R185.md) · [CHANGELOG-v0.11.0-R186-R204.md](docs/changelogs/CHANGELOG-v0.11.0-R186-R204.md)

### 📊 Thousand-Round Eval (PGO-driven)
- **1034/1056 = 97.92%** case pass (215 rounds landed); quick-batch tokens **7354 → ~3969 avg**; C08 reasoning completion **1875 → 479 (-74%)**; 55 real defects fixed, all telemetry-driven.
- Batch trend: **batch204 (mass_422)** 11/11 quick-11 915/case / **batch205 (mass_423)** 11/11 quick-11 995/case — full-23 (vision family T-V01-04) 23/23 first pass; stable after defect 65/66/67/68 fixes. Archives: [42-78](docs/changelogs/CHANGELOG-v0.11.0-R143-R152.md) · [79-108](docs/changelogs/CHANGELOG-v0.11.0-R153-R168.md) · [109-138](docs/changelogs/CHANGELOG-v0.11.0-R169-R185.md) · [139-167](docs/changelogs/CHANGELOG-v0.11.0-R186-R204.md) · [168-177](docs/changelogs/CHANGELOG-v0.11.0-R205-R218.md) · [178-187](docs/changelogs/CHANGELOG-v0.11.0-R219-R228.md). Roll every 30 batches (next: batch228).
- Full report: [Thousand-Round Report](docs/reports/thousand-round-report.md) · ledger: [wave3-ledger](docs/reports/wave3-ledger.md)

### 🧭 Full Capability Panorama (v0.11.0)

**Reasoning & Tasks**
- Intent analysis & sub-task decomposition: 19 CN/EN connectives, Sequential/Parallel/DependsOnOutput relations
- TaskPlan topological execution: level concurrency (Task.WhenAll + MaxParallelism), node retry (exponential backoff + transient classification), sensitive intents (file/git) PausedForApproval
- Isolated tasks: unrelated questions spawn boundary-isolated sub-agents (independent session, no main-memory pollution), destroyed on completion

**Model Scheduling (agent.modelqueue)**
- Three-channel hybrid: Local (LocalLlamaCaller real runs) > Official (hardcoded + in-memory keys) > Remote API
- Model catalog: 18 models (OpenAI/Anthropic/Google/xAI/DeepSeek/Zhipu/Qwen/Moonshot), intent x token-estimate x cost ranking
- auto/manual dual-mode: `/model list` index 1-N; auto-switch on consecutive failures
- Token stats + balance linkage: initial API sync -> local accumulation -> threshold re-sync; insufficient balance switches model + `flags:balance-insufficient`
- Configurable proxy for official endpoints (models.yaml proxy section)

**Vision & Image (v0.12.0 accepted)**
- Vision chain: CLI `-img` -> base64 data URL -> glm-5.3-flash v4 (1M ctx); text-only auto-reroute + coding-endpoint rewrite; dual-form DTO (AOT-safe)
- Render plugins: IImageRenderPlugin (SkiaSharp default w/ edge-opt-out / SVG-text fallback) + LocalSvgRenderer DSL; convergence loop E2E (DSL->render->vision-verify->regenerate->pass)
- Case family T-V01~04 (incl. negative bait) full-23 23/23; baseline docs/reports/v012-acceptance-baseline.md

**Exploration & Think-Chain (v0.13.x in dev, user-directed)**
- Progressive exploration: ExplorationPlanner (max steps per context-block/text/url/dir via config; in-context URL outranks external dir)
- Think-chain convergence: ComplexityGate + EvidenceScorer (multi-source, single-source capped medium) + ThinkMemory RAG association (prefer high-confidence history links, +0.05 citation boost)
- Sticky fallback routing: FallbackConfig (config switch + cost-quality order + sequential fallback verification) + StickyRouteMemory (similar questions reuse successful model; triple-gate)
- Format-repair loop: IFormatRepairPlugin (fenced->search->validate->local-fix->LLM round; max_llm_rounds; skill-matrix)
- RAG data file user-selectable: CLI `-rag <path>` / task `/rag` / env (multi-library isolation)

**Skill Dispatch (agent.skills)**
- SKILL.md directory packages (Anthropic Agent-Skills Open Standard) + legacy yaml coexistence
- Four-level triggering: keywords -> regex -> domain words -> bge semantic (cos >= 0.45), suspected-hit activates
- Lifecycle state machine (LRU/off-domain unload/circuit breaker) + sandboxed context + timeout/idempotent retry

**Context & Memory (agent.contextgradient)**
- Gradient compression: L0 raw/L1 digest/L2 index/L3 archive; P0-P3 anchors (P0 never compressed)
- Topic clustering + triple drift verification (rollback on failure, 10-version chain) + cross-process persistence
- Rolling session memory + GoalProfile + AgentProfile dynamic learning + next-turn forecast persistence

**Config & Output**
- Four-layer YAML config (base/env/modules/runtime): deep merge, @dynamic hot-reload, startup strict validation
- YAML parsing: Yamlify (SourceGenerator-level, zero reflection, AOT zero warnings)
- Unified output: IOutputSink all exits (logs/approvals/frontend directives/step status), zero direct Console writes in libraries
- Log 4-channel switches + thinking stream chunks (`@chatbox:` JSON protocol lines)

**Engineering**
- agent.io protocol library (netstandard2.1, zero deps): single-line events + @stream blocks
- Session interruption recovery: ExecutionCheckpoint atomic persistence, restart restores progress
- NativeAOT: 0 IL warnings end-to-end, 12MB single-file ELF
- Capability plugin interface: ICapabilityPlugin (workspace/tests/review by developers)

### 🚀 v0.9.0 Capability Overview (Requirements 1-6)
- **Three-channel Model Scheduling**: Local model > Official channel > Remote API, fixed priority; Channel concurrency management; Sub-tasks selected by concurrency margin × inference capability × inference speed × price; Official models hardcoded (not in yaml), keys only injected via CLI `--official-key` / `/official-key` (in-memory)
- **agent.io Protocol Library**: netstandard2.1 zero dependency; Single-line events (text/chatbox directives/JSON) + `@stream` multi-line stream block dual-mode read/write, frontend `Console.ReadLine()` line-by-line parsing
- **Session Interruption Recovery**: Task step checkpoints (atomic disk persistence) — Direct execution progress restoration after unexpected interruption
- **Public Configuration Read/Write**: ConfigWriter (dot-path / L3 deep merge / L4 runtime), separated from ConfigSnapshot read/write
- **Capability Plugin Interface**: ICapabilityPlugin — Workspace management/test integration/code review implemented by developers (framework defines contract, see [Capability Enhancement Plan](docs/industrial_enhancements.md))

### 💬 Intelligent Inquiry
- 18 inquiry data type enumerations + pure rule validation (numbers/dates/selections/paths...)
- Batch inquiry: Ask all at once by group, not one by one
- Sub-task confidence + evidence supplementation + maximum question limit
- Inquiry preference library: Record **preference patterns** (not credentials/original values) cross-session reuse

### 🎨 Dual-mode Output
- Markdown / Plain text dual modes, Spectre.Console console color beautification
- All return content (answers/inquiries/logs/approvals) unified underlying structured format
- Inter-agent inquiry silent mode (zero user interface disturbance)

### 🎯 Intent Analysis and Sub-task Decomposition
- **IntentDecomposer**: Complex sentences split into sub-task sequences by connectors, four-level relationship annotation — `Sequential` (then/next, preserve execution order), `Parallel` (simultaneously/and, same-level parallel), `DependsOnOutput` (based on, data dependency); Connectors themselves are splitting points, sentence mis-splitting intercepted by boundary protection
- **19 Chinese-English connectors**, English word boundary matching (`and` doesn't split `android`), single-character connectors must attach to non-Chinese characters on both sides to split ("再次检查" not mis-split)

### 📋 Task Plan Diagram (TaskPlan)
- `TaskPlanBuilder` decomposes sub-tasks into dependency topology graph (Level分层 + ParallelGroup parallel groups)
- **UI JSON Contract**: Nodes contain `Text/Intent/DependsOn/Level/ParallelGroup/Parameters/Clarifications/IsExecutable`, source-gen serialized (AOT safe), directly available for external UI rendering
- Sensitive intents (file operations/git operations) default to `PausedForApproval`, full plan pause pending approval
- Parameter missing generates `Clarification` inquiry nodes, **parameter-independent nodes don't block联动**

### 🔌 Inquiry Protocol
- `IUserPromptService` unified inquiry: Credential requests (`CredentialRequestKind`), approval requests, parameter clarification
- `AnswerAuthority` authority hierarchy: Normal parameters MainAgent can answer, sensitive operations must real user (`RealUserOnly`)
- Non-interactive environments (pipe/CI) automatically degrade, honestly skip without fabrication

### 🛠 Local Mandatory Commands (non-LLM)
- `LocalCommandRouter` intercepts before intent recognition: `/stop` `/continue` `/pause` `/status` `/reset`, zero token consumption

### 📦 Persistent Identity and Next-turn Forecast
- `AgentRegistry`: Main/sub-agent persistent UID + subordination relationship, cross-process reuse
- `NextTurnForecast`: Generate next-turn forecast after task cycle completion, read back on next conversation after shutdown, indicates LLM user input tendency; isolated by Agent UID

### 🧩 Post-processing Segment Marking (pluginized)
- `ResponseSegmenter` quickly marks fenced segments in LLM return content (```html → UI consumption, code blocks → review services, etc.)
- Routing rules pluginized, `IResponseSegmentPlugin` register-to-use, not hardcoded

### 🧠 Memory and Context
- Multi-data source context injection: Memory + Session + Web + UserTendency automatic assembly
- Keyword recall algorithm performance governance: 10k messages `GetRecentMessages` **5424µs → 256µs (21.2x)**, semantic equivalent逐条验证
- Session history Trim upper limit governance, unbounded growth eradication

### 🔍 Search Integration (main backup slots)
- Built-in multi-search source plugins + main backup failover (3 failures熔断 2 minutes, slot sequence persistent `search_slots.json` reuse)
- WebReaper 11.3.1 library direct引用, search results full-text enhancement

### 🦙 Local Inference
- Vendored LLamaSharp fork (ed89226) single-entry loader, `LocalLlamaCaller : ILLMCaller` cloud failure fallback; Vulkan loader unified with Silk.NET
- Honest error reporting when model files missing, no fabricated replies

## Quick Start

```bash
git clone https://github.com/clickmao/click-agent.git
cd click-agent
dotnet restore
dotnet build
```

### CLI Usage

```bash
cd src/agent.host

# Interactive REPL (step details + /status status query + markdown rendering)
dotnet run

# Single mode
dotnet run -- -q "First search AOT materials, then write summary document"

# Output log save as markdown file
dotnet run -- --log run.md -q "your task"
```

CLI built-in commands: `/status` (current status/step details/next-turn forecast), `/reset`, `/exit`; each execution shows `[01] Intent Analysis → [02] Sub-tasks → [03] Pipeline → [04] Segment Marking` step chain.

### Code Usage

```csharp
using Microsoft.Extensions.DependencyInjection;
using agent;            // IndustrialAgentV2 / AgentContext
using agent.core;       // Message / MessageRole

var services = new ServiceCollection();
services.AddAgentFramework(o =>
{
    o.DataStoragePath = "./data";
    o.MaxSubAgents = 4;
});
await using var provider = services.BuildServiceProvider();

var agent = provider.GetRequiredService<IAgent>();
var ctx = new AgentContext(provider) { SessionId = "s1", UserId = "u1" };
await agent.InitializeAsync(ctx);

var reply = await agent.ProcessAsync(new Message
{
    Role = MessageRole.User,
    Content = "First search .NET 10 new features, then write summary based on results",
    SessionId = "s1"
}, CancellationToken.None);
Console.WriteLine(reply.Content);
```

### Template Query

```csharp
using agent.templates;

var templates = provider.GetRequiredService<ITemplateStore>();
var found = await templates.QueryAsync(new TemplateQuery { Category = "DSL" });
```

## Project Structure

```
click-agent/
├── agent.sln
├── src/
│   ├── agent/               # Core: Intent decomposition/Task planning/Registry/Segment routing/Local inference
│   ├── agent.core/          # Base contracts: Message/AgentContext/IAgent
│   ├── agent.config/        # 4-layer YAML config: ConfigSnapshot/ConfigWriter/MiniYaml (Yamlify facade)
│   ├── agent.modelqueue/    # Model queue: Router/Catalog/ChannelScheduler/BalanceQuery/TokenUsage
│   ├── agent.skills/        # Skill dispatch: Registry/TriggerMatcher (bge)/PackageLoader (SKILL.md spec)
│   ├── agent.contextgradient/ # Gradient compression: layers/anchors/clustering/drift check + BgeEmbedder
│   ├── agent.logging/       # Log 4-channels + IChatboxSink (@chatbox: protocol lines)
│   ├── agent.io/            # Protocol library (netstandard2.1): line protocol/stream blocks
│   ├── agent.output/        # Output pipeline: Formatter/Spectre rendering
│   ├── agent.host/          # CLI host (NativeAOT, IOutputSink)
│   ├── agent.codegen/       # Code generation
│   ├── agent.recovery/      # Session recovery: ExecutionCheckpoint
│   ├── agent.rag/           # RAG recall
│   ├── agent.vectormemory/  # Vector memory
│   ├── agent.workspace/     # Workspace
│   └── agent.tests/         # 409 tests
└── docs/                    # Architecture/API/improvement records/plans
```

## Validation Baseline

| Item | Result |
|---|---|
| Compilation (--no-incremental) | 0 errors 0 warnings |
| Tests | 409/409 Passed |
| NativeAOT (linux-x64) | 0 IL/TR warnings (re-verified 6x) + AOT smoke pass |
| Thousand-round eval | 1034/1056 = 97.92% (215 rounds landed) |
| Real 3-endpoint E2E | glm/deepseek chat+balance OK; kimi negative sample honest error |
| Threshold switching | live-fire proven (deepseek $1.25 → glm) |
| bge real chain | JIT+AOT dual acceptance (dim512, 282ms) |

## Documentation

- [Architecture Document](docs/architecture.md)
- [API Document](docs/api.md)
- [CLI Command Instructions](docs/CLI指令说明.md) — All commands + agent.io line protocol (requirement 2)
- [Iteration Master Plan](docs/reports/iteration-master-plan.md) — methodology: constitution / 5 KPI / triggers / negative-data design / authenticity defenses (living doc)
- [Main Report · Dynamic Telemetry & Rollback](docs/reports/dynamic-telemetry-eval-rollback-strategy.md) — status layer (living doc, updated per round)
- [Test Dimensions Ledger](docs/reports/test-dimensions-ledger.md) — 15-dimension panorama + negative family + anti-forgetting policy
- [Improvement Records](docs/improvements.md) — historical release notes & plan archive
- [Task Loop](docs/task_loop.md) · Historical plans: docs/archive/

### 🗺 Next Development Plan (v0.11.0)

> Historical plan (v7.15 ten nodes - all landed) archived in [improvements.md](docs/improvements.md); per-module design details in docs/archive/.

1. **K1 effect closed loop**: profile-driven reply-quality diff (with/without persona rel comparison) — snippet actionable since R141, LLM behavioral benefit pending verification
2. **Batch 56+ thousand-round loop** (quick-10 expanded coverage) + semantic_avg tier observation + per-5-batch audit
3. **K4 long-horizon watch**: skill false-absorption suppression stability + negative-family expansion (8-class checklist toward 25%)
4. **Real-GPU Vulkan test** (needs real GPU; llvmpipe only on this host)

> **Current baseline (R151)**: 409/409 tests green / NativeAOT 0 IL warnings / thousand-round eval 97.92% (215 rounds) / 5-KPI full observability — next: K1 effect verification (profile-driven reply diff), semantic_avg tier observation, negative-family expansion.

## Configuration

Configuration files **unified YAML** (`config/` four-level分层, based on "Full Module YAML Configuration Development Specification"), `appsettings.json` deprecated (migration period compatible reading and warning):

```
config/
├── base/            # L1基础默认 (随版本发布,禁止本地修改): core.yaml
├── env/             # L2环境覆盖: development.yaml / production.yaml (AGENTFRAMEWORK_ENV选择)
├── modules/         # L3模块定制: 同名文件覆盖base同名节 (增量覆盖,未写字段继承)
└── runtime/         # L4动态配置: dynamic.yaml (热更新,仅 @dynamic项生效)
```

```yaml
# config/base/core.yaml (节选,完整见文件)
agent:
  agent_name: MainAgent
  max_sub_agents: 4
  enable_search_cache: true
  summarize_after_turns: 10

openai:
  api_key_env: AGENT_OPENAI_KEY   # 只存环境变量名, Key本身不落配置
  model: gpt-4
```

**Override priority**: `runtime/dynamic.yaml` > `modules/{module}.yaml` (同名覆盖base,用户钦定契约) > `env/{env}.yaml` > `base/{module}.yaml`; deep merge, undefined fields automatically inherit lower层. API Key优先走环境变量 `AGENT_OPENAI_KEY`;未配置时走 `NullLLMCaller`明确报错路径,不静默伪造.模块代码只调 `agent.config.ConfigSnapshot`,禁止自行读 yaml文件.

## License

MIT License