# 酒店订单金融化可行性分析

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

基于ABS/RWA金融模型的酒店订单金融化可行性研究项目。

## 项目概述

本项目旨在分析酒店订单金融化的可行性，通过将未来住宿权益打包成可交易的金融产品（时权ABS），帮助酒店提前回笼资金、优化现金流、提升资产流动性。

### 核心功能

- **数据预处理**：清洗和标准化酒店价格数据
- **金融建模**：基于收益法的时权ABS定价模型
- **可行性分析**：NPV、IRR、ROI等财务指标计算
- **风险评估**：流动性、信用、市场风险量化分析
- **可视化展示**：多维度图表展示分析结果

## 项目结构

```
酒店研究/
├── data/                           # 数据文件
│   ├── cleaned_hotel_prices.csv   # 清洗后的酒店价格数据
│   ├── hotel_future_prices.csv    # 酒店远期价格（底价）
│   ├── hotel_info.csv             # 酒店基本信息
│   ├── 2024_3.csv ~ 2024_6.csv    # 原始月度数据
│   └── 一种对酒店订单金融化的方法(1).docx  # 方法论文档
│
├── src/                           # 源代码
│   ├── hotel_simulation_v5.py     # 主模拟程序（V5最终版）
│   ├── generate_simple_pdf.py     # 报告生成器
│   └── clean_and_generate_prices.py # 数据清洗工具
│
├── output/                        # 输出文件
│   ├── simulation_report_v5.json  # 详细数据报告
│   ├── simulation_visualization_v5.png  # 可视化图表
│   └── 酒店订单金融化可行性分析报告.html  # HTML格式报告
│
├── .trae/specs/                   # 规格文档
│   ├── hotel-simulation-v4/       # V4版本规格
│   └── hotel-simulation-v5/       # V5版本规格
│
├── README.md                      # 项目说明
├── LICENSE                        # 许可证
├── .gitignore                     # Git忽略文件
├── PUSH_COMMANDS.bat              # Windows推送脚本
└── PUSH_TO_GITHUB.md              # GitHub推送说明
```

## 安装依赖

```bash
pip install pandas numpy matplotlib reportlab scipy
```

## 使用方法

### 1. 运行模拟分析

```bash
python src/hotel_simulation_v5.py
```

这将生成：
- `output/simulation_report_v5.json` - 详细的JSON格式报告
- `output/simulation_visualization_v5.png` - 可视化图表

### 2. 生成HTML报告

```bash
python src/generate_simple_pdf.py
```

生成 `output/酒店订单金融化可行性分析报告.html`，可用浏览器打开查看或打印为PDF。

## 核心算法

### 时权ABS定价模型（收益法）

```
发行价格 = Σ(预期未来现金流_t / (1+折现率)^t)

其中：
- 预期未来现金流 = 房间数 × 入住率 × 平均房价 × 365天
- 折现率 = 8%（年化）
- 超发倍数 = 1 / 入住率 × 安全系数(0.8)
```

### 财务指标

- **NPV（净现值）**：项目绝对价值评估
- **IRR（内部收益率）**：项目相对收益评估
- **ROI（投资回报率）**：投资效率评估

## 关键结果

### 对照组 vs 实验组对比

| 指标 | 传统模式 | 金融化模式 | 增量 |
|-----|---------|-----------|------|
| NPV | ¥105.7亿 | ¥167.3亿 | **+58.3%** |
| ROI | 35.00% | 67.46% | **+32.46%** |

### 可行性评估

- **综合评分**: 75/100 (B级推荐)
- **财务可行性**: 通过 ✓
- **市场可行性**: 通过 ✓
- **风险可控性**: 通过 ✓

## 数据说明

本项目使用5家成都地区酒店的真实价格数据：
- 青城后山石见民宿
- 岷江书院·院落式轻奢度假酒店
- 不想浅眠度假别墅
- 糊涂瞰山度假别墅
- 成都青城宋品酒店

数据时间范围：2024年3月-6月

## 技术栈

- **Python 3.8+**
- **pandas** - 数据处理
- **numpy** - 数值计算
- **matplotlib** - 可视化
- **scipy** - 科学计算
- **reportlab** - PDF生成

## 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

## 作者

- 作者：研究团队
- 日期：2024年

## 致谢

感谢所有为本项目提供数据和支持的合作伙伴。
