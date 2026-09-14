# A/B v2.1.0 -> v2.2.0 (同一语料, 同一次 peer 活跃窗口)
before verdicts={"ok": 651, "symbol_absent": 124, "waived": 70, "stale_lines": 4, "stale_path": 29, "relocated": 27}
after  verdicts={"ok": 709, "symbol_absent": 66, "waived": 70, "stale_lines": 4, "stale_path": 29, "relocated": 27}
before gate_all_pass=True exit=0
after  gate_all_pass=True exit=0
after  gate_bool={"G1_instrument_selfproof": true, "G2_two_pass_identical": true, "G2_verdict": true, "G3_waiver_visible": true, "G4_premise_refuted": true, "G5_families_distinct": true, "all_pass": true, "measurable": true}
after  retired_n=0  reloc_fact={"ok": 25, "symbol_absent": 2}
rows before=905 after=905

verdict 变化 (按条目, 非按键去重) transitions={"(('symbol_absent',), ('ok',))": 56, "(('symbol_absent', 'symbol_absent'), ('ok', 'symbol_absent'))": 2}
target doc before={"ok": 40, "symbol_absent": 18, "stale_path": 8, "relocated": 14, "waived": 1}
target doc after ={"ok": 55, "stale_path": 8, "symbol_absent": 3, "relocated": 14, "waived": 1}

## target doc: 仍是非 ok 的行 (v2.2.0)
L52 [stale_path] src/agent/registry/CapabilityPlugin.cs:14-48 sym=['ICapabilityPlugin', 'InitializeAsync', 'ProvidedCapabilities', 'capability_not_provided', 'invalid_capability_fqn', 'plugin_fault', 'plugin_not_registered'] attr=line absent=[] reloc=None rfact=None
L53 [stale_path] src/agent.tests/CapabilityPluginTests.cs:13-13 sym=[] attr=line absent=[] reloc=None rfact=None
L54 [symbol_absent] src/agent/registry/CapabilityScanner.cs:33-35 sym=['AssemblyLoadContext', 'GetTypes'] attr=line absent=['AssemblyLoadContext'] reloc=None rfact=None
L56 [relocated] src/agent/registry/ImageRenderPlugin/IImageRenderPlugin.cs:12-12 sym=['IImageRenderPlugin'] attr=nearest_prev absent=[] reloc=['src/agent.modelqueue/ImageRenderPlugins/IImageRenderPlugin rfact=ok
L56 [relocated] src/agent/registry/format/FormatRepair.cs:8-8 sym=['IFormatRepairPlugin'] attr=nearest_prev absent=[] reloc=['src/agent.exploration/FormatRepair.cs'] rfact=ok
L56 [relocated] src/agent/registry/segment/SegmentKind.cs:45-45 sym=['IResponseSegmentPlugin'] attr=nearest_prev absent=[] reloc=['src/agent/registry/SegmentKind.cs'] rfact=ok
L57 [stale_path] src/agent/registry/CapabilityPlugin.cs:37-37 sym=[] attr=nearest_prev absent=[] reloc=None rfact=None
L67 [stale_path] src/agent.embedcpu/BgeCpuEmbedder.cs:12-12 sym=['EmbedAsync', 'IsAvailable'] attr=line absent=[] reloc=None rfact=None
L68 [symbol_absent] src/agent/extensions/ServiceCollectionExtensions.cs:221-228 sym=['AGENTFRAMEWORK_BGE_MODEL', 'NullTextEmbedder'] attr=line absent=['AGENTFRAMEWORK_BGE_MODEL'] reloc=None rfact=None
L69 [symbol_absent] src/agent.contextgradient/MessageRelevanceScorer.cs:73-73 sym=['ContextAssembler', 'ContextGradientCompressor'] attr=nearest_prev absent=['ContextAssembler', 'ContextGradientCompressor'] reloc=None rfact=None
L69 [relocated] src/agent.llamalocal/EmbeddingRouter.cs:11-27 sym=['EmbeddingRouter'] attr=nearest_prev absent=[] reloc=['src/agent/llamalocal/EmbeddingRouter.cs'] rfact=ok
L69 [relocated] src/agent/agent/IndustrialAgentV2.cs:1118-1118 sym=[] attr=nearest_prev absent=[] reloc=['src/agent/IndustrialAgentV2.cs'] rfact=ok
L78 [stale_path] src/agent.embedcpu/BgeCpuEmbedder.cs:27-44 sym=[] attr=line absent=[] reloc=None rfact=None
L79 [relocated] src/agent.registry/CapabilityScanner.cs:24-30 sym=['_scanned'] attr=line absent=[] reloc=['src/agent/registry/CapabilityScanner.cs'] rfact=ok
L80 [relocated] src/agent.contextassembler/ContextAssembler.cs:41-41 sym=['CacheTtl'] attr=line absent=[] reloc=['src/agent/contextassembler/ContextAssembler.cs'] rfact=ok
L84 [relocated] src/agent.activity/ActivityService.cs:42-57 sym=['ActivityService'] attr=nearest_prev absent=[] reloc=['src/agent/activity/ActivityService.cs'] rfact=ok
L84 [relocated] src/agent/contextassembler/StickyRouteMemory.cs:36-37 sym=['StickyRouteMemory'] attr=nearest_prev absent=[] reloc=['src/agent.exploration/StickyRouteMemory.cs'] rfact=ok
L84 [relocated] src/agent/memory/ExecutorLessonMemory.cs:12-12 sym=['ExecutorLessonMemory'] attr=nearest_prev absent=[] reloc=['src/agent/execution/ExecutorLessonMemory.cs'] rfact=ok
L91 [relocated] src/agent.activity/ActivityService.cs:101-101 sym=['ActivityService'] attr=nearest_prev absent=[] reloc=['src/agent/activity/ActivityService.cs'] rfact=ok
L91 [relocated] src/agent.memory/SessionMemoryStore.cs:79-79 sym=['SessionMemoryStore'] attr=nearest_prev absent=[] reloc=['src/agent/session/SessionMemoryStore.cs'] rfact=symbol_absent
L91 [relocated] src/agent.tendency/TendencyData.cs:131-131 sym=['TendencyData'] attr=nearest_prev absent=[] reloc=['src/agent/tendency/TendencyData.cs'] rfact=ok
L151 [stale_path] src/agent/registry/CapabilityPlugin.cs:37-37 sym=[] attr=nearest_prev absent=[] reloc=None rfact=None
L169 [stale_path] src/agent.embedcpu/BgeCpuEmbedder.cs:27-44 sym=[] attr=nearest_prev absent=[] reloc=None rfact=None
L169 [relocated] src/agent.registry/CapabilityScanner.cs:24-30 sym=[] attr=nearest_prev_tail absent=[] reloc=['src/agent/registry/CapabilityScanner.cs'] rfact=ok
L181 [stale_path] src/agent/registry/CapabilityPlugin.cs:14-48 sym=[] attr=line absent=[] reloc=None rfact=None
L263 [waived] Program.cs:448-448 sym=[] attr=nearest_prev absent=[] reloc=None rfact=None