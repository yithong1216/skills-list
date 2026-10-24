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
**核对状态 → 连接与预检 → 冻结输入 → 测吞吐 → 启动一次 → 事件驱动监控 → 验证并回收。**

三件事必须分开：**SSH 命令返回 ≠ 进程还活着 ≠ 实验目标达成。**

规则背后的事故细节与数字在 [现场笔记](references/field-notes.md)；本文件只保留规则。

## 1. 恢复任务契约

先读用户当前要求、已有入口、最新结果和项目 runbook。复用已授权的操作；只询问确实缺失
且会改变下一步的信息，不重复索取已知 host、路径或许可。

| 用户要求 | 本轮完成条件 |
| --- | --- |
| 只启动 | 精确任务已后台启动，并通过首个有意义的运行检查 |
| 只读状态/排错 | 报告有时间戳的已知状态和未确定项；不借机重启/改环境 |
| 给现有任务加通知 | 单独监听原任务；不包裹后重新运行训练 |
| 跑完实验/评估 | 所需阶段、结果验证和授权的回收全部完成 |
| 拉回指定结果 | 文件范围、传输完整性及本地解析检查通过 |

优先更新项目已有 runbook（`docs/AUTODL_EXPERIMENT_RUNBOOK.md`、`task.md` 或同类文档），记录：
目标/验收；主机别名/工作目录；run ID 与 attempt；session 名；实际 Python；代码/config/
checkpoint/data 标识；当前阶段与最近验证时间；日志/结果/退出码路径；截止时间与时区；
下一步；待回收文件。不建立互相矛盾的状态表。

旧记忆用于定位证据，不用于断言实例在线、PID 存活或端口有效。不同实例、checkout、协议和
attempt 的指标不可拼接。agent 中途死掉是常态：远端脚本边跑边把结果写进 CSV/JSON。

## 2. 连接：每台新实例一次性做完

实例按次租用，host/port 每次都变。用户给出新 `ssh -p <port> root@<host>` 时：

1. **先改别名，再做别的。** 在 `~/.ssh/config` 里原地更新（或新建）该项目的 `Host` 块：
   `HostName`、`Port`、`User root`、`IdentityFile`、`IdentitiesOnly yes`、
   `StrictHostKeyChecking accept-new`、`ServerAliveInterval 30`。此后**所有命令用
   `ssh <alias>`**，不再手写完整的 `-i … -p … root@…`。
2. **验证 key auth**：
   `ssh -o BatchMode=yes -o ConnectTimeout=8 <alias> "hostname; nvidia-smi -L; df -h /root/autodl-tmp"`。
   通了就**不向用户要密码**。不通先判断是别名过期还是 key 没装（Windows 装 key 见现场笔记）。
3. 用户在消息里贴了明文密码：提醒事后轮换；密码不进命令行、脚本、日志、runbook 或任何外发内容。
4. **换实例/快照恢复后先确认机器状态**：系统盘可能保留环境而数据盘为空；快照恢复先刷目录树、
   大文件最后到。`df`/文件计数隔几分钟看两次，**停止增长前不下结论**。
5. **一条命令重建环境。** 项目应在本地维护 `bootstrap.sh`（装依赖、建目录、校验 manifest
   sha256、上传 `status.sh`）。新实例 = 上传 + 运行它；缺失就在第一次搭环境时写出来，
   而不是每次手工重做。记录从拿到 host 到首个任务启动的耗时。
6. **声明 source of truth**：默认本地为权威。修复落到本地源再同步；在远端副本上继续开发前先比 sha。

命令发送方式：
- **Git Bash 里**可直接 `ssh <alias> 'cmd'` 或 `ssh <alias> bash -s` 加单引号 heredoc（不展开 `$`）。
  超过约 10 行或会复用的逻辑，写成本地 LF 脚本上传到 `<PROJECT_ROOT>/scripts/` 再执行。
- **PowerShell 里不要发内联 bash**（它吃掉 `$` 和反斜杠）；改用 Bash 工具或上传脚本。
- 本地 spawn/审批失败不是远端任务退出，先修失败的那一层。

## 3. 低开销操作循环（效率核心）

远程工作的主要成本是**往返次数和每次读进上下文的字节**，不是 GPU。

- **一个 `status.sh` 代替所有临时查询。** 每台实例上传一次
  [`assets/status.sh.template`](assets/status.sh.template) 改成的项目版：一次输出每个 run 的
  存活/退出码/最后一行日志、GPU 5 秒均值、cgroup CPU 用量、两块盘余量，并打印 `ALERT …`/`EVENT …`
  行。查状态 = `ssh <alias> bash <PROJECT_ROOT>/status.sh`。新实验只往里面加几行项目检查
  （队列长度、VALID 标记、worker 数），不再手拼 `tail; screen -ls; nvidia-smi` 一行流，
  也不去读还不存在的日志路径。
- **等待用后台 watcher，不用前台 sleep。** 启动后在同一轮用 `run_in_background` 运行
  `bash <skill>/scripts/watch_events.sh <alias> "bash <PROJECT_ROOT>/status.sh" 120 3600`。
  它在**新的** ALERT/EVENT、ssh 连续失败或心跳到期时退出，退出会唤醒 agent；处理完再重新挂上。
  不写 `sleep 60; ssh …` 的前台轮询，不让单条 ssh 撞 2 分钟超时；超过 1 分钟的远端操作一律进 `screen`。
- **主动汇报**：每个 EVENT（某实验跑完、某阶段结束）立刻向用户报结果，不等全部跑完；ALERT
  先处理再报。说「我会继续盯着」时，后台 watcher 必须已经在跑——否则就是没在监控。
- **空转也是故障。** status.sh 在有活跃 run 而 GPU 均值低于阈值时报 ALERT；CPU 型任务同理
  （持续低于配额一半）。收到后先确认是不是 val/IO 阶段，再决定加并行、加 worker 还是改 batch；
  单个实验已无法更快而资源仍空，主动向用户提议可并行的候选实验。
- **并行前先列资源表。** 同机多任务时，先为每个任务列出 CPU 核、GPU 显存/利用率、RAM、
  磁盘 I/O 需求，再决定并行或排队，并告诉用户谁排在谁后面。
- **线程上限按容器配额算**：读 `/sys/fs/cgroup/cpu.max`，不要信 `nproc`（显示宿主核数）。
  每个 CPU 侧任务设 `OMP_NUM_THREADS=MKL_NUM_THREADS=⌊配额/并发任务数⌋`（上限 8），
  Python 里同时 `torch.set_num_threads`。
- **多会话共用一台机器**：screen 名带任务前缀；队列、脚本和输出目录明确归属一个会话，移交用
  SendMessage 写明「X 从现在归你」。不动别的会话的任务，除非它正在拖垮共享资源，并随即告知对方。
- 交给 subagent/fork 的远程活，brief 里必须给别名、`status.sh` 路径、它独占的文件和 screen 名。

## 4. 预检覆盖真正的入口

新启动、换实例或依赖修复后做针对性预检；健康运行期间不反复扫描全环境。
`scripts/preflight_autodl.sh` 查基础环境，**不能替代**项目入口检查。

1. **代码/配置一致**：确认远端版本与 dirty 文件；无 Git 时用文件清单 + SHA-256。
   **正在被读取的 config、脚本、checkpoint 不原地修改**；变更用新快照/新 attempt。
2. **准确解释器**：记录绝对 Python 路径、关键包版本、CUDA 可用性和一次真实 CUDA 操作。
   禁止激活失败后静默用 base。
3. **真实数据路径**：核对数据、权重、标签映射、空间和写权限；不用名字相近的数据替代。
4. **同一加载路径的 smoke**：用正式入口、参数、解释器和缓存跑最小有意义的子集；单元测试不能替代实际 CLI。
5. **资源与耗时**：用真实计算测峰值显存和吞吐（§5），注明 MiB/GiB。

每次单独确认：`source /etc/network_turbo`（先确认主机提供；写进 `run.sh`）；`ulimit -n 65536`
加 `file_system` sharing strategy；系统盘与数据盘分别的余量；仓库可 import（必要时 `PYTHONPATH`）。

**装包比训练更容易毁掉一天**：unpinned `pip install` 会把 numpy 升到 2.x、替换厂商 torch；
半坏的包比缺失的包更危险；gated HF 仓库在租来的机器上 401，**不把 HF token 复制到租来的实例**。
可用组合（python/torch/numpy/框架版本）写进 `LAUNCH_INFO.md` 与 `bootstrap.sh`。

准备、训练、验证和回收共用同一个截止时间；先测下载/首轮速度，并为验证和回收预留预算。

## 5. 吞吐与显存：先测再改

`run.sh` 里必设（`screen` 内进程不继承交互 shell）：

```bash
export OMP_NUM_THREADS=<按 §3 计算，≤8>
export MKL_NUM_THREADS=$OMP_NUM_THREADS
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

- batch size 用 `scripts/probe_batch_size.sh` 实测：在**最坏 split** 上探（step-down ladder）；
  多尺度训练按 ladder 的 max/base 比放大峰值；探测长度超过框架的时间平均窗口。
- 显存不是目标，利用率才是。读利用率先确认 train/val 阶段，采样间隔 1–2 秒。
- 先量后改：测得的瓶颈与假设冲突时，停下重新诊断，不按原假设动手。

## 6. 启动一次，保留恢复证据

- 用 `screen`/`tmux` 或项目作业管理器（镜像通常只有 `screen`；**`nohup cmd &` 经 SSH 会随会话死**）：
  `ssh <alias> "screen -dmS <run_id> bash <RUN_ROOT>/run.sh"`。脚本自己设置工作目录、解释器、缓存与网络环境。
- 先查相同 run/attempt 是否已启动；新 attempt 用新目录。已有 `.run_claim`/日志/退出码说明目录已用过，
  **不删 claim 绕过检查**。已有入口用 `scripts/wrap_existing_run.sh` 包裹，新入口用 `assets/run.sh.template`。
- 启动返回 0 后，**确认三件事再说「已启动」**：进程在、GPU 被占、第一个 step/route 行出现。随即挂 §3 的 watcher。
- 换了架构/骨干先跑短 lr sanity；不为了「对齐 baseline」沿用不匹配的 lr。
- 首轮出现导入错误、NaN、OOM、写入错误：保留 traceback 与输入版本，修已证实的原因后最小复测。
- 自动衔接下一阶段必须读完整结果和指定 gate；`COMPLETE` 字符串、GPU 归零或退出 0 不能替代科学验收。
- **SSH 启动命令超时可能发生在远端执行之后**：先核对同一 attempt 的进程/产物，再决定是否重试。

## 7. 分开判断连接、进程和结果

| 观测 | 结论与下一步 |
| --- | --- |
| 本地审批/沙箱失败，尚未建立 SSH | 观测未执行，不是训练失败 |
| SSH 断开或读取超时 | 连接状态 UNKNOWN；核对原 run，不直接重启 |
| 匹配启动身份的进程存活 | 运行中；结合日志/计数变化判断是否推进 |
| 空日志、长时间无 checkpoint | 可能缓冲或长阶段；不判完成或挂死 |
| session 不见且无退出码 | 中断或 UNKNOWN；查进程身份、宿主重启、检查点 |
| 退出码非 0 | 进程失败，保全证据后诊断 |
| 退出 0、所需结果不完整 | 进程结束，实验未完成 |

Monitor 纪律：
1. 改 run 目录时同一条命令里同步更新 status.sh/解析脚本的路径。
2. 能独立于日志判断进程消失（session/pgrep）；OOM kill 后日志静止与「安静训练」无法区分。
3. 一个 run 一个 watcher，run 结束就撤；残留 watcher 制造矛盾进度。
4. 失败也要触发：覆盖 `OutOfMemory|Traceback|Killed|EXIT=`。
5. `EXIT=0` 不等于成功：终止条件看存活指标（total loss、主指标非 0），不看正在改的那个分支。
6. watchdog/kill 的 pattern 绑定本 run 唯一标识（`--work-dir`、run root）；拿不到就拒绝启动。绝不全局 `pkill python`。
7. 框架说「已停止」不代表真停了：重启前 `pgrep -af <pattern>` 核实。
8. 共享实例上「GPU 忙」不证明本任务存活，核对 session/PID。

重复故障先定位层次：本地工具 → SSH → shell/环境 → 同步/缓存 → 任务入口 → 训练数值 → 结果验证。
一次修复后症状相同，检查上一个假设，不盲目重跑；不删部分下载、缓存或 checkpoint「从头试试」。

估时只用已完成的 epoch/批次边界；停止准则看拟合趋势不看逐 epoch 差分，点数不够时不给确定预测。

## 8. 通知独立且明确启用

训练授权不自动授权邮件。用户要求且明确收件人后才启用（`NOTIFY_ENABLED=1`）；通知失败不改变训练
退出码。watcher 只用声明的整体进度，没有可靠进度时只报终态。默认不附原始日志。SSH 密码、
SMTP/HF/API token、私钥不进入命令行、技能、runbook 或外发内容。细节见 [操作参考](references/autodl-reference.md)。

## 9. 报数前的信任闸

远程实验最贵的失败是**跑完了、数字很合理、但没有意义**。报数前：空对照必须退化；不绕过工具崩溃
（去掉报错 flag 会改变被测对象）；一个指标只有一个权威实现，CSV/报告/gate 读同一组 key；跨 run
比较先核对评测器、GT hash、config sha、split sha，协议变了就声明不可比；增益给出拆解或明说未拆解。
深入的有效性判断用 `dl-first-principles` skill。

## 10. 验证、回收和结束

- 按授权分批回收，优先不可再生的小型指标、配置、日志、manifest。`scp -P`（大写），先确认来源、
  目标与容量；优先取原子完成的快照；保留远端原件，不擅自清理或关机。
- **按内容校验，不按文件名**：大小 + 可读的中央目录/条目数；上传先写 `<name>.part`，校验后改名。
- **释放实例前必须拉回并核对**：用户给了关机时间，就倒排出回收时刻并提前完成；释放前跑
  `scripts/find_artifacts.sh`。
- **绝不动验证集**：修训练问题只改 train split；val 被动过就在原始 val 上重测。
- 「跑完」需核对全部 ID、结果格式、指定 evaluator、模型/数据版本与约束；截止时缺证据就报未完成项和恢复入口。

最终简要给出：**run/attempt、检查时间、进程状态、实验验收状态、结果位置、通知状态、剩余工作**。

## 完成判据

- 别名已更新并用 `ssh -o BatchMode=yes` 实测；全程没有索要密码。
- 实例上有项目 `status.sh`；状态查询走它，等待走后台 `watch_events.sh`，没有前台 sleep 轮询。
- 每个 EVENT 已主动汇报；GPU/CPU 空转 ALERT 有处理记录。
- 预检含 `network_turbo`、`ulimit -n`、两块盘余量、可 import 性；依赖组合写进 `LAUNCH_INFO.md`/`bootstrap.sh`。
- 长任务在 `screen`/`tmux`/wrapper 中；新 attempt 新目录；运行期间未编辑它会重读的文件。
- 线程数按 cgroup 配额与并发数设定；batch 实测选定。
- watcher 指向当前 run，能检测进程消失，pattern 绑定本 run；`EXIT=0` 不作成功依据。
- 空对照会退化；跨 run 指纹已核对；验证集未改动。
- 结果已按内容校验拉回（释放前完成）；runbook 已更新。

## 配套文件

- [现场笔记](references/field-notes.md)：每条规则背后的事故、命令与数字。
- [操作参考](references/autodl-reference.md)：解释器、缓存、wrapper、通知契约和排错表。
- [英文说明](references/SKILL.en.md)。
- `assets/status.sh.template` 远端一次性状态；`scripts/watch_events.sh` 本地后台事件 watcher。
- [启动记录模板](assets/LAUNCH_INFO.template.md)、[runbook 模板](assets/RUNBOOK_ENTRY.template.md)、
  `assets/run.sh.template`。
- `scripts/probe_batch_size.sh` 实测 batch；`scripts/monitor_run.sh` 单 run 只读快照；
  `scripts/preflight_autodl.sh`；`scripts/find_artifacts.sh`；`scripts/append_autodl_note.py`。
- [离线回归测试](evals)：本地夹具验证 helper，不连接 GPU/SMTP。
