"""
酒店订单ABS/RWA专业报告生成器 V6

生成投行/评级机构级别的分析报告：
- 资产池特征表
- 分层结构表
- 现金流瀑布表
- 蒙特卡洛损失分布图
- 压力测试结果表
- RWA架构图
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


class ABSReportGenerator:
    """ABS专业报告生成器"""
    
    def __init__(self, report_json_path=None, work_dir=None):
        self.work_dir = work_dir or r'C:\Users\weida\Desktop\酒店研究'
        
        if report_json_path is None:
            report_json_path = f'{self.work_dir}/output/abs_report_v6.json'
        
        with open(report_json_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
    
    def generate_visualization(self):
        """生成专业可视化图表"""
        print("\n生成可视化图表...")
        
        fig = plt.figure(figsize=(24, 32))
        gs = gridspec.GridSpec(4, 3, figure=fig, hspace=0.35, wspace=0.30)
        
        # ===== 第1行 =====
        
        # 1.1 资产池等级分布
        ax1 = fig.add_subplot(gs[0, 0])
        levels = self.data['asset_pool']['statistics']['level_diversity']
        colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c']
        wedges, texts, autotexts = ax1.pie(
            levels.values(), labels=levels.keys(), autopct='%1.1f%%',
            colors=colors[:len(levels)], startangle=90
        )
        ax1.set_title('资产池等级分布', fontsize=14, fontweight='bold')
        
        # 1.2 资产池信用分布
        ax2 = fig.add_subplot(gs[0, 1])
        ratings = self.data['asset_pool']['statistics']['rating_distribution']
        rating_order = ['AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC', 'CC', 'C']
        rating_counts = {r: ratings.get(r, 0) for r in rating_order if r in ratings}
        bars = ax2.bar(rating_counts.keys(), rating_counts.values(), color='#34495e')
        ax2.set_xlabel('信用评级')
        ax2.set_ylabel('酒店数量')
        ax2.set_title('资产池信用评级分布', fontsize=14, fontweight='bold')
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}', ha='center', va='bottom', fontsize=9)
        
        # 1.3 分层结构图
        ax3 = fig.add_subplot(gs[0, 2])
        tranches = self.data['tranche_structure']
        names = [t['name'] for t in tranches]
        sizes = [t['size_pct'] * 100 for t in tranches]
        colors_t = ['#27ae60', '#f39c12', '#e74c3c', '#9b59b6']
        bars = ax3.barh(names, sizes, color=colors_t)
        ax3.set_xlabel('占比 (%)')
        ax3.set_title('ABS分层结构', fontsize=14, fontweight='bold')
        for i, (bar, size) in enumerate(zip(bars, sizes)):
            ax3.text(size + 1, i, f'{size:.1f}%', va='center', fontsize=10)
        
        # ===== 第2行 =====
        
        # 2.1 各分层预期损失与信用支持
        ax4 = fig.add_subplot(gs[1, 0])
        el_values = [t['expected_loss'] * 100 for t in tranches]
        cs_values = [t['credit_support_pct'] * 100 for t in tranches]
        x = np.arange(len(names))
        width = 0.35
        bars1 = ax4.bar(x - width/2, el_values, width, label='预期损失率', color='#e74c3c')
        bars2 = ax4.bar(x + width/2, cs_values, width, label='信用支持', color='#27ae60')
        ax4.set_ylabel('百分比 (%)')
        ax4.set_title('分层预期损失 vs 信用支持', fontsize=14, fontweight='bold')
        ax4.set_xticks(x)
        ax4.set_xticklabels(names)
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        # 2.2 蒙特卡洛损失分布 - Senior
        ax5 = fig.add_subplot(gs[1, 1])
        mc = self.data['monte_carlo']['tranche_analysis']
        if 'Senior' in mc:
            hist = mc['Senior']['loss_histogram']
            bins = mc['Senior']['loss_bins']
            bin_centers = [(bins[i] + bins[i+1])/2 * 100 for i in range(len(hist))]
            ax5.bar(bin_centers, hist, width=bins[1]*100*0.8, color='#3498db', alpha=0.7, edgecolor='white')
            ax5.axvline(mc['Senior']['var_95']*100, color='red', linestyle='--', label=f"VaR 95%: {mc['Senior']['var_95']*100:.2f}%")
            ax5.axvline(mc['Senior']['mean_loss_rate']*100, color='green', linestyle='-', label=f"EL: {mc['Senior']['mean_loss_rate']*100:.2f}%")
            ax5.set_xlabel('损失率 (%)')
            ax5.set_ylabel('频数')
            ax5.set_title('Senior层损失分布 (10,000路径)', fontsize=14, fontweight='bold')
            ax5.legend()
            ax5.grid(True, alpha=0.3)
        
        # 2.3 蒙特卡洛损失分布 - Mezzanine
        ax6 = fig.add_subplot(gs[1, 2])
        if 'Mezzanine' in mc:
            hist = mc['Mezzanine']['loss_histogram']
            bins = mc['Mezzanine']['loss_bins']
            bin_centers = [(bins[i] + bins[i+1])/2 * 100 for i in range(len(hist))]
            ax6.bar(bin_centers, hist, width=bins[1]*100*0.8, color='#f39c12', alpha=0.7, edgecolor='white')
            ax6.axvline(mc['Mezzanine']['var_95']*100, color='red', linestyle='--', label=f"VaR 95%: {mc['Mezzanine']['var_95']*100:.2f}%")
            ax6.axvline(mc['Mezzanine']['mean_loss_rate']*100, color='green', linestyle='-', label=f"EL: {mc['Mezzanine']['mean_loss_rate']*100:.2f}%")
            ax6.set_xlabel('损失率 (%)')
            ax6.set_ylabel('频数')
            ax6.set_title('Mezzanine层损失分布 (10,000路径)', fontsize=14, fontweight='bold')
            ax6.legend()
            ax6.grid(True, alpha=0.3)
        
        # ===== 第3行 =====
        
        # 3.1 压力测试对比
        ax7 = fig.add_subplot(gs[2, 0])
        stress = self.data['monte_carlo']['stress_test']
        scenarios = list(stress.keys())
        senior_el = [stress[s]['Senior']['mean_loss_rate'] * 100 for s in scenarios]
        senior_var95 = [stress[s]['Senior']['var_95'] * 100 for s in scenarios]
        x = np.arange(len(scenarios))
        width = 0.35
        ax7.bar(x - width/2, senior_el, width, label='预期损失', color='#3498db')
        ax7.bar(x + width/2, senior_var95, width, label='VaR 95%', color='#e74c3c')
        ax7.set_ylabel('损失率 (%)')
        ax7.set_title('Senior层压力测试对比', fontsize=14, fontweight='bold')
        ax7.set_xticks(x)
        ax7.set_xticklabels(scenarios, rotation=15, ha='right')
        ax7.legend()
        ax7.grid(True, alpha=0.3)
        
        # 3.2 基准情景现金流瀑布
        ax8 = fig.add_subplot(gs[2, 1])
        wf = self.data['baseline_waterfall']['monthly_summary']
        months = [w['month'] for w in wf]
        senior_bal = [w['Senior_balance_end'] / 1e6 for w in wf]
        mezz_bal = [w['Mezzanine_balance_end'] / 1e6 for w in wf]
        junior_bal = [w['Junior_balance_end'] / 1e6 for w in wf]
        
        ax8.fill_between(months, 0, senior_bal, label='Senior', color='#27ae60', alpha=0.8)
        ax8.fill_between(months, senior_bal, [s+m for s,m in zip(senior_bal, mezz_bal)], label='Mezzanine', color='#f39c12', alpha=0.8)
        ax8.fill_between(months, [s+m for s,m in zip(senior_bal, mezz_bal)], 
                        [s+m+j for s,m,j in zip(senior_bal, mezz_bal, junior_bal)], label='Junior', color='#e74c3c', alpha=0.8)
        ax8.set_xlabel('月份')
        ax8.set_ylabel('余额 (百万元)')
        ax8.set_title('基准情景分层余额变化', fontsize=14, fontweight='bold')
        ax8.legend()
        ax8.grid(True, alpha=0.3)
        
        # 3.3 资产池地理分散度
        ax9 = fig.add_subplot(gs[2, 2])
        # 从酒店数据中提取区域分布（简化：用district字段）
        hotels = self.data['asset_pool']['hotels']
        districts = {}
        for h in hotels:
            d = h.get('district', 'unknown')
            districts[d] = districts.get(d, 0) + 1
        
        # 取前10个区域
        top_districts = dict(sorted(districts.items(), key=lambda x: x[1], reverse=True)[:10])
        ax9.barh(list(top_districts.keys()), list(top_districts.values()), color='#34495e')
        ax9.set_xlabel('酒店数量')
        ax9.set_title('资产池地理分布 (Top 10区域)', fontsize=14, fontweight='bold')
        ax9.grid(True, alpha=0.3)
        
        # ===== 第4行 =====
        
        # 4.1 各分层隐含评级对比
        ax10 = fig.add_subplot(gs[3, 0])
        tranche_names = list(mc.keys())
        ratings = [mc[t]['implied_rating'] for t in tranche_names]
        rating_scores = {'Aaa': 9, 'Aa': 8, 'A': 7, 'Baa': 6, 'Ba': 5, 'B': 4, 'Caa': 3, 'Ca-C': 2, 'NR': 1}
        scores = [rating_scores.get(r, 1) for r in ratings]
        colors_r = ['#27ae60' if s >= 7 else '#f39c12' if s >= 5 else '#e74c3c' for s in scores]
        bars = ax10.barh(tranche_names, scores, color=colors_r)
        ax10.set_xlabel('评级得分 (9=Aaa, 1=NR)')
        ax10.set_title('蒙特卡洛隐含评级', fontsize=14, fontweight='bold')
        for i, (bar, rating) in enumerate(zip(bars, ratings)):
            ax10.text(scores[i] + 0.1, i, rating, va='center', fontsize=10)
        ax10.set_xlim(0, 10)
        
        # 4.2 信用增级结构
        ax11 = fig.add_subplot(gs[3, 1])
        ce = self.data['credit_enhancement']
        ce_items = {
            '超额抵押\n(OC)': ce['overcollateralization_pct'] * 100,
            '储备金': ce['reserve_target_pct'] * 100,
            '超额利差\n(12月)': ce['excess_spread_buffer_12m'] * 100,
            '次级保护\n(Senior)': ce['senior_credit_support'] * 100,
        }
        bars = ax11.bar(ce_items.keys(), ce_items.values(), color=['#3498db', '#2ecc71', '#f39c12', '#e74c3c'])
        ax11.set_ylabel('百分比 (%)')
        ax11.set_title('信用增级结构', fontsize=14, fontweight='bold')
        for bar in bars:
            height = bar.get_height()
            ax11.text(bar.get_x() + bar.get_width()/2., height,
                     f'{height:.1f}%', ha='center', va='bottom', fontsize=10)
        
        # 4.3 PD分布
        ax12 = fig.add_subplot(gs[3, 2])
        pds = [h['pd'] * 100 for h in hotels]
        ax12.hist(pds, bins=20, color='#34495e', alpha=0.7, edgecolor='white')
        ax12.axvline(self.data['asset_pool']['statistics']['wtd_pd'] * 100, 
                    color='red', linestyle='--', linewidth=2,
                    label=f"加权平均PD: {self.data['asset_pool']['statistics']['wtd_pd']*100:.2f}%")
        ax12.set_xlabel('违约概率 PD (%)')
        ax12.set_ylabel('酒店数量')
        ax12.set_title('资产池PD分布', fontsize=14, fontweight='bold')
        ax12.legend()
        ax12.grid(True, alpha=0.3)
        
        plt.savefig(f'{self.work_dir}/output/abs_visualization_v6.png', dpi=200, bbox_inches='tight')
        print(f"  图表已保存: {self.work_dir}/output/abs_visualization_v6.png")
        plt.close()
    
    def generate_html_report(self):
        """生成专业HTML报告"""
        print("\n生成HTML报告...")
        
        d = self.data
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>酒店订单ABS/RWA资产证券化专业分析报告</title>
<style>
body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 1400px; margin: 0 auto; padding: 20px; background: #f8f9fa; }}
.container {{ background: white; padding: 40px; box-shadow: 0 2px 20px rgba(0,0,0,0.08); border-radius: 8px; }}
h1 {{ color: #1a252f; text-align: center; border-bottom: 4px solid #2c3e50; padding-bottom: 20px; margin-bottom: 30px; font-size: 28px; }}
h2 {{ color: #2c3e50; border-left: 5px solid #3498db; padding-left: 15px; margin-top: 40px; font-size: 20px; background: #f8f9fa; padding: 10px 15px; }}
h3 {{ color: #34495e; margin-top: 25px; font-size: 16px; }}
.summary {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 8px; margin: 20px 0; }}
.summary h3 {{ color: white; margin-top: 0; }}
table {{ width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 13px; }}
th, td {{ border: 1px solid #e0e0e0; padding: 10px 12px; text-align: left; }}
th {{ background: #2c3e50; color: white; font-weight: 600; }}
tr:nth-child(even) {{ background: #f8f9fa; }}
tr:hover {{ background: #e8f4f8; }}
.metric {{ display: inline-block; margin: 8px; padding: 18px 22px; background: white; border-radius: 8px; border-left: 4px solid #3498db; box-shadow: 0 2px 8px rgba(0,0,0,0.08); min-width: 140px; }}
.metric-value {{ font-size: 22px; font-weight: bold; color: #2c3e50; }}
.metric-label {{ font-size: 11px; color: #7f8c8d; margin-top: 4px; }}
.pass {{ color: #27ae60; font-weight: bold; }}
.fail {{ color: #e74c3c; font-weight: bold; }}
.warning {{ color: #f39c12; font-weight: bold; }}
.chart-container {{ text-align: center; margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 8px; }}
.chart-container img {{ max-width: 100%; height: auto; border-radius: 4px; }}
.rwa-box {{ background: #f0f7ff; border: 1px solid #b3d9ff; padding: 20px; border-radius: 8px; margin: 15px 0; }}
.rwa-box h4 {{ color: #0066cc; margin-top: 0; }}
.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
.footer {{ text-align: center; margin-top: 50px; padding-top: 20px; border-top: 2px solid #ecf0f1; color: #7f8c8d; font-size: 12px; }}
.highlight {{ background: #fff3cd; padding: 2px 6px; border-radius: 3px; }}
</style>
</head>
<body>
<div class="container">
<h1>酒店订单ABS/RWA资产证券化<br>专业分析报告</h1>
<p style="text-align:center;color:#7f8c8d;margin-top:-15px;">
    {d['report_metadata']['title']} | 版本: {d['report_metadata']['version']} | 
    日期: {d['report_metadata']['date']}<br>
    方法论: {d['report_metadata']['methodology']}
</p>

<h2>执行摘要</h2>
<div class="summary">
    <div style="display:flex;flex-wrap:wrap;justify-content:space-around;margin-top:15px;">
        <div class="metric"><div class="metric-value">{len(d['asset_pool']['hotels'])}</div><div class="metric-label">资产池酒店数</div></div>
        <div class="metric"><div class="metric-value">¥{d['asset_pool']['statistics']['total_notional']/1e8:.2f}亿</div><div class="metric-label">资产池总面值</div></div>
        <div class="metric"><div class="metric-value">{d['asset_pool']['statistics']['wtd_pd']*100:.2f}%</div><div class="metric-label">加权平均PD</div></div>
        <div class="metric"><div class="metric-value">{d['asset_pool']['statistics']['wtd_el']*100:.2f}%</div><div class="metric-label">加权平均EL</div></div>
        <div class="metric"><div class="metric-value">{d['monte_carlo']['tranche_analysis']['Senior']['implied_rating']}</div><div class="metric-label">Senior隐含评级</div></div>
    </div>
</div>

<h2>1. 资产池特征</h2>
<h3>1.1 基本规模</h3>
<table>
<tr><th>指标</th><th>数值</th><th>指标</th><th>数值</th></tr>
<tr><td>酒店数量</td><td>{d['asset_pool']['statistics']['pool_size']} 家</td><td>总面值</td><td>¥{d['asset_pool']['statistics']['total_notional']:,.0f}</td></tr>
<tr><td>平均面值</td><td>¥{d['asset_pool']['statistics']['avg_hotel_price']:,.0f}</td><td>面值中位数</td><td>¥{d['asset_pool']['statistics']['median_hotel_price']:,.0f}</td></tr>
<tr><td>覆盖区县数</td><td>{d['asset_pool']['statistics']['district_diversity']} 个</td><td>地区HHI</td><td>{d['asset_pool']['statistics']['district_herfindahl']:.3f}</td></tr>
<tr><td>Top 5集中度</td><td>{d['asset_pool']['statistics']['top5_concentration']*100:.1f}%</td><td>Top 10集中度</td><td>{d['asset_pool']['statistics']['top10_concentration']*100:.1f}%</td></tr>
</table>

<h3>1.2 信用分布</h3>
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
        
        html += f"""
</table>

<h3>1.3 前10大借款人</h3>
<table>
<tr><th>排名</th><th>酒店代码</th><th>酒店名称</th><th>等级</th><th>面值</th><th>评级</th><th>PD</th></tr>
"""
        
        top10 = sorted(d['asset_pool']['hotels'], key=lambda x: x['avgPrice'], reverse=True)[:10]
        for i, h in enumerate(top10, 1):
            html += f"<tr><td>{i}</td><td>{h['hotelCode']}</td><td>{h['hotelName'][:25]}</td>" \
                   f"<td>{h['hotelLevel']}</td><td>¥{h['avgPrice']:,.0f}</td>" \
                   f"<td>{h['rating']}</td><td>{h['pd']*100:.2f}%</td></tr>\n"
        
        html += """
</table>

<h2>2. ABS分层结构</h2>
<h3>2.1 分层设计</h3>
<table>
<tr><th>层级</th><th>规模占比</th><th>规模(元)</th><th>票息(年化)</th><th>目标评级</th><th>信用支持</th><th>预期损失</th></tr>
"""
        
        for t in d['tranche_structure']:
            html += f"<tr><td><strong>{t['name']}</strong></td><td>{t['size_pct']*100:.1f}%</td>" \
                   f"<td>¥{t['notional']:,.0f}</td><td>{t['coupon_annual']*100:.2f}%</td>" \
                   f"<td>{t['target_rating']}</td><td>{t['credit_support_pct']*100:.1f}%</td>" \
                   f"<td>{t['expected_loss']*100:.2f}%</td></tr>\n"
        
        ce = d['credit_enhancement']
        html += f"""
</table>

<h3>2.2 信用增级机制</h3>
<table>
<tr><th>增级机制</th><th>比例</th><th>金额</th></tr>
<tr><td>超额抵押 (OC)</td><td>{ce['overcollateralization_pct']*100:.1f}%</td><td>¥{ce['overcollateralization_amount']:,.0f}</td></tr>
<tr><td>储备金账户</td><td>{ce['reserve_target_pct']*100:.1f}%</td><td>¥{ce['reserve_target_amount']:,.0f}</td></tr>
<tr><td>超额利差 (12月)</td><td>{ce['excess_spread_buffer_12m']*100:.1f}%</td><td>-</td></tr>
<tr><td>Senior次级保护</td><td>{ce['senior_credit_support']*100:.1f}%</td><td>-</td></tr>
<tr><td><strong>总信用支持</strong></td><td><strong>{ce['total_credit_support_pct']*100:.1f}%</strong></td><td><strong>¥{ce['total_credit_support_amount']:,.0f}</strong></td></tr>
</table>

<h2>3. 蒙特卡洛模拟分析</h2>
<p>基于 <strong>{d['monte_carlo']['n_paths']:,}</strong> 条蒙特卡洛路径 × <strong>{d['monte_carlo']['n_months']}</strong> 期的违约模拟，使用 Gaussian Copula 模型。</p>

<h3>3.1 分层损失统计</h3>
<table>
<tr><th>分层</th><th>预期损失(EL)</th><th>VaR 95%</th><th>VaR 99%</th><th>CVaR 95%</th><th>损失概率</th><th>隐含评级</th></tr>
"""
        
        for name, stats in d['monte_carlo']['tranche_analysis'].items():
            rating_color = 'pass' if stats['implied_rating'] in ['Aaa', 'Aa', 'A'] else 'warning' if stats['implied_rating'] in ['Baa'] else 'fail'
            html += f"<tr><td><strong>{name}</strong></td><td>{stats['mean_loss_rate']*100:.2f}%</td>" \
                   f"<td>{stats['var_95']*100:.2f}%</td><td>{stats['var_99']*100:.2f}%</td>" \
                   f"<td>{stats['cvar_95']*100:.2f}%</td><td>{stats['prob_any_loss']*100:.1f}%</td>" \
                   f"<td class='{rating_color}'>{stats['implied_rating']}</td></tr>\n"
        
        html += """
</table>

<h3>3.2 压力测试对比</h3>
<table>
<tr><th>情景</th><th colspan="4">Senior层</th><th colspan="4">Mezzanine层</th></tr>
<tr><th></th><th>EL</th><th>VaR95</th><th>VaR99</th><th>评级</th><th>EL</th><th>VaR95</th><th>VaR99</th><th>评级</th></tr>
"""
        
        for scenario, stats in d['monte_carlo']['stress_test'].items():
            s = stats.get('Senior', {})
            m = stats.get('Mezzanine', {})
            html += f"<tr><td><strong>{scenario}</strong></td>" \
                   f"<td>{s.get('mean_loss_rate', 0)*100:.2f}%</td><td>{s.get('var_95', 0)*100:.2f}%</td>" \
                   f"<td>{s.get('var_99', 0)*100:.2f}%</td><td>{s.get('implied_rating', 'N/A')}</td>" \
                   f"<td>{m.get('mean_loss_rate', 0)*100:.2f}%</td><td>{m.get('var_95', 0)*100:.2f}%</td>" \
                   f"<td>{m.get('var_99', 0)*100:.2f}%</td><td>{m.get('implied_rating', 'N/A')}</td></tr>\n"
        
        html += """
</table>

<h2>4. RWA代币化架构</h2>
<div class="rwa-box">
<h4>链下架构</h4>
<ul>
<li><strong>SPV（特殊目的载体）</strong>：{d['rwa_architecture']['architecture']['off_chain']['spv']['jurisdiction']}注册，破产隔离，持有酒店未来住宿订单收益权</li>
<li><strong>服务商</strong>：负责月度现金流归集、违约监控、储备金管理</li>
<li><strong>受托人</strong>：代表投资者利益，监督SPV运营，执行触发器</li>
</ul>
</div>

<div class="rwa-box">
<h4>链上架构</h4>
<ul>
<li><strong>代币标准</strong>：{d['rwa_architecture']['architecture']['on_chain']['token_standard']}</li>
<li><strong>区块链</strong>：{d['rwa_architecture']['architecture']['on_chain']['blockchain']}</li>
<li><strong>代币种类</strong>：{len(d['rwa_architecture']['architecture']['on_chain']['tokens'])} 种（每档分层一种）</li>
<li><strong>预言机</strong>：{d['rwa_architecture']['architecture']['on_chain']['oracle']['provider']}，月度更新</li>
<li><strong>智能合约</strong>：代币合约 + 瀑布分配合约 + 储备金合约 + 触发器合约</li>
</ul>
</div>

<div class="rwa-box">
<h4>智能合约触发器逻辑</h4>
<ul>
"""
        
        for trigger in d['rwa_architecture']['smart_contract_logic']['triggers']:
            html += f"<li>{trigger}</li>\n"
        
        html += f"""
</ul>
</div>

<h2>5. 可视化分析</h2>
<div class="chart-container">
<img src="abs_visualization_v6.png" alt="ABS分析可视化">
<p><em>图1: 酒店订单ABS/RWA分析综合可视化图表</em></p>
</div>

<h2>6. 免责声明与方法论</h2>
<div style="background:#fff3cd;padding:15px;border-radius:8px;font-size:12px;color:#856404;">
<p><strong>重要声明：</strong></p>
<ul>
<li>本报告基于历史价格数据的统计分析，不构成投资建议。</li>
<li>违约概率(PD)由价格波动率通过Merton模型推导，假设期限结构稳定。</li>
<li>蒙特卡洛模拟使用Gaussian Copula，假设相关性结构在压力情景下不变。</li>
<li>酒店行业具有特殊性，历史4个月数据可能不足以捕捉完整周期风险。</li>
<li>实际ABS发行需经过监管机构审批、律师事务所尽职调查、评级机构独立评估。</li>
</ul>
<p><strong>方法论：</strong>{d['report_metadata']['methodology']}</p>
</div>

<div class="footer">
<p>酒店订单ABS/RWA资产证券化专业分析报告 V6</p>
<p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</div>
</div>
</body>
</html>
"""
        
        output_path = f'{self.work_dir}/output/酒店订单ABS专业分析报告_v6.html'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"  HTML报告已保存: {output_path}")
        return output_path
    
    def generate_all(self):
        """生成所有输出"""
        self.generate_visualization()
        self.generate_html_report()
        print("\n所有报告生成完成！")


def main():
    gen = ABSReportGenerator()
    gen.generate_all()


if __name__ == '__main__':
    main()
