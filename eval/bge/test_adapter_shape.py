#!/usr/bin/env python3
"""W 形状归一回归 (真机缺陷固化: solve_ridge 嵌套行 vs matvec 扁平假设)。"""
import sys, math
sys.path.insert(0, "/home/agentuser/AgentFramework/eval/bge")
import bge_lib as L

r = 3
flat = [1.0, 0.5, 0.0,  0.0, 1.0, 0.25,  0.5, 0.0, 2.0]
nested = [flat[0:3], flat[3:6], flat[6:9]]
v = [1.0, 2.0, 3.0]

a1, a2 = L.matvec(flat, v), L.matvec(nested, v)
assert a1 == a2, (a1, a2)                      # 两种形状同结果
mean = [0.0] * 6
V = [[1.0, 0, 0, 0, 0, 0], [0, 1.0, 0, 0, 0, 0], [0, 0, 1.0, 0, 0, 0]]
lams = [1.0, 1.0, 1.0]
ad_flat = L.Adapter(mean, V, lams, alpha=0.5, W=flat)
ad_nest = L.Adapter(mean, V, lams, alpha=0.5, W=nested)
x = [0.3, -0.7, 1.1, 0.2, 0.9, -0.4]
assert ad_flat.encode(x, query_side=True) == ad_nest.encode(x, query_side=True)
assert ad_nest.W == flat                        # 构造后一律扁平

# 负向控制: 错形状必须被断言拦住 (不得静默算出垃圾)
try:
    L.Adapter(mean, V, lams, W=[1.0, 2.0, 3.0])
    raise SystemExit("FAIL 负向控制: 错形状未被拦")
except AssertionError:
    pass
print("OK 形状归一 (嵌套==扁平) + 负向控制 (错形状被拦)")
