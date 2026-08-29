# 网络层问题：超时、卡死、时通时不通

> 这一类问题最难查，因为**报错发生的位置和原因所在的位置往往不是一个地方**——
> 客户端报超时，原因可能在 IPv6 路由、在 MTU、在一个你早就忘了的环境变量。
>
> 这份文档按「最容易误判」的顺序排列，每一项都给了判别命令。
> 基础排错见 [`troubleshooting.md`](troubleshooting.md)。

## 一、小请求正常，一发长内容就卡死 —— MTU 黑洞

**这是最难自己想到的一个。** 典型表现：

- `claude --version` 正常
- curl 打个 `hi` 正常返回
- 一旦贴进去几百行代码、或者对话轮次多了，请求**挂在那里不动**，最后超时
- 重试还是同一个位置卡住，看起来像"服务端处理不过来"

原因是链路上某一跳的 MTU 比你本机小，而**路径 MTU 发现（PMTUD）所依赖的
ICMP 报文被中间设备丢弃了**。小包能过，超过阈值的大包直接进黑洞，
两边都不会收到任何错误——所以表现是"卡死"而不是"报错"。

VPN、部分家用路由、某些云厂商的隧道网络都可能造成这个。

### 判别

用逐步增大的包探测，找到断点：

```bash
# Linux / macOS：-M do 禁止分片，-s 指定负载大小
for s in 1200 1300 1400 1472; do
  printf "%5d: " $s
  ping -c1 -W2 -M do -s $s api.anthropic.com >/dev/null 2>&1 \
    && echo ok || echo "FAIL ← 超过这个尺寸就不通了"
done
```

macOS 上参数不同：

```bash
ping -c1 -D -s 1400 api.anthropic.com
```

**判读**：1200 通、1400 不通，说明路径 MTU 在两者之间。
正常以太网是 1500（负载 1472 + 28 字节头），PPPoE 常见 1492，
各类隧道再减 20～80 不等。

### 处理

把接口 MTU 调到探测出来的安全值以下：

```bash
# Linux，临时生效，重启后失效
sudo ip link set dev eth0 mtu 1400

# WSL 里网卡通常叫 eth0，先确认
ip -brief link
```

如果是 VPN 或代理软件造成的，优先在那一侧调，别改物理网卡。

⚠️ **改 MTU 会影响这台机器的所有网络流量**，先用探测确认真是 MTU 问题再动，
不要当成万能解药。

## 二、IPv6 线路不通，但系统优先走 IPv6

表现是"时通时不通"或者"一直连不上，但别人都正常"。

多数系统在同时拿到 A 和 AAAA 记录时优先尝试 IPv6。如果本地有 IPv6 地址
但那条路由实际不通，每个请求都要先等 IPv6 超时才回退到 IPv4——
轻则慢得离谱，重则直接失败。

### 判别

分别用两个协议族打一次，对比：

```bash
curl -4 -sI -m 10 https://api.anthropic.com/v1/messages | head -1   # 强制 IPv4
curl -6 -sI -m 10 https://api.anthropic.com/v1/messages | head -1   # 强制 IPv6
```

| 结果 | 结论 |
|---|---|
| `-4` 通、`-6` 超时 | **IPv6 路由不通**，需要让系统优先走 IPv4 |
| 两个都通 | 不是这个问题 |
| 两个都不通 | 是端点或更基础的网络问题 |

看解析结果：

```bash
getent ahosts api.anthropic.com     # Linux
dig +short AAAA api.anthropic.com   # 只看 IPv6 记录
```

### 处理

Linux 上调整地址选择策略，让 IPv4 优先：

```bash
# 查看当前策略
getent ahosts api.anthropic.com | head

# /etc/gai.conf 里取消这一行的注释即可让 IPv4 优先
# precedence ::ffff:0:0/96  100
sudo sed -i 's/^#precedence ::ffff:0:0\/96  100/precedence ::ffff:0:0\/96  100/' /etc/gai.conf
```

单条命令临时验证可以直接用 `curl -4`。

## 三、代理环境变量：一个早就忘了的 export

详见 [`troubleshooting.md`](troubleshooting.md#请求全部超时但-curl-直连端点是通的)。
简述：变量指向一个当前环境里不存在的地址时，**每个请求都先撞一次超时**，
现象是"什么都慢、什么都失败"，但单独 curl 测端点却是好的。

```bash
env | grep -iE "proxy|PROXY"
```

### WSL 的特殊情况

**WSL 和 Windows 是两套独立的网络栈。** `.bashrc` 里的 `127.0.0.1:某端口`
在 WSL 里指的是 WSL 自己的回环，不是 Windows 侧的同名端口——
如果代理只在 Windows 上监听，WSL 里就是连不通的。

```bash
curl -sI --max-time 3 http://127.0.0.1:端口号 || echo "该端口在 WSL 内不可用"
```

## 四、配置写进去了 ≠ 当前 shell 生效

不是网络问题，但表现常常被当成网络问题（"改了地址还是连旧的"）。

```bash
env | grep -i anthropic     # 当前 shell 里实际是什么值
grep -rn "ANTHROPIC" ~/.bashrc ~/.zshrc 2>/dev/null   # 配置文件里写的是什么
```

两者不一致时，**以当前 shell 里的为准**——命令行 export 过的值优先级高于配置文件，
`source ~/.bashrc` 也覆盖不回来。开个新终端，或手动重新 export。

## 一个通用的排查顺序

```text
本机环境变量  →  DNS 解析  →  协议族（v4/v6）  →  MTU  →  端点本身
```

**从最靠近自己的一层开始查**，因为越靠近自己的越容易验证、也越容易被忽略。
顺序反了就会在最后一层上耗掉一下午——而问题其实在第一层。

每一层的验证成本都不到一分钟：

```bash
env | grep -iE "proxy|anthropic"                          # 环境变量
getent ahosts api.anthropic.com | head -3                 # DNS
curl -4 -sI -m 10 https://api.anthropic.com/v1/messages | head -1   # 协议族
ping -c1 -M do -s 1400 api.anthropic.com >/dev/null && echo mtu-ok  # MTU
```

---

由 [Code2AI](https://www.code2ai.codes/) 维护 · MIT License
