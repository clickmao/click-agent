# Role（扮演角色）使用说明 — v0.21.0

> Role 是 click-agent CLI 的"扮演角色"系统：给 agent 加上**性格、自身倾向和跨会话的成长经历**。
> 唯一形态 = **单文件 `.rbin` 外挂**（非明文、压缩友好、快读快写、可扩展）。
> 设计与工程细节见 `docs/plans/v0.21.0-role-system-plan.md`；本文只讲怎么用。

## 1. 快速开始

```
# 挂载角色启动（可空 —— 不传即无角色，行为与默认完全一致）
agenthost --role ./my-role.rbin

# 无角色
agenthost
```

启动后 Role 的语风种子与成长实况会注入 system 块；外部前端可用 `role.info` 查看实况。

## 2. .rbin 文件格式（为什么不是明文）

| 层 | 内容 |
|---|---|
| 头 16B | magic `ARBL` + version + flags + 压缩长度 + 原始长度 |
| 载荷 | `AES-256-GCM( gzip( JSON 文档 ) )` |

- **密钥**：`data/master.key`（持久主密钥，与凭据加密同层级）。跨会话可解；**换机器不可解**（密钥不随文件走）。
- **可扩展**：JSON 中未知的 `x:` 前缀键在读写往返中自动保留 —— 未来版本加字段不会丢数据。
- **原子写**：`tmp + rename`，写入过程崩溃不会留下半个文件。
- 实测：700B 文本的人格包 → **306B**（压缩 + 加密后）。

## 3. 文档模型（API 读写的载体）

```
Id           角色 id（如 "skeptic"）
Name         显示名（如 "疑问者"）
ProfileSeed  人格种子语料（可空 —— 无种子时角色完全由赏罚动态构成）
Growth       域 → (赏, 罚) 计数（成长账本持久化）
TokensUsed   累计 token（可观测）
Extra        任意自定义键值（扩展保留区）
```

## 4. API（读取 / 修改 / 写入）

```csharp
var key = CredentialEncryption.LoadOrCreateMasterKey("data");

// 读
var doc = RoleBinaryFile.Read("my-role.rbin", key);

// 改（任意字段）
doc.Name = "疑问者·改";
doc.Growth["docker"] = (0, 5);
doc.Extra["custom-note"] = "v2";

// 写（原子替换）
RoleBinaryFile.Write("my-role.rbin", doc, key);
```

- 读写失败语义：非 `ARBL` 文件 / 版本不支持 → `InvalidDataException`；篡改或密钥错误 → `CryptographicException`（GCM 认证拒绝，绝不返回脏数据）。

## 5. 四种"区别"从哪来

1. **性格区别** = `ProfileSeed` 语料。写**示例对话**，别堆形容词——LLM 模仿示例远强于服从标签。
2. **能力区别** = 成长账本中的域分布（哪些域被赏/被罚），影响后续同域策略。
3. **自身倾向** = 由赏罚**自然涌现**，无需手写规则：
   置信度 `(赏+1)/(总+2)`（Laplace 平滑）→ `<0.4 先怀疑` / `>0.7 信任` / 样本 <5 观察中。
   例：docker 域被纠正 5 次 → 置信度 0.143 → 下次 docker 问题先要证据再答。
4. **成长经历** = `Growth` 计数跨会话保持；`data/roles/{id}.growth.json` 累积增量后回写文档。

**怀疑的表现是提问与前提澄清，不是拒答**——这是产品语义边界。

## 6. 推理中止（自体失败信号）

- 检测：LLM 超时 / token 超限 / 自证循环（窗口 3 轮回复 trigram 相似度 ≥0.95 = 原地打转）。
- 归类：失败问题按指纹入簇（`data/roles/failureClusters.json`）。指纹为**进程间稳定**实现（FNV-1a + 序数排序，不走运行时字符串 hash）—— 落盘后重启仍命中同簇，跨 locale 不漂移。
- 前置注入：某簇罚分 ≥3 → 该主题新问题自动获得策略警告（先澄清边界 → 降级方案 → 诚实说明做不到的部分）。

## 7. 门禁（重要）

**赏罚是 Role 的能力**：未挂载 `.rbin` 时整链失效 ——
不起后台判定 Task、不调 LLM（0 token 消耗）、不写失败簇、联想前置注入自动关闭。
无角色运行与不含本系统的版本行为一致。

## 8. 写好 ProfileSeed 的三条军规

1. 用"你"开头写守则，给 2-3 个真实感示例对话。
2. 语料 ≤2KB（超限截断，不报错）。
3. 想要"观感不同"，改语料；想要"态度不同"，靠赏罚积累（别手写规则）。
