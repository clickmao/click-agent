#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AOT 产物「字符串存在性」判据方法探针 (通用代码逻辑)。

结论 (R499 实测): 环境变量**字面量**在 .NET NativeAOT 产物里既不是 ASCII 明文, 也不是
UTF-16LE 明文 (两种编码在 /tmp/pub_r498 与 /tmp/pub_r499 上命中均为 0) ⇒
`grep -ac AGENTFRAMEWORK_X <bin>` 这种存在性检查是**假阴性源**, 不得作拒跑依据 (R492 曾据此判「缺闸」)。
可用的判据 = 元数据**类型/方法名表** (ASCII 明文, 见 CLASS 段):
  LocalParaphraseChannel / ReplayPairTrim / ToolDeclGate / LocalDecisionLedger / MicroStepIsolationGate ...
用法: python3 probe_aot_string_presence.py <bin> [<bin> ...]
"""
import sys


KEYS = ["AGENTFRAMEWORK_LOCAL_PARAPHRASE", "AGENTFRAMEWORK_REPLAY_PAIR_TRIM",
        "AGENTFRAMEWORK_TOOL_DECL_GATE", "AGENTFRAMEWORK_TOOL_DECL_CHANNEL",
        "AGENTFRAMEWORK_LOCAL_DECISION_MOUNT", "AGENTFRAMEWORK_ACTION_BOUNDARY"]
CLASSES = ["LocalParaphraseChannel", "ReplayPairTrim", "ToolDeclGate", "LocalDecisionLedger",
           "MicroStepIsolationGate", "LocalGenerationPort", "ActionLoop", "IndustrialAgentV2"]


def main() -> int:
    bins = sys.argv[1:] or ["/tmp/pub_r499/agenthost"]
    bad = 0
    for b in bins:
        try:
            data = open(b, "rb").read()
        except OSError as e:
            print("[致命] 读不到 %s: %s" % (b, e)); bad += 1; continue
        print("== %s (%d B) ==" % (b, len(data)))
        for k in KEYS:
            a = data.count(k.encode("ascii"))
            u = data.count(k.encode("utf-16-le"))
            print("   LITERAL %-38s ascii=%d utf16le=%d" % (k, a, u))
        miss = [c for c in CLASSES if data.count(c.encode("ascii")) == 0]
        for c in CLASSES:
            print("   CLASS   %-30s = %d" % (c, data.count(c.encode("ascii"))))
        print("   CLASS_MISSING=%s" % (",".join(miss) if miss else "(none)"))
        if miss:
            bad += 1
    print("PROBE_VERDICT=%s" % ("OK" if bad == 0 else "CLASS_MISSING"))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
