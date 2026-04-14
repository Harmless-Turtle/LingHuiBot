<p align="center">
  <a href="https://github.com/Harmless-Turtle/LingHuiBot"><img src="http://q.qlogo.cn/headimg_dl?dst_uin=3806419216&spec=640&img_type=jpg" width="200" height="200" alt="nonebot"></a>
</p>

<h1 align="center">LingHuiBot</h1>

_✨ 欢迎来到凌辉 Bot GitHub 仓库 ✨_

<p align="center">
  <a href="./LICENSE">
    <img src="https://img.shields.io/github/license/cscs181/QQ-Github-Bot.svg" alt="license">
  </a>
  <img src="https://img.shields.io/badge/python-3.13.5-blue.svg" alt="python">
</p>

## 写在前面

欢迎您来到由凌辉Bot 开发组开发与维护的凌辉 Bot 开源仓库~ <br>
您可以在这里提交 Issue 或 bug 以反馈您在使用凌辉 Bot 时遇到的问题。也可以在这里提出你的新功能诉求。

> 您可以在`任何界面`通过单击头部的凌辉Bot图片回到本页。

## 用户协议

详见 [用户协议](markdown/user_agreement.md)

<h2><em>凌辉Bot是什么?</em></h2>
凌辉Bot是一个<em>Tencent QQ</em>的Q群Robot，同时是一个应该达到了平均水准的<em>FurBot</em>，可以为您提供一定的<em>
Furry服务</em>，它使用OneBot V11标准、NoneBot作为Robot框架、NapCat作为监听客户端、使用Python语言进行功能开发。使用了部分<em>
NoneBot商店功能</em>以改进凌辉Bot的部分功能。

<h2><em>凌辉Bot可以做什么?</em></h2>
您可以通过查阅Markdown文件以了解凌辉Bot的可用/开发中的功能，详见下列超链接：<br>

| 系统名称                                                  | 系统介绍        |
|-------------------------------------------------------|-------------|
| <a href="./markdown/main_system.md">主要系统</a>          | 基本的QRobot功能 |
| <a href="./markdown/furry_system.md">furry系统</a>      | furry功能     |
| <a href="./markdown/entertainment_system.md">娱乐系统</a> | 娱乐系统        |
| <a href="./markdown/admin_system.md">管理系统</a>         | (SU)凌辉管理员菜单 |

<h2><em>怎么使用凌辉Bot(普通用户)?</em></h2>
通过联系主要开发者：一只无害的py海龟（A Harmless py Turtle）以将凌辉Bot添加进您的群聊中。<br>
联系方式：<br>
QQ：1097740481<br>
项目链接（可直接跳转至内测用的QQ群）<br>
加入凌辉Bot内测用群：795413705

<h2><em>怎么使用凌辉Bot(开发者和高级用户)?</em></h2>

> 面向想要clone凌辉Bot并想要进行二次开发的用户和开发者。

你需要准备：<br>
一台搭载了任意Windows或Linux操作系统的设备，且性能不低于如下配置：

---

CPU：<code>Intel® Xeon® CPU E5-2680 v4 2.34GHz(4 Core)</code><br>
GPU：<code>可选的</code><br>
RAM：<code>≥8GB</code><br>
SWAP：<code>≥2GB</code><br>

----

若您的设备性能已满足如上最低条件，请开始部署您的软件部分：<br>
Windows操作系统安装教程：<br>
>
注意！以下安装教程建立在你已经部署完毕NapCatQQ或任意反向WebSocket端，且配置好协议对应端口的前提。如果您没有配置好协议端，在此处是无法连接的<br>

1. 安装 <a href="https://github.com/astral-sh/uv">uv</a> ，然后同步项目环境 `uv sync`

2. 将 `.env.example` 重命名成 `.env` 并填写相应配置。

3. 运行命令 `playwright install chromium` ，安装 `playwright`

4. 尝试运行 `nb run --reload` ，按提示更新至最新迁移并观察终端Log是否出现如下信息：

> 01-31 01:24:18 [INFO] nonebot | OneBot V11 | Bot <此处应该是你Bot的QQ号> connected

若出现如上信息，即意味着您已经成功将凌辉Bot部署于您的电脑中。您可以通过例如NapCatQQ等WebSocket服务器通过监听<code>ws:
//localhost:9090/onebot/v11/ws</code>来将QQ对接至凌辉Bot

> 注意：如果您的NoneBot2启动失败，请修改.env文件的<code>PORT=9090</code>为你系统中任一未被占用的端口，并在上述所说的WebSocket服务端中将<code>localhost:9090</code>中的9090更换为你自己配置的端口

Linux操作系统安装流程：<br>

<s>既然都用Linux了，安装流程就不必教了，和Windows操作系统安装流程差不太多，换个命令而已</s>

文件依赖：<br>
凌辉 Bot 要求您至少应该准备如下ttf字体文件包在data目录下：
- <code>SarasaFixedSlabJ-SemiBoldItalic.ttf</code><br>
下载链接：[SarasaFixedSlabJ-SemiBoldItalic](https://mirror.nju.edu.cn/github-release/be5invis/Sarasa-Gothic/LatestRelease/Sarasa-TTC-Unhinted-1.0.37.7z)

> 这个下载链接将会直接下载一个7z压缩包，解压后请将其中的<code>SarasaFixedSlabJ-SemiBoldItalic.ttf</code>文件放入凌辉Bot的data目录下。

<h2>联系开发组</h2>

（项目创始人）[一只无害的py海龟](https://qm.qq.com/q/rCmn3awLsY)

（特邀程序员）[bool听后摇了摇头](https://github.com/BoolCox)

<h6>十分感谢bool愿意给这托shift添砖加瓦（</h6>