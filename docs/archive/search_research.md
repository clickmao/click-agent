# 搜索方案调研与实施记录 (2026-09-05)

## 用户约束演进
1. 以 github.com/alex-on-ai/WebReaper 为基底, 或更优 **准确 + AOT** 方案
2. DDG 国内不可达 → 要求兼容国内环境
3. **插件化主备槽位**: 主要插件失败选备用; 多次失败则可用备源提升为主槽;
   槽位主次变化持久化, 下次启动复用
4. **免费源优先** (DDG/WebReaper), 失败再选付费 API
5. **凭据缺失必须问询真实用户**: 问询含作用说明 + 类型 flag; 回答持久化复用
6. **问询身份模型**: subagent 发起的问题, 回答者可能是主 agent 而非真实用户 ——
   凭据类 (RealUserOnly) 永远只接受真实用户回答, 策略类才允许主 agent 代答
7. 敏感操作 (删除文件/执行外部程序/系统配置) 在非 full 托管下必须主动问询

## WebReaper 事实核查 (GitHub API 实测)
- 真实存在: C#, MIT, 146★, v11.3.2 (2026-06)
- **本质是 scraper/crawler 而非搜索引擎**: 输入 URL 输出内容, 无按关键词发现 URL 的能力
- AOT: core `IsAotCompatible=true` (Newtonsoft-free); Cdp 卫星 AOT-clean
- core TFM=net10.0 (本工程 net8.0 不可 NuGet 引用) → 采用 **CLI 单二进制进程调用**
  (AOT 发布, 12MB, `webreaper scrape <url> --format md`), ArgumentList 传参无注入风险

## 已实施架构 (v6.0)

### 搜索层: 插件 + 主备槽位故障转移
- `ISearchProvider` 契约: Name/IsConfigured/DefaultPriority/SearchAsync
- 5 个插件 (全部 HttpClient + source-gen JSON/GeneratedRegex = Native AOT 零反射):
  | 插件 | 端点 | Key | 初始优先级 |
  |------|------|-----|-----------|
  | duckduckgo | html.duckduckgo.com/html/ (POST) | 免费 | 10 (主槽) |
  | bocha 博查 | api.bochaai.com/v1/web-search | 需 Key | 20 |
  | searxng | 用户实例 /search?format=json | 免费(自建) | 30 |
  | bingcn | cn.bing.com/search | 免费 | 40 |
  | baidu | www.baidu.com/s | 免费 | 50 |
- `SearchFailoverService`: 槽位序尝试 → 连续 3 失败熔断 (2min 冷却) →
  首个健康备源提升主槽 (原主槽降级队尾) → 槽位序+健康统计持久化 search_slots.json
- 缓存 1h / 500 条 LRU; 全源失败返回明确错误 (绝不伪造)

### 问询层: IUserPromptService
- `CredentialRequest` (Kind flag: ApiKey/Endpoint/ApiKeyAndEndpoint/ExternalToolPath)
  + Purpose 作用说明 + FallbackNote 降级说明
- `SensitiveOperationRequest` (Kind flag: CreateFile/DeleteFile/ModifyFile/
  ExecuteProcess/ExternalNetwork/SystemConfig)
- 身份/权威模型: `PromptOrigin`(AskedByAgentId/AskingDepth) + `AnswerAuthority`
  (RealUserOnly/MainAgentAllowed) + `PromptAnswerSource` 审计标记
  - 凭据类: 物理阻断 agent 代答, 只等真实用户
  - 敏感操作: Full 托管自动批(不可逆除外) / Standard 低风险主 agent 代答 /
    其余问真人; subagent 嵌套深度 >2 强制升级真人 (防层级代答闭环)
- 凭据持久化 credentials.json (0600 权限) + prompt_audit.jsonl 审计流水
- fail-closed: 无问询服务时删除操作直接拒绝

### 门禁接入点
- Workspace.DeleteFileAsync / DeleteDirectoryAsync → DeleteFile 审批 (RealUserOnly)
- SearchFailoverService.ExtractViaWebReaper → ExecuteProcess 审批 (主 agent 可代答)

### 抓取层
- WebReaper CLI 优先 (PATH 探测), 不可用降级内置 HTTP+HTML 提取
- WebReaperCliPath 可配置; ExternalToolPath 类型问询预留

## 清理的旧伪实现
- WebSearchService.cs 删除 (虚构 localhost:8080/api/search, FirstOrDefault 单条,
  写死 RelevanceScore=1.0)
- agent.core.SearchResultSource 重复枚举删除
- WebReaperEndpoint 死配置删除
- MAFService.IsConnected 伪状态 (仅看配置位) → 真实通信健康度
