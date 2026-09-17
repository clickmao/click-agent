"""games 包的 CLI 入口: python3 -m games <game_id>

契约:
  * STDIN 整体读入, 原样交给对应子游戏的 solve(text);
  * solve 的返回文本原样写到 STDOUT (末尾补一个换行);
  * 不打印任何多余文字/提示/调试信息;
  * 退出码: 0 = 正常; 1 = 自检失败; 2 = 用法错误/未知 game_id。

用法:
  python3 -m games <game_id>        # life | sub | nim | wythoff
  python3 -m games --list
  python3 -m games --selftest [<game_id> | all]
"""

from __future__ import annotations

import io
import sys

from . import GAMES, __version__, game_ids, get_solver

USAGE = (
    "usage: python3 -m games <game_id>\n"
    "       game_id: %s\n"
    "       python3 -m games --list | --selftest [<game_id>|all]\n"
    % ", ".join(game_ids())
)

# 每个子游戏的 CLI 级样例: (输入文本, 期望输出文本)
# 这里刻意经由真实入口 solve 驱动, 而不是自带参数直连内部函数 —— 用于接线核查。
_CLI_CASES = {
    "life": [
        ("3 3 0\n.#.\n.#.\n.#.\n", ".#.\n.#.\n.#."),
        ("3 3 1\n.#.\n.#.\n.#.\n", "...\n###\n..."),
    ],
    "sub": [
        ("4 2\n", "WIN"),
        ("3 2\n", "LOSE"),
        ("0 3\n", "LOSE"),
    ],
    "nim": [
        ("3\n1 2 3\n", "LOSE"),
        ("2\n3 3\n", "LOSE"),
        ("1\n5\n", "WIN 1 0 5"),
    ],
    "wythoff": [
        ("1 2\n", "LOSE"),
        ("3 5\n", "LOSE"),
        ("1 1\n", "WIN"),
    ],
}


def _run_solver(game_id, text):
    """调用 solve 并把结果规范成 str。"""
    out = get_solver(game_id)(text)
    if out is None:
        return ""
    if isinstance(out, (list, tuple)):
        return "\n".join(str(x) for x in out)
    return str(out)


def _selftest_one(game_id):
    """对单个 game_id 跑 CLI 级样例 + 子模块自带 --selftest。"""
    failures = []

    # (a) 子模块自带自检 (无头)
    module_name = GAMES[game_id][0]
    module = __import__(module_name, fromlist=["_selftest"])
    hook = getattr(module, "_selftest", None) or getattr(module, "selftest", None)
    if hook is None:
        failures.append("%s: 子模块未导出 _selftest/selftest" % game_id)
    else:
        try:
            ok = bool(hook())
            if not ok:
                failures.append("%s: 子模块自检返回 False" % game_id)
        except AssertionError as exc:
            failures.append("%s: 子模块自检断言失败: %s" % (game_id, exc))
        except Exception as exc:  # noqa: BLE001 - 自检要如实报告
            failures.append("%s: 子模块自检异常: %r" % (game_id, exc))

    # (b) 经真实入口 (get_solver -> solve) 驱动的 CLI 级样例
    for text, want in _CLI_CASES[game_id]:
        try:
            got = _run_solver(game_id, text)
        except Exception as exc:  # noqa: BLE001
            failures.append("%s: solve(%r) 异常 %r" % (game_id, text, exc))
            continue
        if got != want:
            failures.append(
                "%s: solve(%r) -> %r, 期望 %r" % (game_id, text, got, want)
            )

    return failures


def _selftest(target="all"):
    """无头自检; 返回 (ok, 失败明细列表)。"""
    if target in ("all", None, ""):
        ids = game_ids()
    else:
        ids = [target]

    failures = []
    for game_id in ids:
        if game_id not in GAMES:
            failures.append("unknown game_id: %r" % (game_id,))
            continue
        failures.extend(_selftest_one(game_id))

    # 分派器自身的负向控制: 未知 id 必须抛 KeyError, 且不能静默吞掉
    try:
        get_solver("__no_such_game__")
        failures.append("dispatcher: 未知 game_id 未抛 KeyError (负向控制失败)")
    except KeyError:
        pass
    except Exception as exc:  # noqa: BLE001
        failures.append("dispatcher: 未知 game_id 抛了非 KeyError: %r" % (exc,))

    # game_ids 排序契约
    if game_ids() != sorted(game_ids()):
        failures.append("game_ids() 未按升序返回")

    return (not failures), failures


def _selftest_main(argv):
    target = argv[0] if argv else "all"
    ok, failures = _selftest(target)
    if ok:
        sys.stdout.write("PASS\n")
        return 0
    sys.stdout.write("FAIL\n")
    for line in failures:
        sys.stdout.write("  - %s\n" % line)
    return 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv:
        sys.stderr.write(USAGE)
        return 2

    first = argv[0]

    if first in ("-h", "--help"):
        sys.stderr.write(USAGE)
        return 0
    if first == "--version":
        sys.stdout.write(__version__ + "\n")
        return 0
    if first == "--list":
        sys.stdout.write("\n".join(game_ids()) + "\n")
        return 0
    if first == "--selftest":
        return _selftest_main(argv[1:])

    if first not in GAMES:
        sys.stderr.write("error: unknown game_id %r\n" % (first,))
        sys.stderr.write(USAGE)
        return 2

    # 真实入口: STDIN 整体读入 -> solve -> STDOUT 原样写出 (无多余文字)
    data = sys.stdin.read()
    text = _run_solver(first, data)
    if text:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
