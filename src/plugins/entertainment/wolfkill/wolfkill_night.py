# wolfkill_night.py
# 狼人杀夜晚行动流程实现

from typing import Dict, Optional


class NightActionResult:
    def __init__(self):
        self.killed: Optional[int] = None  # 狼人刀死
        self.poisoned: Optional[int] = None  # 女巫毒死
        self.saved: Optional[int] = None  # 女巫救人
        self.checked: Optional[int] = None  # 预言家查验
        self.protected: Optional[int] = None  # 守卫守护
        self.poison_used: bool = False
        self.save_used: bool = False


class WolfKillNight:
    def __init__(self, role_map: Dict[int, str]):
        self.role_map = role_map
        self.actions = NightActionResult()

    def wolf_kill(self, target_id: int):
        self.actions.killed = target_id

    def witch_save(self, target_id: int):
        self.actions.saved = target_id
        self.actions.save_used = True

    def witch_poison(self, target_id: int):
        self.actions.poisoned = target_id
        self.actions.poison_used = True

    def prophet_check(self, target_id: int) -> str:
        self.actions.checked = target_id
        return self.role_map.get(target_id, "未知")

    def guard_protect(self, target_id: int):
        self.actions.protected = target_id

    def resolve(self) -> Dict[str, Optional[int]]:
        # 结算夜晚行动
        killed = self.actions.killed
        if killed is not None:
            # 女巫救人
            if self.actions.saved == killed:
                killed = None
            # 守卫守护
            if self.actions.protected == self.actions.killed:
                killed = None
        # 女巫毒人
        poisoned = self.actions.poisoned
        return {
            "killed": killed,
            "poisoned": poisoned,
            "checked": self.actions.checked,
            "protected": self.actions.protected
        }

# 用法示例：
# night = WolfKillNight(role_map)
# night.wolf_kill(123)
# night.witch_save(123)
# night.witch_poison(456)
# night.prophet_check(789)
# night.guard_protect(123)
# result = night.resolve()
