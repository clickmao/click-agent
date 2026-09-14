# A/B v2.3.0 修前 -> 修后 (续引 [:NNN] 形态建模 + 本档 §1.4/§1.5/§3.3/§4.2 引用定点修复)
probe_version=2.3.0  corpus=docs 176 / inputs 591
before citations={'ok': 724, 'symbol_absent': 65, 'waived': 70, 'stale_lines': 4, 'retired': 5, 'stale_path': 24, 'relocated': 22}
after  citations={'ok': 734, 'symbol_absent': 65, 'waived': 70, 'stale_lines': 4, 'retired': 8, 'relocated': 13, 'stale_path': 21}
before cont={'ok': 53, 'retired': 6, 'stale_lines': 1, 'relocated': 7, 'waived': 2, 'stale_path': 1} tiers={'same_line_prev': 56, 'stem_symbol': 5, 'block_unique_prev': 7, 'waived': 2}
after  cont={'ok': 57, 'retired': 6, 'relocated': 3, 'waived': 2, 'stale_path': 1} tiers={'same_line_prev': 55, 'stem_symbol': 5, 'block_unique_prev': 7, 'waived': 2}
before gates={'G1_instrument_selfproof': True, 'G2_two_pass_identical': True, 'G2_verdict': True, 'G3_waiver_visible': True, 'G4_premise_refuted': True, 'G5_families_distinct': True, 'G6_cont_nontrivial': True, 'all_pass': True, 'measurable': True}
after  gates={'G1_instrument_selfproof': True, 'G2_two_pass_identical': True, 'G2_verdict': True, 'G3_waiver_visible': True, 'G4_premise_refuted': True, 'G5_families_distinct': True, 'G6_cont_nontrivial': True, 'all_pass': True, 'measurable': True}

# 本档 (docs/plans/v0.22.0-exp1-local-index-and-code-graph.md)
before 完整引用非绿={'symbol_absent': 2, 'stale_path': 3, 'relocated': 9}  续引={'ok': 40, 'retired': 6, 'stale_lines': 1, 'relocated': 4}
after  完整引用非绿={'symbol_absent': 2}  续引={'ok': 44, 'retired': 6}

## 本档 修后 残留非绿明细 (完整引用)
L54 [symbol_absent] src/agent/registry/CapabilityScanner.cs:33-35 sym=['AssemblyLoadContext', 'GetTypes'] absent=['AssemblyLoadContext'] attr=line
L69 [symbol_absent] src/agent.contextgradient/MessageRelevanceScorer.cs:73-73 sym=['ContextAssembler', 'ContextGradientCompressor'] absent=['ContextAssembler', 'ContextGradientCompressor'] attr=nearest_prev

## 本档 修后 续引全表 (tier / verdict / anchor)
L40 [:151] same_line_prev    ok          anchor=src/agent.rag/RAGConfig.cs inherited=None
L40 [:141] same_line_prev    ok          anchor=src/agent.rag/RAGConfig.cs inherited=None
L40 [:279] same_line_prev    ok          anchor=src/agent.rag/RAGConfig.cs inherited=None
L40 [:380] same_line_prev    ok          anchor=src/agent.rag/RAGConfig.cs inherited=None
L40 [:806] same_line_prev    ok          anchor=src/agent.rag/RAGConfig.cs inherited=None
L40 [:835] same_line_prev    ok          anchor=src/agent.rag/RAGConfig.cs inherited=None
L40 [:437-439] same_line_prev    ok          anchor=src/agent.rag/RAGConfig.cs inherited=None
L40 [:444-460] same_line_prev    ok          anchor=src/agent.rag/RAGConfig.cs inherited=None
L40 [:479-507] same_line_prev    ok          anchor=src/agent.rag/RAGConfig.cs inherited=None
L40 [:511-516] same_line_prev    ok          anchor=src/agent.rag/RAGConfig.cs inherited=None
L41 [:69] same_line_prev    ok          anchor=src/agent.rag/RAGConfig.cs inherited=None
L42 [:439-449] same_line_prev    ok          anchor=src/agent.workspace/Workspace.cs inherited=None
L42 [:413] same_line_prev    ok          anchor=src/agent.workspace/Workspace.cs inherited=None
L44 [:469] same_line_prev    ok          anchor=src/agent/contextassembler/ContextAssembler.cs inherited=None
L44 [:476-478] same_line_prev    ok          anchor=src/agent/contextassembler/ContextAssembler.cs inherited=None
L44 [:481-482] same_line_prev    ok          anchor=src/agent/contextassembler/ContextAssembler.cs inherited=None
L44 [:47] same_line_prev    ok          anchor=src/agent/contextassembler/ContextAssembler.cs inherited=None
L44 [:48] same_line_prev    ok          anchor=src/agent/contextassembler/ContextAssembler.cs inherited=None
L44 [:507-508] same_line_prev    ok          anchor=src/agent/contextassembler/ContextAssembler.cs inherited=None
L44 [:490] same_line_prev    ok          anchor=src/agent/contextassembler/ContextAssembler.cs inherited=None
L45 [:387] same_line_prev    ok          anchor=src/agent.vectormemory/VectorDocument.cs inherited=None
L45 [:166] same_line_prev    ok          anchor=src/agent.vectormemory/VectorDocument.cs inherited=None
L46 [:92] same_line_prev    ok          anchor=src/agent/keywordannotation/KeywordIndex.cs inherited=None
L46 [:11] same_line_prev    ok          anchor=src/agent/extensions/ServiceCollectionExtensions.cs inherited=None
L46 [:133] same_line_prev    ok          anchor=src/agent/extensions/ServiceCollectionExtensions.cs inherited=None
L52 [:54-118] same_line_prev    retired     anchor=src/agent/registry/CapabilityPlugin.cs inherited=True
L55 [:18-24] same_line_prev    ok          anchor=src/agent.skills/ScriptPluginRunner.cs inherited=None
L55 [:36-50] same_line_prev    ok          anchor=src/agent.skills/ScriptPluginRunner.cs inherited=None
L55 [:151-154] same_line_prev    ok          anchor=src/agent.skills/ScriptPluginRunner.cs inherited=None
L55 [:173-178] same_line_prev    ok          anchor=src/agent.skills/ScriptPluginRunner.cs inherited=None
L67 [:23] same_line_prev    retired     anchor=src/agent.embedcpu/BgeCpuEmbedder.cs inherited=None
L67 [:47] same_line_prev    retired     anchor=src/agent.embedcpu/BgeCpuEmbedder.cs inherited=True
L67 [:52] same_line_prev    retired     anchor=src/agent.embedcpu/BgeCpuEmbedder.cs inherited=True
L67 [:25] same_line_prev    retired     anchor=src/agent.embedcpu/BgeCpuEmbedder.cs inherited=True
L67 [:92-102] same_line_prev    retired     anchor=src/agent.embedcpu/BgeCpuEmbedder.cs inherited=True
L80 [:42] same_line_prev    ok          anchor=src/agent/contextassembler/ContextAssembler.cs inherited=None
L80 [:99] same_line_prev    ok          anchor=src/agent/contextassembler/ContextAssembler.cs inherited=None
L80 [:278] same_line_prev    ok          anchor=src/agent/contextassembler/ContextAssembler.cs inherited=None
L80 [:280-287] same_line_prev    ok          anchor=src/agent/contextassembler/ContextAssembler.cs inherited=None
L81 [:15] stem_symbol       ok          anchor=src/agent.workspace/Workspace.cs inherited=None
L81 [:16] stem_symbol       ok          anchor=src/agent.workspace/Workspace.cs inherited=None
L81 [:155-167] stem_symbol       ok          anchor=src/agent.workspace/Workspace.cs inherited=None
L82 [:653-659] same_line_prev    ok          anchor=src/agent/search/SearchFailoverService.cs inherited=None
L82 [:225] same_line_prev    ok          anchor=src/agent/search/SearchFailoverService.cs inherited=None
L83 [:184-195] same_line_prev    ok          anchor=src/agent.skills/SkillLifecycle.cs inherited=None
L89 [:393] same_line_prev    ok          anchor=src/agent.workspace/Workspace.cs inherited=None
L89 [:413] same_line_prev    ok          anchor=src/agent.workspace/Workspace.cs inherited=None
L89 [:432] same_line_prev    ok          anchor=src/agent.workspace/Workspace.cs inherited=None
L89 [:100-439] same_line_prev    ok          anchor=src/agent.workspace/Workspace.cs inherited=None
L90 [:101-440] block_unique_prev ok          anchor=src/agent.workspace/Workspace.cs inherited=None

## 修前 本档非绿续引 (v2.3.0 净新增发现)
L68 [:225-242] stale_lines anchor=src/agent.llamacpp/LlamaCppTextEmbedder.cs w=None
L80 [:42-42] relocated anchor=src/agent.contextassembler/ContextAssembler.cs w=None
L80 [:99-99] relocated anchor=src/agent.contextassembler/ContextAssembler.cs w=None
L80 [:278-278] relocated anchor=src/agent.contextassembler/ContextAssembler.cs w=None
L80 [:280-287] relocated anchor=src/agent.contextassembler/ContextAssembler.cs w=None

## 修前 本档 死引用续引 -> 留痕继承 (retired)
L52 [:54] inherited=True anchor=src/agent/registry/CapabilityPlugin.cs
L67 [:47] inherited=True anchor=src/agent.embedcpu/BgeCpuEmbedder.cs
L67 [:52] inherited=True anchor=src/agent.embedcpu/BgeCpuEmbedder.cs
L67 [:25] inherited=True anchor=src/agent.embedcpu/BgeCpuEmbedder.cs
L67 [:92] inherited=True anchor=src/agent.embedcpu/BgeCpuEmbedder.cs

## 本轮踩到的测量层自指实例 (入档)
附录 F 初稿把 L68 的**修复前原文**（含续引 [:NNN]）直接写进正文 ⇒ 机检把「记录缺陷的文本」当活引用:
  本档续引 waived +1 (continuation_unclaimed) / stale_lines +1 (错锚 llamacpp) / ServiceCollectionExtensions 侧 symbol_absent +1
处置: 引用示例移入 ``` 围栏 (仪器跳过围栏内容) + 去掉正文里的 [:NNN] 字面量 ⇒ 本档回到 symbol_absent=2 (均为 E.3 已裁定的主语型假阳性)

## 本轮踩到的写入通道缺陷 (入档)
两次实测: 长字面量里的斜杠被改写 (24h/7d -> 24h.7d, 逐字符 diff 定位) / 路径字面量匹配 0 命中
处置: 所有替换串由**文件自身派生** (行内 token / 正则), 标记常量由**码点**构造; 不再手打长字面量
