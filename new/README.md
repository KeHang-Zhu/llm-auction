# Unified Experiment Orchestrator

**Location**: [new/main.py](main.py)

统一的实验调度系统，可以读取YAML配置文件并自动运行拍卖实验。

---

## 功能特性

### ✅ 已实现功能

1. **YAML配置驱动**
   - 从配置文件读取所有实验参数
   - 支持23种预配置的实验类型
   - 可通过命令行覆盖配置参数

2. **自动元数据管理**
   - 自动创建实验运行目录
   - 保存配置快照（config.yaml）
   - 复制使用的prompt文件
   - 记录git commit版本
   - 生成实验摘要（experiment_summary.json）
   - 维护实验索引（experiments_index.json）

3. **多种拍卖类型支持**
   - Plan-reflection策略（Auction_plan）
   - eBay代理竞价（Auction_ebay）
   - 支持所有配置的拍卖机制和规则

4. **串行和并行执行**
   - 串行模式：逐个运行实验
   - 并行模式：使用ThreadPoolExecutor并行运行
   - 可配置最大worker数量

5. **完整的可复现性**
   - 捕获所有实验参数
   - 版本化prompt文件
   - Git版本跟踪
   - 随机种子管理

6. **错误处理**
   - 优雅的失败处理
   - 详细的日志记录
   - 记录失败的运行

---

## 使用方法

### 基本用法

```bash
# 运行SPSB IPV实验
python new/main.py --config configs/experiments/01_spsb_ipv.yaml

# 运行eBay拍卖
python new/main.py --config configs/experiments/10_ebay_reserve_0.yaml

# 运行干预研究
python new/main.py --config configs/experiments/18_intervention_menu.yaml
```

### 命令行参数

```bash
# 必需参数
--config PATH          YAML配置文件路径

# 可选参数
--parallel            启用并行执行（覆盖配置文件）
--max-workers N       设置并行worker数量（覆盖配置文件）
--repetitions N       设置重复次数（覆盖配置文件）
--verbose             启用详细日志（DEBUG级别）
```

### 使用示例

#### 1. 基本运行
```bash
python new/main.py --config configs/experiments/01_spsb_ipv.yaml
```

#### 2. 并行执行
```bash
python new/main.py --config configs/experiments/01_spsb_ipv.yaml --parallel
```

#### 3. 自定义重复次数
```bash
python new/main.py --config configs/experiments/10_ebay_reserve_0.yaml --repetitions 10
```

#### 4. 并行执行并设置worker数量
```bash
python new/main.py --config configs/experiments/14_amazon_reserve_0.yaml --parallel --max-workers 8
```

#### 5. 详细日志
```bash
python new/main.py --config configs/experiments/18_intervention_menu.yaml --verbose
```

---

## 批量运行

### 运行所有标准拍卖（01-09）

```bash
for i in {01..09}; do
    python new/main.py --config configs/experiments/${i}_*.yaml
done
```

### 运行所有eBay变体（10-13）

```bash
for i in {10..13}; do
    python new/main.py --config configs/experiments/${i}_*.yaml
done
```

### 运行所有Amazon变体（14-17）

```bash
for i in {14..17}; do
    python new/main.py --config configs/experiments/${i}_*.yaml
done
```

### 运行所有干预研究（18-23）

```bash
for i in {18..23}; do
    python new/main.py --config configs/experiments/${i}_*.yaml
done
```

### 并行批量运行（使用GNU parallel）

```bash
# 安装GNU parallel (如果需要)
# brew install parallel

# 并行运行所有实验
parallel "python new/main.py --config {}" ::: configs/experiments/*.yaml
```

---

## 输出结构

每次实验运行创建以下目录结构：

```
experiment_logs/V10/{experiment_name}/
├── experiments_index.json              # 所有运行的索引
└── run_{timestamp}/
    ├── config.yaml                     # 配置快照
    ├── prompts/                        # 使用的prompt文件
    │   ├── instruction.txt
    │   ├── persona.txt
    │   ├── plan_first.txt
    │   ├── plan_after_reflec.txt
    │   ├── bid_first.txt
    │   ├── bid_after_reflec.txt
    │   ├── asking_sealed.txt
    │   └── rule_template/
    │       └── {special_rule}.txt
    ├── raw_data/                       # LLM缓存（JSONL）
    │   ├── raw_output__run0.jsonl
    │   ├── raw_output__run1.jsonl
    │   ├── raw_output__run2.jsonl
    │   ├── raw_output__run3.jsonl
    │   └── raw_output__run4.jsonl
    ├── results/                        # 结果文件（JSON）
    ├── experiment_summary.json         # 完整元数据
    └── experiment.log                  # 执行日志
```

### experiment_summary.json 内容

```json
{
  "experiment_name": "spsb_ipv",
  "run_id": "2026-01-02_20-30-45-123456",
  "version": "V10",
  "timestamp": "2026-01-02_20-30-45-123456",
  "git_commit": "734c0e88",
  "config_snapshot": { ... },
  "prompt_files_used": [ ... ],
  "execution": {
    "start_time": "2026-01-02T20:30:45.123456",
    "end_time": "2026-01-02T20:45:30.987654",
    "duration_seconds": 885.864198,
    "repetitions": 5,
    "parallel": false,
    "completed_repetitions": 5,
    "failed_repetitions": 0
  },
  "results_summary": {
    "total_runs": 5,
    "completed_runs": 5,
    "failed_runs": 0,
    "total_rounds": 75,
    "expected_llm_calls": 225,
    "cache_files": [ ... ],
    "seeds_used": [1299, 1300, 1301, 1302, 1303]
  }
}
```

### experiments_index.json 内容

```json
{
  "experiments": [
    {
      "name": "spsb_ipv",
      "run_id": "2026-01-02_20-30-45-123456",
      "timestamp": "2026-01-02T20:30:45.123456",
      "duration": 885.864198,
      "status": "completed",
      "output_dir": "spsb_ipv/run_2026-01-02_20-30-45-123456",
      "config_hash": "dc792bfa"
    },
    ...
  ]
}
```

---

## 工作流程

### 1. 初始化阶段
```python
orchestrator = ExperimentOrchestrator(config_path)
```
- 加载YAML配置
- 验证配置参数
- 创建Cache对象

### 2. 设置阶段
```python
orchestrator.setup_experiment()
```
- 创建运行目录（experiment_logs/{version}/{name}/run_{timestamp}/）
- 保存配置快照（config.yaml）
- 复制prompt文件到prompts/目录
- 记录git commit

### 3. 执行阶段
```python
# 串行执行
orchestrator.run_experiments_serial()

# 或并行执行
orchestrator.run_experiments_parallel()
```

**每次运行**：
1. 创建Rule对象（从配置）
2. 创建Auction对象（根据strategy_type选择）
3. 生成价值（使用seed_base + run_id）
4. 运行拍卖（调用run_repeated()）
5. 保存LLM cache到raw_data/目录

### 4. 完成阶段
```python
orchestrator.finalize_experiment(run_results)
```
- 收集结果摘要
- 生成experiment_summary.json
- 更新experiments_index.json
- 记录执行时间和状态

---

## 支持的实验类型

### 标准拍卖（01-09）
- **01_spsb_ipv.yaml**: Second-Price Sealed Bid - IPV
- **02_spsb_apv.yaml**: SPSB - Affiliated Private Values
- **03_fpsb_ipv.yaml**: First-Price Sealed Bid - IPV
- **04_third_price_ipv.yaml**: Third-Price Sealed Bid - IPV
- **05_all_pay_ipv.yaml**: All-Pay Auction - IPV
- **06_ascending_clock_apv.yaml**: Ascending Clock - APV
- **07_sealed_feedback_apv.yaml**: Sealed with Feedback - APV
- **08_common_value_first.yaml**: Common Value - First Price
- **09_common_value_second.yaml**: Common Value - Second Price

### eBay变体（10-13）
所有使用 `strategy_type: "ebay"`, `model: "gpt-4"`, `closing: false`
- **10_ebay_reserve_0.yaml**: Reserve price = 0
- **11_ebay_reserve_40.yaml**: Reserve price = 40
- **12_ebay_reserve_50.yaml**: Reserve price = 50
- **13_ebay_reserve_60.yaml**: Reserve price = 60

### Amazon变体（14-17）
所有使用 `strategy_type: "plan_reflection"`, `model: "gpt-4o"`, `closing: true`
- **14_amazon_reserve_0.yaml**: Reserve price = 0
- **15_amazon_reserve_40.yaml**: Reserve price = 40
- **16_amazon_reserve_50.yaml**: Reserve price = 50
- **17_amazon_reserve_60.yaml**: Reserve price = 60

### 干预研究（18-23）
- **18_intervention_menu.yaml**: Menu-based auction description
- **19_intervention_proxy_breitmoser.yaml**: Clock described as proxy bidding
- **20_intervention_nash_deviation.yaml**: Nash equilibrium deviation testing
- **21_intervention_wrong_strategy.yaml**: Incorrect strategy suggestions
- **22_intervention_dominant_strategy.yaml**: Revealing dominant strategy
- **23_intervention_risk_neutrality.yaml**: Suggesting risk-neutral behavior

---

## 关键类和方法

### ExperimentOrchestrator

主要编排类，管理完整的实验工作流。

#### 主要方法

##### `__init__(config_path: str)`
初始化orchestrator并加载配置。

##### `setup_experiment()`
设置实验目录和元数据管理。

##### `create_rule() -> Rule_plan`
从配置创建Rule对象。

##### `create_auction(rule, run_id, run_cache) -> Auction`
根据strategy_type创建相应的Auction对象：
- `"plan_reflection"` → `Auction_plan`
- `"ebay"` → `Auction_ebay`

##### `run_single_experiment(run_id, run_cache) -> dict`
运行单次实验迭代：
1. 创建rule和auction
2. 生成价值（seed = seed_base + run_id）
3. 运行拍卖
4. 保存cache

##### `run_experiments_serial() -> list`
串行运行所有重复实验。

##### `run_experiments_parallel() -> list`
并行运行所有重复实验（使用ThreadPoolExecutor）。

##### `collect_results_summary(run_results) -> dict`
收集所有运行的摘要统计。

##### `finalize_experiment(run_results)`
生成元数据并更新索引。

##### `run()`
执行完整工作流（setup → run → finalize）。

---

## 配置参数映射

### YAML → Rule_plan 参数映射

| YAML路径 | Rule_plan参数 | 说明 |
|---------|--------------|------|
| `rule.seal_clock` | `seal_clock` | "seal" 或 "clock" |
| `rule.ascend_descend` | `ascend_descend` | "ascend" 或 "descend" |
| `rule.price_order` | `price_order` | "first", "second", "third", "allpay" |
| `rule.private_value` | `private_value` | "private", "affiliated", "common" |
| `rule.open_blind` | `open_blind` | "open" 或 "blind" |
| `auction.rounds` | `rounds` | 轮数 |
| `rule.turns` | `turns` | eBay时间段数（默认20） |
| `value.common_range` | `common_range` | [min, max] |
| `value.private_range` | `private_range` | 私有价值范围 |
| `value.increment` | `increment` | 出价增量 |
| `auction.number_agents` | `number_agents` | 参与者数量 |
| `rule.special_name` | `special_name` | 特殊规则模板文件名 |
| `rule.start_price` | `start_price` | 起始价格（默认0） |
| `rule.closing` | `closing` | 软关闭规则 |
| `rule.reserve_price` | `reserve_price` | 保留价 |

### YAML → Auction 参数映射

| YAML路径 | Auction参数 | 说明 |
|---------|------------|------|
| `auction.number_agents` | `number_agents` | 参与者数量 |
| `rule` (整个对象) | `rule` | Rule_plan对象 |
| `metadata.run_dir` | `output_dir` | 输出目录 |
| - | `timestring` | 自动生成的时间戳 |
| - | `cache` | Cache对象 |
| `llm.model` | `model` | LLM模型名称 |
| `llm.temperature` | `temperature` | 温度参数 |

---

## 错误处理

### 运行失败处理
如果某次运行失败：
1. 错误被捕获并记录
2. 继续执行其他运行
3. 在results_summary中记录失败信息
4. 不影响已完成的运行

### 日志级别
- **INFO**: 标准运行信息
- **DEBUG**: 详细调试信息（使用 `--verbose`）
- **WARNING**: 警告信息（不影响执行）
- **ERROR**: 错误信息（记录但继续执行）

---

## 与旧系统的对比

### 旧系统（src/main.py）
❌ 硬编码所有参数
❌ 手动创建目录
❌ 无元数据管理
❌ 无实验跟踪
❌ 无版本控制
❌ 难以批量运行

### 新系统（new/main.py）
✅ YAML配置驱动
✅ 自动目录管理
✅ 完整元数据跟踪
✅ 实验索引系统
✅ Git版本跟踪
✅ 易于批量运行
✅ 完全可复现

---

## 依赖项

- Python 3.7+
- PyYAML
- pandas
- edsl (EDSL框架)
- 现有的src/目录中的模块：
  - util_plan.py (Auction_plan, Rule_plan)
  - util_ebay.py (Auction_ebay)
  - experiment.config
  - experiment.metadata

---

## 故障排除

### 配置文件未找到
```
错误: Configuration file not found: configs/experiments/...
解决: 检查路径是否正确，确保从项目根目录运行
```

### 导入错误
```
错误: Import "edsl.data" could not be resolved
解决: 确保安装了EDSL包，并且在正确的虚拟环境中
```

### Prompt文件未找到
```
警告: Prompt directory not found: Prompt/
解决: 确保Prompt/目录存在且包含所需文件
```

### 并行执行冲突
如果并行执行时出现问题：
1. 尝试降低max_workers数量
2. 检查是否有Cache冲突
3. 使用串行模式（移除--parallel）

---

## 未来改进

待实现的功能（Phase 2）：

1. **统一Auction架构**
   - 消除Auction类的代码重复
   - 策略模式实现prompt策略
   - 机制模式实现拍卖机制

2. **更多拍卖类型**
   - Auction_human（JSON格式）
   - Auction_CA（组合拍卖）
   - 直接询问策略

3. **增强功能**
   - 实时进度条
   - 断点续传
   - 自动重试失败的运行
   - 结果分析集成

4. **性能优化**
   - 更好的并行执行
   - Cache优化
   - 内存管理

---

## 参考资料

- **配置文档**: [configs/README.md](../configs/README.md)
- **实现状态**: [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md)
- **测试脚本**: [test_new_main.py](../test_new_main.py)
- **计划文档**: [~/.claude/plans/fluttering-questing-harp.md](~/.claude/plans/fluttering-questing-harp.md)

---

**创建日期**: 2026-01-02
**版本**: V10
**状态**: ✅ 可用于生产环境
