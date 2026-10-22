# 现场笔记（每条对应一次真实事故）

只读当前阶段需要的一节。这里是具体命令和实测数字；流程判断在 SKILL.md，
helper 脚本契约在 [autodl-reference.md](autodl-reference.md)。

## 连接与身份

**先验证再问。** 实例按次租用，host/port 每次都变，`~/.ssh/config` 的 alias 几乎总是
过期的：

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 <alias> "hostname; nvidia-smi -L; df -h /root/autodl-tmp"
```

通了就是 key auth 已配好——**不要向用户要密码**。反复发生：用户在提示词里贴了明文
密码，而 key 一直是通的。不通时先分辨是 alias 过期（改 `HostName`/`Port`）还是 key 没装。

**Windows 一次性装 key（不需要 sshpass/plink/paramiko）。** OpenSSH ≥ 8.4 能用 askpass
helper 读密码：把密码写进 scratchpad 文件 + 一个 `cat` 该文件的 askpass 脚本，然后

```bash
SSH_ASKPASS=<script> SSH_ASKPASS_REQUIRE=force DISPLAY=:0 \
  ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -p <port> <user>@<host> \
  "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

装完立刻删掉密码文件，之后全部走 key，并提醒用户轮换已泄露的密码。为每台机器建一个
专用 key + config alias（下次续租只改 `HostName`/`Port`）。注意：用户预先存在的
`~/.ssh/id_ed25519` 私钥可能与它的 `.pub` 不匹配，不要依赖它。

**远端命令走脚本文件，不走 PowerShell 内联一行流。** PowerShell 会吃掉 `$` 和反斜杠。
本地写 LF 脚本 → `mkdir -p` 父目录 → 上传 → `ssh <alias> bash <remote_path>`，记录 sha。

**后台方式**：这类镜像通常只有 `screen`，没有 `tmux`；`nohup cmd &` 经 SSH 会随会话
一起死（实测两次静默失败）。用 `screen -dmS <run_id> bash <RUN_ROOT>/run.sh`。

**换实例 / 快照恢复**：系统盘可能保留 conda/torch/缓存而 `/root/autodl-tmp` 数据盘是
空的；快照恢复先刷出目录树、大 `.pth` 最后才到，run 目录会空约 10 分钟。`df`、文件
计数、partial 文件各看两次再下结论。

## 依赖陷阱

**先固定约束，再装任何东西。** 以下都是实测：

- **不要用 unpinned `pip install`。** 一条 `pip install timm transformers` 把 numpy 悄悄
  升到 2.x，而 torch 是按 numpy 1.x 编的 → `Failed to initialize NumPy: _ARRAY_API not
  found`，mmcv 一起挂。**每装一次包就重新断言一次关键版本**，不是开头 pin 一次就完事。
- **半坏的包比缺失的包更危险。** `mmengine` 无条件 import `transformers`：缺失会被优雅
  地按 ImportError 处理，而版本不兼容的 `transformers` 抛 AttributeError 并把
  mmcv/mmengine 一起带走。这种依赖**直接卸载**比降级省事。
- **prebuilt wheel 才是真正的约束**，不是 `setup.py` 里声明的范围。mmcv 2.1.0 只有
  torch 2.1 / py ≤ 3.11 的预编译轮子；默认镜像的 torch 2.8 / py3.12 没有可用轮子，
  硬上就是源码编译。
- **厂商定制的 torch 会被 pip 静默替换。** `2.2.0a0+git…` 这类 pre-release 不满足
  `torch>=2.2.0`，pip 直接下 PyPI 的 CUDA 版盖掉。用 constraints 文件把本地版本钉死让它
  **报错而不是覆盖**，必要时 `--no-deps`。同源问题：某些库声明 `transformers>=5.1.0`
  而 transformers 5.x 需要 torch ≥ 2.4，在 torch 2.2 上会静默禁用 PyTorch 并清空命名
  空间——按实际可用组合降级，不要跟着声明走。
- **HuggingFace**：gated 仓库在租来的机器上会 401。**不要把 HF token 复制到租来的实例**
  ——实例会被回收，凭据不会跟着回收。改用未 gated 的等价来源（例如 timm 提供的同一权重），
  或从本地缓存把 `model.safetensors` + `config.json` 传上去。下载卡在 0 字节时设
  `HF_HUB_DISABLE_XET=1`。已完整缓存且校验过时，在启动进程里设 `HF_HUB_OFFLINE=1`
  （必须在 library import 之前）以避开 Hub 元数据请求。

把最终可用的组合（python / torch / torchvision / numpy / 关键框架版本）写进
`LAUNCH_INFO.md`，下次开机直接复现，不要重新试错。

**国产/异构卡的额外一层**：算子可能存在但极慢或缺失。判断"某算子是不是瓶颈"时，
`torch.profiler` 会因为异步排队把耗时归错 op；用 `TorchDispatchMode` 在每个 aten op
周围同步才可靠。两个可复用的佐证：**在 sync 下变便宜的开销，本来就不属于那个 op**；
换成手写等价实现后耗时不变，也说明找错了。

## 吞吐与显存

**线程超订是这类机器的头号杀手。** 实例常是 100–256 核，PyTorch 默认 intra-op 线程池
= 核数。实测 256 核机器：主进程 168 线程、1372% CPU、**GPU 利用率 4%**；设
`OMP_NUM_THREADS=8` 后 48 线程、GPU 40%，配合正确 batch，epoch 47 分 → 20 分（2.3×）。
三个变量必须写进 `run.sh`（`screen` 里的进程不继承交互式 shell 的 export）：

```bash
export OMP_NUM_THREADS=8
export MKL_NUM_THREADS=8
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

**batch 实测表**（RF-DETR-Medium 800px / 24 GB，`scripts/probe_batch_size.sh`）：

| batch | GPU 均值 | 峰值显存 | 结论 |
|---|---|---|---|
| 2 | 40% | 7.3 GiB | 利用不足 |
| **4** | **58%** | **12.2 GiB** | **最优** |
| 8 | 42% | 22.8 GiB | 更慢且离 OOM 只剩 0.7 GiB |
| 12 | — | — | OOM |

探测三条修正：**在最坏 split 上探**（batch pad 到最大成员：800×800 train 上探出的 batch
到 1333×800 test 面积 ×1.67 直接 OOM，用 step-down ladder 如 `48 28 14`）；**多尺度乘以
ladder 的 max/base 比**（`expanded_scales` 最高 1056px = 1.39×，短窗口采不到）；
**探测长度超过框架的时间平均窗口**（mmengine 在 25 iter 上平均 `time:`，12 iter 的探测
全是 warmup 主导，8 倍 batch 范围内 s/iter 完全一样）。

**读利用率两个坑**：先确认在 train 还是 val 阶段（val 本来就低）；采样间隔 1–2 秒
（5 秒会跳过 bursty 训练的尖峰）。**显存不是目标，利用率才是**——I/O bound 的 capture
任务填满 VRAM 只买到吞吐。

**主机侧 RAM 也会杀死训练。** mosaic 类增强每个 worker 持有 4 张解码图 + 大画布，
`persistent_workers=True` 跨 epoch 保活；再叠一个 CPU 推理任务就 OOM。报错形如
`Caught MemoryError in DataLoader worker` 且申请量很小（几 MB），**很容易误读成 GPU
问题，其实是宿主 RAM**。降 `num_workers` 往往还更快（compute-bound 时 `data_time` ≈ 0.01 s）。

## 监控事故清单

| 事故 | 代价 | 规则 |
|---|---|---|
| monitor 仍读旧 run 的日志 | 空烧 **12 小时** GPU | 改 run 目录必须在同一条命令里改 monitor 路径 |
| OOM kill 后日志停止增长 | 与"安静训练中"无法区分 | `pgrep -f "<script>" >/dev/null \|\| echo PROCESS_GONE` |
| 残留旧 monitor | 互相矛盾的进度 | 一 run 一 monitor，结束即撤 |
| filter 只匹配成功标志 | crashloop 与正常同样沉默 | 覆盖 `OutOfMemory\|Traceback\|Killed\|EXIT=` |
| mmdet 穿过 NaN 退出 0 | 又对着尸体评测 35 分钟 | 看存活指标，不看你改的那个分支 |
| `pkill -f "tools/train.py"` | 误杀同机另一个健康 run | pattern 必须含该 run 的 `--work-dir`，拿不到就拒启 |
| 框架报告后台任务 killed | 重启后两个副本抢同一输出文件 | `pgrep -af` / `netstat` 核实后再重启 |

**存活指标要选对**：实测 concept loss 从 0.82 漂亮地降到 0.48，而模型早已 NaN 死亡——
focal 类有界损失在死模型上照样收敛。看 `loss_cls`、total loss 和主指标非 0。

**梯度诊断**：要抓爆炸源就在 clip **之前** 抓 per-group 梯度范数（`after_train_iter`
钩子看不到，框架在 `update_params` 内部已清零）。爆的那一组常常不是你改的那一组。

## 时间、指标与数据完整性

- **epoch 耗时只用已完成的 epoch 边界估算。** 第一个 checkpoint 往往是训练前的 sanity
  validation（启动后 20 秒就可能写出）；warm-up epoch 也不代表稳态。
- **停止准则用饱和曲线拟合，不用逐 epoch 差分。** 实测 delta 标准差 0.017 对阈值 0.001，
  差 17 倍。拟合本身会变：同一条曲线 5 点给渐近线 0.5063，6 点 0.5650，10 点才稳定在
  0.5535——点数不够时不要给出确定的预测。
- **压缩包按内容校验。** 一个 19 MB 的 `ShipRSImageNet.zip`（完整 4.31 GB）带着正确文件名
  躺在源目录里，build 按名字匹配到它反复失败：

  ```bash
  S=$(stat -c %s "$F"); N=$(unzip -l "$F" 2>/dev/null | tail -1 | awk '{print $2}')
  [ "$S" = "$EXPECTED_BYTES" ] && [ -n "$N" ] && echo "OK $N entries" || echo "TRUNCATED/CORRUPT"
  ```

  上传时先写 `<name>.part`，校验通过再改名。
- **未 commit 的产物是单副本。** 已部署的 checkpoint 曾只在一台随后被释放的机器上多存
  一份。释放实例前跑 `scripts/find_artifacts.sh` 并按内容校验。

## 移植/换卡时的验证纪律

判定一次 GPU 移植是否正确，**只看被保留的检测结果，不看整张量最大偏差**。两个都让
健全的移植看起来彻底崩坏的陷阱：**把模型 build 两次**会让 checkpoint 里没有的参数每次
拿到不同随机初始化（build 一次再 `.to(device)`）；**合成输入**会让所有 query 落在
0.05 置信度以下，两阶段 top-k 在背景 token 间打破近似平局的方式随 kernel 而异，于是垃圾
query 带着任意 box（最大偏差 0.81），而 0.05 以上的 query 一致到 8.5e-05。用真实域内 crop
做对照。
