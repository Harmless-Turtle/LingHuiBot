<p align="center">
  <a href="https://github.com/Harmless-Turtle/LingHuiBot"><img src="http://q.qlogo.cn/headimg_dl?dst_uin=3806419216&spec=640&img_type=jpg" width="200" height="200" alt="nonebot"></a>
</p>

<h1 align="center">LingHuiBot</h1>

_✨ 欢迎来到凌辉 Bot GitHub 仓库 ✨_

<p align="center">
  <a href="./LICENSE">
    <img src="https://img.shields.io/github/license/cscs181/QQ-Github-Bot.svg" alt="license">
  </a>
  <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="python">
</p>

## 写在前面

欢迎您来到由一只无害的 py 海龟（A Harmless Py Turtle）开发与维护的凌辉 Bot 开源仓库~ <br>
您可以在这里提交 Issue 或 bug 以反馈您在使用凌辉 Bot 时遇到的问题。也可以在这里提出你的新功能诉求。

> 您可以在`任何界面`通过单击头部的凌辉Bot图片回到本页。

## 用户协议

详见 [用户协议](./Markdown/User_Agreement.md)


<h2><em>凌辉Bot是什么?</em></h2>
凌辉Bot是一个<em>Tencent QQ</em>的Q群Robot，同时是一个应该达到了平均水准的<em>FurBot</em>，可以为您提供一定的<em>Furry服务</em>，它使用OneBot V11标准、NoneBot作为Robot框架、NapCat作为监听客户端、使用Python语言进行功能开发。使用了部分<em>NoneBot商店功能</em>以改进凌辉Bot的部分功能。

<h2><em>凌辉Bot可以做什么?</em></h2>
您可以通过查阅Markdown文件以了解凌辉Bot的可用/开发中的功能，详见下列超链接：<br>

|系统名称|系统介绍|
|---|---|
|<a href="./Markdown/Main_System.md">主要系统</a>|基本的QRobot功能|
|<a href="./Markdown/Furry_System.md">furry系统</a>|furry功能|

<h2><em>怎么使用凌辉Bot(普通用户)?</em></h2>
通过联系主要开发者：一只无害的py海龟（A Harmless py Turtle）以将凌辉Bot添加进您的群聊中。<br>
联系方式：<br>
QQ：1097740481<br>
项目链接（可直接跳转至哔哩哔哩主页）<br>
加入凌辉Bot内测用群：795413705

<h2><em>怎么使用凌辉Bot(开发者和高级用户)?</em></h2>

> 面向想要clone凌辉Bot并想要进行二次开发的用户和开发者。

你需要准备：<br>
一台搭载了任意Windows或Linux操作系统的设备，且性能不低于如下配置：

---

CPU：<code>Intel(R) Xeon(R) CPU E5-2680 v4 2.34GHz</code><br>
GPU：<code>可选的</code><br>
RAM：<code>≥8GB</code><br>
SWAP：<code>≥2GB</code><br>

----

若您的设备性能已满足如上最低条件，请开始部署您的软件部分：<br>
Windows操作系统安装教程：<br>
安装<code>Python 3.9+</code>，<code>Python 3.10.11是已被验证的版本号</code><br>
安装链接：<a href="https://www.python.org/">Python</a>，请根据您的操作系统来安装对应版本的<code>Python</code><br>

> 在安装时，请选择<code>Customize installation</code>，并确保<code>pip</code>被勾选。

安装完毕后，打开终端并键入命令：<code>pip install nb-cli</code>

> 如果您不希望更改您现有的开发环境，建议您新建dotEnv或Anaconda等虚拟环境后再输入命令

运行结束后，在终端中键入命令：<code>cd /d <您clone本仓库的文件夹路径或虚拟环境路径></code>并使用<code>.\activate</code>以进入虚拟环境

> 需先进行<code>pip install nb-cli</code>命令以安装NoneBot2，详情请见[NoneBot](https://nonebot.dev/)

随后运行下面的这些命令，确保商店插件被正常执行：<br>
<code>nb plugin install "nonebot_plugin_apscheduler" -i https://pypi.tuna.tsinghua.edu.cn/simple<br>
nb plugin install "nonebot_plugin_htmlrender" -i https://pypi.tuna.tsinghua.edu.cn/simple<br>
nb plugin install "nonebot_plugin_localstore" -i https://pypi.tuna.tsinghua.edu.cn/simple<br>
nb plugin install "nonebot_plugin_picstatus" -i https://pypi.tuna.tsinghua.edu.cn/simple<br>
nb plugin install "nonebot_plugin_multincm" -i https://pypi.tuna.tsinghua.edu.cn/simple<br>
nb plugin install "nonebot_plugin_wordle" -i https://pypi.tuna.tsinghua.edu.cn/simple<br>
nb plugin install "nonebot_plugin_datastore" -i https://pypi.tuna.tsinghua.edu.cn/simple<br>
nb plugin install "nonebot_plugin_mc_server_status" -i https://pypi.tuna.tsinghua.edu.cn/simple<br>
nb plugin install "nonebot_plugin_picmcstat" -i https://pypi.tuna.tsinghua.edu.cn/simple<br>
nb plugin install "nonebot_plugin_sentry" -i https://pypi.tuna.tsinghua.edu.cn/simple<br>
nb plugin install "nonebot_bison" -i https://pypi.tuna.tsinghua.edu.cn/simple</code>

尝试运行<code>nb run --reload</code>，并观察终端Log是否出现如下信息：

> [INFO] sentry_sdk | Uvicorn running on http://127.0.0.1:9090 (Press CTRL+C to quit)

若出现如上信息，即意味着您已经成功将凌辉Bot部署于您的电脑中。您可以通过例如NapCatQQ等WebSocket服务器通过监听<code>ws://localhost:9090/onebot/v11/ws</code>来将QQ对接至凌辉Bot

Linux操作系统安装流程：<br>
<s>既然都用Linux了，安装流程就不必教了，和Windows操作系统安装流程差不太多，换个命令而已</s>