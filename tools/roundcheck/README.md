# roundcheck —— 每轮有效性校对 + 起臂前置闸（调试器具, 非评测夹具）

动机（用户令 2026-09-19）：「你需要一些额外的调试工具来帮你校对每轮有效性和验证你的方案可行性」。
翻车只有两类，本器具各管一类：

- **这一轮根本不算有效**：轮号重号 / 证据没落档 / 冻结 pin 与现盘字节不一致 / 提交面混进垃圾或 key 面 / 读数无档可查。
- **方案根本跑不起来**：key 面缺（臂全 VOID）/ 内存·磁盘不过起手闸 / 已有兄弟会话在写同仓（撞轮）。

## 用法

```bash
python3 tools/roundcheck/roundcheck.py audit --round R582                 # 校对某轮是否有效
python3 tools/roundcheck/roundcheck.py preflight --round R583 \
        --need-key AGENTFRAMEWORK_KEYS_DEEPSEEK --min-avail-mb 2650        # 起臂前判可行性
python3 tools/roundcheck/roundcheck.py --selftest                          # 器具自证（先过这个再用）
python3 tools/roundcheck/roundcheck.py audit --round R616 --baseline tools/roundcheck/baseline.json
python3 tools/roundcheck/roundcheck.py baseline --add \
        --item R7_no_secret_in_commit --subject config/base/models.yaml \
        --reason "该行是 env 变量名引用(非密钥值), 规则对其假红" \
        --expires-round R625 --scope-round R609 --round R616                # 唯一能登记/抬上限的入口
python3 tools/roundcheck/roundcheck.py baseline --remove \
        --item R7_no_secret_in_commit --subject config/base/models.yaml     # 撤销（抑制只许减）
```

退出码：`0` 无 FAIL（允许 WARN / BASELINED）/ `1` ≥1 FAIL / `2` 用法或环境错。

## 判据

`audit`（每条 PASS/FAIL/WARN，明细带证据）：

| 判据 | 校对什么 |
|---|---|
| R1 registry_row | 登记表里有 `owner_round=<轮>` 的行 |
| R2 commit_unique | 恰好 1 个 `R<轮>: ...` 提交（0 = 未落档; ≥2 = 轮号重号） |
| R3 evidence_present | 每个登记行的 `evidence_path` 在位且 ≥200 字符 |
| R4 pin_matches | 行内 `artifact_sha12` / `instrument_sha12` 与**现盘字节**一致（冻结 pin 的翻车面） |
| R5 doc_shape | 证据文档有「诚实边界」段、无占位符、够长 |
| R6 commit_hygiene | 本轮提交文件数 ≤40（疑 `git add -A` 的代理判据）、无 `*.log/tmp/bak/scratch` |
| R7 no_secret_in_commit | 本轮提交内无 key 面（私钥块 / `AGENTFRAMEWORK_KEYS_*=值` / key-token 赋值 / `sk-`） |
| R8 readings_backed | 文档+登记行内含 build 读数、形式门禁读数、通过率 `x/y` |
| R9 staged_hygiene | 暂存面卫生（提交前跑：是否恰好等于本轮清单、有无垃圾/敏感面） |
| W1 secret_in_worktree | 工作区出现 key 面 ⇒ 提醒「可留工作区、禁入库」 |
| R10 baseline | 违例基线形态（缺失 ⇒ 旧行为逐字节不变；非法/条目缺 `reason`/缺 `expires_round` ⇒ **出声不豁免**） |
| R11 expired_exception | 基线例外**过期未清** ⇒ 红（到期回红 = 强制回看；不接受永久豁免） |
| R12 disable_count | **抑制只许减**：`entries > max_entries` ⇒ 红（新增豁免必须走显式 `baseline --add`） |

`preflight`：P1 依赖 key 面 set/unset（**只报 set/unset 和字符数, 绝不回显值**）/ P2 权重在盘 /
P3 `MemAvailable` ≥ 闸 / P4 磁盘余量 ≥ 闸 / P5 有无在飞执行体（同仓并发纪律）/ P6 轮号占用仲裁 /
P7 目标轮号是否空闲 / P8 `PUSH_PAUSED` 状态。

## 违例基线（R616 起，采 ZCode `.architecture-baseline.json` 治理模型）

- 只吸收**已在册**的旧违例：`FAIL → BASELINED`（不计入 `rc()`），其余红照旧。
- 条目录必填 `item / subject / reason(≥20 字符) / expires_round`；可选 `round` 作用域（防宽 `subject` 跨轮吃掉一族红）。
- **缺基线文件 ⇒ 旧行为逐字节不变**；基线非法 ⇒ `R10` 红，不静默放行。
- 唯一能抬 `max_entries` 的入口是 `baseline --add`（显式命令，CI/审计路径从不自动刷新）。

## 纪律与边界

- **只读**：除 `--selftest` 在 `tmp` 里造样本、`baseline --add/--remove` 写**指定的**基线文件外，从不改被审仓库。
- **器具先自证有牙**：`--selftest` = 负控 3/3（错 pin ⇒ R4 红 / 提交内 key 面 ⇒ R7 红 / 无提交轮号 ⇒ R2 红）
  + 正控 1/1 + 假红控制 2/2（正常 `task-*` 不得误判 `sk-`；调用者自身不得被算作「在飞执行体」）
  + 对照轮分支 正控 1/1 + 负控 5/5 + **基线分支 正控 4/4 + 负控 7/7**。真实在飞的 `agenthost/llama-server` 只作注记（P5 的 fail-closed 语义），不当自匹配。
- R8 的「形式门禁」读数面是**结构判定**（形如 `形式 14/14` / `形式门禁 13/14`），不绑魔法常量 ⇒ 闸真不是 14/14 时可以如实写。
- 只审「台账 / 证据 / 提交面」的一致性，**不判产品能力**；R6 的 40 文件阈值是代理判据，不是 `git add -A` 的证明。
- 未采纳 ZCode 的 `--changed` 差量扫描与树级结构规则族（本器判据本就按轮作用域）⇒ 「差量扫描」仍是缺面。
