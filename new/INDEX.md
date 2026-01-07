# New Experiment System - File Index

## 📋 概览

这个目录包含了改进后的实验系统，主要包括：
1. **单个实验编排器** ([main.py](main.py)) - 运行单个 YAML 配置的实验
2. **批量任务控制器** ([task_controller.py](task_controller.py)) - 批量运行多个实验

## 📁 文件列表

### 核心实现

| 文件 | 说明 | 行数 |
|------|------|------|
| [main.py](main.py) | 单个实验编排器 (ExperimentOrchestrator) | ~520 行 |
| [task_controller.py](task_controller.py) | 批量任务控制器 (TaskController) | ~650 行 |

### 文档

| 文件 | 说明 | 语言 |
|------|------|------|
| [QUICKSTART_task_controller.md](QUICKSTART_task_controller.md) | Task Controller 快速开始指南 | 中文 |
| [README_task_controller.md](README_task_controller.md) | Task Controller 完整文档 | 英文 |
| [SUMMARY.md](SUMMARY.md) | 实现总结 | 中文 |
| [INDEX.md](INDEX.md) | 本文件 - 文件索引 | 中文 |

### 示例和测试

| 文件 | 说明 |
|------|------|
| [example_experiments.txt](example_experiments.txt) | 示例实验配置列表 |
| [demo_task_controller.sh](demo_task_controller.sh) | 演示脚本 |
| [test_task_controller.py](test_task_controller.py) | 测试脚本 |

## 🚀 快速开始

### 运行单个实验

```bash
# 使用 main.py
python3 new/main.py --config configs/experiments/01_01_spsb_ipv.yaml
```

### 批量运行多个实验

```bash
# 使用 task_controller.py
python3 new/task_controller.py \
  --configs "configs/robustness/01_01_*.yaml" \
  --max-workers 4
```

## 📖 文档阅读顺序

1. **新用户**：
   - 先看 [QUICKSTART_task_controller.md](QUICKSTART_task_controller.md)
   - 快速了解如何使用 Task Controller

2. **需要详细信息**：
   - 看 [README_task_controller.md](README_task_controller.md)
   - 包含所有参数说明和故障排查

3. **开发者**：
   - 看 [SUMMARY.md](SUMMARY.md)
   - 了解实现细节和技术架构

## 💡 主要功能

### Task Controller 核心功能

✅ **批量执行**
- 从 YAML 配置列表运行多个实验
- 支持通配符和文件列表

✅ **并行处理**
- 可配置并发数 (`--max-workers`)
- 每个 worker 独立执行

✅ **智能检测**
- 自动检查已完成的实验
- 避免重复运行

✅ **状态跟踪**
- 实时跟踪成功/失败状态
- 详细的执行报告

✅ **灵活配置**
- 全局覆盖 repetitions
- 强制重新运行选项

## 🎯 常见使用场景

### 场景 1: 运行所有 robustness 实验

```bash
python3 new/task_controller.py \
  --configs "configs/robustness/*.yaml" \
  --max-workers 4
```

### 场景 2: 测试不同模型

```bash
python3 new/task_controller.py \
  --configs configs/robustness/01_01_spsb_ipv_gpt5mini.yaml \
            configs/robustness/01_01_spsb_ipv_llama.yaml \
            configs/robustness/01_01_spsb_ipv_claude_sonnet.yaml \
  --max-workers 3
```

### 场景 3: 快速测试（减少 repetitions）

```bash
python3 new/task_controller.py \
  --configs "configs/experiments/01_*.yaml" \
  --repetitions 1 \
  --max-workers 8
```

## 📊 输出和报告

### 实验输出结构

```
experiment_logs/V10/{experiment_name}/
└── run_{timestamp}/
    ├── config.yaml              # 配置快照
    ├── experiment_summary.json  # 执行摘要 (包含完成状态)
    ├── raw_data/                # 原始 LLM 输出
    ├── results/                 # CSV 结果
    └── prompts/                 # 使用的 prompts
```

### 批量报告

```json
{
  "total_tasks": 10,
  "successful_tasks": 8,
  "failed_tasks": 2,
  "skipped_tasks": 0,
  "total_duration_seconds": 3245.67,
  "task_results": [
    {
      "experiment_name": "spsb_ipv_gpt5mini",
      "status": "success",
      "completed_repetitions": 5,
      "total_repetitions": 5,
      "duration_seconds": 324.56,
      "run_dir": "..."
    }
  ]
}
```

## 🔍 检查实验完成状态

### 方法 1: 从 batch_report.json

```bash
# 查看成功的实验
cat batch_report.json | jq '.task_results[] | select(.status=="success") | .experiment_name'

# 查看完成的 repetitions
cat batch_report.json | jq '.task_results[] | {name: .experiment_name, completed: .completed_repetitions, total: .total_repetitions}'
```

### 方法 2: 从 experiment_logs 目录

```bash
# 查看所有实验
ls -la experiment_logs/V10/

# 查看特定实验的摘要
cat experiment_logs/V10/spsb_ipv_gpt5mini/run_*/experiment_summary.json | jq '.results_summary'
```

### 方法 3: 使用 Task Controller 自动检测

```bash
# Task Controller 会自动检测并跳过已完成的实验
python3 new/task_controller.py --configs "configs/robustness/*.yaml" --max-workers 4

# 强制重新运行
python3 new/task_controller.py --configs "configs/robustness/*.yaml" --force-rerun
```

## ⚙️ 配置选项

### Task Controller 主要参数

```bash
# 必需参数（二选一）
--configs [PATHS...]           # YAML 配置文件路径（支持通配符）
--config-list FILE             # 包含配置路径的文本文件

# 执行选项
--max-workers N                # 最大并行工作线程数（默认: 4）
--repetitions N                # 覆盖所有实验的 repetitions
--force-rerun                  # 强制重新运行已完成的实验
--no-check-existing            # 不检查现有实验

# 输出选项
--report-output FILE           # 批量报告保存路径（默认: batch_report.json）
--verbose                      # 启用详细日志
```

## 🎓 学习路径

### 初学者
1. 阅读 [QUICKSTART_task_controller.md](QUICKSTART_task_controller.md)
2. 运行示例命令
3. 查看生成的报告

### 进阶用户
1. 阅读 [README_task_controller.md](README_task_controller.md)
2. 了解所有参数和选项
3. 自定义批量执行流程

### 开发者
1. 阅读 [SUMMARY.md](SUMMARY.md)
2. 查看源代码实现
3. 扩展或修改功能

## 🔗 相关文件

### 在 src/ 目录

- `src/util_plan.py` - 拍卖实现（已添加 robust parsing）
- `src/experiment/config.py` - 配置系统
- `src/experiment/metadata.py` - 元数据管理
- `src/export_results.py` - 结果导出

### 在 configs/ 目录

- `configs/experiments/` - 主实验配置
- `configs/robustness/` - Robustness 检查配置

## 📝 最近的改进

1. **Bid Parsing 鲁棒性增强** (util_plan.py)
   - 现在可以正确处理 `<ACTION> [45] </ACTION>` 格式
   - 支持多种格式变体

2. **Task Controller 实现**
   - 完整的批量执行系统
   - 智能完成检测
   - 详细的报告生成

## 🤝 使用建议

1. **从小规模开始**：先用 1-2 个实验测试
2. **监控资源**：根据机器调整 `max_workers`
3. **保存报告**：为不同批次使用不同的报告文件名
4. **利用跳过功能**：中断后重新运行会自动跳过已完成的

## 📞 获取帮助

```bash
# 查看帮助
python3 new/task_controller.py --help

# 运行演示
bash new/demo_task_controller.sh

# 查看文档
cat new/QUICKSTART_task_controller.md
```

---

**最后更新**: 2026-01-04
**版本**: V10
