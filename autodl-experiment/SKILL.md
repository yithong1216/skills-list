---
name: autodl-experiment
description: >
  Use when launching, monitoring, recovering, or finishing an AutoDL or
  SeetaCloud SSH GPU experiment; connecting to a newly rented, swapped, or
  snapshot-restored instance; diagnosing remote connection, dependency, cache,
  throughput, VRAM, transfer, or process failures; adding explicitly requested
  email notifications; or pulling back and recording experiment results before
  an instance is released. Excludes local-only debugging.
---

# AutoDL Experiment

把远程实验当作可核验、可恢复的运行过程：
**核对状态 → 连接与预检 → 冻结输入 → 测吞吐 → 启动一次 → 按证据监控 → 验证并回收。**

三件事必须分开，混同它们是这个 skill 存在的原因：
**SSH 命令返回 ≠ 进程还活着 ≠ 实验目标达成。**

## 1. 恢复任务契约

先读用户当前要求、已有入口、最新结果和项目 runbook。复用已授权的操作；
只询问确实缺失且会改变下一步的信息，不重复索取已知 host、路径或许可。

| 用户要求 | 本轮完成条件 |
| --- | --- |
| 只启动 | 精确任务已后台启动，并通过首个有意义的运行检查 |
| 只读状态/排错 | 报告有时间戳的已知状态和未确定项；不借机重启/改环境 |
| 给现有任务加通知 | 单独监听原任务；不包裹后重新运行训练 |
| 跑完实验/评估 | 所需阶段、结果验证和授权的回收全部完成 |
| 拉回指定结果 | 文件范围、传输完整性及本地解析检查通过 |

优先更新已有 `docs/AUTODL_EXPERIMENT_RUNBOOK.md` 或项目同类文档，保留以下简短
运行记录，不建立互相矛盾的状态表：

```text
目标/验收条件；本轮范围和既有授权
主机/端口/工作目录；run ID 和本次 attempt；session、PID/启动身份
实际 Python；代码/config/checkpoint/data 标识；缓存位置
当前阶段、依赖、最近已验证状态和时间；日志/结果/退出码路径
截止时间及其时区、剩余预算；下一步及重试前提；待回收文件
```

旧记忆用于定位证据，不用于断言实例仍在线、原 PID 仍存活或旧端口仍有效。
不同实例、checkout、实验协议和 attempt 的指标不可拼接。

**agent 中途死掉是常态**（spend limit、超时、断线）：让远端脚本边跑边把结果写进
CSV/JSON，报告阶段挂掉也不用重烧一遍 GPU。远程会话状态不转移给冷启动的
subagent——远程活自己做完，本地活才外包。

## 2. 连接纪律（每次换实例都会踩）

实例按次租用，host/port 每次都变，`~/.ssh/config` 里的 alias 几乎总是过期的。
**先验证连通，再问任何东西：**

```bash
ssh -o BatchMode=yes -o ConnectTimeout=8 <alias> "hostname; nvidia-smi -L; df -h /root/autodl-tmp"
```

- 这条通了就说明 key auth 已配好，**不要向用户要密码**。反复发生：用户在提示里
  贴了明文密码，而 key 一直是通的。
- 不通先判断是 alias 过期（改 `HostName`/`Port`）还是 key 没装，不要直接退回密码。
- 用户已贴过明文密码时提醒事后轮换；不把它写进命令行、脚本、日志摘要、
  `LAUNCH_INFO.md`、runbook 或任何会外发的内容。
- Windows 上一次性装 key（不需要 sshpass/plink/paramiko）：见
  [现场笔记](references/field-notes.md)「连接与身份」。

**不要从 PowerShell 发内联 bash 一行流。** PowerShell 会吃掉 `$` 和反斜杠，远端收到
的命令和你写的不是同一条。做法：本地写 LF 脚本 → 上传（先 `mkdir -p` 父目录，多数
put 助手不会自动建）→ `ssh <alias> bash <remote_path>`，并记录脚本 sha。
**本地 spawn/审批失败不是远端任务退出**，先修失败的那一层。

**镜像通常只有 `screen`，没有 `tmux`；`nohup cmd &` 经 SSH 会随会话一起死**
（实测两次静默失败）。先 `tmux -V || screen -v` 确认，默认写法：

```bash
ssh <alias> "screen -dmS <run_id> bash <RUN_ROOT>/run.sh"
```

**换实例 / 快照恢复后，先确认这台机器是不是你以为的那台。** 新实例的系统盘可能
保留 conda/torch/缓存，而 `/root/autodl-tmp` 数据盘是空的；快照恢复会**先刷出目录树、
大 `.pth` 最后才到**，run 目录会空约 10 分钟。**下结论前先看增长**：`df`、文件计数、
partial 文件各看两次，间隔几分钟，不要据此判定基线丢失。

**明确声明哪边是 source of truth。** 在远程副本上继续开发前先 diff 或比 sha——曾照着
一份数小时前的远端旧快照重写约 700 行，本地才是权威版本。修复必须落到本地源再同步
过去；只加在远端 staged 副本里的环境修复会被下一次同步覆盖掉。

## 3. 预检覆盖真正的入口

在新启动、实例变化或相关依赖修复后做针对性预检；健康运行期间不要反复扫描全环境。
`scripts/preflight_autodl.sh` 检查基础环境，**不能替代**项目入口检查。

1. **代码/配置一致**：确认实际远端版本和 dirty 文件；无 Git 时用明确文件清单与
   SHA-256。**正在被读取的 config、字典、脚本、checkpoint 不原地修改**——曾在 replay
   还在跑时编辑它会重复读取的 config（类别数 5→10），后 10 个 variant 被换了评测器，
   整张表作废。把必要输入冻结进 run/attempt，变更用新快照。
2. **准确解释器**：记录绝对 Python 路径、环境、关键包版本、CUDA 可用性及一次实际
   CUDA 操作。`find_spec` 成功不证明 ABI/算子可用；`python3` 不存在不证明 Python 未
   安装。先查项目正在使用的解释器，禁止激活失败后静默用 base。
3. **真实数据路径**：核对指定数据、权重、字典、样本/标签映射、空间和写权限。不用
   「名字相近」的数据替代，不用半份 manifest 启动依赖它的正式阶段。
4. **同一加载路径的 smoke**：用正式入口、工作目录、参数、解释器和缓存执行最小有意义
   的 batch/子集，验证导入、前向/反向或推理、保存和结果可读取。单元测试通过不能替代
   实际 CLI（`python tools/....py`）的测试。
5. **资源与耗时**：用真实计算测峰值显存和吞吐（见 §4），说明 MiB/GiB 与 GB 的单位。
   并发需留 CPU、RAM、显存、磁盘和 I/O 余量，不能只凭单进程的孤立估算叠加。

**这四项每次单独确认，各自对应一次真实事故：**

- `source /etc/network_turbo` —— 不开的话 **huggingface.co 完全不可达**；必须写进
  `run.sh`，交互式 shell 里 export 不会被 `screen` 里的进程继承。先确认该主机确实
  提供它，不要当成所有实例的必备项。
- `ulimit -n` —— 默认 1024，多 worker 大 batch 会死在 `received 0 items of ancdata`。
  修法**两条一起**：`ulimit -n 65536` 且训练脚本里
  `torch.multiprocessing.set_sharing_strategy` 设为 `file_system`。
- **系统盘与数据盘分别的余量** —— checkpoint 写满系统盘会静默失败。
- **仓库是否真的可 import** —— 没有 `setup.py` 的仓库 `pip install -e .` 是 no-op，
  需要 `PYTHONPATH=<repo>`；mmdet 系还要在 build dataloader 前调用
  `init_default_scope` 指定 mmdet，否则自定义 Dataset 不在 registry 里。

**装包比训练更容易毁掉一天**：unpinned `pip install` 会把 numpy 悄悄升到 2.x 而 torch
是按 1.x 编的；半坏的包比缺失的包更危险；prebuilt wheel 才是真正的约束；厂商定制 torch
会被 pip 静默替换；gated HF 仓库在租来的机器上 401，**不要把 HF token 复制到租来的
实例**。完整清单和修法见 [现场笔记](references/field-notes.md)。把最终可用的组合
（python/torch/torchvision/numpy/框架版本）写进 `LAUNCH_INFO.md`，下次直接复现。

准备、训练、验证和回收共用同一个截止时间。先测下载/首轮速度再决定是否继续，并为验证
和回收预留预算；新数据或大下载必须在授权范围内，不能消耗整段租期后才发现目标尚未开始。

## 4. 吞吐与显存：先测再改

AutoDL/SeetaCloud 实例常是 **100–256 核**，PyTorch 默认让 intra-op 线程池等于核数，
主进程开出上百个线程互相争抢，**GPU 反而被饿死**。实测：256 核机器上 168 线程 /
1372% CPU / **GPU 利用率 4%**；设 `OMP_NUM_THREADS=8` 后线程降到 48、GPU 升到 40%，
配合正确 batch，epoch 时间 **47 分 → 20 分（2.3×）**。

`run.sh` 里必设（不是交互式 shell —— `screen` 里的进程不继承）：

```bash
export OMP_NUM_THREADS=8
export MKL_NUM_THREADS=8
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

**batch size 实测决定，不要猜。** `scripts/probe_batch_size.sh` 用真实训练命令在若干
batch 上各跑一小段，报告 GPU 均值利用率、峰值显存和是否 OOM。batch 越大不一定越快——
接近显存上限时分配器开销占主导。

探测的三条必修正，每条对应一次真实 OOM 或一次废掉的测量：

1. **在最坏的那个 split 上探，不要在训练集上探。** 一个 batch 会 pad 到它最大的成员：
   统一 800×800 的 train 上探出的 batch，到 1333×800 的 test 面积 ×1.67 直接 OOM。
   用 step-down BATCH_LADDER（如 `48 28 14`），并让 capture 可续跑。
2. **多尺度训练要把实测峰值乘以 ladder 的 max/base 比。** `expanded_scales` 最高训到
   1056px = 1.39× 显存，短窗口探测根本没采到最高那一档。
3. **探测长度必须超过框架的时间平均窗口。** mmengine 把 `time:` 在 25 iter 窗口上平均，
   12 iter 的探测每一行都是 warmup 主导——8 倍 batch 范围内 s/iter 完全一样，看着
   「很稳定」，其实一个数都不能用。

**显存不是目标，利用率才是**：capture/推理这类任务把 VRAM 填到 23.4/24.5 GB 也可能是
I/O bound，这时填满显存只买到吞吐。读 GPU 利用率两个坑：**先确认当前是 train 还是 val
阶段**（val 本来就低，在 val 期间采样会得出「数据加载饿死 GPU」的错误结论），**采样间隔
1–2 秒**（5 秒会跳过 bursty 训练的短促尖峰）。

**先量后改。** 测得 dataloader worker 只占 3% CPU，瓶颈就不是 `num_workers`，改它是浪费
一次重启。任何一次测量与假设冲突时，停下来重新诊断，不要按原假设动手。

## 5. 启动一次，保留恢复证据

长任务使用可用的 `screen`/`tmux` 或项目已有作业管理器。脚本自己设置工作目录、解释器
及所需缓存/网络环境，不能依赖先前交互 shell 的状态。

- 先排查相同 run/attempt 是否已启动；新 attempt 使用新目录和日志。已有 `.run_claim`、
  日志或退出状态说明该目录已被使用——换新 attempt 或走项目已验证的 resume 路径，
  **不要删除 claim 绕过检查**。
- 不覆盖原 `.sh`。已有入口用 `scripts/wrap_existing_run.sh` 包裹；新入口用
  `assets/run.sh.template`。可预放 config/脚本，但已有运行状态/日志必须先核对。
- 记录 session、实际进程及启动身份、日志和原子退出码。启动命令返回 0 后，**再检查首个
  batch/epoch 或实际结果写入**；这才支持「已成功启动」。
- **换了架构/骨干先跑一次短 lr sanity**（几个 epoch、不带 val）。「为了对齐 baseline 所以
  沿用同一个 lr」不是对照，是保证有一边失配：SGD 0.02 适配 ResNet+FPN，而接在冻结 ViT 上
  的随机初始化 head 直接发散成全背景解。整个 30 epoch 才 22 分钟，先探 lr 永远划算。
- 首轮出现导入错误、NaN、OOM 或写入错误时，保留 traceback 与输入版本，修复已证实原因后
  做最小复测，不盲目启动全部正式实验臂。
- 自动衔接下一阶段必须读取完整结果和指定 gate；`COMPLETE` 字符串、GPU 归零或退出 0 不能
  替代科学验收。

**SSH 启动命令超时可能发生在远端执行之后。先核对同一个 attempt 的进程/session/退出码/
产物，再决定是否重试**，不能因为客户端没收到确认就重复启动。

## 6. 分开监控连接、进程和结果

`scripts/monitor_run.sh` 是一次只读快照，不是持久监控服务。报告状态需注明检查时间和
证据，并区分：

| 观测 | 结论与下一步 |
| --- | --- |
| 本地审批/沙箱失败，尚未建立 SSH | 观测未执行，不是训练失败；修复调用层，保留旧状态时间戳 |
| SSH 断开或读取超时 | 连接状态未知；核对原 run，不能直接重启 |
| 匹配启动身份的进程存活 | 进程运行；结合日志/计数/吞吐变化判断是否推进 |
| 空日志、长时间无 checkpoint | 可能缓冲或有长阶段；检查预期写出边界，不能判完成或挂死 |
| session/PID 不见且无退出码 | 中断或 UNKNOWN；查进程身份、宿主重启、日志和检查点 |
| 同一 attempt 的退出码非 0 | 进程失败，保全证据后诊断；与通知失败分开 |
| 退出 0、所需结果不完整 | 进程正常结束，实验仍未完成 |

### Monitor 纪律（各自对应一次真实事故）

1. **改 run 目录时，必须在同一条命令里同时更新 monitor / 解析脚本的路径。** 曾把训练迁到
   新 run dir 却让 monitor 继续读旧日志，训练 OOM 崩了无人发现，**空烧 12 小时 GPU**。
2. **monitor 必须能独立于日志判断进程是否还活着。** 进程被 OOM kill 后日志就不再增长，
   看起来和「安静地训练中」完全一样。至少加一条：
   `pgrep -f "<train_script>" >/dev/null || echo PROCESS_GONE`。
3. **一个 run 只留一个 monitor，run 结束就撤掉。** 残留的旧 monitor 会制造互相矛盾的进度。
4. **失败也要能触发通知。** filter 只匹配成功标志时，crashloop 和「还在跑」是同一种沉默。
   至少覆盖 `OutOfMemory|Traceback|Killed|EXIT=`。
5. **`EXIT=0` 不等于跑成功。** mmdet 会一路穿过 NaN 正常退出：一次 run 报 EXIT=0、主指标
   0.0000，后面链起来的评测又对着一具尸体跑了 35 分钟。**终止条件要看存活指标**
   （`loss_cls`、total loss、主指标非 0），**不要看你正在改的那个分支**——实测 concept
   loss 从 0.82 漂亮地降到 0.48，而模型早就死了。
6. **watchdog 必须绑定到具体 run。** 第一版 NaN watchdog 用 `pkill -f tools/train.py`，
   顺手杀掉了同机上另一个健康的 run。pattern 必须包含该 run 的 `--work-dir` 或等价唯一
   标识，**拿不到唯一 pattern 就拒绝启动**。绝不使用全局 `pkill python`。
7. **主动汇报，不要等用户问。** 启动后立刻确认三件事：进程在、GPU 被占、第一个
   epoch/step 行出现了——OOM 和 config 错在这里就能看见，而不是 30 分钟后。然后挂一个
   后台 watcher 等终止标志，只在**启动确认 / 出错 / 完成**三个点汇报。
8. **多个 run 共享一张卡时，明确说谁排在谁后面。** 峰值接近显存上限的任务不能重叠。
9. **框架说「已停止」不代表真的停了。** 后台 `scp` / `ssh -L` / `docker build` 被报告
   killed 而进程仍在跑（本地 Windows 侧同样发生过）。重启前先 `pgrep -af <pattern>` /
   `netstat` 核实，否则会起一个和原任务抢同一个输出文件的副本。

检查频率按阶段耗时设定；没有变化时退避，不连续刷相同命令，也不把重复状态总结当进展。
共享实例上「GPU 忙」不证明本任务存活，应核对 PID。失联但可能仍活着的任务保留 UNKNOWN，
继续完成不依赖连接的有用工作。若要在会话结束后持续检查，使用用户授权的远端 watcher 或
宿主定时工具并验证注册成功；**「我会继续监控」本身不建立监控**。

对重复故障先定位层次：本地工具 → SSH → shell/环境 → 同步/缓存 → 任务入口 → 训练数值
→ 结果验证。一次修复后症状相同，就检查上一个假设和生产/读取接口；只有修复或新证据改变
条件才重新运行。不删除部分下载、缓存或 checkpoint 来「从头试试」。

### 时间与指标的取数纪律

- **只用「已完成的 epoch 边界」估算 epoch 耗时。** 第一个 checkpoint 往往是训练前的 sanity
  validation（可能启动后 20 秒就写出），拿它算速度会得到荒谬结论；warm-up epoch 也不能
  代表稳态。
- **停止准则看拟合趋势，不看逐 epoch 差分。** delta 噪声远大于阈值时（实测 delta 标准差
  0.017 对阈值 0.001，相差 17 倍），「连续 3 个 epoch 增益 < 0.001」要么误触发要么永不触发。
  正确做法是每隔几个 epoch 用饱和曲线重新拟合，并说明拟合会变：同一条曲线 5 点拟合渐近线
  0.5063，6 点变 0.5650，10 点才稳定在 0.5535。**点数不够时不要给出言之凿凿的预测。**

## 7. 通知独立且明确启用

训练授权不自动授权邮件。用户要求通知且明确收件人/策略后才启用；复用已有通知授权，无须
反复确认。wrapper 默认关闭通知，显式 `NOTIFY_ENABLED=1` 才运行 watcher；通知失败不改变
训练退出码。

watcher 使用已声明的整体进度：进度文件中的单个百分数，或显式 `AUTODL_PROGRESS=37.5`。
没有可靠进度时只报告进程终态，**不把 batch 100%、accuracy 或某一阶段的完成当成全实验
完成**。`ERROR`/Traceback 是诊断线索，终态来自本 attempt 的有效退出码。

状态文件绑定 project/run，原子写入并对发送与状态提交加互斥锁；发送成功才记已发送。
dry-run 不消耗正式去重状态，且只证明格式，不证明 SMTP 可达。SMTP 服务端可能已收件而
客户端没收到响应，因此重试不能承诺严格的「恰好一次」。

默认邮件不附原始日志；用户明确需要时先检查范围与敏感内容再显式启用，脱敏正则只是辅助。
SSH 密码、SMTP/HF/API token、私钥和私有链接不进入命令行、技能、runbook、启动记录或公开
内容；诊断不输出完整环境或配置中的秘密。

## 8. 报数之前的信任闸

远程实验最贵的失败不是崩溃，是**跑完了、数字很合理、但没有意义**。报任何数字前：

- **先看空对照有没有退化。** shuffled / random 控制如果和真信号给出一样的数（实测到小数点
  后 15 位相同），说明那条通道根本没接上，整张表是装饰品。
- **不要绕过工具崩溃。** 一次 auditor 崩了，去掉 `--full-dictionary` 绕过去——而那个 flag
  正是填充 target 的，结果 schema 全是 −1、所有 variant 塌成同一个分数。工具崩溃是在报告
  「我读不了你的输入」，不是麻烦。
- **一个指标只能有一个权威实现。** 曾经报告打印本地 VOC-AP、gate 读官方 key，同一次 run 的
  两个产物给出相反结论（+9.42 vs −13.42 mAP）。让 CSV、报告、gate 读同一组 key，两套实现
  的差值**显式打印**。
- **跨 run 比较前先核对指纹**：评测器类别数、GT 集合 hash、config sha、split 文件 sha。
  协议变了（例如 4×5 → 2×10）就是**不可比**，要显式声明，不要并排放进一张表。
- 报增益时给出拆解（哪部分来自哪个因子）；没有配平的 A/B 就明说「未拆解」。同时改 freezing
  和 batch 拆分得到的 +38.6 mAP 说不清归谁，配平重测后 freezing 只值 +3.5、batch 值 +4.8。

深入的证据有效性、噪声下限和捷径基线判断，用 `dl-first-principles` skill。

## 9. 验证、回收和结束

结果出现后按授权范围分批回收，优先不可再生的小型指标、配置、日志和 manifest；大
checkpoint/特征/图像的传输由任务与空间预算决定。

在本地执行 `scp -P`（大写 P），先确认精确来源、目标目录、文件清单与容量。运行中的文件
可能仍在写，优先取原子完成的快照。保留远端原件，不擅自清理或关机。

**按内容校验，不要按文件名。** 一个 19 MB 的 `ShipRSImageNet.zip`（完整应为 4.31 GB）带着
正确文件名躺在源目录里，构建脚本按名字匹配到它，导致 build 反复失败。校验大小 + 可读的
中央目录 + 条目数；**上传时先写 `<name>.part`，校验通过再改名**，这样中断的传输不会被误当
成完整文件。

**释放实例前必须先拉回并核对。** 未 commit 的 `.pth` 和结果在租来的机器上是单副本——曾有
一个已部署的 checkpoint，唯一的另一份就在一台随后被释放的机器上。释放前跑一遍
`scripts/find_artifacts.sh` 确认清单已落到本地。

### 绝对不要动验证集

训练侧的问题只在训练集上修。曾为修训练时的 CUDA OOM，把「每图 box 数上限」同时套在 train 和
val 上：val 只少了 3.9% 的图，却少了 **36% 的标注**，同一份权重 mAP 从 0.3693 跳到 0.5770
——**+0.21 全是换了验证集造成的假象**，且与历史基线再也无法比较。规则：改数据修训练问题只
改 train split；万一 val 被动过，最终必须在**原始未过滤 val** 上重测；任何跨 run 的指标对比
先确认两边的 val 是同一个。

「跑完」的任务需核对全部所需 ID、结果格式/数值、指定 evaluator、模型与数据版本、规定指标和
运行约束；**退出 0 或邮件 success 仅代表进程结束**。截止时若仍缺证据，报告未完成项和恢复
入口，不降低目标或虚报完成。

最终简要给出：**run/attempt、检查时间、进程状态、实验验收状态、结果位置、通知状态、剩余
工作**。只启动/只读查询无需制造额外训练、邮件或回收任务。

## 完成判据

- key auth 已实测可用（`ssh -o BatchMode=yes` 通过），全程没有向用户索要过密码。
- 远程命令通过上传的脚本文件执行，不是 PowerShell 内联一行流。
- 预检结果已记录，含 `network_turbo`、`ulimit -n`、两块盘余量、可 import 性。
- 可用依赖组合（python/torch/numpy/框架版本）已写进 `LAUNCH_INFO.md`。
- 长任务在 `screen`/`tmux` 或 wrapper 中（不是裸 `nohup &`）；新 attempt 用新目录。
- config 已冻结进 run 目录；运行期间没有编辑过它会重新读取的文件。
- `run.sh` 里已固定 `OMP_NUM_THREADS` / `MKL_NUM_THREADS` / `PYTORCH_CUDA_ALLOC_CONF`。
- batch size 由 `probe_batch_size.sh` 实测选定，并按最坏 split 与 ladder 比修正。
- monitor 指向**当前** run 的日志，能独立于日志检测进程消失；一个 run 一个 monitor；
  watchdog pattern 绑定本 run 唯一标识。
- 已确认存活指标而不是只看被改的分支；`EXIT=0` 不作为成功依据。
- 空对照确认会退化；跨 run 比较前指纹已核对；增益已拆解或明说未拆解。
- 邮件通知已按用户选择启用/跳过/dry-run 验证，且失败也会触发。
- 验证集未被改动；若曾改动，最终数字已在原始 val 上重测。
- 重要结果已**按内容**校验拉回（实例释放前完成）；可复用问题已追加到 runbook。
- 最终回复包含 run id、远程路径、session、状态、通知策略、结果文件和下一条检查命令。

## 配套文件

- [现场笔记](references/field-notes.md)：连接、依赖陷阱、吞吐、监控事故的具体命令与数字。
- [操作参考](references/autodl-reference.md)：解释器、缓存、wrapper、通知契约和排错表。
- [英文说明](references/SKILL.en.md)：同一工作流的英文摘要。
- [启动记录模板](assets/LAUNCH_INFO.template.md) 与 [runbook 模板](assets/RUNBOOK_ENTRY.template.md)。
- `scripts/probe_batch_size.sh` 实测 batch；`scripts/monitor_run.sh` 只读快照；
  `scripts/append_autodl_note.py` 追加 runbook 条目。
- [离线回归测试](evals)：本地夹具验证 helper，不连接 GPU/SMTP。
