"""
酒店订单时权ABS专业报告生成器 V7

生成投行/评级机构级别的分析报告：
- 时权池特征（超发比例、物理间夜 vs 发行间夜）
- 分层结构表（含兑付方式设计）
- 三方收益分析图
- 蒙特卡洛损失分布图
- 压力测试结果表
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


class TimeRightABSReportGenerator:
    """时权ABS专业报告生成器"""
    
    def __init__(self, report_json_path=None, work_dir=None):
        self.work_dir = work_dir or r'C:\Users\weida\Desktop\酒店研究'
        if report_json_path is None:
            report_json_path = f'{self.work_dir}/output/time_right_abs_report_v7.json'
        
        with open(report_json_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
    
    def generate_visualization(self):
        print("\n生成可视化图表...")
        
        fig = plt.figure(figsize=(24, 32))
        gs = gridspec.GridSpec(4, 3, figure=fig, hspace=0.35, wspace=0.30)
        
        d = self.data
        pool_stats = d['time_right_pool']['statistics']
        tranches = d['tranche_structure']
        names = [t['name'] for t in tranches]
        mc = d['monte_carlo']['tranche_analysis']
        tp = d['three_party_analysis']
        
        # 1.1 时权池超发结构
        ax1 = fig.add_subplot(gs[0, 0])
        labels = ['物理间夜', '超发间夜']
        physical = pool_stats['total_physical_rights']
        issued = pool_stats['total_rights']
        overbooking = issued - physical
        sizes = [physical, overbooking]
        colors = ['#3498db', '#e74c3c']
        wedges, texts, autotexts = ax1.pie(
            sizes, labels=labels, autopct='%1.1f%%',
            colors=colors, startangle=90
        )
        ax1.set_title(f'时权超发结构\n(超发比例: {pool_stats["overbooking_ratio"]:.2f}x)', 
                     fontsize=14, fontweight='bold')
        
        # 1.2 资产池等级分布
        ax2 = fig.add_subplot(gs[0, 1])
        levels = pool_stats['level_diversity']
        colors_l = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c']
        ax2.pie(levels.values(), labels=levels.keys(), autopct='%1.1f%%',
               colors=colors_l[:len(levels)], startangle=90)
        ax2.set_title('资产池等级分布', fontsize=14, fontweight='bold')
        
        # 1.3 分层结构
        ax3 = fig.add_subplot(gs[0, 2])
        sizes_t = [t['size_pct'] * 100 for t in tranches]
        colors_t = ['#27ae60', '#f39c12', '#e74c3c', '#9b59b6']
        bars = ax3.barh(names, sizes_t, color=colors_t)
        ax3.set_xlabel('占比 (%)')
        ax3.set_title('时权ABS分层结构', fontsize=14, fontweight='bold')
        for i, (bar, size) in enumerate(zip(bars, sizes_t)):
            ax3.text(size + 1, i, f'{size:.1f}%', va='center', fontsize=10)
        
        # 2.1 兑付方式设计
        ax4 = fig.add_subplot(gs[1, 0])
        cash_pcts = [t['cash_redemption_pct'] * 100 for t in tranches]
        physical_pcts = [t['physical_redemption_pct'] * 100 for t in tranches]
        x = np.arange(len(names))
        width = 0.35
        ax4.bar(x - width/2, cash_pcts, width, label='现金兑付', color='#3498db')
        ax4.bar(x + width/2, physical_pcts, width, label='实物兑付', color='#e74c3c')
        ax4.set_ylabel('比例 (%)')
        ax4.set_title('各层兑付方式设计', fontsize=14, fontweight='bold')
        ax4.set_xticks(x)
        ax4.set_xticklabels(names)
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        # 2.2 三方收益对比
        ax5 = fig.add_subplot(gs[1, 1])
        parties = ['酒店方', '平台方', '投资者方']
        profits = [tp['hotel']['profit'], tp['platform']['profit'], tp['investors']['net_return']]
        colors_p = ['#2ecc71', '#f39c12', '#9b59b6']
        bars = ax5.bar(parties, profits, color=colors_p)
        ax5.set_ylabel('收益 (元)')
        ax5.set_title('三方收益分析', fontsize=14, fontweight='bold')
        for bar in bars:
            height = bar.get_height()
            ax5.text(bar.get_x() + bar.get_width()/2., height,
                    f'¥{height:,.0f}', ha='center', va='bottom', fontsize=10)
        
        # 2.3 兑付成本对比（现金 vs 实物）
        ax6 = fig.add_subplot(gs[1, 2])
        cash_costs = []
        physical_costs = []
        for t in tranches:
            name = t['name']
            redemption = tp['investors']['by_tranche'].get(name, {})
            cash_costs.append(redemption.get('cash_cost', 0) / 1e6)
            physical_costs.append(redemption.get('physical_cost', 0) / 1e6)
        
        x = np.arange(len(names))
        ax6.bar(x - width/2, cash_costs, width, label='现金兑付成本', color='#3498db')
        ax6.bar(x + width/2, physical_costs, width, label='实物兑付成本', color='#e74c3c')
        ax6.set_ylabel('成本 (百万元)')
        ax6.set_title('各层兑付成本对比', fontsize=14, fontweight='bold')
        ax6.set_xticks(x)
        ax6.set_xticklabels(names)
        ax6.legend()
        ax6.grid(True, alpha=0.3)
        
        # 3.1 蒙特卡洛 Senior 损失分布
        ax7 = fig.add_subplot(gs[2, 0])
        if 'Senior' in mc:
            hist = mc['Senior']['loss_histogram']
            bins = mc['Senior']['loss_bins']
            bin_centers = [(bins[i] + bins[i+1])/2 * 100 for i in range(len(hist))]
            ax7.bar(bin_centers, hist, width=bins[1]*100*0.8, color='#3498db', alpha=0.7)
            ax7.axvline(mc['Senior']['var_95']*100, color='red', linestyle='--', 
                       label=f"VaR 95%: {mc['Senior']['var_95']*100:.2f}%")
            ax7.axvline(mc['Senior']['mean_loss_rate']*100, color='green', linestyle='-',
                       label=f"EL: {mc['Senior']['mean_loss_rate']*100:.2f}%")
            ax7.set_xlabel('损失率 (%)')
            ax7.set_ylabel('频数')
            ax7.set_title('Senior层损失分布', fontsize=14, fontweight='bold')
            ax7.legend()
            ax7.grid(True, alpha=0.3)
        
        # 3.2 压力测试对比
        ax8 = fig.add_subplot(gs[2, 1])
        stress = d['monte_carlo']['stress_test']
        scenarios = list(stress.keys())
        senior_el = [stress[s]['Senior']['mean_loss_rate'] * 100 for s in scenarios]
        senior_var95 = [stress[s]['Senior']['var_95'] * 100 for s in scenarios]
        x = np.arange(len(scenarios))
        ax8.bar(x - width/2, senior_el, width, label='预期损失', color='#3498db')
        ax8.bar(x + width/2, senior_var95, width, label='VaR 95%', color='#e74c3c')
        ax8.set_ylabel('损失率 (%)')
        ax8.set_title('Senior层压力测试', fontsize=14, fontweight='bold')
        ax8.set_xticks(x)
        ax8.set_xticklabels(scenarios, rotation=15, ha='right')
        ax8.legend()
        ax8.grid(True, alpha=0.3)
        
        # 3.3 信用分布
        ax9 = fig.add_subplot(gs[2, 2])
        ratings = pool_stats['rating_distribution']
        rating_order = ['AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC', 'CC', 'C']
        rating_counts = {r: ratings.get(r, 0) for r in rating_order if r in ratings}
        bars = ax9.bar(rating_counts.keys(), rating_counts.values(), color='#34495e')
        ax9.set_xlabel('信用评级')
        ax9.set_ylabel('酒店数量')
        ax9.set_title('资产池信用评级分布', fontsize=14, fontweight='bold')
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax9.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}', ha='center', va='bottom', fontsize=9)
        
        # 4.1 隐含评级
        ax10 = fig.add_subplot(gs[3, 0])
        tranche_names = list(mc.keys())
        ratings_imp = [mc[t]['implied_rating'] for t in tranche_names]
        rating_scores = {'Aaa': 9, 'Aa': 8, 'A': 7, 'Baa': 6, 'Ba': 5, 'B': 4, 'Caa': 3, 'Ca-C': 2, 'NR': 1}
        scores = [rating_scores.get(r, 1) for r in ratings_imp]
        colors_r = ['#27ae60' if s >= 7 else '#f39c12' if s >= 5 else '#e74c3c' for s in scores]
        bars = ax10.barh(tranche_names, scores, color=colors_r)
        ax10.set_xlabel('评级得分')
        ax10.set_title('蒙特卡洛隐含评级', fontsize=14, fontweight='bold')
        for i, (bar, rating) in enumerate(zip(bars, ratings_imp)):
            ax10.text(scores[i] + 0.1, i, rating, va='center', fontsize=10)
        ax10.set_xlim(0, 10)
        
        # 4.2 信用增级结构
        ax11 = fig.add_subplot(gs[3, 1])
        ce = d['credit_enhancement']
        ce_items = {
            '超额抵押': ce['overcollateralization_pct'] * 100,
            '储备金': ce['reserve_target_pct'] * 100,
            '超额利差': ce['excess_spread_buffer_12m'] * 100,
            '次级保护': ce['senior_credit_support'] * 100,
        }
        bars = ax11.bar(ce_items.keys(), ce_items.values(), 
                       color=['#3498db', '#2ecc71', '#f39c12', '#e74c3c'])
        ax11.set_ylabel('百分比 (%)')
        ax11.set_title('信用增级结构', fontsize=14, fontweight='bold')
        for bar in bars:
            height = bar.get_height()
            ax11.text(bar.get_x() + bar.get_width()/2., height,
                     f'{height:.1f}%', ha='center', va='bottom', fontsize=10)
        
        # 4.3 PD分布
        ax12 = fig.add_subplot(gs[3, 2])
        hotels = d['time_right_pool']['hotels']
        pds = [h['pd'] * 100 for h in hotels]
        ax12.hist(pds, bins=20, color='#34495e', alpha=0.7, edgecolor='white')
        ax12.axvline(pool_stats['wtd_pd'] * 100, color='red', linestyle='--', linewidth=2,
                    label=f"加权平均PD: {pool_stats['wtd_pd']*100:.2f}%")
        ax12.set_xlabel('违约概率 PD (%)')
        ax12.set_ylabel('酒店数量')
        ax12.set_title('资产池PD分布', fontsize=14, fontweight='bold')
        ax12.legend()
        ax12.grid(True, alpha=0.3)
        
        plt.savefig(f'{self.work_dir}/output/time_right_abs_v7.png', dpi=200, bbox_inches='tight')
        print(f"  图表已保存: {self.work_dir}/output/time_right_abs_v7.png")
        plt.close()
    
    def generate_html_report(self):
        print("\n生成HTML报告...")
        d = self.data
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>酒店订单时权ABS/RWA资产证券化分析报告 V7</title>
<style>
body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 1400px; margin: 0 auto; padding: 20px; background: #f8f9fa; }}
.container {{ background: white; padding: 40px; box-shadow: 0 2px 20px rgba(0,0,0,0.08); border-radius: 8px; }}
h1 {{ color: #1a252f; text-align: center; border-bottom: 4px solid #2c3e50; padding-bottom: 20px; margin-bottom: 30px; font-size: 28px; }}
h2 {{ color: #2c3e50; border-left: 5px solid #3498db; padding-left: 15px; margin-top: 40px; font-size: 20px; background: #f8f9fa; padding: 10px 15px; }}
.innovation-box {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 8px; margin: 20px 0; }}
table {{ width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 13px; }}
th, td {{ border: 1px solid #e0e0e0; padding: 10px 12px; text-align: left; }}
th {{ background: #2c3e50; color: white; font-weight: 600; }}
tr:nth-child(even) {{ background: #f8f9fa; }}
.metric {{ display: inline-block; margin: 8px; padding: 18px 22px; background: white; border-radius: 8px; border-left: 4px solid #3498db; box-shadow: 0 2px 8px rgba(0,0,0,0.08); min-width: 140px; }}
.metric-value {{ font-size: 22px; font-weight: bold; color: #2c3e50; }}
.metric-label {{ font-size: 11px; color: #7f8c8d; margin-top: 4px; }}
.chart-container {{ text-align: center; margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 8px; }}
.footer {{ text-align: center; margin-top: 50px; padding-top: 20px; border-top: 2px solid #ecf0f1; color: #7f8c8d; font-size: 12px; }}
</style>
</head>
<body>
<div class="container">
<h1>酒店订单时权ABS/RWA<br>资产证券化分析报告</h1>
<p style="text-align:center;color:#7f8c8d;margin-top:-15px;">
    版本: V7 | 日期: {d['report_metadata']['date']}<br>
    {d['report_metadata']['methodology']}
</p>

<div class="innovation-box">
    <h3 style="margin-top:0;">V7 核心创新</h3>
    <ul>
        <li><strong>时权资产池</strong>：每份证券对应真实的可入住间夜，非抽象收益权</li>
        <li><strong>统计超发</strong>：基于入住率冗余超发 {d['time_right_pool']['statistics']['overbooking_ratio']:.2f} 倍，提升融资效率</li>
        <li><strong>双轨兑付</strong>：投资者到期可自选现金收益或优惠入住</li>
        <li><strong>三方共赢</strong>：酒店提前回笼资金、平台赚取手续费、投资者获得收益或消费权益</li>
    </ul>
</div>

<h2>执行摘要</h2>
<div style="display:flex;flex-wrap:wrap;justify-content:space-around;margin-top:15px;">
    <div class="metric"><div class="metric-value">{d['time_right_pool']['statistics']['pool_size']}</div><div class="metric-label">资产池酒店数</div></div>
    <div class="metric"><div class="metric-value">{d['time_right_pool']['statistics']['total_rights']:,}</div><div class="metric-label">时权发行总量</div></div>
    <div class="metric"><div class="metric-value">{d['time_right_pool']['statistics']['overbooking_ratio']:.2f}x</div><div class="metric-label">超发倍数</div></div>
    <div class="metric"><div class="metric-value">¥{d['time_right_pool']['statistics']['total_notional']/1e8:.2f}亿</div><div class="metric-label">时权池总面值</div></div>
    <div class="metric"><div class="metric-value">{d['monte_carlo']['tranche_analysis']['Senior']['implied_rating']}</div><div class="metric-label">Senior隐含评级</div></div>
</div>

<h2>1. 时权池特征</h2>
<table>
<tr><th>指标</th><th>数值</th><th>指标</th><th>数值</th></tr>
<tr><td>酒店数量</td><td>{d['time_right_pool']['statistics']['pool_size']} 家</td><td>时权总量</td><td>{d['time_right_pool']['statistics']['total_rights']:,} 份</td></tr>
<tr><td>物理间夜</td><td>{d['time_right_pool']['statistics']['total_physical_rights']:,} 间夜</td><td>超发比例</td><td>{d['time_right_pool']['statistics']['overbooking_ratio']:.2f}x</td></tr>
<tr><td>总面值</td><td>¥{d['time_right_pool']['statistics']['total_notional']:,.0f}</td><td>平均发行价</td><td>¥{d['time_right_pool']['statistics']['avg_issue_price']:,.0f}</td></tr>
</table>

<h2>2. 分层结构与兑付方式</h2>
<table>
<tr><th>层级</th><th>规模</th><th>票息</th><th>现金兑付</th><th>实物兑付</th><th>入住折扣</th><th>目标客群</th><th>隐含评级</th></tr>
"""
        
        for t in d['tranche_structure']:
            mc_rating = d['monte_carlo']['tranche_analysis'].get(t['name'], {}).get('implied_rating', 'N/A')
            html += f"<tr><td><strong>{t['name']}</strong></td><td>{t['size_pct']*100:.1f}%</td>" \
                   f"<td>{t['coupon_annual']*100:.2f}%</td><td>{t['cash_redemption_pct']*100:.0f}%</td>" \
                   f"<td>{t['physical_redemption_pct']*100:.0f}%</td>" \
                   f"<td>{t['physical_discount']*100:.0f}%</td><td>{t['investor_type']}</td>" \
                   f"<td>{mc_rating}</td></tr>\n"
        
        tp = d['three_party_analysis']
        html += f"""
</table>

<h2>3. 三方收益分析</h2>
<table>
<tr><th>参与方</th><th>收入/回报</th><th>成本/投资</th><th>净收益</th><th>收益率</th></tr>
<tr><td><strong>酒店方</strong></td><td>¥{tp['hotel']['issuance_proceeds']:,.0f}</td><td>¥{tp['hotel']['redemption_cost']:,.0f}</td><td>¥{tp['hotel']['profit']:,.0f}</td><td>{tp['hotel']['roi']:.2f}%</td></tr>
<tr><td><strong>平台方</strong></td><td>¥{tp['platform']['total_revenue']:,.0f}</td><td>-</td><td>¥{tp['platform']['profit']:,.0f}</td><td>-</td></tr>
<tr><td><strong>投资者方</strong></td><td>¥{tp['investors']['total_return']:,.0f}</td><td>¥{tp['investors']['total_cost']:,.0f}</td><td>¥{tp['investors']['net_return']:,.0f}</td><td>{tp['investors']['return_rate']:.2f}%</td></tr>
</table>

<h2>4. 可视化分析</h2>
<div class="chart-container">
<img src="time_right_abs_v7.png" alt="时权ABS分析可视化">
</div>

<div class="footer">
<p>酒店订单时权ABS/RWA资产证券化分析报告 V7</p>
<p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</div>
</div>
</body>
</html>
"""
        
        output_path = f'{self.work_dir}/output/酒店订单时权ABS分析报告_v7.html'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"  HTML报告已保存: {output_path}")
        return output_path
    
    def generate_all(self):
        self.generate_visualization()
        self.generate_html_report()
        print("\n所有报告生成完成！")


def main():
    gen = TimeRightABSReportGenerator()
    gen.generate_all()


if __name__ == '__main__':
    main()
