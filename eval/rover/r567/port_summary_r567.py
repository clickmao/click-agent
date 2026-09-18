#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R567 summary 端口 (机械派生, 禁手抄): summary_r566.py → summary_r567.py
  ① 复用 port_r567.port() 的全部替换规则 (轮号/窗号/臂名/dose);
  ② 唯一新增差异 = 「优化前后并排」块从**硬编码 R565 数字**改为**程序化读 R566 summary JSON**
     (R567 的上一轮是 R566; 手抄数字 = 违纪律, 故改为机取)。
"""
import io, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import port_r567 as P

SRC = os.path.join(P.SRC, "summary_r566.py")
DST = os.path.join(P.DST, "summary_r567.py")

NEW_BLOCK = '''    # 优化前后并排 (禁止相减): R566 (同轴 0 vs 1) vs R567 (同轴 0 vs 3) —— 逐格机取自各自 summary JSON, 不手抄
    try:
        s566 = json.load(io.open(os.path.join(REPO, "eval/rover/r566/summary-r566.json"), encoding="utf-8"))
        out["prev_round_R566"] = {
            a: {"windows": s566["windows"], "cases_windows": s566["arms"][a]["cases_windows"],
                "median": s566["arms"][a]["median"], "range": s566["arms"][a]["range"],
                "calls": s566["arms"][a]["calls"], "new_prompt": s566["arms"][a]["new_prompt"],
                "completion": s566["arms"][a]["completion"], "v_all_med": s566["arms"][a]["v_all_med"],
                "v_incr_med": s566["arms"][a]["v_incr_med"]}
            for a in ("C1", "R566B0", "R566B1")}
    except Exception as e:
        out["prev_round_R566"] = {"error": str(e)}
'''


def main():
    t = P.port(io.open(SRC, encoding="utf-8").read())
    t_ported = t   # 端口化产物 (未插入新块) —— 残留检查的靶面
    # 逐字定位并替换「优化前后并排 … R560 dose 轴 … except 块」整段 (以 json.dump(OUT) 为界, 保证不越界)
    start = t.index("    # 优化前后并排")
    end = t.index('    json.dump(out, io.open(OUT, "w", encoding="utf-8")')
    old = t[start:end]
    assert "R560" in old and "prev_round_R565" in old, "块边界不符, 拒绝改写"
    assert 'print("R560:"' in t
    t = t[:start] + NEW_BLOCK + t[end:]
    t = t.replace('print("R560:", json.dumps(out["prev_round_R560_dose_axis"], ensure_ascii=False))',
                  'print("R566(prev):", json.dumps(out["prev_round_R566"], ensure_ascii=False))')
    t = t.replace('"""R567 汇总', '"""R567 汇总 (机械派生自 summary_r566.py; 唯一新增差异 = 上一轮块改为机取 R566) ')
    io.open(DST, "w", encoding="utf-8").write(t)
    print("[port_summary_r567] wrote %s (%d bytes, 替换块 %d chars)" % (DST, os.path.getsize(DST), len(old)))
    for bad in ("R565", "R560", "agentB1", "w125", "w130", "49446", "/tmp/r566"):
        if bad in t:
            print("[FAIL] 最终文本残留 %r" % bad); return 3
    for bad in ("R566B1", "R566B0", "agentB0'"):
        if bad in t_ported:
            print("[FAIL] 端口化文本残留 %r" % bad); return 3
    assert 'prev_round_R566' in t and 'summary-r566.json' in t
    print("[check] 无残留旧轮/旧窗/旧臂名; 上一轮块 = 机取")
    return 0


if __name__ == "__main__":
    sys.exit(main())
