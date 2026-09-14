# R411-V 机检运行证据

形式校验过滤器：`FullyQualifiedName~VerificationForm|FullyQualifiedName~SkillGeneralization|FullyQualifiedName~DevPlanDocRef`

| 文件 | 说明 |
|---|---|
| `run1-RED.txt` | 第 1 跑：`Failed: 1, Passed: 12, Total: 13` / `TEST_EXIT=1` —— 失败项是**本轮新写的负控表自身**（注入坏行 `e.dead_cmd_path` 指向了真实存在的 csproj ⇒ 该行没坏 ⇒ R2b 断言失败）。留档理由：这是「负控不能空心」的现场证据。 |
| `run2-GREEN.txt` | 第 2 跑（仅改那一行后）：`Failed: 0, Passed: 13, Skipped: 0` / `TEST_EXIT=0`。 |

| `run3-FINAL.txt` | 第 3 跑（最终树：R403 状态措辞 + kpi 行定稿后）：`Failed: 0, Passed: 13` / `TEST_EXIT=0`。|

两跑均在隔离副本 `/tmp/r411v`（= `git archive HEAD` + 本轮 7 个改动文件，md5 已逐一比对）内执行：
并发 session（R411 = K2b 长驻本地生成端口线）当时正在同一工作树编辑未提交文件，
按「build / 批测 / 单测三者互斥」纪律不在共享树内跑构建。

复现（等价，任意干净检出）：

```bash
export DOTNET_ROOT="$HOME/.dotnet"; export PATH="$DOTNET_ROOT:$PATH"
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR dotnet test src/agent.tests/agentframework.tests.csproj \
  --filter "FullyQualifiedName~VerificationForm|FullyQualifiedName~SkillGeneralization|FullyQualifiedName~DevPlanDocRef" --nologo -v q
echo "TEST_EXIT=$?"   # 结论取本标记, 不取管道末条命令的退出码
```

详见 `docs/reports/r411v/registry-liveness.md`。
