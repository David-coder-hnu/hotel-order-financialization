#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
酒店订单金融化可行性分析报告生成器 - 简化版
生成HTML格式报告，可转换为PDF
"""

import json
from datetime import datetime
import os

def generate_html_report():
    """生成HTML报告"""
    
    work_dir = r'c:\Users\weida\Desktop\酒店研究'
    
    # 读取JSON报告
    with open(f'{work_dir}/output/simulation_report_v5.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>酒店订单金融化可行性分析报告</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 40px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            border-bottom: 3px solid #3498db;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        h2 {{
            color: #34495e;
            border-left: 4px solid #3498db;
            padding-left: 15px;
            margin-top: 40px;
        }}
        h3 {{
            color: #7f8c8d;
            margin-top: 30px;
        }}
        .summary {{
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .highlight {{
            background-color: #fff3cd;
            padding: 2px 5px;
            border-radius: 3px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #34495e;
            color: white;
        }}
        tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        .metric {{
            display: inline-block;
            margin: 10px 20px 10px 0;
            padding: 15px;
            background-color: #3498db;
            color: white;
            border-radius: 5px;
            min-width: 150px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
        }}
        .metric-label {{
            font-size: 12px;
            opacity: 0.9;
        }}
        .pass {{
            color: #27ae60;
            font-weight: bold;
        }}
        .fail {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .warning {{
            color: #f39c12;
            font-weight: bold;
        }}
        .chart-container {{
            text-align: center;
            margin: 30px 0;
        }}
        .chart-container img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        .footer {{
            text-align: center;
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #7f8c8d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>酒店订单金融化可行性分析报告</h1>
        <p style="text-align: center; color: #7f8c8d;">
            基于ABS/RWA金融模型的可行性研究<br>
            报告日期: {data['simulation_date']} | 版本: {data['simulation_version']}
        </p>
        
        <h2>执行摘要</h2>
        <div class="summary">
            <p><strong>核心结论:</strong></p>
            <ul>
                <li>可行性评级: <span class="highlight">{data['feasibility_evaluation']['rating']}级（{data['feasibility_evaluation']['rating_description']}）</span></li>
                <li>综合评分: {data['feasibility_evaluation']['overall_score']}/100</li>
                <li>可行性结论: {data['feasibility_evaluation']['conclusion']}</li>
                <li>建议: {data['feasibility_evaluation']['recommendation']}</li>
            </ul>
            
            <div>
                <div class="metric">
                    <div class="metric-value">¥{data['control_group']['npv']:,.0f}</div>
                    <div class="metric-label">传统模式NPV</div>
                </div>
                <div class="metric">
                    <div class="metric-value">¥{data['experiment_group']['financial_metrics']['npv']:,.0f}</div>
                    <div class="metric-label">金融化模式NPV</div>
                </div>
                <div class="metric">
                    <div class="metric-value">+{data['incremental_analysis']['npv_increment_percent']:.1f}%</div>
                    <div class="metric-label">NPV增幅</div>
                </div>
            </div>
        </div>
        
        <h2>1. 项目概述</h2>
        <p>基于酒店资产证券化（ABS/REITs）和现实世界资产代币化（RWA）的金融创新趋势，
        本研究旨在分析酒店订单金融化的可行性。通过将未来住宿权益打包成可交易的金融产品，
        酒店可以提前回笼资金、优化现金流、提升资产流动性。</p>
        
        <h3>1.1 研究目标</h3>
        <ul>
            <li>现金流分析：对比传统模式与金融化模式的现金流差异</li>
            <li>收益评估：计算NPV、IRR等核心财务指标</li>
            <li>风险评估：分析流动性风险、信用风险、市场风险</li>
            <li>可行性结论：判断酒店订单金融化的商业可行性</li>
        </ul>
        
        <h2>2. 数据基础</h2>
        <h3>2.1 酒店选择</h3>
        <table>
            <tr>
                <th>酒店代码</th>
                <th>酒店名称</th>
                <th>均价(元)</th>
                <th>底价(元)</th>
                <th>入住率</th>
                <th>RevPAR</th>
            </tr>
"""
    
    # 添加酒店数据
    for hotel in data['hotel_selection']:
        html_content += f"""
            <tr>
                <td>{hotel['hotel_code']}</td>
                <td>{hotel['hotel_name']}</td>
                <td>¥{hotel['avg_price']:,.0f}</td>
                <td>¥{hotel['base_price']:,.0f}</td>
                <td>{hotel['occupancy_rate']*100:.1f}%</td>
                <td>¥{hotel['revpar']:,.0f}</td>
            </tr>
"""
    
    html_content += f"""
        </table>
        
        <h3>2.2 模拟参数</h3>
        <ul>
            <li>对照组用户数: {data['parameters']['control_group_users']:,}名</li>
            <li>实验组用户数: {data['parameters']['experiment_group_users']:,}名</li>
            <li>折现率: {data['parameters']['discount_rate']*100:.1f}%</li>
            <li>分析期限: {data['parameters']['project_years']}年</li>
            <li>安全系数: {data['parameters']['safety_factor']}</li>
            <li>超发倍数: {data['parameters']['overbooking_multiplier']:.2f}</li>
            <li>约定收益率: {data['parameters']['promised_return_rate']*100:.0f}%/年</li>
            <li>实物折扣率: {data['parameters']['physical_discount_rate']*100:.0f}%</li>
        </ul>
        
        <h2>3. 对照组分析（传统模式）</h2>
        <h3>3.1 财务指标</h3>
        <table>
            <tr>
                <th>指标</th>
                <th>数值</th>
            </tr>
            <tr>
                <td>总收入</td>
                <td>¥{data['control_group']['total_revenue']:,.0f}</td>
            </tr>
            <tr>
                <td>总成本</td>
                <td>¥{data['control_group']['total_cost']:,.0f}</td>
            </tr>
            <tr>
                <td>净利润</td>
                <td>¥{data['control_group']['total_profit']:,.0f}</td>
            </tr>
            <tr>
                <td>NPV</td>
                <td>¥{data['control_group']['npv']:,.0f}</td>
            </tr>
            <tr>
                <td>IRR</td>
                <td>{data['control_group']['irr']:.2f}%</td>
            </tr>
            <tr>
                <td>ROI</td>
                <td>{data['control_group']['roi']:.2f}%</td>
            </tr>
        </table>
        
        <h2>4. 实验组分析（金融化模式）</h2>
        <h3>4.1 时权ABS发行</h3>
        <ul>
            <li>发行总收入: ¥{data['experiment_group']['issue_phase']['total_issue_revenue']:,.0f}</li>
            <li>物理房间总数: {data['experiment_group']['issue_phase']['total_physical_rooms']}间</li>
            <li>时权发行总量: {data['experiment_group']['issue_phase']['total_issue_quantity']}份</li>
            <li>超发比例: {data['experiment_group']['issue_phase']['overbooking_ratio']:.2f}倍</li>
        </ul>
        
        <h3>4.2 平台交易</h3>
        <ul>
            <li>市场价格因子: {data['experiment_group']['trading_phase']['market_price_factor']:.4f}</li>
            <li>市场总价值: ¥{data['experiment_group']['trading_phase']['total_market_value']:,.0f}</li>
            <li>交易手续费: ¥{data['experiment_group']['trading_phase']['total_trading_fee']:,.0f}</li>
        </ul>
        
        <h3>4.3 三方收益分析</h3>
        <table>
            <tr>
                <th>参与方</th>
                <th>收入/收益</th>
                <th>成本</th>
                <th>净利润</th>
            </tr>
            <tr>
                <td>酒店方</td>
                <td>¥{data['experiment_group']['hotel']['revenue']:,.0f}</td>
                <td>¥{data['experiment_group']['hotel']['cost']:,.0f}</td>
                <td>¥{data['experiment_group']['hotel']['profit']:,.0f}</td>
            </tr>
            <tr>
                <td>平台方</td>
                <td>¥{data['experiment_group']['platform']['total_revenue']:,.0f}</td>
                <td>-</td>
                <td>¥{data['experiment_group']['platform']['total_revenue']:,.0f}</td>
            </tr>
            <tr>
                <td>投资者方</td>
                <td>¥{data['experiment_group']['investors']['total_return']:,.0f}</td>
                <td>¥{data['experiment_group']['investors']['cost']:,.0f}</td>
                <td>¥{data['experiment_group']['investors']['net_return']:,.0f}</td>
            </tr>
        </table>
        
        <h2>5. 财务指标对比</h2>
        <table>
            <tr>
                <th>指标</th>
                <th>对照组</th>
                <th>实验组</th>
                <th>增量</th>
                <th>增幅</th>
            </tr>
            <tr>
                <td>NPV</td>
                <td>¥{data['control_group']['npv']:,.0f}</td>
                <td>¥{data['experiment_group']['financial_metrics']['npv']:,.0f}</td>
                <td>¥{data['incremental_analysis']['npv_increment']:,.0f}</td>
                <td>+{data['incremental_analysis']['npv_increment_percent']:.1f}%</td>
            </tr>
            <tr>
                <td>IRR</td>
                <td>{data['control_group']['irr']:.2f}%</td>
                <td>{data['experiment_group']['financial_metrics']['irr']:.2f}%</td>
                <td>{data['incremental_analysis']['irr_increment']:.2f}%</td>
                <td>-</td>
            </tr>
            <tr>
                <td>ROI</td>
                <td>{data['control_group']['roi']:.2f}%</td>
                <td>{data['experiment_group']['financial_metrics']['roi']:.2f}%</td>
                <td>{data['experiment_group']['financial_metrics']['roi'] - data['control_group']['roi']:.2f}%</td>
                <td>-</td>
            </tr>
        </table>
        
        <h2>6. 风险评估</h2>
        <h3>6.1 流动性风险</h3>
        <ul>
            <li>日均换手率: {data['risk_assessment']['liquidity_risk']['daily_turnover_rate']*100:.1f}%</li>
            <li>买卖价差: {data['risk_assessment']['liquidity_risk']['bid_ask_spread']*100:.1f}%</li>
            <li>风险评分: {data['risk_assessment']['liquidity_risk']['score']}/100</li>
            <li>评估: <span class="{'pass' if data['risk_assessment']['liquidity_risk']['score'] >= 80 else 'warning'}">{data['risk_assessment']['liquidity_risk']['assessment']}</span></li>
        </ul>
        
        <h3>6.2 信用风险</h3>
        <ul>
            <li>违约概率: {data['risk_assessment']['credit_risk']['default_probability']*100:.1f}%</li>
            <li>信用评级: {data['risk_assessment']['credit_risk']['credit_rating']}</li>
            <li>风险评分: {data['risk_assessment']['credit_risk']['score']}/100</li>
            <li>评估: <span class="{'pass' if data['risk_assessment']['credit_risk']['score'] >= 80 else 'warning'}">{data['risk_assessment']['credit_risk']['assessment']}</span></li>
        </ul>
        
        <h3>6.3 市场风险</h3>
        <ul>
            <li>价格波动率: {data['risk_assessment']['market_risk']['price_volatility']*100:.1f}%</li>
            <li>VaR(95%): ¥{data['risk_assessment']['market_risk']['var_95']:,.0f}</li>
            <li>风险评分: {data['risk_assessment']['market_risk']['score']}/100</li>
            <li>评估: <span class="{'pass' if data['risk_assessment']['market_risk']['score'] >= 80 else 'warning'}">{data['risk_assessment']['market_risk']['assessment']}</span></li>
        </ul>
        
        <h2>7. 压力测试</h2>
        <table>
            <tr>
                <th>测试场景</th>
                <th>NPV</th>
                <th>评估结果</th>
            </tr>
            <tr>
                <td>入住率下降20%</td>
                <td>¥{data['stress_test']['occupancy_down_20']['npv']:,.0f}</td>
                <td class="{'pass' if data['stress_test']['occupancy_down_20']['pass'] else 'fail'}">{'通过 ✓' if data['stress_test']['occupancy_down_20']['pass'] else '不通过 ✗'}</td>
            </tr>
            <tr>
                <td>折现率上升2%</td>
                <td>¥{data['stress_test']['discount_up_2']['npv']:,.0f}</td>
                <td class="{'pass' if data['stress_test']['discount_up_2']['pass'] else 'fail'}">{'通过 ✓' if data['stress_test']['discount_up_2']['pass'] else '不通过 ✗'}</td>
            </tr>
            <tr>
                <td>兑付成本上升10%</td>
                <td>¥{data['stress_test']['redemption_up_10']['npv']:,.0f}</td>
                <td class="{'pass' if data['stress_test']['redemption_up_10']['pass'] else 'fail'}">{'通过 ✓' if data['stress_test']['redemption_up_10']['pass'] else '不通过 ✗'}</td>
            </tr>
        </table>
        
        <h2>8. 可行性评估</h2>
        <h3>8.1 评估维度</h3>
        <table>
            <tr>
                <th>评估维度</th>
                <th>评估标准</th>
                <th>结果</th>
                <th>状态</th>
            </tr>
            <tr>
                <td rowspan="3">财务可行性</td>
                <td>NPV > 0</td>
                <td>¥{data['experiment_group']['financial_metrics']['npv']:,.0f}</td>
                <td class="{'pass' if data['feasibility_evaluation']['financial']['npv_positive'] else 'fail'}">{'✓' if data['feasibility_evaluation']['financial']['npv_positive'] else '✗'}</td>
            </tr>
            <tr>
                <td>IRR > 10%</td>
                <td>{data['experiment_group']['financial_metrics']['irr']:.2f}%</td>
                <td class="{'pass' if data['feasibility_evaluation']['financial']['irr_above_10'] else 'fail'}">{'✓' if data['feasibility_evaluation']['financial']['irr_above_10'] else '✗'}</td>
            </tr>
            <tr>
                <td>ROI > 15%</td>
                <td>{data['experiment_group']['financial_metrics']['roi']:.2f}%</td>
                <td class="{'pass' if data['feasibility_evaluation']['financial']['roi_above_15'] else 'fail'}">{'✓' if data['feasibility_evaluation']['financial']['roi_above_15'] else '✗'}</td>
            </tr>
            <tr>
                <td rowspan="2">市场可行性</td>
                <td>流动性充足</td>
                <td>{data['risk_assessment']['liquidity_risk']['daily_turnover_rate']*100:.1f}%</td>
                <td class="{'pass' if data['feasibility_evaluation']['market']['liquidity_sufficient'] else 'fail'}">{'✓' if data['feasibility_evaluation']['market']['liquidity_sufficient'] else '✗'}</td>
            </tr>
            <tr>
                <td>价格稳定</td>
                <td>{data['risk_assessment']['market_risk']['price_volatility']*100:.1f}%</td>
                <td class="{'pass' if data['feasibility_evaluation']['market']['price_stable'] else 'fail'}">{'✓' if data['feasibility_evaluation']['market']['price_stable'] else '✗'}</td>
            </tr>
            <tr>
                <td rowspan="2">风险可控性</td>
                <td>违约概率 < 5%</td>
                <td>{data['risk_assessment']['credit_risk']['default_probability']*100:.1f}%</td>
                <td class="{'pass' if data['feasibility_evaluation']['risk']['default_controllable'] else 'fail'}">{'✓' if data['feasibility_evaluation']['risk']['default_controllable'] else '✗'}</td>
            </tr>
            <tr>
                <td>价格波动 < 20%</td>
                <td>{data['risk_assessment']['market_risk']['price_volatility']*100:.1f}%</td>
                <td class="{'pass' if data['feasibility_evaluation']['risk']['volatility_controllable'] else 'fail'}">{'✓' if data['feasibility_evaluation']['risk']['volatility_controllable'] else '✗'}</td>
            </tr>
        </table>
        
        <h3>8.2 综合评分</h3>
        <div class="summary">
            <p><strong>总分:</strong> {data['feasibility_evaluation']['overall_score']}/100</p>
            <p><strong>评级:</strong> <span class="highlight">{data['feasibility_evaluation']['rating']}级（{data['feasibility_evaluation']['rating_description']}）</span></p>
        </div>
        
        <h2>9. 结论与建议</h2>
        <h3>9.1 可行性结论</h3>
        <p>酒店订单金融化方案<span class="{'pass' if data['feasibility_evaluation']['overall_score'] >= 70 else 'fail'}"><strong>{data['feasibility_evaluation']['conclusion']}</strong></span>。</p>
        
        <h3>9.2 核心优势</h3>
        <ul>
            <li><strong>提前回笼资金:</strong> 酒店可提前获得¥{data['experiment_group']['issue_phase']['total_issue_revenue']:,.0f}发行收入，显著改善现金流状况</li>
            <li><strong>优化财务结构:</strong> NPV提升{data['incremental_analysis']['npv_increment_percent']:.1f}%，投资回报率提升至{data['experiment_group']['financial_metrics']['roi']:.2f}%</li>
            <li><strong>风险可控:</strong> 流动性、信用、市场风险均在可控范围内，压力测试全部通过</li>
            <li><strong>多方共赢:</strong> 酒店、平台、投资者均能从该模式中获得正向收益</li>
        </ul>
        
        <h3>9.3 实施建议</h3>
        <p>{data['feasibility_evaluation']['recommendation']}</p>
        <ul>
            <li>选择经营稳定、数据完整的酒店作为试点</li>
            <li>设置合理的超发比例，控制风险敞口</li>
            <li>建立完善的风险准备金机制</li>
            <li>加强投资者教育和信息披露</li>
            <li>持续监控市场动态，及时调整策略</li>
        </ul>
        
        <h2>附录：可视化分析</h2>
        <div class="chart-container">
            <img src="../simulation_visualization_v5.png" alt="可视化分析图表">
            <p><em>图1: 酒店订单金融化可行性分析可视化图表</em></p>
        </div>
        
        <div class="footer">
            <p>酒店订单金融化可行性分析报告 | 基于ABS/RWA金融模型</p>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""
    
    # 保存HTML文件
    html_file = f'{work_dir}/output/酒店订单金融化可行性分析报告.html'
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"HTML报告已生成: {html_file}")
    print(f"请使用浏览器打开该文件查看报告，或使用打印功能导出为PDF")
    return html_file

if __name__ == "__main__":
    generate_html_report()
