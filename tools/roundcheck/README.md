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
```

退出码：`0` 无 FAIL（允许 WARN）/ `1` ≥1 FAIL / `2` 用法或环境错。

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

`preflight`：P1 依赖 key 面 set/unset（**只报 set/unset 和字符数, 绝不回显值**）/ P2 权重在盘 /
P3 `MemAvailable` ≥ 闸 / P4 磁盘余量 ≥ 闸 / P5 有无在飞执行体（同仓并发纪律）/ P6 轮号占用仲裁 /
P7 目标轮号是否空闲 / P8 `PUSH_PAUSED` 状态。

## 纪律与边界

- **只读**：除 `--selftest` 在 `tmp` 里造样本，从不改被审仓库。
- **器具先自证有牙**：`--selftest` 内 3 个负控（错 pin ⇒ R4 红 / 提交内 key 面 ⇒ R7 红 / 无提交轮号 ⇒ R2 红）
  + 1 个假红控制（正常 `task-*` 标识符不得误判为 `sk-` key）。
- 只审「台账 / 证据 / 提交面」的一致性，**不判产品能力**；R6 的 40 文件阈值是代理判据，不是 `git add -A` 的证明。
