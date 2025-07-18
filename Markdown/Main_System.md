<p align="center">
  <a href="https://github.com/Harmless-Turtle/LingHuiBot"><img src="http://q.qlogo.cn/headimg_dl?dst_uin=3806419216&spec=640&img_type=jpg" width="200" height="200" alt="nonebot"></a>
</p>

<h1 align="center"><em>凌辉Bot 主系统功能列表</em></h1>

此系统功能代码位于 <a href="../src/plugins/Main.py">Main.py</a> 中

## 如何阅读该文档？
可用：表示该功能是否可以使用。<br>
> 可用图例：<br>✅：经过测试后，未发现明显问题或bug的功能。<br>⚠️：正在进行测试或需要更进一步验证的功能。<br>❌：暂未上线或正在开发中的功能。

功能：功能名称。<br>
> 功能名字中的斜杠是或的意思<br>例如功能`签到/凌辉好久不见`的用法是`直接发送`，那么当您在使用签到这个功能时`直接发送签到`或者`直接发送凌辉好久不见`即可。<br>在功能名称中的“<>”符号意味着这是一个需要填写的文本。它可能是数字或文字。例如`来只<数字id>`功能需要您输入一个数字，以查找该数字的图片是否存在。

语法实例/用法：如何使用该功能。
> 直接发送即使用时直接发送功能名字即可。

效果：该功能的效果
> 功能实现的具体效果，即凌辉Bot会如何响应该命令。

## 功能列表
<h3>未分类功能</h3>

| 可用 | 功能              | 语法示例/用法 | 效果                                                                  |
| ---- | ----------------- | ------------- | --------------------------------------------------------------------- |
| ✅   | 签到/凌辉好久不见 | `直接发送`    | 对当天进行群聊签到                                                    |
| ✅   | 塔罗牌            | `直接发送`    | 返回一张塔罗牌                                                        |
| ✅   | 一言              | `直接发送`    | 返回一句每日一言                                                      |
| ✅   | 我是福瑞控(？)    | `我是海龟控`  | 返回群成员昵称/头衔/资料卡中第一个含`海龟`的资料卡                    |
| ✅   | 点赞/赞我         | `直接发送`    | 让凌辉 Bot 点赞你的资料卡 10 次<em>（偶尔无法点赞/可以点很多次）</em> |
| ✅   | 今天吃什么        | `直接发送`    | 随便甩两个吃的/喝的，适合纠结症（？）                                 |

---

<h3>群欢迎/送行功能</h3>

> 神 tm 送行（

| 可用 | 功能                                | 语法示例/用法         | 效果                                                    |
| ---- | ----------------------------------- | --------------------- | ------------------------------------------------------- |
| ✅   | 入群欢迎(开/关)                     | `入群欢迎开`          | 操作凌辉 Bot 是否需要对新入群的群友发送`入群欢迎信息`   |
| ✅   | 修改欢迎/修改入群欢迎/欢迎文本      | `修改欢迎 欢迎新成员` | 更改<em>当前群聊</em>的新成员入群欢迎时的发送的欢迎信息 |
| ✅   | 退群提示/退群提醒/退群通知/退群检测 | `退群提示开`          | 操作凌辉 Bot 是否需要响应群友退群事件                   |
|✅|入群检测(开/关)|`入群检测开`|操作凌辉Bot是否需要检测新人入群<br><b>`需要管理员权限`</b>|

<h3>菜单显示</h3>

|可用|功能|语法实例/用法|效果|
|----|----|----|----|
|✅|菜单/凌辉菜单|`直接发送`|输出凌辉Bot所有的功能|
|✅|菜单01/基本菜单|`直接发送`|输出凌辉Bot主功能菜单|
|✅|菜单02/Furry菜单/furry菜单|`直接发送`|输出凌辉Bot furry系统功能菜单|
|✅|菜单03/结婚菜单|`直接发送`|输出凌辉Bot结婚系统功能菜单|