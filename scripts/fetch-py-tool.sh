#!/usr/bin/env bash
# 下载"测试用的 py tool" (固定解释器) —— 让真跑闸门有可复现的 python, 不靠 PATH 上偶然的解释器。
#
# 为什么需要它 (T4 决策, v0.22.0 exp9 §11):
#   产物自测 (--selftest) 必须**真跑**才有物理含义; 但"真跑"要有一个确定的解释器:
#     · PATH 上的 python3 可能是别的 venv (本机实测: 排第一的是 hermes venv 的 python3) → 结论不可复现
#     · 版本漂移会让同一产物在不同机器上得到不同结论
#   所以: 固定版本 + 记录路径 + 解析顺序明确 (PythonInterpreterResolver)。
#
# 用法: bash scripts/fetch-py-tool.sh [版本]   (默认 3.12.14; 幂等: 已装则秒回)
set -euo pipefail

VERSION="${1:-3.12.14}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RECORD_DIR="$REPO_ROOT/tools/py"
RECORD="$RECORD_DIR/interpreter.txt"

command -v uv >/dev/null 2>&1 || { echo "FAIL: 需要 uv (未安装)" >&2; exit 1; }

echo "==> 安装固定解释器 cpython-$VERSION (uv 托管, 自带下载校验)"
uv python install "$VERSION"

PY="$(uv python find "$VERSION")"
[ -x "$PY" ] || { echo "FAIL: 解释器不可执行: $PY" >&2; exit 1; }

# 自证: 版本 + py_compile 能力 (产物闸门正是用 py_compile + 真跑, 这里先证明解释器本身可用)
VER="$("$PY" -c 'import sys;print(sys.version.split()[0])')"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
printf 'print("py-tool-ok")\n' > "$TMP/t.py"
"$PY" -m py_compile "$TMP/t.py"
OUT="$("$PY" "$TMP/t.py")"
[ "$OUT" = "py-tool-ok" ] || { echo "FAIL: 解释器执行异常 (输出=$OUT)" >&2; exit 1; }

mkdir -p "$RECORD_DIR"
printf '%s\n' "$PY" > "$RECORD"

echo "OK: python $VER"
echo "    解释器 = $PY"
echo "    记录   = $RECORD"
echo "    说明: tools/py/ 属本机产物 (不入库); 版本口径见本脚本首行注释与 exp9 §11"
