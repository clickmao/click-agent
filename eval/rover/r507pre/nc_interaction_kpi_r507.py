#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R507 补测 · NC 器：注入两处缺陷，证明交互/人性化 KPI 器**不是空心**。

① 正控(反空心): 未改动的器件 ⇒ 自检必须 `SELFTEST=OK`（若它也失败 ⇒ `NC_HOLLOW` 弃权）
② 注入缺陷 A: 取消「代码围栏内不计问号」⇒ 负控用例「? 在代码围栏内」必转 FAIL
③ 注入缺陷 B: 取消「面板行剥离」⇒ 正控用例「本侧面板」必转 FAIL（prose/问号被面板污染）

判定: 三态 —— `detect:NC_DETECTED`(两处注入均被抓, 且正控绿) / `detect:NC_HOLLOW`(正控就红) /
      `detect:NC_MISS`(注入未被抓)。
"""
import io, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = os.path.join(HERE, "kpi_interaction_r507.py")
TMP = os.path.join(HERE, ".nc_tmp_kpi_interaction.py")

MUT_A = ("        if in_code:\n            code_chars += len(raw)\n            continue",
         "        if in_code:\n            code_chars += len(raw)")
MUT_B = ('        tag = None\n        for name, rx in CHROME_PATTERNS:',
         '        tag = None\n        for name, rx in []:')


def run(path):
    p = subprocess.run([sys.executable, "-I", "-B", path, "--selftest"],
                       capture_output=True, text=True, cwd=HERE)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    src = io.open(DEV, encoding="utf-8").read()
    try:
        # ① 正控（反空心）
        shutil.copyfile(DEV, TMP)
        rc0, out0 = run(TMP)
        if rc0 != 0 or "SELFTEST=OK" not in out0:
            print("detect:NC_HOLLOW 未改动器件自检即失败 ⇒ 负控无效")
            print(out0[-500:]); return 1
        print("[正控] 未改动器件: rc=%d SELFTEST=OK" % rc0)

        # ② 注入 A: 代码围栏内问号被计入
        if MUT_A[0] not in src:
            print("detect:NC_HOLLOW 变异锚 A 未命中（器件已改版）"); return 1
        io.open(TMP, "w", encoding="utf-8", newline="\n").write(src.replace(*MUT_A))
        rcA, outA = run(TMP)
        okA = rcA != 0 and "SELFTEST=FAIL" in outA and "负控: ? 在代码围栏内" in outA
        print("[注入A] 取消围栏排除: rc=%d 抓到=%s" % (rcA, okA))

        # ③ 注入 B: 面板行不再剥离
        io.open(TMP, "w", encoding="utf-8", newline="\n").write(src.replace(*MUT_B))
        rcB, outB = run(TMP)
        okB = rcB != 0 and "SELFTEST=FAIL" in outB
        print("[注入B] 取消面板剥离: rc=%d 抓到=%s" % (rcB, okB))

        if okA and okB:
            print("detect:NC_DETECTED 两处注入均被抓且正控绿")
            return 0
        print("detect:NC_MISS 注入未被完全抓到 (A=%s B=%s)" % (okA, okB))
        return 1
    finally:
        if os.path.isfile(TMP):
            os.remove(TMP)


if __name__ == "__main__":
    sys.exit(main())
