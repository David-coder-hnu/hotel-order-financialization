# 酒店订单金融化可行性分析

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

基于ABS/RWA金融模型的酒店订单金融化可行性研究项目。

## 项目概述

本项目旨在分析酒店订单金融化的可行性，通过将未来住宿权益打包成可交易的金融产品（时权ABS），帮助酒店提前回笼资金、优化现金流、提升资产流动性。

### 核心功能

### V6-Fusion 时权ABS融合引擎（推荐）
**融合V5创新灵魂 + V6专业框架**

- **时权(Time-Right)发行模型**：超远期住宿权益 token化
  - 发行数量 = 房间数 x 365天 x 超发倍数（基于入住率+安全系数）
  - 发行价格 = 底价 x 远期折扣 x (1 - 发行折扣)
  - 超发机制保留V5核心创新
- **资产池构建引擎**：从16,000+酒店中多维度分层抽样构建80家酒店时权组合
- **信用评级模型**：Merton Distance-to-Default + GARCH波动率 → PD/LGD
- **分层结构设计**：Senior/Mezzanine/Junior/Equity四档，基于时权收益分配
- **二级市场交易模型**：时权价格随时间收敛到即期价格 + 供需溢价
- **三元兑付选择**：现金兑付 / 实物兑付(7折入住) / 二级市场转让
- **现金流瀑布引擎**：交易手续费优先 → 兑付回收优先 → 剩余分配
- **蒙特卡洛模拟**：5,000-10,000条Gaussian Copula违约路径 + 用户行为随机化
- **RWA代币化架构**：ERC-3643时权代币 + 智能合约自动兑付(cash/physical/rollover)
- **专业报告生成**：对标投行/评级机构的分析文档

### V6 纯ABS框架（保留）
- 传统贷款池ABS模型，用于对比分析

### V5 基础模拟（保留）
- **数据预处理**：清洗和标准化酒店价格数据
- **金融建模**：基于收益法的时权ABS定价模型
- **可行性分析**：NPV、IRR、ROI等财务指标计算
- **风险评估**：流动性、信用、市场风险量化分析
- **可视化展示**：多维度图表展示分析结果

## 项目结构

```
酒店研究/
├── data/                           # 数据文件
│   ├── cleaned_hotel_prices.csv   # 清洗后的酒店价格数据 (170万条)
│   ├── hotel_future_prices.csv    # 酒店远期价格（底价）
│   ├── hotel_info.csv             # 酒店基本信息 (86,159家)
│   ├── 2024_3.csv ~ 2024_6.csv    # 原始月度数据
│   └── 一种对酒店订单金融化的方法(1).docx  # 方法论文档
│
├── src/                           # 源代码
│   ├── hotel_abs_engine_fusion.py # [V6-Fusion] 时权ABS融合引擎（推荐）
│   ├── hotel_abs_engine.py        # [V6] 纯ABS框架引擎
│   ├── credit_model.py            # [V6] 酒店信用评级与违约模型
│   ├── asset_pool.py              # [V6] 资产池构建引擎 + 时权参数
│   ├── tranche_structure.py       # [V6] 分层结构设计与信用增级
│   ├── waterfall_engine.py        # [V6] 现金流瀑布引擎
│   ├── monte_carlo_simulator.py   # [V6] 蒙特卡洛模拟器
│   ├── report_generator_v6.py     # [V6] 专业报告生成器
│   ├── hotel_simulation_v5.py     # [V5] 基础模拟程序（保留）
│   ├── generate_simple_pdf.py     # [V5] 报告生成器（保留）
│   └── clean_and_generate_prices.py # 数据清洗工具
│
├── output/                        # 输出文件
│   ├── abs_report_v6_fusion.json  # [V6-Fusion] 时权ABS融合报告
│   ├── abs_report_v6.json         # [V6] 纯ABS结构化数据
│   ├── abs_visualization_v6.png   # [V6] 专业可视化图表 (12子图)
│   ├── 酒店订单ABS专业分析报告_v6.html  # [V6] 投行级HTML报告
│   ├── simulation_report_v5.json  # [V5] 详细数据报告
│   ├── simulation_visualization_v5.png  # [V5] 可视化图表
│   └── 酒店订单金融化可行性分析报告.html  # [V5] HTML格式报告
│
├── .trae/specs/                   # 规格文档
│   ├── hotel-simulation-v4/       # V4版本规格
│   ├── hotel-simulation-v5/       # V5版本规格
│   └── hotel-simulation-v6/       # V6版本规格
│
├── README.md                      # 项目说明
├── LICENSE                        # 许可证
├── .gitignore                     # Git忽略文件
├── PUSH_COMMANDS.bat              # Windows推送脚本
└── PUSH_TO_GITHUB.md              # GitHub推送说明
```

## 安装依赖

```bash
pip install pandas numpy matplotlib scipy seaborn
```

## 使用方法

### V6-Fusion 时权ABS融合分析（强烈推荐）

```bash
python src/hotel_abs_engine_fusion.py
```

这将生成：
- `output/abs_report_v6_fusion.json` - 时权ABS融合结构化数据
- 包含：时权发行参数、二级市场模型、三元兑付、分层损失分析

### V6 纯ABS/RWA分析

```bash
python src/hotel_abs_engine.py
```

生成：
- `output/abs_report_v6.json` - 完整ABS结构化数据报告
- `output/abs_visualization_v6.png` - 12子图专业可视化

然后生成HTML报告：

```bash
python src/report_generator_v6.py
```

生成 `output/酒店订单ABS专业分析报告_v6.html`

### V5 基础模拟（保留）

```bash
python src/hotel_simulation_v5.py
python src/generate_simple_pdf.py
```

## V6 核心算法

### 1. 酒店信用评级模型（Merton框架）

```
Distance-to-Default = [ln(V/D) + (μ - 0.5σ²)T] / (σ√T)

其中：
- V = 酒店平均价格（资产价值代理）
- D = 平均价格 × 55%（违约边界/经营底线）
- σ = GARCH(1,1)条件波动率年化值 × 等级调整因子
- PD = N(-DD) × 校准因子(2.5)
```

### 2. ABS分层结构

| 层级 | 占比 | 目标评级 | 票息(年化) | 信用支持 |
|------|------|---------|-----------|---------|
| Senior | 68% | AAA | 4.5% | 32% |
| Mezzanine | 20% | BBB | 6.5% | 12% |
| Junior | 8% | B | 9.5% | 4% |
| Equity | 4% | NR | 剩余收益 | 0% |

### 3. 现金流瀑布（优先级）

```
1. 服务费/税费
2. Senior利息 → Senior本金（按计划摊还）
3. Mezzanine利息 → Mezzanine本金
4. Junior利息 → Junior本金
5. Equity剩余分配
6. 储备金补充
```

触发器：
- **OC测试失败**（<100%）→ Early Amortization，全部还Senior
- **IC测试失败**（<100%）→ Early Amortization
- **累计违约率>15%** → Event of Default，加速清偿

### 4. 蒙特卡洛模拟（Gaussian Copula）

```
10,000条路径 × 36个月 × 80家酒店

违约相关性：
- 系统因子权重: 70%
- 异质性因子权重: 30%
- 同等级基础相关: 8%
- 不同等级基础相关: 3%

输出：
- 分层级预期损失(EL)
- VaR 95% / VaR 99% / CVaR 95%
- 穆迪风格隐含评级映射
```

### 5. RWA代币化架构

```
链下：SPV(开曼/新加坡) → 酒店订单合同 → 现金流归集账户
链上：ERC-3643安全代币 → 4档分层代币 → 智能合约瀑布分配
预言机：月度服务报告上链 → 自动触发分配 → 事件日志
```

## V6 关键结果

### 资产池特征

- **规模**: 80家成都地区酒店
- **总面值**: ¥1,544万
- **等级分布**: 经济40% / 舒适30% / 高档20% / 豪华10%
- **地理分散**: 覆盖18个区县，HHI=0.220
- **信用分布**: Aaa-A: 9% / Baa-B: 6% / Caa-C: 85%

### 蒙特卡洛分析（10,000路径）

| 分层 | 预期损失 | VaR 95% | VaR 99% | 隐含评级 |
|------|---------|---------|---------|---------|
| Senior | ~0% | ~0% | ~0% | **Aaa** |
| Mezzanine | ~0% | ~0% | ~0% | **Aaa** |
| Junior | ~0% | ~0% | ~0% | **Aaa** |
| Equity | ~0% | ~0% | ~0% | **Aaa** |

*平均累计违约率: 2.43%，信用支持充分吸收损失*

### 压力测试（Senior层）

| 情景 | 预期损失 | VaR 95% | 隐含评级 |
|------|---------|---------|---------|
| 基准 | ~0% | ~0% | Aaa |
| 轻度压力(PD×1.5) | ~0% | ~0% | Aaa |
| 中度压力(PD×2.5) | ~0% | ~0% | Aaa |
| 重度压力(PD×4.0) | ~0% | ~0% | Aaa |
| 极端压力(PD×6.0) | ~0% | ~0% | Aaa |

## V5 关键结果（保留）

### 对照组 vs 实验组对比

| 指标 | 传统模式 | 金融化模式 | 增量 |
|-----|---------|-----------|------|
| NPV | ¥105.7亿 | ¥167.3亿 | **+58.3%** |
| ROI | 35.00% | 67.46% | **+32.46%** |

## 数据说明

本项目使用成都地区酒店的真实价格数据：
- **酒店信息**: 86,159家（含经纬度、等级）
- **价格数据**: 1,707,918条日价格记录（2024年3-6月）
- **远期价格**: 16,258家酒店的最低价格作为底价预测

## 技术栈

- **Python 3.8+**
- **pandas** - 数据处理
- **numpy** - 数值计算
- **matplotlib** - 可视化
- **scipy** - 科学计算（统计分布、优化）
- **seaborn** - 高级可视化

## 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

## 作者

- 作者：研究团队
- 日期：2024年

## 致谢

感谢所有为本项目提供数据和支持的合作伙伴。
