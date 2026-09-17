# CHANGELOG v0.13.3 — R249-R268 (批 218-247)

> README 30 批滚动制度归档 (2026-09-09 滚动点批258 前补账, 用户点名欠账)。批 188-217 见 R229-R248 归档。

| 批 | 轮 | 口径 | 通过 | tok/case | 备注 |
|---|---|---|---|---|---|
| 218 | mass_436 | quick-11 | 11/11 | 1607 | R250 C14 离群 (7555tok, 已定性单批方差, 破线诚实登记) |
| 219 | mass_437 | quick-11 | 11/11 | 1133 | R251 C14 回归正常 |
| 220 | mass_438 | quick-11 | 11/11 | 1063 | R252 (sibling 双跑零冲突) |
| 220 | mass_440 | quick-11 | 11/11 | 1117 | R254 双跑复核 + R242-R253 台账回填 |
| 222 | mass_442 | quick-11 | 11/11 | 963 | R256 |
| 223 | mass_443 | quick-11 | 11/11 | 1137 | R256 撞号协议执行 |
| 224 | mass_444 | quick-11 | 11/11 | 1034 | R257 A3 收口验证 + 撞号险情 (mass_443) |
| 225 | mass_445 | quick-11 | 11/11 | 1185 | R258 缺陷69 (bge 超窗→截断+chunking) |
| 226 | mass_446 | quick-11 | 11/11 | 1087 | R260 chunking 归并生效 |
| 227 | mass_447 | quick-11 | 11/11 | 1196 | R261 压缩防线 D1/D2 后 |
| 228 | mass_448 | quick-11 | 11/11 | 1053 | R262 D3 降级链 |
| 229 | mass_449 | quick-11 | 11/11 | 1027 | R264 D4 熔断器 |
| 230 | mass_450 | quick-11 | 11/11 | 997 | R268 retry-lock |
| 231 | mass_451 | quick-11 | 11/11 | 1066 | R267 IDF 稀缺度+SN 判别 |
| 233 | mass_452 | quick-11 | 11/11 | 1124 | R269 (趋势滚动点 批233/237) |
| 234 | mass_454 | quick-11 | 11/11 | 1402 | R274 单批离群 (登记) |
| 237 | mass_457 | quick-11 | 11/11 | 1087 | R275 |
| 238 | mass_458 | quick-11 | 10/11 | 1251 | R282 C08 意图抖动 (单批事件, 已定性关闭) |
| 239 | mass_459 | quick-11 | 11/11 | 974 | R283 C08 复证 11/11 |
| 240 | mass_460 | quick-11 | 11/11 | 920 | R286 think-chain 宿主链 live |
| 241 | mass_461 | quick-11 | 11/11 | 1124 | R296 文档大梳理后 |
| 242 | mass_462 | XL-7 | 7/7 | 9289 | R297 XL 周期首排 (gate 三态) |
| 244 | mass_464 | quick-11 | 11/11 | 1176 | R299 缺陷70 修复 (read_telemetry errors=replace) |
| 245 | mass_465 | quick-11 | 11/11 | 1157 | R302 K1 开关回归 |
| 246 | mass_466 | quick-11 | 10/11 | 1080 | R303 (C15 缺口, 次批复绿) |
| 247 | mass_467 | quick-11 | 11/11 | 1040 | R305 缺陷71 关闭 (writer-null) |

## 轮期能力 (R249-R268)

- **召回链三修 (R256-R261)**: 缺陷69 bge 超窗截断+chunking 多向量; 同父去重; 补偿倍增撤除 (弱相关 chunk 反压实证); 短查询 0.45 定性=同分平局 → 健康线 0.40 对抗/0.65 长查询
- **压缩失败防护 D1-D5 (对标工业 M1-M6)**: D1 per-snippet 异常隔离 / D2 哨兵 (SN-\d+ + URL, SentinelLosses 打点上移) / D3 降级链 / D4 熔断器 (threshold 5/cooldown 60s/half-open, 6 测试) / D5 不可变源 (2 测试)
- **IDF 稀缺度加权 (R267)**: log(1+N/df) 上限 0.35 + SN 全局唯一判别查询 → 期望文档 top-1 0.80 vs 0.75
- **多轮 repl 驱动 (R268)**: multi_turn_driver.py select 非阻塞读; 缺陷70 初判撤销 (无参=smoke 语义) → 真身 UnicodeDecodeError → errors="replace"
- **B2 微步骤宿主链 E2E (R274 前置)**: host build 级联教训 (dotnet build 单项目不刷 host bin)
- **台账回填制度**: R242-R253 sibling 13 commits 回填 (429 调度/长观察/压缩审计/ContextBudgetGate L1-L5/XL 7/7/召回 R@5=0.70)
