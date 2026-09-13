# 稠密 vs 词法 互补性 (R370)

> 语料/查询冻结于 eval/bge/fixtures (1299 块 / 120 查询)。oracle 为**上界**, 非可达值。

| 方法 | r@1 | r@5 | r@10 | r@20 | MRR@10 | miss@50 |
|---|---|---|---|---|---|---|
| lexical-bigram | 0.4417 | 0.7167 | 0.75 | 0.7667 | 0.5571 | 0.2 |
| bge-base-zh-v1.5-q8 | 0.4417 | 0.6667 | 0.7417 | 0.8 | 0.5416 | 0.1083 |
| bge-small-zh-v1.5-q8 | 0.3083 | 0.5667 | 0.6333 | 0.7 | 0.415 | 0.2333 |

| 对照 (基准=lexical-bigram) | dense_only_wins(≤20) | lexical_only_wins(≤20) | both_fail | union@10 | union@20 |
|---|---|---|---|---|---|
| bge-base-zh-v1.5-q8 vs 词法 | 15 | 11 | 13 | 0.8667 | 0.8917 |
| bge-small-zh-v1.5-q8 vs 词法 | 7 | 15 | 21 | 0.7917 | 0.825 |

**全方法 oracle (完美选择器上界, 非可达值)**: oracle@1=0.625, oracle@5=0.8583, oracle@10=0.8667, oracle@20=0.9
