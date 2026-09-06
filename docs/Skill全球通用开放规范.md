# Skill 全球通用开放规范 (AgentFramework 落地版)

> 本文档定义 AgentFramework 的 Skill 打包规范。核心格式遵循 **Anthropic Agent-Skills Open Standard**
> (SKILL.md 文件夹包格式, agentskills.io) — 该规范为事实开放标准, OpenAI、多家 Agent 框架兼容此打包规范。
> AgentFramework 在开放规范核心之上做**触发调度扩展** (向后兼容: 外部生态包无需修改即可加载)。

## 1. 包结构规范 (开放标准)

```
skill-name/                # 目录名必须等于 front-matter name; kebab-case 小写
├── SKILL.md               # 【强制】YAML front-matter + Markdown 正文
├── scripts/               # 可选: py/sh 可执行脚本
├── references/            # 可选: 大段参考文档、openapi、样例, 不要塞在 SKILL.md
└── assets/                # 可选: 模板、静态资源
```

### 1.1 强制规则 (开放标准语义)

| 规则 | 说明 |
|---|---|
| 目录名 = front-matter `name` | 大小写不敏感比对; 不一致 → 包被拒绝 (静默跳过) |
| `SKILL.md` 必须存在 | 无 SKILL.md 的目录不是 Skill 包 |
| front-matter `name` 必填 | 缺失 → 包被拒绝 |
| `description` 必填 (推荐) | 语义匹配 (bge 嵌入) 的代表文本; 缺失时回退用正文前 200 字符 |

### 1.2 front-matter 字段

**开放标准核心字段** (任何兼容框架都识别):

```yaml
---
name: git-commit-helper      # 必填, kebab-case, = 目录名
description: 一句话技能说明    # 必填, 语义匹配文本
version: 1.0.0               # 推荐
license: MIT                 # 推荐
---
```

**AgentFramework 调度扩展字段** (可选 — 外部包缺省时走纯语义/关键词调度):

```yaml
keywords:          # 一级关键词触发 (包含匹配, 任一命中)
  - 提交信息
regex_patterns:    # 二级正则精匹配 (覆盖关键词)
  - "(写|生成).{0,6}commit"
domain_words:      # 疑似命中领域词
  - git
priority: 6        # 冲突裁决权重 (默认 5)
exclusive: false   # true = 命中后独占
timeout_seconds: 30
type: normative    # normative (口径型) / executive (执行型)
force_template: "固定口径模板 {input}"   # normative force 承载
forbidden_words:   # 结果禁语校验
```

## 2. 双格式并存 (迁移期)

| 格式 | 位置 | 状态 |
|---|---|---|
| **开放标准包** | `skills/<name>/SKILL.md` | **推荐** — 新技能一律用此格式 |
| legacy 平文件 | `skills/<name>.yaml` | 兼容 (identity.yaml 存量) — 后续版本移除 |

`SkillRegistry.LoadFromDirectory` 同时加载两种格式; 同名时开放标准包优先注册。

## 3. 触发调度 (三级 + 语义)

1. **一级关键词**: `keywords` 任一包含命中 → level 2, precision 0.6
2. **二级正则**: `regex_patterns` 命中 → level 3, precision 0.95
3. **领域词疑似**: `domain_words` 命中 → level 1, precision 0.3
4. **语义层 (v0.10.0 P3)**: 以上全未命中 → bge 384 维嵌入余弦相似度 ≥ 0.45 → level 1 (疑似)
   - 语义代表文本: `description` > `name + domain + keywords` 串接
   - 嵌入器不可用 → 静默回退纯词面匹配 (行为兼容)

裁决: `exclusive` > `priority` > `precision` > `level`。

## 4. SKILL.md 正文语义

开放标准: 正文即技能工作流/规则/业务流程文档。AgentFramework 落地:

- `type: normative` 且无 `force_template` → **正文 Markdown 作为 force 模板基底** (命中时口径承载)
- `type: executive` → 正文供执行委托参考 (`scripts/` 内脚本为执行体, 走 SkillExecutor)

## 5. 互操作性声明

- **输入兼容**: 任何符合 Anthropic Agent-Skills Open Standard 的包 (含 OpenAI 生态兼容包)
  放入 `skills/` 即被加载 — 扩展字段缺省不报错
- **输出兼容**: 本框架产出的包 (仅用核心字段时) 可被其他兼容框架直接消费
- 示例包: `skills/git-commit-helper/`、`skills/code-review-checklist/` (均含调度扩展字段)
