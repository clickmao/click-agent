#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨实现对账: agent.gpu 自载探针  vs  系统 vulkaninfo (独立实现 oracle)。

理由 (R393 方法论铁律): 自写绑定"能跑通"不算证据 —— 必须与**独立实现**对同一设备逐值对账,
否则加载器名字/结构体偏移/枚举语义的错误会被自洽地掩盖。

对账字段: 设备名 / apiVersion / driverVersion / vendorID / deviceID / deviceType
"""
import re
import subprocess
import sys

# 允许用环境变量切换被测 CLI (JIT dll / AOT 单文件产物), 两形态必须给出同一结论
import os
CLI = (os.environ.get("AGENTFRAMEWORK_GPU_CLI") or "dotnet src/agent.gpu/bin/Release/net10.0/agent.gpu.dll").split() + ["probe"]


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    return p.returncode, p.stdout, p.stderr


def parse_mine(out):
    devs = {}
    for line in out.splitlines():
        m = re.match(r"vkdevice\{index=(\d+) name=\"(.*?)\" api=([\d.]+) driver=(\d+) "
                     r"vendor=0x([0-9A-Fa-f]+) device=0x([0-9A-Fa-f]+) type=(\w+)\}", line)
        if m:
            devs[int(m.group(1))] = {
                "name": m.group(2), "api": m.group(3), "driver_raw": int(m.group(4)),
                "vendor": int(m.group(5), 16), "device": int(m.group(6), 16), "type": m.group(7),
            }
    return devs


def parse_vulkaninfo(text):
    """vulkaninfo 的 GPU 块 → 与上面同名的字段 (格式化版本号转回 packed)。"""
    devs = {}
    blocks = re.split(r"\nGPU(\d+):\n", text)
    for i in range(1, len(blocks) - 1, 2):
        idx, body = int(blocks[i]), blocks[i + 1]

        def g(pat):
            m = re.search(pat, body)
            return m.group(1).strip() if m else None

        api = g(r"apiVersion\s*=\s*([\d.]+)")
        drv = g(r"driverVersion\s*=\s*([\d.]+)")
        ven = g(r"vendorID\s*=\s*(0x[0-9A-Fa-f]+)")
        dev = g(r"deviceID\s*=\s*(0x[0-9A-Fa-f]+)")
        typ = g(r"deviceType\s*=\s*(\S+)")
        nm = g(r"deviceName\s*=\s*(.+)")
        packed = 0
        if drv:
            a, b, c = (int(x) for x in drv.split("."))
            packed = (a << 22) | (b << 12) | c
        type_map = {"PHYSICAL_DEVICE_TYPE_OTHER": "other", "PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU": "integrated",
                    "PHYSICAL_DEVICE_TYPE_DISCRETE_GPU": "discrete", "PHYSICAL_DEVICE_TYPE_VIRTUAL_GPU": "virtual",
                    "PHYSICAL_DEVICE_TYPE_CPU": "cpu"}
        devs[idx] = {"name": nm, "api": api, "driver_raw": packed,
                     "vendor": int(ven, 16) if ven else None, "device": int(dev, 16) if dev else None,
                     "type": type_map.get(typ or "", (typ or "").lower())}
    return devs


def main():
    rc, out, err = run(CLI)
    if rc != 0:
        print(f"error{{kind=cli_failed rc={rc} stderr={err.strip()[:200]}}}")
        return 1
    mine = parse_mine(out)
    rc2, vout, verr = run(["vulkaninfo"])
    if rc2 != 0:
        print(f"error{{kind=vulkaninfo_failed rc={rc2} stderr={verr.strip()[:200]}}}")
        return 1
    theirs = parse_vulkaninfo(vout)
    print(f"mine_devices={sorted(mine)} vulkaninfo_devices={sorted(theirs)}")
    fail = 0
    for idx in sorted(set(mine) & set(theirs)):
        a, b = mine[idx], theirs[idx]
        for f in ("name", "api", "driver_raw", "vendor", "device", "type"):
            ok = a[f] == b[f]
            if not ok:
                fail += 1
            print(f"field{{gpu={idx} field={f} mine={a[f]} oracle={b[f]} verdict={'ok' if ok else 'FAIL'}}}")
    for idx in sorted(set(mine) ^ set(theirs)):
        print(f"field{{gpu={idx} field=device_set mine={'mine' if idx in mine else 'oracle'} verdict=FAIL}}")
        fail += 1
    print(f"crosscheck{{devices={len(mine)} fields={6 * len(mine)} diff={fail} verdict={'SOUND' if fail == 0 else 'MISMATCH'}}}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
