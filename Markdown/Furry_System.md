<p align="center">
  <a href="https://github.com/Harmless-Turtle/LingHuiBot"><img src="http://q.qlogo.cn/headimg_dl?dst_uin=3806419216&spec=640&img_type=jpg" width="200" height="200" alt="nonebot"></a>
</p>

<h1 align="center"><em>凌辉Bot Furry系统功能列表</em></h1>

此系统脚本位于 <a href="https://github.com/Harmless-Turtle/LingHuiBot/blob/main/src/plugins/Furry.py">Furry.py</a> 中

## 如何阅读该文档？
可用：表示该功能是否可以使用。<br>
> 可用图例：<br>✅：经过测试后，未发现明显问题或bug的功能。<br>⚠️：正在进行测试或需要更进一步验证的功能。<br>❌：暂未上线或正在开发中的功能。

功能：功能名称。<br>
> 功能名字中的斜杠是或的意思<br>例如功能`签到/凌辉好久不见`的用法是`直接发送`，那么当您在使用签到这个功能时`直接发送签到`或者`直接发送凌辉好久不见`即可。<br>在功能名称中的“<>”符号意味着这是一个需要填写的文本。它可能是数字或文字。例如`来只<数字id>`功能需要您输入一个数字，以查找该数字的图片是否存在。

语法实例/用法：如何使用该功能。
> 直接发送即使用时直接发送功能名字即可。

效果：该功能的效果
> 功能实现的具体效果，即凌辉Bot会如何响应该命令。

## 提醒事项
由于该系统非常依赖于远程服务器的响应速度以及网络环境，这意味着此系统受网络影响。可能会不稳定或拉取失败，若出现少数无法获取的情况，请重试多几次。若一直无法响应请联系开发者或提出Issue。

## 功能列表
<h3>FurPic功能</h3>

> 该功能由`兽云祭API`提供服务及技术支持

|可用|功能|语法示例|效果|
|----|----|----|----|
|✅|来只兽兽/来只毛/来只兽|`来只兽兽`|拉取一张随机的Furry图片|
|✅|来只<数字 id / 文本 名字><br>指定<数字 id / 文本 名字><br>指定#<数字 id / 文本 名字>|`来只9162`<br>`来只海龟`|返回数字id为`9162`的图片信息或图片名字含有`海龟`的随机图片的信息|
|✅|查列表<文本 名字><br>查兽兽<文本 名字><br>查列表#<文本 名字>|`查列表海龟`|返回名字中所有带有`海龟`名字的图片信息<em>`不带图片`</em>|
|✅|投图#<文本 名字>#<数字 类型>#<文本 留言>#<image图片>|`投图#海龟#1#没什么好留言的x#img对象`|向`兽云祭API`平台上传一张照片|

> 在手机上使用投图功能需要将发图方式更改为半屏相册，操作指南：<br>在聊天页单击左上角头像（不是名字）或从左向右滑动一下屏幕->单击左下角设置->单击通用->单击发图方式->改为半屏相册->回到群聊发送投图命令

### 上传示例
|在移动设备中上传|在Windows中上传|
|----|----|
|<a href="https://github.com/Harmless-Turtle/LingHuiBot/blob/main/Markdown/Example_Picture/mobile_upload.gif">上传示例（手机）</a>|<a href="https://github.com/Harmless-Turtle/LingHuiBot/blob/main/Markdown/Example_Picture/PC_upload.gif">上传示例（电脑）</a>|