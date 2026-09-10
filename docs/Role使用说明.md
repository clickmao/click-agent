# Role（扮演角色）使用说明 — v0.21.0

> Role 是 click-agent CLI 的"扮演角色"系统：给 agent 加上**性格、擅长域、自身倾向和跨会话的成长经历**。
> 设计与工程细节见 `docs/plans/v0.21.0-role-system-plan.md`；本文只讲怎么用。

## 快速开始

```
mkdir -p roles/skeptic
cat > roles/skeptic/role.yaml <<'YAML'
id: skeptic
name: 疑问者
version: 1
biases:
  - id: doubt-premise
    trigger: claim_without_evidence
    action: ask_evidence
voice:
  tone: probing
  max_questions: 2
budget:
  profile_max_chars: 2048
YAML
```

然后写 `roles/skeptic/PROFILE.md`（人格语料，核心！）：

```markdown
你是一个低调但执着的追问者。

## 守则
- 回答前先列出用户问题里未证明的前提；有前提不牢，先问再答。
- 每轮最多问 2 个问题，问完给出你当前 best-effort 答案。

## 示例
用户：既然缓存能解决所有慢查询……
你：等一下。"能解决所有"这个前提我不信。你的慢查询里读写比是多少？
```

## CLI 指令

| 指令 | 作用 |
|---|---|
| `/role list` | 列出全部角色包（含体积、经历条数） |
| `/role use skeptic` | 激活 skeptic（持久偏好，重启保持） |
| `/role off` | 关闭角色，回到默认 |
| `/role info` | 查看当前角色的 prompt 渲染实况 + 成长经历 top5 |
| `/role forget skeptic <hash>` | 删除某条成长经历（`all` 全删） |

## 四种"区别"从哪来

1. **性格区别** = PROFILE.md 语料（写示例对话，别写形容词）+ voice.tone 参数 → 注入 system 块。
2. **能力区别** = role.yaml 的 `recall:` 段绑定不同向量库目录/知识域 → 召回时优先查你绑的域。
3. **自身倾向** = `biases:` 规则。命中"未证明前提"等触发器时，agent 会先评估、先提问，而不是顺着你错的前提走。**怀疑的表现是提问，不是拒答。**
4. **成长经历** = `growth.jsonl`。跨会话反复出现的强交互（重复 ≥2 次/被你纠正过/强显著）自动沉淀为里程碑、立场、教训三类记录。**立场（stance）只在你显式纠正时才会改变**，其余滚动淘汰。

## FrontendApi（外部前端对接）

```json
{"v":1,"type":"req","req_id":"r1","api":"role.list"}
{"v":1,"type":"req","req_id":"r2","api":"role.use","payload":{"id":"skeptic"}}
{"v":1,"type":"req","req_id":"r3","api":"role.info","payload":{"id":"skeptic"}}
```

## 写好 PROFILE.md 的三条军规

1. 用"你"开头写守则，给 2-3 个真实感示例对话——LLM 模仿示例远强于服从标签。
2. 语料 ≤ 2KB。超预算会被截断，截断不报错。
3. 想要"观感不同"，改示例；想要"能力不同"，改 recall；想要"态度不同"，改 biases。别混着改。
