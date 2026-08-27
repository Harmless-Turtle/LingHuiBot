from typing import Dict

group_lottery: Dict[int, dict] = {}


def add_bet(group_id: int, user_id: int, number: int, amount: int):
    # 累加下注金额
    if group_id not in group_lottery:
        # 若意外缺失，则创建基础结构（或抛出明确异常以便调试）
        group_lottery[group_id] = {"bets": {}}
    bets = group_lottery[group_id].setdefault("bets", {})
    user_bets = bets.setdefault(user_id, {})
    user_bets[number] = user_bets.get(number, 0) + amount


def get_user_bet_amount(group_id: int, user_id: int, number: int) -> int:
    """获取用户对某数字的已下注总额"""
    bets = group_lottery.get(group_id, {}).get("bets", {})
    return bets.get(user_id, {}).get(number, 0)
