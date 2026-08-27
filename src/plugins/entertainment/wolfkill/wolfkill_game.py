import random
from pathlib import Path
from typing import List, Dict, Optional

from .wolfkill_night import WolfKillNight
from .wolfkill_vote import WolfKillVote


class WolfKillGame:
    def auto_check_and_finish(self):
        """
        自动判定胜负，如有胜负则返回胜利方，否则返回None。
        """
        winner = self.check_win()
        if winner:
            self.status = 'finished'
            self.data['status'] = 'finished'
            self.data['winner'] = winner
            self.save()
        return winner

    def __init__(self, room_file: Path, data: dict):
        self.room_file = room_file
        self.data = data
        self.players = data.get('players', [])
        self.status = data.get('status', 'waiting')
        self.max_players = data.get('max_players', 12)
        self.game_data = data.get('game_data', {})

    def assign_roles(self) -> Dict[int, str]:
        """
        分配角色，返回玩家ID到角色的映射。
        """
        num_players = len(self.players)
        roles = self._get_roles(num_players)
        random.shuffle(self.players)
        random.shuffle(roles)
        role_map = {pid: role for pid, role in zip(self.players, roles)}
        self.game_data['roles'] = role_map
        self.data['game_data'] = self.game_data
        return role_map

    def _get_roles(self, num_players: int) -> List[str]:
        """
        根据人数生成角色列表。
        """
        if num_players < 8:
            raise ValueError('人数不足，无法分配角色')
        roles = ['狼人'] * (num_players // 4)
        roles += ['预言家', '女巫', '猎人', '守卫', '白痴']
        while len(roles) < num_players:
            roles.append('村民')
        return roles[:num_players]

    def get_player_role(self, user_id: int) -> Optional[str]:
        return self.game_data.get('roles', {}).get(user_id)

    def save(self):
        from src.plugins import utils
        utils.handle_json(self.room_file, 'w', self.data)

    # 夜晚行动相关
    def start_night(self):
        """
        开启夜晚行动，初始化夜晚流程。
        """
        role_map = self.game_data.get('roles', {})
        self.night = WolfKillNight(role_map)
        self.game_data['night_action'] = {}
        return self.night

    def resolve_night(self):
        """
        结算夜晚行动，返回结果。
        """
        if not hasattr(self, 'night'):
            role_map = self.game_data.get('roles', {})
            self.night = WolfKillNight(role_map)
        result = self.night.resolve()
        self.game_data['night_result'] = result
        self.data['game_data'] = self.game_data
        self.save()
        return result

    # 投票与胜负判定
    def start_vote(self):
        """
        开启白天投票，初始化投票对象。
        """
        alive_players = self.game_data.get('alive_players', self.players)
        self.vote = WolfKillVote(alive_players)
        self.game_data['vote'] = {}
        return self.vote

    def cast_vote(self, voter: int, target: int):
        if not hasattr(self, 'vote'):
            alive_players = self.game_data.get('alive_players', self.players)
            self.vote = WolfKillVote(alive_players)
        self.vote.cast_vote(voter, target)
        self.game_data['vote'][voter] = target
        self.data['game_data'] = self.game_data
        self.save()

    def tally_vote(self):
        if not hasattr(self, 'vote'):
            alive_players = self.game_data.get('alive_players', self.players)
            self.vote = WolfKillVote(alive_players)
            for voter, target in self.game_data.get('vote', {}).items():
                self.vote.cast_vote(int(voter), int(target))
        out = self.vote.tally()
        if out is not None:
            # 票数最多的玩家出局
            alive = self.game_data.get('alive_players', self.players)
            if out in alive:
                alive.remove(out)
            self.game_data['alive_players'] = alive
            self.data['game_data'] = self.game_data
            self.save()
        return out

    def check_win(self):
        role_map = self.game_data.get('roles', {})
        alive_players = self.game_data.get('alive_players', self.players)
        return WolfKillVote.check_win(role_map, alive_players)

    def assign_roles(self) -> Dict[int, str]:
        """
        分配角色，返回玩家ID到角色的映射。
        """
        num_players = len(self.players)
        roles = self._get_roles(num_players)
        random.shuffle(self.players)
        random.shuffle(roles)
        role_map = {pid: role for pid, role in zip(self.players, roles)}
        self.game_data['roles'] = role_map
        self.data['game_data'] = self.game_data
        return role_map

    def _get_roles(self, num_players: int) -> List[str]:
        """
        根据人数生成角色列表。
        """
        # 以12人为例：3狼3民1预言家1女巫1猎人1守卫2白痴
        # 可根据实际需求调整
        if num_players < 8:
            raise ValueError('人数不足，无法分配角色')
        roles = ['狼人'] * (num_players // 4)
        roles += ['预言家', '女巫', '猎人', '守卫', '白痴']
        while len(roles) < num_players:
            roles.append('村民')
        return roles[:num_players]

    def get_player_role(self, user_id: int) -> Optional[str]:
        return self.game_data.get('roles', {}).get(user_id)

    def save(self):
        from src.plugins import utils
        utils.handle_json(self.room_file, 'w', self.data)

    # 其他游戏流程方法可继续补充，如夜晚行动、投票、胜负判定等
