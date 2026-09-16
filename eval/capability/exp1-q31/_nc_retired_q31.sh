#!/usr/bin/env bash
# EXP1-Q31 · C1 负控: 退役面断言器具的判别力自证。
# 夹具: 在临时树里**重建**一条退役路径 (src/agent.embedcpu) ⇒ 器具必须判红 (rc=2, RETIRED_CHECK=FAIL)。
# 若注入后仍绿, 说明断言空心 (只比对不变量/未真正枚举路径)。
set -u
D=/tmp/q31nc-retired
rm -rf "$D"
mkdir -p "$D/src/agent.embedcpu"
OUT="$(python3 eval/capability/exp1-q31/instruments/retired_interop_absent.py --root "$D" 2>&1)"
RC=$?
echo "$OUT"
rm -rf "$D"
if [ "$RC" -eq 2 ] && printf '%s' "$OUT" | grep -q 'RETIRED_CHECK=FAIL'; then
  echo "NC_DETECTED (重建退役路径 ⇒ 器具判红 rc=2)"
  exit 0
fi
echo "NC_NOT_DETECTED (rc=$RC)"
exit 1
