def check_number(udid:str,mode:str) -> tuple[str | None,str]:
    """
    校验传入的str是否为纯数字
    """
    if mode == "group":
        if udid.isdigit():
            return udid,f"群聊 {udid} "
        else:
            return None,""
    else:
        if udid.isdigit():
            return udid,f"用户 {udid} "
        else:
            return None,""