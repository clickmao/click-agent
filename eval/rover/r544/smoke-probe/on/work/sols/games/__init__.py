"""case_id -> 求解函数 的注册表。"""
from sols.games.alpha import run as _alpha_run

_GAMES = {
    "alpha": _alpha_run,
}


def get_game(case_id):
    """返回注册在 ``case_id`` 下的求解函数（text -> 输出）。"""
    try:
        return _GAMES[case_id]
    except KeyError:
        raise KeyError(case_id)
