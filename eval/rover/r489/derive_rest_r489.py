#!/usr/bin/env python3
# R489: 由 run_both_r489.sh 机派生「剩余臂」驱动 —— B 臂已于首跑完成 (usage-Aroleb.jsonl 有读数),
#   命名空间闸会拒绝重跑 B (REFUSE_NS_COLLISION) ⇒ 只取 R1/R2/R3 三条臂。
#   计数断言: 源 22 行, 丢弃含 ' Arole b ' 的 2 行, 输出 3 条 R 臂调用 + key/gate 前置。
import pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
src = (HERE / "run_both_r489.sh").read_text(encoding="utf-8").splitlines(keepends=True)
drop = [i for i, l in enumerate(src) if " Arole b " in l]
drop += [i + 1 for i in drop]                      # 连同紧随其后的 ok/失败 回显行
if len(src) != 21 or len(drop) != 2:
    sys.exit("MISMATCH: 源行数=%d (期望 21), B 臂行数=%d (期望 2) ⇒ 不写产物" % (len(src), len(drop)))
out = [l for i, l in enumerate(src) if i not in drop]
text = "".join(out)
if text.count("run_arm_real_r489.sh R ") != 3:
    sys.exit("MISMATCH: R 臂调用数=%d (期望 3)" % text.count("run_arm_real_r489.sh R "))
if "Arole b" in text:
    sys.exit("MISMATCH: 残留 B 臂调用")
text = text.replace("# R489 稳定性重复顺序执行 (B ×1 → R1 → R2 → R3)",
                    "# R489 剩余臂驱动 (**机派生**: B 臂首跑已完成, 本文件只跑 R1→R2→R3)")
dst = HERE / "run_rest_r489.sh"
dst.write_text(text, encoding="utf-8")
print("[derive_rest] wrote %s (源 %d 行 → %d 行; R 臂调用 3)" % (dst.name, len(src), len(out)))
