# wolfkill_vote.py
# 投票与胜负判定逻辑
from collections import Counter
from typing import Dict, List, Optional


class WolfKillVote:
    def __init__(self, alive_players: List[int]):
        self.alive_players = alive_players
        self.votes: Dict[int, int] = {}  # {投票人: 被投票人}

    def cast_vote(self, voter: int, target: int):
        if voter in self.alive_players and target in self.alive_players:
            self.votes[voter] = target

    def tally(self) -> Optional[int]:
        """
        统计票数，返回被投票最多的玩家ID，平票返回None。
        """
        if not self.votes:
            return None
        count = Counter(self.votes.values())
        if not count:
            return None
        most_common = count.most_common()
        if len(most_common) == 1 or (len(most_common) > 1 and most_common[0][1] > most_common[1][1]):
            return most_common[0][0]
        return None  # 平票

    @staticmethod
    def check_win(role_map: Dict[int, str], alive_players: List[int]) -> Optional[str]:
        """
        判断胜负，返回胜利方（'狼人'/'好人'/None）
        """
        wolves = [pid for pid in alive_players if role_map.get(pid) == '狼人']
        others = [pid for pid in alive_players if role_map.get(pid) != '狼人']
        if not wolves:
            return '好人'
        if len(wolves) >= len(others):
            return '狼人'
        return None
