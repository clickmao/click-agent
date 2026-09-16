#!/usr/bin/env python3
# R489 候选④: 把 R486 空正文差分夹具**打开 ACTION_LOOP** 重跑 (机派生, 计数断言)。
#   只换四件事: 输出命名空间 r486→r489 / 端口段 / ACTION_LOOP off→on (+工作区) / 完成标记。
#   桩与驱动器**复用** r486 的既有件 (不复制, 免漂移): 桩走绝对路径。
import pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent            # eval/rover/r489
SRC = HERE.parent / "r486" / "run_diff_r486.sh"
DST = HERE / "run_diff_loop_r489.sh"
TABLE = [
    ("DIR=$ROOT/eval/rover/r486", "DIR=$ROOT/eval/rover/r489", 1),
    ("export AGENTFRAMEWORK_ACTION_LOOP=off",
     "export AGENTFRAMEWORK_ACTION_LOOP=on   # R489 候选④: 打开动作环 (原夹具 ACTION_LOOP=off ⇒ 结论不覆盖该形态)", 1),
    ("export AGENTFRAMEWORK_LLAMA_BIN=/bin/false",
     "export AGENTFRAMEWORK_LLAMA_BIN=/bin/false\nexport AGENTFRAMEWORK_WORKSPACE=\"$ROOT/eval/rover/r489/ws-loop\"\nmkdir -p \"$ROOT/eval/rover/r489/ws-loop\"", 1),
    ("TASK=$DIR/task-r486.json", "TASK=$ROOT/eval/rover/r486/task-r486.json", 1),
    ("python3 -u \"$DIR/stub_upstream_r486.py\"", "python3 -u \"$ROOT/eval/rover/r486/stub_upstream_r486.py\"", 1),
    ("SPORT=$((48600 + idx)); APORT=$((48620 + idx))", "SPORT=$((48940 + idx)); APORT=$((48960 + idx))", 1),
    ('echo "[done] r486"', 'echo "[done] r489-loop"', 1),
    ("# R486 差分器", "# R489 差分器 (机派生自 R486 版; ACTION_LOOP=on)", 1),
    ("# R486 臂: 远端端点 = 本地确定性桩", "# R489 臂: 远端端点 = 本地确定性桩", 1),
]
src = SRC.read_text(encoding="utf-8")
for old, new, want in TABLE:
    got = src.count(old)
    if got != want:
        sys.exit("MISMATCH: count=%d want=%d :: %r" % (got, want, old[:60]))
out = src
for old, new, _ in TABLE:
    out = out.replace(old, new)
for bad in ("r486/run-", "AGENTFRAMEWORK_ACTION_LOOP=off", "48600", "48620"):
    if bad in out:
        sys.exit("残留: %r" % bad)
DST.write_text(out, encoding="utf-8")
(HERE / "run_diff_loop_r489.diff").write_text(
    "".join(__import__("difflib").unified_diff(src.splitlines(True), out.splitlines(True),
                                               "r486/run_diff_r486.sh", "r489/run_diff_loop_r489.sh")),
    encoding="utf-8")
print("[derive_loop] wrote %s (替换 %d 处, 残留 clean)" % (DST.name, len(TABLE)))
