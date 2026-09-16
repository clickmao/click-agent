#!/usr/bin/env python3
# R489 臂执行器/双臂驱动 **机派生** (语言无关: 只做文本替换 + 计数断言, 不含语言/文件后缀分支)。
#   源: eval/rover/r488/{run_arm_real_r488.sh, run_both_r488.sh}
#   目标: eval/rover/r489/{run_arm_real_r489.sh, run_both_r489.sh}
#   纪律: 每条替换**先前置计数断言** (计数为 0 ⇒ rc=3 弃权, 不写任何产物);
#         派生后对输出做**残留扫描** (禁残留旧命名空间/旧二进制/旧 key 变量)。
#   额外: 候选⑤ 夹具 teardown 硬化 —— 在臂脚本收口前插入断言调用 (进程组回收 + 端口断言)。
import pathlib
import sys

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
SRC = ROOT / "eval/rover/r488"
DST = ROOT / "eval/rover/r489"
OLD_BIN = "/tmp/pub_r485/agenthost"
NEW_BIN = "/tmp/pub_r489/agenthost"

# (源文件, 目标文件, 替换表[(old,new,期望计数)], 残留禁词)
JOBS = [
    (
        SRC / "run_arm_real_r488.sh",
        DST / "run_arm_real_r489.sh",
        [
            ("# R488 臂执行器 —— 由 R487 版**机派生** (eval/rover/r488/derive_r488.py: 替换表逐条计数断言, 差异见 derive_r488.diff)。",
             "# R489 臂执行器 —— 由 R488 版**机派生** (eval/rover/r489/derive_r489.py: 替换表逐条计数断言, 差异见 derive_r489.diff)。", 1),
            ("#   1) 命名空间 r487 → r488 (DIR / round / key 变量名)",
             "#   1) 命名空间 r488 → r489 (DIR / round / key 变量名)", 1),
            ("#   2) 候选①: 臂矩阵改 **2x2 析因** (B=Arole / G / S / R) —— 同二进制只翻开关, 隔离 turn_gate 与 repeat_skip",
             "#   2) 候选①: 臂矩阵改 **稳定性重复** (B ×1 + R ×3, 同一臂参仅换命名空间/端口) —— 主臂重复 3 跑求分布, 否定\"单次读数\"", 1),
            ("#   3) 候选④: TAG 并入 relay 命名 (原传 $ARM ⇒ Arole485/R485 真值列落共用名, 臂自身 usage-<ARM><TAG> 恒 0 字节) + tel-/telcount- 一并并入 TAG",
             "#   3) TAG 语义改为**重复序号** (R 1 / R 2 / R 3 ⇒ 命名空间 R1/R2/R3, 各跑独立), 用于跨跑独立性机检", 1),
            ("#   4) 二进制**不动** (/tmp/pub_r485/agenthost): 换二进制就无法与 R487 Arole485 基线比",
             "#   4) 二进制 = R489 AOT 重新发布物 (/tmp/pub_r489/agenthost): 含 R489 文案裁决 (本地确认语模板), 四臂**同一产物**", 1),
            ("#   Arole = 门关 + rj=on + repeat_skip off (B 基线)  ← 同刻分母",
             "#   Arole = 门关 + rj=on + repeat_skip off (B 基线, 同刻分母; 一次)", 1),
            ("#   G     = 门开 + rj=on + repeat_skip off          ← turn_gate 单独效应",
             "#   R     = 门开 + rj=on + repeat_skip on           ← 生产形态 (主臂; 重复 3 跑)", 1),
            ("#   S     = 门关 + rj=on + repeat_skip on           ← repeat_skip 单独效应\n#   R     = 门开 + rj=on + repeat_skip on           ← 生产形态 (r1 在管道内)",
             "#   基线与主臂唯一差异 = 门控开关 (同二进制/同夹具/同窗/同 role)", 1),
            ("# 用法: bash run_arm_real_r488.sh <Arole|G|S|R> [tag] [relay_port] [api_port]",
             "# 用法: bash run_arm_real_r489.sh <Arole|G|S|R> [tag] [relay_port] [api_port]", 1),
            ("set -u\nARM=${1:?用法: run_arm_real_r488.sh", "set -u\nARM=${1:?用法: run_arm_real_r489.sh", 1),
            ("DIR=$ROOT/eval/rover/r488", "DIR=$ROOT/eval/rover/r489", 1),
            ("HOST=${AGENTFRAMEWORK_HOST_BIN:-/tmp/pub_r485/agenthost}", "HOST=${AGENTFRAMEWORK_HOST_BIN:-" + NEW_BIN + "}", 1),
            # R489 候选③(修正): teardown 断言前**先按命名空间收口** —— B 臂实测 llama-server 非 host 直接
            #   子进程 (pkill -P 漏杀), 只断言不收口 ⇒ 真泄漏把整轮链条打断 (rc=11)。⇒ 插入的调用带 --reap。
            ("--round R488", "--round R489", 1),
            ("R488_UPSTREAM_KEY", "R489_UPSTREAM_KEY", 3),
            ("# R488 臂 (端点 = 本地中继 v2 → 真供应商; 其余与生产 config/base/models.yaml 逐字同)",
             "# R489 臂 (端点 = 本地中继 v2 → 真供应商; 其余与生产 config/base/models.yaml 逐字同)", 1),
            # 候选⑤+③: teardown **先收口再断言** (R489 修正)
            (
                'echo "[done] arm=$ARM"',
                'python3 "$DIR/teardown_assert.py" --arm "$ARM$TAG" --api-port "$API_PORT" --relay-port "$RELAY_PORT" --reap \\\n'
                '  --out "$DIR/teardown-$ARM$TAG.json" || { echo "[致命] teardown 断言红 (候选⑤/③)"; exit 11; }\n'
                'echo "[done] arm=$ARM"',
                1,
            ),
        ],
        ["r488/", "/tmp/pub_r485", "R488_UPSTREAM_KEY", "run_arm_real_r488.sh"],
    ),
    (
        SRC / "run_both_r488.sh",
        DST / "run_both_r489.sh",
        [
            ("# R488 四臂析因顺序执行 (B=Arole488b → G488g → S488s → R488r); key 只从 .env.local 取一次, 不回显。",
             "# R489 稳定性重复顺序执行 (B ×1 → R1 → R2 → R3); key 只从 .env.local 取一次, 不回显。", 1),
            ("#   机派生自 eval/rover/r488/derive_r488.py (替换表逐条计数断言)。",
             "#   机派生自 eval/rover/r489/derive_r489.py (替换表逐条计数断言)。", 1),
            ("R488_UPSTREAM_KEY", "R489_UPSTREAM_KEY", 3),
            ("# R488 候选⑦: 起手闸前置", "# R489 候选⑦: 起手闸前置", 1),
            ("--out eval/rover/r488/preflight-both.json --round R488", "--out eval/rover/r489/preflight-both.json --round R489", 1),
            ("[both-r488]", "[both-r489]", 12),
            ("[both-r489] G 失败", "[both-r489] R1 失败", 1),
            ("[both-r489] G ok", "[both-r489] R1 ok", 1),
            ("[both-r489] S 失败", "[both-r489] R2 失败", 1),
            ("[both-r489] S ok", "[both-r489] R2 ok", 1),
            ("[both-r489] R 失败", "[both-r489] R3 失败", 1),
            ("[both-r489] R ok", "[both-r489] R3 ok", 1),
            ("eval/rover/r488/run_arm_real_r488.sh Arole b 48810 48812", "eval/rover/r489/run_arm_real_r489.sh Arole b 48910 48912", 1),
            ("eval/rover/r488/run_arm_real_r488.sh G g 48814 48816", "eval/rover/r489/run_arm_real_r489.sh R 1 48914 48916", 1),
            ("eval/rover/r488/run_arm_real_r488.sh S s 48818 48820", "eval/rover/r489/run_arm_real_r489.sh R 2 48918 48920", 1),
            ("eval/rover/r488/run_arm_real_r488.sh R r 48822 48824", "eval/rover/r489/run_arm_real_r489.sh R 3 48922 48924", 1),
            ('echo "[both-r489] B ok $(date +%H:%M:%S)"', 'echo "[both-r489] B ok $(date +%H:%M:%S)"', 1),
            ("/tmp/pub_r485/agenthost", "/tmp/pub_r489/agenthost", 4),
        ],
        ["r488/", "/tmp/pub_r485", "R488_UPSTREAM_KEY", "both-r488"],
    ),
]


def main() -> int:
    DST.mkdir(parents=True, exist_ok=True)
    fail = 0
    for src, dst, table, residual in JOBS:
        if not src.exists():
            print(f"[derive] MISSING_SOURCE {src}")
            return 3
        text = src.read_text(encoding="utf-8")
        total = 0
        for old, new, want in table:
            got = text.count(old)
            status = "OK" if got == want else "MISMATCH"
            print(f"[derive] {src.name}: count={got} want={want} {status} :: {old.splitlines()[0][:64]!r}")
            if got != want:
                fail = 1
            text = text.replace(old, new)
            total += got
        if fail:
            print("[derive] ABORT: 替换计数不符 ⇒ 不写任何产物 (rc=3)")
            return 3
        for bad in residual:
            if bad in text:
                print(f"[derive] ABORT: 残留禁词 {bad!r} ⇒ 不写产物 (rc=3)")
                return 3
        dst.write_text(text, encoding="utf-8")
        dst.chmod(0o755)
        print(f"[derive] wrote {dst.relative_to(ROOT)} (替换计数合计 {total}, 残留扫描 clean)")
    # diff 归档
    import difflib
    for src, dst, _t, _r in JOBS:
        d = "".join(
            difflib.unified_diff(
                src.read_text(encoding="utf-8").splitlines(True),
                dst.read_text(encoding="utf-8").splitlines(True),
                fromfile=src.name, tofile=dst.name, n=2,
            )
        )
        (DST / (dst.stem + ".diff")).write_text(d, encoding="utf-8")
        print(f"[derive] diff {dst.stem}.diff lines={len(d.splitlines())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
