# 常见报错排查

> 实际会撞上的几类报错，每个都给了可直接跑的诊断命令和明确的判断依据。
>
> 安装问题见 [`install.md`](install.md)，端点配置见 [`configuration.md`](configuration.md)，
> 升级卡住见 [`upgrade.md`](upgrade.md)。

## 先分清是哪一层

```bash
curl -sI -m 10 https://registry.npmjs.org/@anthropic-ai/claude-code | head -1   # 安装源
curl -sI -m 10 https://api.anthropic.com/v1/messages | head -1                  # API 端点
```

安装、请求、升级依赖三个**互相独立**的服务，
先确认是哪一层出问题，再往下查——这一步能省掉大量无效尝试。

## `Is a directory`

```text
/home/用户名/.local/bin/claude: Is a directory
```

软链指到了版本目录而不是二进制文件。
完整成因和两种目录布局的区别见 [`upgrade.md`](upgrade.md#软链必须指到二进制文件本身)。

先看软链指向哪儿：

```bash
ls -la ~/.local/bin/claude
```

## 请求全部超时，但 curl 直连端点是通的

先检查 shell 里有没有残留的网络相关环境变量。这类变量一旦指向一个当前环境里
**不存在的地址**，所有请求都会先撞一次超时才失败——现象就是「什么都慢、什么都失败」，
但单独用 curl 测端点却是好的。

```bash
env | grep -iE "proxy|PROXY"        # 看有没有
```

如果有，且你并不需要它们：

```bash
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
claude --version
```

写脚本调用 API 时，最好在程序里直接把这几个变量摘掉——
**你要测的是端点，不是本机的网络配置**：

```python
import os
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
          "all_proxy", "ALL_PROXY"):
    os.environ.pop(k, None)
```

### WSL 里要特别注意的一点

**WSL 和 Windows 是两套独立的网络栈。** `.bashrc` 里写的 `127.0.0.1:某端口`，
在 WSL 里指的是 WSL 自己的回环地址，**不是 Windows 侧的同名端口**——
如果那个端口只在 Windows 上监听，WSL 里就是连不通的。

```bash
curl -sI --max-time 3 http://127.0.0.1:端口号 || echo "该端口在 WSL 内不可用"
```

结论：WSL 里跑的命令通常直接走默认网络即可。
配了不可用的地址反而让每个请求都先超时一轮。

## `401` / `403`

密钥错误或已失效。**先用 curl 单独验证**，把客户端因素排除掉
（命令见 [`configuration.md`](configuration.md#验证端点是否真的通了)）。

### 403 要看响应体，不要只看状态码

403 可能来自三个完全不同的地方，处理方式毫无关系：

| 响应体长什么样 | 真正的原因 |
|---|---|
| 纯文本 `error code: 1010`，或一整页 HTML | **WAF / CDN 拦截**，跟你的密钥无关 |
| `{"error":{"type":"authentication_error",...}}` | 鉴权真的失败了 |
| `{"error":{"type":"permission_error",...}}` | 密钥有效，但没有这个权限 |

第一种最容易误判——**自己写脚本时尤其常见**。`urllib` 默认发
`Python-urllib/3.x`、`requests` 默认发 `python-requests/2.x`，
CDN 的 WAF 会直接拒掉这类特征明显的客户端签名，返回的 403 和「密钥不对」长得一样。

控制变量确认（其余全固定，只改 UA）：

```python
import os, json, urllib.request, urllib.error

BODY = json.dumps({"model": "claude-sonnet-5", "max_tokens": 8,
                   "messages": [{"role": "user", "content": "hi"}]}).encode()

def go(ua):
    h = {"content-type": "application/json",
         "x-api-key": os.environ["ANTHROPIC_AUTH_TOKEN"],
         "anthropic-version": "2023-06-01"}
    if ua:
        h["user-agent"] = ua
    req = urllib.request.Request(
        os.environ["ANTHROPIC_BASE_URL"] + "/v1/messages",
        data=BODY, headers=h, method="POST")
    try:
        return f"HTTP {urllib.request.urlopen(req, timeout=30).status}"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}  body: {e.read()[:60].decode('utf-8','ignore')}"

print("默认 UA:", go(None))
print("普通 UA:", go("my-tool/1.0"))
```

一行 header 的差别。修复就是给你的客户端一个正常的 UA——
建议**报上工具自己的名字**而不是伪装成浏览器，HTTP 规范里 UA 本来就是用于标识客户端的。

## `404`，但配置看着都对

`ANTHROPIC_BASE_URL` 里重复写了 `/v1/messages`。
多数客户端会自己补这一段，于是实际路径变成 `/v1/messages/v1/messages`。

判别方法是看**客户端最后拼出来的完整 URL**，不是看你配了什么。
详见 [`configuration.md`](configuration.md#base_url-的路径规则)。

## `temperature is deprecated for this model`

Claude 5 家族等新模型已弃用 `temperature` 参数，请求里带上会直接 400。
自己写脚本调用时去掉即可；用 Claude Code CLI 不会遇到这个。

## `claude --version` 正常但一启动就报错

说明二进制没问题，是配置或网络层。按顺序：

1. `env | grep -i anthropic` —— 环境变量对不对
2. 用 curl 直接打端点 —— 把客户端因素排除掉
3. `env | grep -i proxy` —— 有没有残留的代理变量

## 一个通用原则

排查这类问题时，**故障现象出现的位置，和故障原因所在的位置，经常不是同一个地方**——
报错在你的客户端里，原因在 CDN、在环境变量、在配置字符串里。

所以动手改之前，先建两个对照组：

| 对照组 | 怎么做 | 能排除什么 |
|---|---|---|
| **换客户端** | 同一个请求用 curl 再打一次 | 区分「端点问题」和「客户端问题」 |
| **去掉凭证** | 故意不带密钥打一次 | 确认端点活着，看清它的错误结构长什么样 |

第二条最被低估。不带凭证打一次，一个请求同时告诉你三件事：
端点是活的、它的错误响应是不是标准 JSON 结构、它接受哪些鉴权头（通常直接写在报错里）。

```bash
curl -sS -X POST "$ANTHROPIC_BASE_URL/v1/messages" \
  -H 'content-type: application/json' -d '{}'
```

两条加起来不到一分钟，能省掉一下午。

---

由 [Code2AI](https://www.code2ai.codes/) 维护 · MIT License
