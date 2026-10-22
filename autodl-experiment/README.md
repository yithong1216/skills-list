# AutoDL Experiment Runner

用于启动、恢复和完成 AutoDL / SeetaCloud SSH GPU 实验的 Codex skill。
[English README](README.en.md) · [完整工作流](SKILL.md) · [操作参考](references/autodl-reference.md)

## 使用

```text
用 $autodl-experiment 完成这个远程评估并拉回结果。
先恢复已有 run 的状态，复用已确认的解释器、模型缓存和连接配置。
核对全部样本与官方指标，为服务器到期前的验证和回收留时间。
```

只启动、只读状态、给原任务加通知、跑完整实验，各自有明确完成条件。
已有任务优先核对状态；SSH 超时不直接触发重启。代码、配置和数据标识随
run/attempt 冻结，避免分析期间改配置或使用旧远端代码。

## 辅助脚本

- `preflight_autodl.sh`：解释器、CUDA 和一次真实 CUDA 操作；还需执行项目 CLI smoke。
- `wrap_existing_run.sh`：保留原入口，拒绝复用运行目录，写入身份、日志和原子退出码。
- `monitor_run.sh`：一次只读快照，区分运行、进程退出和 UNKNOWN；不证明实验验收通过。
- `watch_progress_notify.py`：显式整体进度及退出码通知，绑定 run 的原子去重状态。
- `find_artifacts.sh` / `append_autodl_note.py`：定位候选结果、记录复盘；范围和内容仍需核对。

缓存沿用已验证路径，不自动切换到新空目录。中断时若无法确认整个任务结束，
保留 UNKNOWN 与恢复证据；不根据一个消失的 shell 宣告实验失败或完成。

## 邮件

邮件默认关闭，需已有收件人与事件授权并设置 `NOTIFY_ENABLED=1`。
训练授权本身不启用邮件。进度来自单值进度文件或 `AUTODL_PROGRESS=37.5`，
不再解析任意百分比、accuracy 或 batch 进度。退出码表示进程终态。

原始日志默认不附邮件；脱敏正则不能保证任意日志安全。凭据仅通过安全运行环境
或未提交的私密配置提供，不进入技能、命令行、聊天或 runbook。配置文件存在
不等于通知已获授权。`--dry-run` 不发送邮件，也不消耗正式通知状态。

旧版无 run 归属的通知状态不能直接复用；保留原件并按操作参考选用新状态文件。
通知尽力去重，无法保证 SMTP 超时后的严格恰好一次。

## 离线检查

```powershell
python -m unittest discover -s evals -p "test_*.py" -v
```

需要 Python 3 和 Bash；Windows 可设置 `BASH_BIN` 为 Git Bash。
测试使用临时本地夹具，不连接 GPU 服务器或 SMTP。Linux 进程身份、真实 GPU、
tmux/screen 和邮件服务仍需部署环境验证。

## 安装与许可

此目录是本机修订包；安装时复制经审核的完整目录到个人 skills 目录，并保留旧版
备份。上游项目为 [autodl-experiment-skill](https://github.com/handsomeZR-netizen/autodl-experiment-skill)，
上游版本不一定含本机修订。

MIT；见 [LICENSE](LICENSE)。
