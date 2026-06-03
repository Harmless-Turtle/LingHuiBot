<p align="center">
  <a href="https://github.com/Harmless-Turtle/LingHuiBot"><img src="https://q.qlogo.cn/headimg_dl?dst_uin=3806419216&spec=640&img_type=jpg" width="200" height="200" alt="nonebot"></a>
</p>

<h1 align="center"><em>凌辉Bot CookieCloud配置指南</em></h1>

凌辉Bot使用的nonebot_plugin_bilichat插件将使用CookieCloud方式获取用户Cookie以登录，这么做理论上可以降低订阅哔哩哔哩时，因登录状态异常导致的订阅获取失败问题。<br>
**解决例如ERROR 412或者ERROR 429问题。**<br>
**警告：实验性功能！应用请注意可能的环境损坏风险！**<br>
该功能已经配置在[src/plugins/cookiecloud](cookiecloud)中，这个文件会**运行Uvicorn服务器。**<br>
请按照如下的操作对bilichat插件进行配置，**此配置教程默认您已经成功将凌辉Bot运行于您的服务器中**

> 前置要求：找一个登录过哔哩哔哩的浏览器，安装CookieCloud插件，并在其中设置好密码和UUID。<br>
> CookieCloud插件的下载地址：
> - Chrome商店：https://chromewebstore.google.com/detail/cookiecloud/ffjiejobkoibkjlhjnlgmcnnigeelbdl
> - Edge商店：https://microsoftedge.microsoft.com/addons/detail/cookiecloud/bffenpfpjikaeocaihdonmgnjjdpjkeo
> - Firefox商店：https://addons.mozilla.org/zh-CN/firefox/addon/cookiecloud2/

1. 打开config/nonebot_plugin_config/config.yaml文件。 <br>
2. 找到其中的local_api_config配置项，在下面添加内容：<br>
cookie_clouds:<br>
**-**   password: CookieCloud配置的密码<br>
    url: http://127.0.0.1:23333br>
    uuid: CookieCloud配置的UUID<br>

> 由于markdown渲染的问题，您需要保证粘贴的内容符合Yaml文件规则。
3. 在终端定位到src/plugins/cookiecloud目录下，执行命令：<br>
   - Linux系统：<br>
   `nohup <你的虚拟环境位置，示例：.venv/bin/uvicorn> main:app --host 127.0.0.1 --port 23333 > cc.log 2>&1 &`<br>

    - Windows系统：<br>
`.venv/bin/uvicorn main:app --host 127.0.0.1 --port 23333`

4. 在浏览器的CookieCloud插件中，单击`测试`或者`手动同步`按钮，观察uvicorn终端是否出现如下信息：<br>
> INFO:     127.0.0.1:42378 - "GET /get/<你的uuid> HTTP/1.1" 200 OK

5. 重启凌辉Bot实例，观察终端是否出现：
`[INFO] nonebot_plugin_bilichat | 本地 API 已启用, 地址: http: //127.0.0.1:9090/bilichat_local_request_api/bilichatapi 配置: `<br>
````
{
	"log_level": "DEBUG",<br>
	"log_trace_retention": 3,<br>
	"log_info_retention": 30,<br>
	"log_request_retention": 0,<br>
	"log_compression_format": "tar.xz",<br>
	"data_path": "/home/LingHui/NoneBot/LingHuiBot/data/nonebot_plugin_bilichat/bilichat_request",<br>
	"sentry_dsn": "",<br>
	"playwright_download_host": "",<br>
	"playwright_headless": true,<br>
	"retry": 3,<br>
	"timeout": 20,<br>
	"dynamic_cache_ttl": 120,<br>
	"pc_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",<br>
	"mobile_user_agent": "Mozilla/5.0 (Android 15; Mobile; rv:135.0) Gecko/135.0 Firefox/135.0",<br>
	"api_access_token": "",<br>
	"api_sub_dynamic_limit": "720/hour",<br>
	"api_sub_live_limit": "1800/hour",<br>
	"api_enable_health_check": false,<br>
	"account_recover_interval": 120,<br>
	"cookie_clouds": [{
		"url": "http://127.0.0.1:23333",<br>
		"uuid": "<你的UUID>",<br>
		"password": "<你的Password>"<br>
	}]<br>
}<br>
````
如果出现如上信息，即意味着您已经成功配置了CookieCloud，并且现在凌辉Bot的bilichat插件已经可以使用CookieCloud获取用户Cookie了。<br>
更详细的问题或疑难解答，请联系开发者解决。
