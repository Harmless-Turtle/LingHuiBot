from . import commands
from ...menu import admin_menu

sign_in = commands.sign_in
poke_check = commands.poke_check
tarot = commands.tarot
a_word = commands.a_word
btfrk = commands.btfrk
like = commands.like
eat_what = commands.eat_what
add_group = commands.add_group
switch_add_group = commands.switch_add_group
change_welcome = commands.change_welcome
change_welcome_text = commands.change_welcome_text
exit_change = commands.exit_change
GroupExitMember = commands.GroupExitMember
like_friend = commands.like_friend
add_friend = commands.add_friend
choice_friend = commands.choice_friend
handle_group = commands.handle_group
add_welcome = commands.add_welcome
SelfJoinGroupWelcome = commands.SelfJoinGroupWelcome

__all__ = [
    "sign_in",
    "poke_check",
    "tarot",
    "a_word",
    "btfrk",
    "like",
    "eat_what",
    "add_group",
    "switch_add_group",
    "change_welcome",
    "change_welcome_text",
    "exit_change",
    "GroupExitMember",
    "like_friend",
    "add_friend",
    "choice_friend",
    "handle_group",
    "SelfJoinGroupWelcome",
    "add_welcome"
]