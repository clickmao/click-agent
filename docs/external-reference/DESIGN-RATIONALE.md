# Claude-Fable-5.1 泄露 system 的设计动因分析（机检取证版）

审计对象：`/tmp/fable51.md`（274,608 字符 / 2,196 行 / 311 个顶层锚点）。
所有数字均由脚本机检（`/tmp/fable_probe{,2,3}.py`），非人工目测。

## 一、拓扑读数

| 区域 | 字符区间 | 体量 | 占比 |
|---|---|---|---|
| 行为/记忆（身份→安全→语气→记忆系统+示例） | 0 – 96,083 | 96,083 | 35.0% |
| 工具使用规则（搜索/连接器/产物/可视化） | 96,083 – 161,245 | 65,162 | 23.7% |
| 工具 schema 附录（46 个 `<function>`） | 161,245 – 252,856 | 91,611 | 33.4% |
| 尾部：技能菜单 + 部署事实 | 252,856 – 274,608 | 21,752 | 7.9% |

分块方式：**全部**用 XML 标签或标题成块（`<product_information>`、`<memory_filesystem>`…），
块顺序固定；无 markdown 散文夹杂。

## 二、七条设计动因（逐条绑证据）

### 1. 前缀逐字节恒定 ⇒ 吃满前缀缓存
- 全文**没有日期、没有用户信息**：`<current_date>` / `<user_information>` 均不存在（`find` 返回 -1）。
- 正文显式写 **"The current date is (provided in the conversation below)"** ⇒ 时钟/用户态下沉到会话层。
- 推论：系统前缀跨天、跨会话、跨用户逐字节相同 ⇒ 前缀缓存恒命中；易变项只出现在 user 轮尾部。
- **R1 实测验证**：前缀 3,652 字符 sha `27a7be53f394f3ea` 跨 4 次调用恒定 ⇒ 第 2–4 次调用
  `prompt_cache_hit_tokens` 各 **1,408**（命中 85.0/88.2/86.5/88.0%），4 次合计 **86.9%**，新算仅 849 token。

### 2. 安全前置 + 每个能力边界再断言（不是一段总纲）
| 安全块 | 偏移 | 体量 |
|---|---|---|
| `<critical_child_safety_instructions>` | 4,960（全文 **1.8%** 处） | 6,622 |
| `<important_safety_reminders>` | 83,956 | 2,002 |
| `<CRITICAL_COPYRIGHT_COMPLIANCE>` | 137,409 | — |
| `<hard_limits>` | 141,562 | 801 |
| `<harmful_content_safety>` | 148,529 | 1,516 |
| `<critical_reminders>` | 150,045 | 3,933 |

硬门不在末尾统一收口，而是**紧贴各自能力段**（记忆、搜索、图像搜索各带一套）。
四个粗区间的负向/硬门词频近似均匀（6.1 / 4.8 / 6.9 / 6.4 per 10k 字符）⇒ 禁止项是**逐能力局部断言**。

### 3. 能力段模板化：何时用 → 格式 → 落位 → 校准 → 反例
`<memory_filesystem>`(29,091) 的子块次序即模板：
`What's already filed` → `File format` → `Where it goes` → `When to write` → `Calibration` →
`Read before writing` → 示例 → `<privacy_requirements>`/`<protected_attributes>`/`<sensitive_information>`
→ `<never_store>`/`<forbidden_memory_phrases>`/`<appropriate_boundaries_re_memory>`。
即：**每个能力都先给规格、再给反规格**，而不是只描述功能。

### 4. 对比式 few-shot 代替抽象规则
计数：`<example_user_memories>`×18、`<good_response>`×17、`<bad_response>`×4、`<rationale>`×7。
形态固定为 `user → good_response [+ bad_response] [+ rationale]`：
复杂语义用**正例+反例+理由**编码，而不是形容词堆叠。

### 5. 工具契约自带准入/排除判据与终止语义
- schema 描述中位 820 字符、最长 4,380（描述合计 42,836 = schema 区 46.8%）；
  例：`comparison_card_display_v0` 里写 **"DON'T use this card when: … use featured_card_display_v0 instead"**
  ⇒ 互斥工具**互相指路**；
- 反造假写进参数描述："Omit if you don't have a real one — **never fabricate a link**"；
- 终止语义写进描述："**After calling this, your turn is done** … Don't keep writing"（`ask_user_input_v0`）。
⇒ 工具描述 = **调用协议**，不是使用手册；散文里不重复 schema。

### 6. schema 附录机器可读、可 diff
46 个工具**按名字字母序**（机检 `names == sorted(names)` 为 True），两个重名变体；
33.4% 的体量花在 schema 上，换来的是：确定性顺序 ⇒ 跨版本 diff 稳定、缓存稳定。

### 7. 尾部锚定"部署事实"
- `<available_skills>` 菜单 @265,649（skills 区只给 name/description/location 菜单 + 明令
  "Reading the relevant SKILL.md is a **required first step** before writing any code"，并给 3 个微型示范）；
- `<network_configuration>` @273,458（出口白名单 22 个域 + `x-deny-reason` 头）；
- `<filesystem_configuration>` @274,213（只读挂载 5 个目录 + "先拷到工作目录再改"）。
⇒ 部署/环境差异集中在尾部，主前缀不动。

## 三、R1 明确不采用（避免照抄）
- `<product_information>`（商用身份/产品线话术，无功能价值）；
- 第三方 MCP/连接器推荐与目录、可视化卡片族（12 个 `*_display_v0`）、图像搜索、
  `end_conversation` / `past_chats` / `artifacts` 发布面 —— 与本项目能力面无关；
- few-shot 的**商业话术样例**（早餐/午餐类）—— 只借**三元组形态**，不借内容。
