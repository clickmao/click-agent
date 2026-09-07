# CHANGELOG v0.11.0 — R153-R168 (批 79-108)

> README 30 批滚动制度归档 (2026-09-08 滚动点批108)。批42-78 见 R143-R152 归档。

| 批 | 轮 | 口径 | 通过 | tok/case |
|---|---|---|---|---|
| 79 | mass_295 | quick-11 | 11/11 | 928 |
| 80 | mass_296 | quick-11 | 11/11 | 860 |
| 81 | mass_297 | quick-11 | 11/11 | 939 |
| 83 | mass_299 | quick-11 | 11/11 | 767 |
| 84 | mass_300 | quick-11 | 11/11 | 894 |
| 85 | mass_301 | full-19 | 19/19 | 1076 |
| 86 | mass_302 | quick-11 | 11/11 | 781 |
| 87 | mass_303 | quick-11 | 11/11 | 808 |
| 88 | mass_304 | quick-11 | 11/11 | 810 |
| 89 | mass_305 | quick-11 | 11/11 | 821 |
| 90 | mass_306 | quick-11 | 11/11 | 810 |
| 91 | mass_307 | quick-11 | 11/11 | 985 |
| 92 | mass_308 | quick-11 | 11/11 | 744 |
| 93 | mass_309 | quick-11 | 11/11 | 981 |
| 94 | mass_310 | quick-11 | 11/11 | 800 |
| 95 | mass_311 | quick-11 | 11/11 | 825 |
| 96 | mass_312 | quick-11 | 11/11 | 942 |
| 97 | mass_313 | full-19 | 19/19 | 1088 |
| 98 | mass_314 | quick-11 | 11/11 | 897 |
| 99 | mass_315 | quick-11 | 11/11 | 781 |
| 100 | mass_316 | quick-11 | 11/11 | 831 |
| 101 | mass_317 | quick-11 | 11/11 | 840 |
| 102 | mass_318 | quick-11 | 11/11 | 807 |
| 103 | mass_319 | quick-11 | 11/11 | 858 |
| 104 | mass_320 | quick-11 | 11/11 | 902 |
| 105 | mass_321 | quick-11 | 11/11 | 796 |
| 106 | mass_322 | quick-11 | 11/11 | 903 |
| 107 | mass_323 | quick-11 | 11/11 | 890 |
| 108 | mass_324 | quick-11 | 11/11 | 787 |

**统计**: quick-11 27 批均值 851 tok/case; 全量 2 批 (85/97) 19/19; 缺陷58 修复 (R154) 后零非绿。

## 关键修复
- R153 缺陷57 (D4 gate 读 os.environ→load_env 统一)
- R154 缺陷58 (harness dotnet PATH fail-fast; mass_298 RETIRED)
- R155 must_not_contain string|list + C15 三重断言全量验证
- R158 C03 min_reply_chars 内容锚 (rel 阈值不动)
