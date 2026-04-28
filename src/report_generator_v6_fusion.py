"""
酒店订单时权ABS/RWA融合报告生成器 V6-Fusion

生成投行/评级机构级别的融合分析报告：
- 时权发行与价格收敛可视化
- 三方收益对比分析
- 传统vs时权模式对比
- 敏感性分析与风险评估
- 专业美观的HTML报告
"""

import json
import os
import numpy as np
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from datetime import datetime


class ABSFusionReportGenerator:
    """时权ABS融合报告生成器"""
    
    def __init__(self, report_json_path=None, work_dir=None):
        self.work_dir = work_dir or r'C:\Users\weida\Desktop\酒店研究'
        
        if report_json_path is None:
            report_json_path = f'{self.work_dir}/output/abs_report_v6_fusion.json'
        
        with open(report_json_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
    
    def generate_visualization(self):
        """生成融合版专业可视化图表 (15子图, 5x3布局)"""
        print("\n生成融合版可视化图表...")
        
        fig = plt.figure(figsize=(28, 40))
        gs = gridspec.GridSpec(5, 3, figure=fig, hspace=0.38, wspace=0.32)
        
        d = self.data
        
        # ========== 第1行: 时权发行概览 ==========
        
        # 1.1 时权发行结构 (Top 15酒店)
        ax1 = fig.add_subplot(gs[0, 0])
        tr = d['asset_pool']['time_rights'][:15]
        hotel_names = [t['hotelCode'][-6:] for t in tr]
        quantities = [t['issue_quantity'] for t in tr]
        colors_lvl = {'经济': '#3498db', '舒适': '#2ecc71', '高档': '#f39c12', '豪华': '#e74c3c'}
        bar_colors = [colors_lvl.get(t['hotelLevel'], '#34495e') for t in tr]
        ax1.barh(hotel_names, quantities, color=bar_colors)
        ax1.set_xlabel('发行数量 (份)')
        ax1.set_title('时权发行结构 (Top 15酒店)', fontsize=14, fontweight='bold')
        ax1.invert_yaxis()
        ax1.grid(True, alpha=0.3)
        
        # 1.2 时权价格收敛路径
        ax2 = fig.add_subplot(gs[0, 1])
        market_sim = d.get('time_right_market_simulation', {})
        if 'price_convergence_path' in market_sim and market_sim['price_convergence_path']:
            price_path = market_sim['price_convergence_path']
            months = list(range(len(price_path)))
            ax2.plot(months, price_path, color='#3498db', linewidth=2.5, marker='o', markersize=3)
            # 添加发行价和即期价参考线
            tr0 = d['asset_pool']['time_rights'][0]
            ax2.axhline(tr0['issue_price'], color='green', linestyle='--', alpha=0.7, label='发行价')
            ax2.axhline(tr0['spot_predicted'], color='red', linestyle='--', alpha=0.7, label='即期预测价')
            ax2.fill_between(months, price_path, alpha=0.2, color='#3498db')
            ax2.set_xlabel('月份')
            ax2.set_ylabel('平均价格 (元)')
            ax2.set_title('时权价格收敛路径 (36个月)', fontsize=14, fontweight='bold')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        else:
            ax2.text(0.5, 0.5, '价格收敛数据不可用', ha='center', va='center', transform=ax2.transAxes)
            ax2.set_title('时权价格收敛路径', fontsize=14, fontweight='bold')
        
        # 1.3 兑付选择分布
        ax3 = fig.add_subplot(gs[0, 2])
        tripartite = d.get('tripartite_benefit_analysis', {})
        user_data = tripartite.get('user', {})
        choices = user_data.get('avg_choice_ratios', {'cash': 0.25, 'physical': 0.50, 'transfer': 0.25})
        choice_labels = ['现金兑付\n(8%年化)', '实物兑付\n(7折入住)', '二级市场\n转让']
        choice_values = [choices['cash'], choices['physical'], choices['transfer']]
        choice_colors = ['#27ae60', '#f39c12', '#9b59b6']
        wedges, texts, autotexts = ax3.pie(
            choice_values, labels=choice_labels, autopct='%1.1f%%',
            colors=choice_colors, startangle=90, explode=(0.02, 0.02, 0.02)
        )
        ax3.set_title('用户兑付选择分布', fontsize=14, fontweight='bold')
        
        # ========== 第2行: 三方收益对比 ==========
        
        # 2.1 酒店现金流对比 (传统 vs 时权)
        ax4 = fig.add_subplot(gs[1, 0])
        comp = d.get('comparison_analysis', {})
        trad = comp.get('traditional_mode', {})
        tr_mode = comp.get('time_right_mode', {})
        
        if trad.get('monthly_cashflow') and tr_mode.get('monthly_cashflow'):
            trad_monthly = np.array(trad['monthly_cashflow']) / 1e8
            tr_monthly = np.array(tr_mode['monthly_cashflow']) / 1e8
            months = list(range(len(trad_monthly)))
            
            ax4.bar([m - 0.2 for m in months], trad_monthly, width=0.35, label='传统模式', color='#95a5a6', alpha=0.8)
            ax4.bar([m + 0.2 for m in months], tr_monthly, width=0.35, label='时权模式', color='#3498db', alpha=0.8)
            ax4.set_xlabel('月份')
            ax4.set_ylabel('现金流 (亿元)')
            ax4.set_title('酒店现金流对比: 传统 vs 时权', fontsize=14, fontweight='bold')
            ax4.legend()
            ax4.grid(True, alpha=0.3)
            ax4.axhline(0, color='black', linewidth=0.5)
        else:
            ax4.text(0.5, 0.5, '现金流对比数据不可用', ha='center', va='center', transform=ax4.transAxes)
            ax4.set_title('酒店现金流对比', fontsize=14, fontweight='bold')
        
        # 2.2 平台收益构成
        ax5 = fig.add_subplot(gs[1, 1])
        platform = tripartite.get('platform', {})
        if platform:
            plat_items = {
                '发行管理费\n(1%)': platform.get('issuance_management_fee', 0) / 1e8,
                '交易手续费\n(0.5%)': platform.get('trading_fee_income', 0) / 1e8,
                '兑付服务费\n(1%)': platform.get('redemption_service_fee', 0) / 1e8,
            }
            plat_colors = ['#3498db', '#2ecc71', '#f39c12']
            bars = ax5.bar(plat_items.keys(), plat_items.values(), color=plat_colors)
            ax5.set_ylabel('收益 (亿元)')
            ax5.set_title('平台收益构成', fontsize=14, fontweight='bold')
            for bar in bars:
                height = bar.get_height()
                ax5.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}', ha='center', va='bottom', fontsize=10)
            ax5.grid(True, alpha=0.3)
        else:
            ax5.text(0.5, 0.5, '平台收益数据不可用', ha='center', va='center', transform=ax5.transAxes)
            ax5.set_title('平台收益构成', fontsize=14, fontweight='bold')
        
        # 2.3 用户收益分布
        ax6 = fig.add_subplot(gs[1, 2])
        if user_data:
            user_items = {
                '现金兑付\n回报': user_data.get('cash_redemption_return', 0) / 1e8,
                '实物兑付\n节省': user_data.get('physical_redemption_savings', 0) / 1e8,
                '二级市场\n溢价': user_data.get('secondary_market_premium', 0) / 1e8,
            }
            user_colors = ['#27ae60', '#f39c12', '#9b59b6']
            bars = ax6.bar(user_items.keys(), user_items.values(), color=user_colors)
            ax6.set_ylabel('收益 (亿元)')
            ax6.set_title('用户收益分布', fontsize=14, fontweight='bold')
            for bar in bars:
                height = bar.get_height()
                ax6.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}', ha='center', va='bottom', fontsize=10)
            ax6.grid(True, alpha=0.3)
        else:
            ax6.text(0.5, 0.5, '用户收益数据不可用', ha='center', va='center', transform=ax6.transAxes)
            ax6.set_title('用户收益分布', fontsize=14, fontweight='bold')
        
        # ========== 第3行: ABS风险分析 ==========
        
        # 3.1 资产池等级分布
        ax7 = fig.add_subplot(gs[2, 0])
        levels = d['asset_pool']['statistics']['level_diversity']
        colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c']
        wedges, texts, autotexts = ax7.pie(
            levels.values(), labels=levels.keys(), autopct='%1.1f%%',
            colors=colors[:len(levels)], startangle=90
        )
        ax7.set_title('资产池等级分布', fontsize=14, fontweight='bold')
        
        # 3.2 资产池信用评级分布
        ax8 = fig.add_subplot(gs[2, 1])
        ratings = d['asset_pool']['statistics']['rating_distribution']
        rating_order = ['AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC', 'CC', 'C']
        rating_counts = {r: ratings.get(r, 0) for r in rating_order if r in ratings}
        bars = ax8.bar(rating_counts.keys(), rating_counts.values(), color='#34495e')
        ax8.set_xlabel('信用评级')
        ax8.set_ylabel('酒店数量')
        ax8.set_title('资产池信用评级分布', fontsize=14, fontweight='bold')
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax8.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}', ha='center', va='bottom', fontsize=9)
        
        # 3.3 ABS分层结构
        ax9 = fig.add_subplot(gs[2, 2])
        tranches = d['tranche_structure']
        names = [t['name'] for t in tranches]
        sizes = [t['size_pct'] * 100 for t in tranches]
        colors_t = ['#27ae60', '#f39c12', '#e74c3c', '#9b59b6']
        bars = ax9.barh(names, sizes, color=colors_t)
        ax9.set_xlabel('占比 (%)')
        ax9.set_title('ABS分层结构', fontsize=14, fontweight='bold')
        for i, (bar, size) in enumerate(zip(bars, sizes)):
            ax9.text(size + 1, i, f'{size:.1f}%', va='center', fontsize=10)
        
        # ========== 第4行: 蒙特卡洛与压力测试 ==========
        
        # 4.1 各分层预期损失 vs 信用支持
        ax10 = fig.add_subplot(gs[3, 0])
        el_values = [t['expected_loss'] * 100 for t in tranches]
        cs_values = [t['credit_support_pct'] * 100 for t in tranches]
        x = np.arange(len(names))
        width = 0.35
        bars1 = ax10.bar(x - width/2, el_values, width, label='预期损失率', color='#e74c3c')
        bars2 = ax10.bar(x + width/2, cs_values, width, label='信用支持', color='#27ae60')
        ax10.set_ylabel('百分比 (%)')
        ax10.set_title('分层预期损失 vs 信用支持', fontsize=14, fontweight='bold')
        ax10.set_xticks(x)
        ax10.set_xticklabels(names)
        ax10.legend()
        ax10.grid(True, alpha=0.3)
        
        # 4.2 Senior层损失分布
        ax11 = fig.add_subplot(gs[3, 1])
        mc = d['monte_carlo']['tranche_analysis']
        if 'Senior' in mc:
            hist = mc['Senior']['loss_histogram']
            bins = mc['Senior']['loss_bins']
            bin_centers = [(bins[i] + bins[i+1])/2 * 100 for i in range(len(hist))]
            ax11.bar(bin_centers, hist, width=bins[1]*100*0.8, color='#3498db', alpha=0.7, edgecolor='white')
            ax11.axvline(mc['Senior']['var_95']*100, color='red', linestyle='--', label=f"VaR 95%: {mc['Senior']['var_95']*100:.2f}%")
            ax11.axvline(mc['Senior']['mean_loss_rate']*100, color='green', linestyle='-', label=f"EL: {mc['Senior']['mean_loss_rate']*100:.2f}%")
            ax11.set_xlabel('损失率 (%)')
            ax11.set_ylabel('频数')
            ax11.set_title('Senior层损失分布 (5000路径)', fontsize=14, fontweight='bold')
            ax11.legend()
            ax11.grid(True, alpha=0.3)
        
        # 4.3 Mezzanine层损失分布
        ax12 = fig.add_subplot(gs[3, 2])
        if 'Mezzanine' in mc:
            hist = mc['Mezzanine']['loss_histogram']
            bins = mc['Mezzanine']['loss_bins']
            bin_centers = [(bins[i] + bins[i+1])/2 * 100 for i in range(len(hist))]
            ax12.bar(bin_centers, hist, width=bins[1]*100*0.8, color='#f39c12', alpha=0.7, edgecolor='white')
            ax12.axvline(mc['Mezzanine']['var_95']*100, color='red', linestyle='--', label=f"VaR 95%: {mc['Mezzanine']['var_95']*100:.2f}%")
            ax12.axvline(mc['Mezzanine']['mean_loss_rate']*100, color='green', linestyle='-', label=f"EL: {mc['Mezzanine']['mean_loss_rate']*100:.2f}%")
            ax12.set_xlabel('损失率 (%)')
            ax12.set_ylabel('频数')
            ax12.set_title('Mezzanine层损失分布 (5000路径)', fontsize=14, fontweight='bold')
            ax12.legend()
            ax12.grid(True, alpha=0.3)
        
        # ========== 第5行: 高级分析 ==========
        
        # 5.1 敏感性分析 - 入住率 vs NPV
        ax13 = fig.add_subplot(gs[4, 0])
        sens = d.get('sensitivity_analysis', {})
        occ_sens = sens.get('occupancy_sensitivity', [])
        if occ_sens:
            occ_rates = [s['occupancy_rate'] for s in occ_sens]
            occ_npvs = [s['npv'] / 1e8 for s in occ_sens]
            ax13.plot(occ_rates, occ_npvs, color='#3498db', marker='o', linewidth=2.5, markersize=8)
            ax13.fill_between(occ_rates, occ_npvs, alpha=0.2, color='#3498db')
            ax13.axvline(0.62, color='red', linestyle='--', alpha=0.7, label='基准入住率')
            ax13.set_xlabel('入住率')
            ax13.set_ylabel('NPV (亿元)')
            ax13.set_title('入住率敏感性分析', fontsize=14, fontweight='bold')
            ax13.legend()
            ax13.grid(True, alpha=0.3)
        else:
            ax13.text(0.5, 0.5, '敏感性数据不可用', ha='center', va='center', transform=ax13.transAxes)
            ax13.set_title('入住率敏感性分析', fontsize=14, fontweight='bold')
        
        # 5.2 传统vs时权NPV/IRR对比
        ax14 = fig.add_subplot(gs[4, 1])
        if comp:
            metrics = ['NPV', 'IRR']
            trad_vals = [
                trad.get('npv', 0) / 1e8,
                trad.get('irr', 0) * 100,
            ]
            tr_vals = [
                tr_mode.get('npv', 0) / 1e8,
                tr_mode.get('irr', 0) * 100,
            ]
            x = np.arange(len(metrics))
            width = 0.35
            ax14_twin = ax14.twinx()
            bars1 = ax14.bar(x - width/2, [trad_vals[0]], width, label='传统NPV', color='#95a5a6')
            bars2 = ax14.bar(x + width/2, [tr_vals[0]], width, label='时权NPV', color='#3498db')
            bars3 = ax14_twin.bar(x - width/2, [0, trad_vals[1]], width, label='传统IRR', color='#95a5a6', alpha=0.5)
            bars4 = ax14_twin.bar(x + width/2, [0, tr_vals[1]], width, label='时权IRR', color='#3498db', alpha=0.5)
            
            # 简化：只显示NPV对比
            ax14.clear()
            categories = ['传统模式', '时权模式']
            npv_vals = [trad_vals[0], tr_vals[0]]
            irr_vals = [trad_vals[1], tr_vals[1]]
            x = np.arange(len(categories))
            width = 0.35
            bars1 = ax14.bar(x - width/2, npv_vals, width, label='NPV(亿元)', color='#3498db')
            ax14_twin = ax14.twinx()
            bars2 = ax14_twin.bar(x + width/2, irr_vals, width, label='IRR(%)', color='#e74c3c')
            ax14.set_ylabel('NPV (亿元)', color='#3498db')
            ax14_twin.set_ylabel('IRR (%)', color='#e74c3c')
            ax14.set_xticks(x)
            ax14.set_xticklabels(categories)
            ax14.set_title('传统 vs 时权: NPV & IRR对比', fontsize=14, fontweight='bold')
            ax14.legend(loc='upper left')
            ax14_twin.legend(loc='upper right')
            ax14.grid(True, alpha=0.3)
        else:
            ax14.text(0.5, 0.5, '对比数据不可用', ha='center', va='center', transform=ax14.transAxes)
            ax14.set_title('NPV & IRR对比', fontsize=14, fontweight='bold')
        
        # 5.3 风险评估雷达图
        ax15 = fig.add_subplot(gs[4, 2], projection='polar')
        risk = d.get('risk_assessment', {})
        if risk and 'liquidity_risk' in risk:
            risk_items = ['流动性', '信用', '市场', '操作', '法律监管']
            risk_scores = [
                risk['liquidity_risk']['score'],
                risk['credit_risk']['score'],
                risk['market_risk']['score'],
                risk['operational_risk']['score'],
                risk['legal_regulatory_risk']['score'],
            ]
            # 闭合雷达图
            risk_scores += risk_scores[:1]
            angles = np.linspace(0, 2 * np.pi, len(risk_items), endpoint=False).tolist()
            angles += angles[:1]
            
            ax15.plot(angles, risk_scores, 'o-', linewidth=2, color='#3498db')
            ax15.fill(angles, risk_scores, alpha=0.25, color='#3498db')
            ax15.set_xticks(angles[:-1])
            ax15.set_xticklabels(risk_items, fontsize=11)
            ax15.set_ylim(0, 10)
            ax15.set_title('风险评估雷达图 (得分越高风险越低)', fontsize=14, fontweight='bold', pad=20)
            ax15.grid(True)
        else:
            ax15.text(0.5, 0.5, '风险评估数据不可用', ha='center', va='center', transform=ax15.transAxes)
            ax15.set_title('风险评估雷达图', fontsize=14, fontweight='bold', pad=20)
        
        plt.savefig(f'{self.work_dir}/output/abs_visualization_v6_fusion.png', dpi=200, bbox_inches='tight')
        print(f"  图表已保存: {self.work_dir}/output/abs_visualization_v6_fusion.png")
        plt.close()


    def generate_html_report(self):
        """生成专业美观的融合版HTML报告"""
        print("\n生成融合版HTML报告...")
        
        d = self.data
        
        def fmt_money(val, unit=1e8):
            return f"{val/unit:.2f}亿" if val >= unit else f"{val/1e4:.2f}万" if val >= 1e4 else f"{val:,.0f}"
        
        def rating_color_class(r):
            return 'badge-pass' if r in ['Aaa', 'Aa', 'A'] else 'badge-warning' if r in ['Baa'] else 'badge-fail'
        
        def risk_badge(score):
            if score >= 7:
                return 'badge-pass'
            elif score >= 5:
                return 'badge-warning'
            else:
                return 'badge-fail'
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>酒店订单时权ABS/RWA融合分析报告</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Microsoft YaHei','PingFang SC',Arial,sans-serif; line-height: 1.7; color: #2c3e50; background: #f0f2f5; }}
.container {{ max-width: 1200px; margin: 0 auto; background: white; box-shadow: 0 4px 30px rgba(0,0,0,0.1); }}

/* 封面 */
.cover {{ background: linear-gradient(135deg,#1a252f 0%,#2c3e50 50%,#34495e 100%); color: white; padding: 80px 60px; text-align: center; min-height: 500px; display: flex; flex-direction: column; justify-content: center; }}
.cover h1 {{ font-size: 36px; font-weight: 700; margin-bottom: 20px; letter-spacing: 2px; border: none; }}
.cover .subtitle {{ font-size: 20px; font-weight: 300; opacity: 0.9; margin-bottom: 40px; }}
.cover .meta {{ font-size: 14px; opacity: 0.7; line-height: 2; }}
.cover .badge {{ display: inline-block; background: rgba(255,255,255,0.15); padding: 8px 24px; border-radius: 20px; margin-top: 30px; font-size: 13px; letter-spacing: 1px; }}

/* 目录 */
.toc {{ background: #1a252f; padding: 15px 40px; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 10px rgba(0,0,0,0.2); }}
.toc ul {{ list-style: none; display: flex; flex-wrap: wrap; gap: 8px 20px; justify-content: center; }}
.toc a {{ color: #bdc3c7; text-decoration: none; font-size: 13px; transition: color 0.2s; }}
.toc a:hover {{ color: #3498db; }}

/* 内容 */
.content {{ padding: 40px 50px; }}
h2 {{ color: #1a252f; font-size: 22px; margin-top: 50px; margin-bottom: 20px; padding: 12px 20px; background: linear-gradient(90deg,#3498db 0%,#2980b9 100%); color: white; border-radius: 6px; box-shadow: 0 2px 8px rgba(52,152,219,0.3); }}
h3 {{ color: #2c3e50; font-size: 17px; margin-top: 30px; margin-bottom: 15px; padding-left: 12px; border-left: 4px solid #e74c3c; }}
h4 {{ color: #34495e; font-size: 15px; margin-top: 20px; margin-bottom: 10px; }}

/* 执行摘要 */
.summary-banner {{ background: linear-gradient(135deg,#667eea 0%,#764ba2 100%); color: white; padding: 35px; border-radius: 12px; margin: 25px 0; box-shadow: 0 4px 15px rgba(102,126,234,0.3); }}
.summary-banner .conclusion {{ font-size: 16px; line-height: 1.8; margin-bottom: 25px; text-align: center; opacity: 0.95; }}
.metrics-grid {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 15px; }}
.metric-card {{ background: rgba(255,255,255,0.95); padding: 18px; border-radius: 10px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1); transition: transform 0.2s; }}
.metric-card:hover {{ transform: translateY(-3px); }}
.metric-card .icon {{ font-size: 28px; margin-bottom: 8px; }}
.metric-card .value {{ font-size: 22px; font-weight: 700; color: #2c3e50; }}
.metric-card .label {{ font-size: 12px; color: #7f8c8d; margin-top: 5px; }}

/* 表格 */
table {{ width: 100%; border-collapse: collapse; margin: 18px 0; font-size: 13px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); border-radius: 8px; overflow: hidden; }}
th {{ background: linear-gradient(180deg,#2c3e50 0%,#1a252f 100%); color: white; padding: 12px 14px; text-align: left; font-weight: 600; }}
td {{ padding: 10px 14px; border-bottom: 1px solid #ecf0f1; }}
tr:nth-child(even) {{ background: #f8f9fa; }}
tr:hover {{ background: #e8f4f8; }}

/* 卡片 */
.card-grid {{ display: grid; grid-template-columns: repeat(3,1fr); gap: 20px; margin: 20px 0; }}
.card {{ background: white; border-radius: 10px; padding: 25px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); border-top: 4px solid #3498db; }}
.card.green {{ border-top-color: #27ae60; }}
.card.orange {{ border-top-color: #f39c12; }}
.card.purple {{ border-top-color: #9b59b6; }}
.card.red {{ border-top-color: #e74c3c; }}
.card h4 {{ margin-top: 0; color: #2c3e50; font-size: 16px; }}
.card .big-value {{ font-size: 28px; font-weight: 700; color: #2c3e50; margin: 10px 0; }}
.card .small-text {{ font-size: 12px; color: #7f8c8d; }}

/* 徽章 */
.badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
.badge-pass {{ background: #d4edda; color: #155724; }}
.badge-warning {{ background: #fff3cd; color: #856404; }}
.badge-fail {{ background: #f8d7da; color: #721c24; }}
.badge-info {{ background: #cce5ff; color: #004085; }}

/* 信息框 */
.info-box {{ background: #f0f7ff; border-left: 4px solid #3498db; padding: 18px 20px; margin: 15px 0; border-radius: 0 8px 8px 0; }}
.info-box.green {{ background: #e8f5e9; border-left-color: #27ae60; }}
.info-box.orange {{ background: #fff8e1; border-left-color: #f39c12; }}
.info-box.purple {{ background: #f3e5f5; border-left-color: #9b59b6; }}
.info-box h4 {{ margin-top: 0; margin-bottom: 10px; }}

.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 25px; margin: 20px 0; }}

/* 图表容器 */
.chart-container {{ text-align: center; margin: 30px 0; padding: 25px; background: #f8f9fa; border-radius: 12px; box-shadow: inset 0 1px 4px rgba(0,0,0,0.05); }}
.chart-container img {{ max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); }}

/* 进度条 */
.progress-bar {{ width: 100%; height: 24px; background: #ecf0f1; border-radius: 12px; overflow: hidden; margin: 8px 0; }}
.progress-fill {{ height: 100%; border-radius: 12px; display: flex; align-items: center; justify-content: flex-end; padding-right: 10px; color: white; font-size: 12px; font-weight: 600; }}
.progress-fill.green {{ background: linear-gradient(90deg,#27ae60,#2ecc71); }}
.progress-fill.blue {{ background: linear-gradient(90deg,#3498db,#5dade2); }}
.progress-fill.orange {{ background: linear-gradient(90deg,#f39c12,#f5b041); }}
.progress-fill.red {{ background: linear-gradient(90deg,#e74c3c,#ec7063); }}

/* 免责声明 */
.disclaimer {{ background: linear-gradient(135deg,#fff3cd 0%,#ffeeba 100%); padding: 25px; border-radius: 10px; margin-top: 40px; font-size: 12px; color: #856404; border: 1px solid #ffeaa7; }}

/* 页脚 */
.footer {{ text-align: center; padding: 30px; background: #1a252f; color: #95a5a6; font-size: 12px; }}

@media print {{
    .toc {{ display: none; }}
    .cover {{ min-height: auto; padding: 40px; }}
    .content {{ padding: 20px; }}
    h2 {{ page-break-after: avoid; }}
    table {{ page-break-inside: avoid; }}
    .card-grid {{ grid-template-columns: repeat(2,1fr); }}
}}
@media (max-width: 768px) {{
    .metrics-grid {{ grid-template-columns: repeat(2,1fr); }}
    .card-grid {{ grid-template-columns: 1fr; }}
    .two-col {{ grid-template-columns: 1fr; }}
    .content {{ padding: 20px; }}
}}
</style>
</head>
<body>
<div class="container">

<!-- 封面 -->
<div class="cover">
    <h1>酒店订单时权ABS/RWA<br>融合分析报告</h1>
    <div class="subtitle">超远期住宿权发行 + 二级市场交易 + 三元兑付机制</div>
    <div class="meta">
        版本: {d['report_metadata']['version']}<br>
        日期: {d['report_metadata']['date']}<br>
        方法论: {d['report_metadata']['methodology']}
    </div>
    <div class="badge">CONFIDENTIAL - 内部研究报告</div>
</div>

<!-- 目录 -->
<nav class="toc">
    <ul>
        <li><a href="#sec-summary">执行摘要</a></li>
        <li><a href="#sec-innovation">创新模型</a></li>
        <li><a href="#sec-pool">资产池</a></li>
        <li><a href="#sec-tranche">分层结构</a></li>
        <li><a href="#sec-mc">蒙特卡洛</a></li>
        <li><a href="#sec-market">时权市场</a></li>
        <li><a href="#sec-tripartite">三方收益</a></li>
        <li><a href="#sec-compare">对比分析</a></li>
        <li><a href="#sec-risk">风险敏感</a></li>
        <li><a href="#sec-feasibility">可行性</a></li>
        <li><a href="#sec-rwa">RWA架构</a></li>
        <li><a href="#sec-viz">可视化</a></li>
    </ul>
</nav>

<div class="content">

<!-- 执行摘要 -->
<h2 id="sec-summary">执行摘要</h2>
<div class="summary-banner">
    <div class="conclusion">
        本报告基于80家酒店、{d['asset_pool']['statistics'].get('time_right_total_quantity',0)/1e6:.2f}百万份时权Token的融合分析，<br>
        时权ABS模式相比传统经营可实现<strong>NPV提升{d.get('comparison_analysis',{}).get('npv_uplift',{}).get('percentage',0):.1f}%</strong>，<br>
        平台方可获得<strong>{fmt_money(d.get('tripartite_benefit_analysis',{}).get('platform',{}).get('total_platform_revenue',0))}</strong>综合收益，<br>
        用户平均可获得<strong>{d.get('tripartite_benefit_analysis',{}).get('user',{}).get('user_roi',0):.1f}%</strong>投资回报率。
    </div>
    <div class="metrics-grid">
        <div class="metric-card"><div class="icon">🏨</div><div class="value">{len(d['asset_pool']['hotels'])}</div><div class="label">资产池酒店数</div></div>
        <div class="metric-card"><div class="icon">🎫</div><div class="value">{d['asset_pool']['statistics'].get('time_right_total_quantity',0)/1e6:.2f}M</div><div class="label">时权发行总量</div></div>
        <div class="metric-card"><div class="icon">💰</div><div class="value">{fmt_money(d['asset_pool']['statistics'].get('time_right_total_face_value',0))}</div><div class="label">时权总面值</div></div>
        <div class="metric-card"><div class="icon">📊</div><div class="value">{d['asset_pool']['statistics']['wtd_pd']*100:.2f}%</div><div class="label">加权平均PD</div></div>
        <div class="metric-card"><div class="icon">🛡️</div><div class="value">{d['monte_carlo']['tranche_analysis']['Senior']['implied_rating']}</div><div class="label">Senior隐含评级</div></div>
        <div class="metric-card"><div class="icon">📈</div><div class="value">{d.get('tripartite_benefit_analysis',{}).get('platform',{}).get('platform_roi',0):.1f}%</div><div class="label">平台ROI</div></div>
        <div class="metric-card"><div class="icon">👤</div><div class="value">{d.get('tripartite_benefit_analysis',{}).get('user',{}).get('user_roi',0):.1f}%</div><div class="label">用户平均ROI</div></div>
        <div class="metric-card"><div class="icon">🚀</div><div class="value">+{d.get('comparison_analysis',{}).get('npv_uplift',{}).get('percentage',0):.1f}%</div><div class="label">NPV提升幅度</div></div>
    </div>
</div>

<!-- 第1章 -->
<h2 id="sec-innovation">第1章 创新模型概述</h2>
<h3>1.1 时权ABS核心概念</h3>
<div class="info-box">
    <h4>什么是酒店时权ABS?</h4>
    <p>酒店时权ABS（Time-Right ABS）是将酒店未来住宿权利转化为可交易金融资产的证券化产品。投资者提前购买未来时段的住宿权利，在二级市场上自由交易，到期时选择现金兑付、实物入住或市场转让。</p>
</div>
<div class="two-col">
    <div class="info-box green">
        <h4>创新点一: 超远期发行</h4>
        <p>酒店提前36个月发行住宿时权，一次性锁定未来收入。投资者以 discounted price 购买，到期享受收益或住宿。</p>
    </div>
    <div class="info-box orange">
        <h4>创新点二: 超发倍数机制</h4>
        <p>超发倍数 = 1 / 入住率 × 安全系数(0.8)，平均约1.29x。基于历史入住率数据动态调整，确保安全垫充足。</p>
    </div>
</div>
<div class="two-col">
    <div class="info-box">
        <h4>创新点三: 二级市场交易</h4>
        <p>时权Token可在二级市场自由转让，价格随到期日临近向即期价格收敛。平台收取0.5%交易手续费。</p>
    </div>
    <div class="info-box purple">
        <h4>创新点四: 三元兑付机制</h4>
        <p>到期时用户可选择: (1)现金兑付获8%年化回报; (2)实物入住享7折优惠; (3)二级市场转让变现。</p>
    </div>
</div>

<h3>1.2 与传统模式的本质区别</h3>
<table>
<tr><th>维度</th><th>传统酒店经营模式</th><th>时权ABS模式</th></tr>
<tr><td>现金流时点</td><td>逐月、分散、不确定</td><td>发行时一次性大额锁定</td></tr>
<tr><td>资金成本</td><td>高（需垫付运营资金）</td><td>低（用户预付）</td></tr>
<tr><td>用户粘性</td><td>低（每次重新选择）</td><td>高（提前锁定+投资收益）</td></tr>
<tr><td>资产流动性</td><td>无（酒店资产不可分）</td><td>高（Token可拆分交易）</td></tr>
<tr><td>风险分散</td><td>单一酒店经营风险</td><td>80家酒店组合+分层保护</td></tr>
</table>

<!-- 第2章 -->
<h2 id="sec-pool">第2章 资产池特征</h2>
<h3>2.1 基本规模</h3>
<table>
<tr><th>指标</th><th>数值</th><th>指标</th><th>数值</th></tr>
<tr><td>酒店数量</td><td>{d['asset_pool']['statistics']['pool_size']} 家</td><td>时权发行总量</td><td>{d['asset_pool']['statistics'].get('time_right_total_quantity',0):,.0f} 份</td></tr>
<tr><td>时权总面值</td><td>{fmt_money(d['asset_pool']['statistics'].get('time_right_total_face_value',0))}</td><td>平均单份发行价</td><td>¥{d['asset_pool']['statistics'].get('time_right_avg_price',0):,.0f}</td></tr>
<tr><td>平均超发倍数</td><td>{d['asset_pool']['time_rights'][0].get('overbooking_multiplier',0):.2f}x</td><td>覆盖区县数</td><td>{d['asset_pool']['statistics']['district_diversity']} 个</td></tr>
<tr><td>地区HHI</td><td>{d['asset_pool']['statistics']['district_herfindahl']:.3f}</td><td>Top 5集中度</td><td>{d['asset_pool']['statistics']['top5_concentration']*100:.1f}%</td></tr>
</table>

<h3>2.2 时权发行参数 (Top 10)</h3>
<table>
<tr><th>排名</th><th>酒店代码</th><th>等级</th><th>房间数</th><th>发行量</th><th>发行价</th><th>超发倍数</th><th>总面值</th></tr>
"""
        
        tr_list = sorted(d['asset_pool']['time_rights'], key=lambda x: x['total_face_value'], reverse=True)[:10]
        for i, t in enumerate(tr_list, 1):
            html += f"<tr><td>{i}</td><td>{t['hotelCode'][-10:]}</td><td>{t['hotelLevel']}</td>" \
                   f"<td>{t['rooms']}</td><td>{t['issue_quantity']:,}</td>" \
                   f"<td>¥{t['issue_price']:,.0f}</td><td>{t['overbooking_multiplier']:.2f}x</td>" \
                   f"<td>{fmt_money(t['total_face_value'])}</td></tr>\n"
        
        html += f"""
</table>

<h3>2.3 信用分布</h3>
<table>
<tr><th>评级</th><th>数量</th><th>占比</th><th>评级</th><th>数量</th><th>占比</th></tr>
"""
        
        ratings = d['asset_pool']['statistics']['rating_distribution']
        rating_items = sorted(ratings.items())
        for i in range(0, len(rating_items), 2):
            r1, c1 = rating_items[i]
            p1 = c1 / d['asset_pool']['statistics']['pool_size'] * 100
            if i + 1 < len(rating_items):
                r2, c2 = rating_items[i + 1]
                p2 = c2 / d['asset_pool']['statistics']['pool_size'] * 100
                html += f"<tr><td>{r1}</td><td>{c1}</td><td>{p1:.1f}%</td><td>{r2}</td><td>{c2}</td><td>{p2:.1f}%</td></tr>\n"
            else:
                html += f"<tr><td>{r1}</td><td>{c1}</td><td>{p1:.1f}%</td><td></td><td></td><td></td></tr>\n"
        
        html += """
</table>

<!-- 第3章 -->
<h2 id="sec-tranche">第3章 ABS分层结构</h2>
<h3>3.1 分层设计</h3>
<table>
<tr><th>层级</th><th>规模占比</th><th>规模</th><th>票息(年化)</th><th>目标评级</th><th>信用支持</th><th>预期损失</th><th>收益来源</th></tr>
"""
        
        for t in d['tranche_structure']:
            desc = t.get('description', '')
            rc = rating_color_class(t['target_rating'])
            html += f"<tr><td><strong>{t['name']}</strong></td><td>{t['size_pct']*100:.1f}%</td>" \
                   f"<td>{fmt_money(t['notional'])}</td><td>{t['coupon_annual']*100:.2f}%</td>" \
                   f"<td><span class='badge {rc}'>{t['target_rating']}</span></td>" \
                   f"<td>{t['credit_support_pct']*100:.1f}%</td><td>{t['expected_loss']*100:.2f}%</td>" \
                   f"<td><small>{desc}</small></td></tr>\n"
        
        ce = d.get('credit_enhancement', {})
        html += f"""
</table>

<h3>3.2 信用增级机制</h3>
<table>
<tr><th>增级机制</th><th>比例</th><th>金额</th><th>说明</th></tr>
<tr><td>超额抵押 (OC)</td><td>{ce.get('overcollateralization_pct',0)*100:.1f}%</td><td>{fmt_money(ce.get('overcollateralization_amount',0))}</td><td>资产池价值超过负债面值</td></tr>
<tr><td>储备金账户</td><td>{ce.get('reserve_target_pct',0)*100:.1f}%</td><td>{fmt_money(ce.get('reserve_target_amount',0))}</td><td>用于覆盖短期流动性缺口</td></tr>
<tr><td>超额利差 (12月)</td><td>{ce.get('excess_spread_buffer_12m',0)*100:.1f}%</td><td>-</td><td>资产收益超过负债成本的缓冲</td></tr>
<tr><td>Senior次级保护</td><td>{ce.get('senior_credit_support',0)*100:.1f}%</td><td>-</td><td>Mezzanine+Junior+Equity提供的信用支持</td></tr>
<tr><td><strong>总信用支持</strong></td><td><strong>{ce.get('total_credit_support_pct',0)*100:.1f}%</strong></td><td><strong>{fmt_money(ce.get('total_credit_support_amount',0))}</strong></td><td>综合信用增级水平</td></tr>
</table>

<!-- 第4章 -->
<h2 id="sec-mc">第4章 蒙特卡洛模拟分析</h2>
<p>基于 <strong>{d['monte_carlo']['n_paths']:,}</strong> 条蒙特卡洛路径 × <strong>{d['monte_carlo']['n_months']}</strong> 期的违约模拟，使用 Gaussian Copula 模型刻画酒店间违约相关性。</p>

<h3>4.1 分层损失统计</h3>
<table>
<tr><th>分层</th><th>预期损失(EL)</th><th>VaR 95%</th><th>VaR 99%</th><th>CVaR 95%</th><th>损失概率</th><th>隐含评级</th></tr>
"""
        
        for name, stats in d['monte_carlo']['tranche_analysis'].items():
            rc = rating_color_class(stats['implied_rating'])
            html += f"<tr><td><strong>{name}</strong></td><td>{stats['mean_loss_rate']*100:.2f}%</td>" \
                   f"<td>{stats['var_95']*100:.2f}%</td><td>{stats['var_99']*100:.2f}%</td>" \
                   f"<td>{stats.get('cvar_95',0)*100:.2f}%</td><td>{stats.get('prob_any_loss',0)*100:.1f}%</td>" \
                   f"<td><span class='badge {rc}'>{stats['implied_rating']}</span></td></tr>\n"
        
        html += """
</table>

<h3>4.2 压力测试对比</h3>
<table>
<tr><th>情景</th><th colspan="4">Senior层</th><th colspan="4">Mezzanine层</th><th colspan="4">Junior层</th><th colspan="4">Equity层</th></tr>
<tr><th></th><th>EL</th><th>VaR95</th><th>VaR99</th><th>评级</th><th>EL</th><th>VaR95</th><th>VaR99</th><th>评级</th><th>EL</th><th>VaR95</th><th>VaR99</th><th>评级</th><th>EL</th><th>VaR95</th><th>VaR99</th><th>评级</th></tr>
"""
        
        for scenario, stats in d['monte_carlo']['stress_test'].items():
            html += f"<tr><td><strong>{scenario}</strong></td>"
            for tname in ['Senior', 'Mezzanine', 'Junior', 'Equity']:
                s = stats.get(tname, {})
                html += f"<td>{s.get('mean_loss_rate',0)*100:.2f}%</td><td>{s.get('var_95',0)*100:.2f}%</td>" \
                       f"<td>{s.get('var_99',0)*100:.2f}%</td><td>{s.get('implied_rating','N/A')}</td>"
            html += "</tr>\n"
        
        html += "</table>\n"
        
        # 保存到self以便后续追加
        self._html_part1 = html
        self._fmt_money = fmt_money
        self._rating_color_class = rating_color_class
        self._risk_badge = risk_badge

        html = self._html_part1
        d = self.data
        fmt_money = self._fmt_money
        rating_color_class = self._rating_color_class
        risk_badge = self._risk_badge
        
        # ===== 第5章: 时权市场模拟 =====
        html += f"""
<h2 id="sec-market">第5章 时权市场模拟</h2>
<p>基于5,000条蒙特卡洛路径模拟时权二级市场交易与兑付过程，价格随到期日临近向即期价格收敛。</p>

<h3>5.1 市场模拟概览</h3>
<div class="card-grid">
    <div class="card blue">
        <h4>累计交易手续费</h4>
        <div class="big-value">{fmt_money(d.get('time_right_market_simulation',{}).get('total_trading_fee_income',0))}</div>
        <div class="small-text">按0.5%费率，月均5%换手率估算</div>
    </div>
    <div class="card green">
        <h4>累计现金兑付</h4>
        <div class="big-value">{fmt_money(d.get('time_right_market_simulation',{}).get('total_cash_redemption',0))}</div>
        <div class="small-text">含8%年化承诺回报</div>
    </div>
    <div class="card orange">
        <h4>累计实物兑付</h4>
        <div class="big-value">{fmt_money(d.get('time_right_market_simulation',{}).get('total_physical_redemption',0))}</div>
        <div class="small-text">按7折入住，变动成本35%</div>
    </div>
</div>

<h3>5.2 价格收敛路径</h3>
<table>
<tr><th>月份</th><th>平均价格(元)</th><th>相对发行价变化</th><th>月份</th><th>平均价格(元)</th><th>相对发行价变化</th></tr>
"""
        
        price_path = d.get('time_right_market_simulation', {}).get('price_convergence_path', [])
        if price_path:
            base_price = price_path[0] if price_path else 1
            for i in range(0, min(len(price_path), 36), 2):
                p1 = price_path[i]
                chg1 = (p1 / base_price - 1) * 100 if base_price > 0 else 0
                if i + 1 < len(price_path):
                    p2 = price_path[i + 1]
                    chg2 = (p2 / base_price - 1) * 100 if base_price > 0 else 0
                    html += f"<tr><td>{i+1}</td><td>¥{p1:,.0f}</td><td>{chg1:+.1f}%</td>" \
                           f"<td>{i+2}</td><td>¥{p2:,.0f}</td><td>{chg2:+.1f}%</td></tr>\n"
                else:
                    html += f"<tr><td>{i+1}</td><td>¥{p1:,.0f}</td><td>{chg1:+.1f}%</td><td></td><td></td><td></td></tr>\n"
        
        html += """
</table>

<h3>5.3 月度交易手续费与兑付成本</h3>
<table>
<tr><th>月份</th><th>交易手续费</th><th>现金兑付</th><th>实物兑付</th><th>月份</th><th>交易手续费</th><th>现金兑付</th><th>实物兑付</th></tr>
"""
        
        tf_monthly = d.get('time_right_market_simulation', {}).get('trading_fee_income_monthly', [])
        cash_monthly = d.get('time_right_market_simulation', {}).get('cash_redemption_monthly', [])
        phys_monthly = d.get('time_right_market_simulation', {}).get('physical_redemption_monthly', [])
        
        for i in range(0, min(len(tf_monthly), 36), 2):
            def fmt_cell(val):
                return fmt_money(val) if val >= 1e4 else f"¥{val:,.0f}"
            
            tf1 = tf_monthly[i] if i < len(tf_monthly) else 0
            c1 = cash_monthly[i] if i < len(cash_monthly) else 0
            p1 = phys_monthly[i] if i < len(phys_monthly) else 0
            
            if i + 1 < len(tf_monthly):
                tf2 = tf_monthly[i + 1]
                c2 = cash_monthly[i + 1] if i + 1 < len(cash_monthly) else 0
                p2 = phys_monthly[i + 1] if i + 1 < len(phys_monthly) else 0
                html += f"<tr><td>{i+1}</td><td>{fmt_cell(tf1)}</td><td>{fmt_cell(c1)}</td><td>{fmt_cell(p1)}</td>" \
                       f"<td>{i+2}</td><td>{fmt_cell(tf2)}</td><td>{fmt_cell(c2)}</td><td>{fmt_cell(p2)}</td></tr>\n"
            else:
                html += f"<tr><td>{i+1}</td><td>{fmt_cell(tf1)}</td><td>{fmt_cell(c1)}</td><td>{fmt_cell(p1)}</td><td></td><td></td><td></td><td></td></tr>\n"
        
        html += "</table>\n"
        
        # ===== 第6章: 三方收益分析 =====
        tripartite = d.get('tripartite_benefit_analysis', {})
        hotel_b = tripartite.get('hotel', {})
        plat_b = tripartite.get('platform', {})
        user_b = tripartite.get('user', {})
        
        html += f"""
<h2 id="sec-tripartite">第6章 三方收益分析</h2>
<p>时权ABS模式实现酒店、平台、用户三方共赢，以下是详细收益测算。</p>

<h3>6.1 酒店方收益</h3>
<div class="card-grid">
    <div class="card green">
        <h4>一次性发行收入</h4>
        <div class="big-value">{fmt_money(hotel_b.get('upfront_cash',0))}</div>
        <div class="small-text">提前36个月锁定未来住宿收入</div>
    </div>
    <div class="card red">
        <h4>未来兑付成本</h4>
        <div class="big-value">{fmt_money(hotel_b.get('redemption_cost',0))}</div>
        <div class="small-text">现金兑付+实物兑付变动成本</div>
    </div>
    <div class="card blue">
        <h4>净收益</h4>
        <div class="big-value">{fmt_money(hotel_b.get('net_benefit',0))}</div>
        <div class="small-text">发行收入 - 兑付成本</div>
    </div>
</div>
<div class="info-box green">
    <h4>现金流改善分析</h4>
    <p>{hotel_b.get('cashflow_improvement_description', '')}</p>
    <p><strong>营运资金提升:</strong> 相当于一次性获得 {fmt_money(hotel_b.get('working_capital_boost',0))} 的营运资金支持，可用于酒店升级改造、债务偿还或业务扩张。</p>
</div>

<h3>6.2 平台方收益</h3>
<div class="card-grid">
    <div class="card blue">
        <h4>发行管理费 (1%)</h4>
        <div class="big-value">{fmt_money(plat_b.get('issuance_management_fee',0))}</div>
    </div>
    <div class="card green">
        <h4>交易手续费 (0.5%)</h4>
        <div class="big-value">{fmt_money(plat_b.get('trading_fee_income',0))}</div>
    </div>
    <div class="card orange">
        <h4>兑付服务费 (1%)</h4>
        <div class="big-value">{fmt_money(plat_b.get('redemption_service_fee',0))}</div>
    </div>
</div>
<table>
<tr><th>指标</th><th>数值</th></tr>
<tr><td>平台总收益</td><td><strong>{fmt_money(plat_b.get('total_platform_revenue',0))}</strong></td></tr>
<tr><td>平台运营成本(估算)</td><td>{fmt_money(plat_b.get('platform_cost',0))}</td></tr>
<tr><td>平台净利润</td><td><strong>{fmt_money(plat_b.get('platform_net_profit',0))}</strong></td></tr>
<tr><td>平台ROI</td><td><span class="badge badge-pass">{plat_b.get('platform_roi',0):.1f}%</span></td></tr>
</table>

<h3>6.3 用户/投资者方收益</h3>
<div class="card-grid">
    <div class="card green">
        <h4>现金兑付回报 (8%年化)</h4>
        <div class="big-value">{fmt_money(user_b.get('cash_redemption_return',0))}</div>
        <div class="small-text">3年累计回报约25.9%</div>
    </div>
    <div class="card orange">
        <h4>实物兑付节省 (7折)</h4>
        <div class="big-value">{fmt_money(user_b.get('physical_redemption_savings',0))}</div>
        <div class="small-text">相当于30%折扣优惠</div>
    </div>
    <div class="card purple">
        <h4>二级市场溢价收益</h4>
        <div class="big-value">{fmt_money(user_b.get('secondary_market_premium',0))}</div>
        <div class="small-text">转让价差收益</div>
    </div>
</div>
<table>
<tr><th>指标</th><th>数值</th></tr>
<tr><td>用户总收益</td><td><strong>{fmt_money(user_b.get('total_user_benefit',0))}</strong></td></tr>
<tr><td>平均每份时权收益</td><td>¥{user_b.get('avg_user_return',0):,.0f}</td></tr>
<tr><td>用户平均ROI</td><td><span class="badge badge-pass">{user_b.get('user_roi',0):.1f}%</span></td></tr>
<tr><td>相比传统预订节省</td><td>{fmt_money(user_b.get('user_savings_vs_traditional',0))}</td></tr>
</table>

<h3>6.4 兑付选择比例</h3>
<table>
<tr><th>兑付方式</th><th>选择比例</th><th>预期收益特征</th></tr>
<tr><td>现金兑付</td><td>{user_b.get('avg_choice_ratios',{}).get('cash',0)*100:.1f}%</td><td>稳健型，8%年化固定收益</td></tr>
<tr><td>实物兑付</td><td>{user_b.get('avg_choice_ratios',{}).get('physical',0)*100:.1f}%</td><td>消费型，7折入住优惠</td></tr>
<tr><td>二级市场转让</td><td>{user_b.get('avg_choice_ratios',{}).get('transfer',0)*100:.1f}%</td><td>进取型，价差交易收益</td></tr>
</table>

<!-- 第7章: 对比分析 -->
<h2 id="sec-compare">第7章 传统模式 vs 时权模式对比</h2>

<h3>7.1 核心财务指标对比</h3>
<table>
<tr><th>指标</th><th>传统经营模式</th><th>时权ABS模式</th><th>差异</th></tr>
"""
        
        comp = d.get('comparison_analysis', {})
        trad = comp.get('traditional_mode', {})
        tr_mode = comp.get('time_right_mode', {})
        npv_up = comp.get('npv_uplift', {})
        cf_front = comp.get('cashflow_frontloading', {})
        
        html += f"""
<tr><td>NPV (3年期, 8%折现)</td><td>{fmt_money(trad.get('npv',0))}</td><td><strong>{fmt_money(tr_mode.get('npv',0))}</strong></td><td><span class="badge badge-pass">+{npv_up.get('percentage',0):.1f}%</span></td></tr>
<tr><td>IRR</td><td>{trad.get('irr',0)*100:.2f}%</td><td><strong>{tr_mode.get('irr',0)*100:.2f}%</strong></td><td><span class="badge badge-pass">+{(tr_mode.get('irr',0)-trad.get('irr',0))*100:.2f}pp</span></td></tr>
<tr><td>3年总收入</td><td>{fmt_money(trad.get('total_3year_revenue',0))}</td><td>{fmt_money(tr_mode.get('issue_revenue',0))}</td><td>-</td></tr>
<tr><td>发行时一次性收入</td><td>¥0</td><td><strong>{fmt_money(tr_mode.get('issue_revenue',0))}</strong></td><td>现金流前置化</td></tr>
<tr><td>前12个月现金流占比</td><td>{cf_front.get('traditional_first12_ratio',0):.1f}%</td><td><strong>{cf_front.get('time_right_first12_ratio',0):.1f}%</strong></td><td>前置化改善</td></tr>
</table>

<h3>7.2 现金流时间价值对比</h3>
<div class="info-box">
    <h4>核心洞察</h4>
    <p>传统模式下，酒店需要逐月等待客人入住才能获得收入，现金流分散且不确定。时权ABS模式下，酒店在发行时一次性获得大额资金，相当于将未来3年的收入提前变现。</p>
    <p>这种<strong>现金流前置化</strong>带来多重好处：</p>
    <ul>
        <li>降低资金成本：无需为等待收入而融资</li>
        <li>提升投资能力：可立即用于酒店升级改造</li>
        <li>对冲经营风险：提前锁定收入，减少入住率波动影响</li>
        <li>优化财务报表：改善现金流结构，提升信用评级</li>
    </ul>
</div>

<!-- 第8章: 风险与敏感性 -->
<h2 id="sec-risk">第8章 风险评估与敏感性分析</h2>

<h3>8.1 风险评估</h3>
<table>
<tr><th>风险类别</th><th>得分(1-10)</th><th>等级</th><th>说明</th></tr>
"""
        
        risk = d.get('risk_assessment', {})
        for risk_name, label in [
            ('liquidity_risk', '流动性风险'),
            ('credit_risk', '信用风险'),
            ('market_risk', '市场风险'),
            ('operational_risk', '操作风险'),
            ('legal_regulatory_risk', '法律监管风险'),
        ]:
            r = risk.get(risk_name, {})
            badge = risk_badge(r.get('score', 5))
            html += f"<tr><td>{label}</td><td>{r.get('score',0):.1f}</td>" \
                   f"<td><span class='badge {badge}'>{r.get('level','')}</span></td>" \
                   f"<td>{r.get('description','')}</td></tr>\n"
        
        overall_badge = risk_badge(risk.get('overall_risk_score', 5))
        html += f"""
<tr><td><strong>综合风险评分</strong></td><td><strong>{risk.get('overall_risk_score',0):.1f}</strong></td>
<td><span class="badge {overall_badge}"><strong>{risk.get('overall_level','')}</strong></span></td>
<td>五项风险加权平均</td></tr>
</table>

<h3>8.2 敏感性分析</h3>
<h4>入住率敏感性</h4>
<table>
<tr><th>入住率</th><th>超发倍数</th><th>NPV</th><th>NPV变化</th></tr>
"""
        
        sens = d.get('sensitivity_analysis', {})
        for s in sens.get('occupancy_sensitivity', []):
            badge = 'badge-pass' if s.get('npv_change_pct',0) > -10 else 'badge-warning' if s.get('npv_change_pct',0) > -30 else 'badge-fail'
            html += f"<tr><td>{s['occupancy_rate']*100:.0f}%</td><td>{s['overbooking_multiplier']:.2f}x</td>" \
                   f"<td>{fmt_money(s['npv'])}</td><td><span class='badge {badge}'>{s['npv_change_pct']:+.1f}%</span></td></tr>\n"
        
        html += """
</table>

<h4>折扣率敏感性</h4>
<table>
<tr><th>折现率</th><th>远期折扣因子</th><th>NPV</th><th>NPV变化</th></tr>
"""
        
        for s in sens.get('discount_rate_sensitivity', []):
            badge = 'badge-pass' if s.get('npv_change_pct',0) > -10 else 'badge-warning'
            html += f"<tr><td>{s['discount_rate']*100:.0f}%</td><td>{s['forward_discount']:.3f}</td>" \
                   f"<td>{fmt_money(s['npv'])}</td><td><span class='badge {badge}'>{s['npv_change_pct']:+.1f}%</span></td></tr>\n"
        
        html += """
</table>

<h4>二级市场溢价敏感性</h4>
<table>
<tr><th>市场溢价率</th><th>交易手续费收入</th><th>对NPV影响</th></tr>
"""
        
        for s in sens.get('market_premium_sensitivity', []):
            html += f"<tr><td>{s['market_premium']*100:.0f}%</td><td>{fmt_money(s['trading_fee_income'])}</td>" \
                   f"<td>{fmt_money(s['npv_impact'])}</td></tr>\n"
        
        html += "</table>\n"
        
        # ===== 第9章: 可行性评估 =====
        feas = d.get('feasibility_evaluation', {})
        score_breakdown = feas.get('score_breakdown', {})
        
        feas_badge = 'badge-pass' if feas.get('rating','') == 'A' else 'badge-warning' if feas.get('rating','') == 'B' else 'badge-fail'
        
        html += f"""
<h2 id="sec-feasibility">第9章 可行性评估</h2>

<h3>9.1 综合评分</h3>
<div class="card-grid">
    <div class="card blue">
        <h4>综合评分</h4>
        <div class="big-value">{feas.get('overall_score',0):.1f}/100</div>
        <div class="small-text">满分100分</div>
    </div>
    <div class="card green">
        <h4>项目评级</h4>
        <div class="big-value"><span class="badge {feas_badge}">{feas.get('rating','')}</span></div>
        <div class="small-text">A=优秀 B=良好 C=一般 D=较差</div>
    </div>
    <div class="card purple">
        <h4>信用质量</h4>
        <div class="big-value">{score_breakdown.get('credit_quality',0):.1f}/25</div>
        <div class="small-text">资产池信用水平</div>
    </div>
</div>

<h3>9.2 评分拆解</h3>
<table>
<tr><th>维度</th><th>权重</th><th>得分</th><th>满分</th><th>得分率</th></tr>
<tr><td>信用质量</td><td>30%</td><td>{score_breakdown.get('credit_quality',0):.1f}</td><td>25</td><td>
    <div class="progress-bar"><div class="progress-fill blue" style="width:{score_breakdown.get('credit_quality',0)/25*100:.0f}%">{score_breakdown.get('credit_quality',0)/25*100:.0f}%</div></div>
</td></tr>
<tr><td>收益潜力</td><td>25%</td><td>{score_breakdown.get('profit_potential',0):.1f}</td><td>25</td><td>
    <div class="progress-bar"><div class="progress-fill green" style="width:{score_breakdown.get('profit_potential',0)/25*100:.0f}%">{score_breakdown.get('profit_potential',0)/25*100:.0f}%</div></div>
</td></tr>
<tr><td>风险控制</td><td>25%</td><td>{score_breakdown.get('risk_control',0):.1f}</td><td>25</td><td>
    <div class="progress-bar"><div class="progress-fill orange" style="width:{score_breakdown.get('risk_control',0)/25*100:.0f}%">{score_breakdown.get('risk_control',0)/25*100:.0f}%</div></div>
</td></tr>
<tr><td>技术可行性</td><td>20%</td><td>{score_breakdown.get('technical_feasibility',0):.1f}</td><td>25</td><td>
    <div class="progress-bar"><div class="progress-fill purple" style="width:{score_breakdown.get('technical_feasibility',0)/25*100:.0f}%">{score_breakdown.get('technical_feasibility',0)/25*100:.0f}%</div></div>
</td></tr>
</table>

<h3>9.3 评估结论</h3>
<div class="info-box green">
    <h4>综合评价</h4>
    <p><strong>{feas.get('recommendation','')}</strong></p>
</div>

<h3>9.4 关键成功因素</h3>
<ul>
"""
        
        for factor in feas.get('key_success_factors', []):
            html += f"<li>{factor}</li>\n"
        
        html += """
</ul>

<h3>9.5 关键风险点</h3>
<ul>
"""
        
        for risk_item in feas.get('critical_risks', []):
            html += f"<li>{risk_item}</li>\n"
        
        html += """
</ul>

<!-- 第10章: RWA代币化架构 -->
<h2 id="sec-rwa">第10章 RWA代币化架构</h2>

<h3>10.1 链下架构</h3>
<div class="info-box">
    <h4>SPV（特殊目的载体）</h4>
    <p>在开曼群岛/新加坡注册，实现破产隔离，持有酒店未来住宿订单收益权。</p>
</div>
<div class="info-box">
    <h4>服务商</h4>
    <p>负责时权发行管理、月度现金流归集、违约监控、储备金管理。</p>
</div>

<h3>10.2 链上架构</h3>
<table>
<tr><th>组件</th><th>详情</th></tr>
<tr><td>代币标准</td><td>ERC-3643 (T-REX Protocol)</td></tr>
<tr><td>区块链</td><td>Ethereum / Polygon</td></tr>
<tr><td>预言机</td><td>Chainlink，月度更新时权价格、兑付比例、违约事件</td></tr>
<tr><td>智能合约</td><td>代币合约 + 瀑布分配合约 + 储备金合约 + 触发器合约</td></tr>
</table>

<h3>10.3 代币详情</h3>
<table>
<tr><th>代币名称</th><th>符号</th><th>对应分层</th><th>功能</th></tr>
"""
        
        for token in d['rwa_architecture']['architecture']['on_chain']['tokens']:
            html += f"<tr><td>{token['name']}</td><td>{token['symbol']}</td><td>{token['tranche']}</td><td>收益权+转让权</td></tr>\n"
        
        html += """
</table>

<h3>10.4 时权生命周期</h3>
<ol>
"""
        
        for step in d['rwa_architecture']['smart_contract_logic']['time_right_lifecycle']:
            html += f"<li>{step}</li>\n"
        
        html += """
</ol>

<!-- 可视化分析 -->
<h2 id="sec-viz">可视化分析</h2>
<div class="chart-container">
<img src="abs_visualization_v6_fusion.png" alt="ABS融合分析可视化">
<p><em>图1: 酒店订单时权ABS/RWA融合分析综合可视化图表 (15子图)</em></p>
</div>

<!-- 免责声明 -->
<h2>免责声明与方法论</h2>
<div class="disclaimer">
<p><strong>重要声明：</strong></p>
<ul>
<li>本报告基于历史价格数据的统计分析，不构成投资建议。</li>
<li>违约概率(PD)由价格波动率通过Merton模型推导，假设期限结构稳定。</li>
<li>蒙特卡洛模拟使用Gaussian Copula，假设相关性结构在压力情景下不变。</li>
<li>酒店行业具有特殊性，历史4个月数据可能不足以捕捉完整周期风险。</li>
<li>实际ABS发行需经过监管机构审批、律师事务所尽职调查、评级机构独立评估。</li>
<li>时权ABS模式涉及金融创新，相关法规尚在完善中，存在政策不确定性。</li>
</ul>
<p><strong>方法论：</strong>"""
        
        html += d['report_metadata']['methodology']
        html += f"""</p>
</div>

</div>

<div class="footer">
<p>酒店订单时权ABS/RWA融合分析报告 V6-Fusion-Enhanced</p>
<p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</div>

</div>
</body>
</html>
"""
        
        output_path = f'{self.work_dir}/output/酒店订单时权ABS融合分析报告_v6_fusion.html'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"  HTML报告已保存: {output_path}")
        return output_path
    
    def generate_all(self):
        """生成所有输出"""
        self.generate_visualization()
        self.generate_html_report()
        print("\n所有融合版报告生成完成！")


def main():
    gen = ABSFusionReportGenerator()
    gen.generate_all()


if __name__ == '__main__':
    main()
