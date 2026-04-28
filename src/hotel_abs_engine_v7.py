"""
酒店订单时权ABS/RWA资产证券化引擎 V7

融合V5的产品创新与V6的金融工程严谨性：
- 资产：时权池（实实在在的可入住间夜）
- 超发：基于入住率统计冗余
- 兑付：现金 + 实物双轨制
- 参与方：酒店 / 平台 / 投资者三方共赢
- 风险：Merton PD + Gaussian Copula + 蒙特卡洛
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from credit_model import HotelCreditModel
from monte_carlo_simulator import MonteCarloSimulator

from time_right_pool import TimeRightPoolBuilder, print_time_right_pool_characteristics
from tranche_structure_v7 import TimeRightTrancheStructure, print_time_right_tranche_structure
from waterfall_engine_v7 import TimeRightWaterfallEngine, print_three_party_summary


class HotelTimeRightABSEngine:
    """酒店时权ABS引擎 V7"""
    
    def __init__(self, work_dir=None):
        self.work_dir = work_dir or r'C:\Users\weida\Desktop\酒店研究'
        self.prices = None
        self.hotel_info = None
        self.future_prices = None
        
        # 中间结果
        self.credit_df = None
        self.corr_matrix = None
        self.pool_df = None
        self.pool_stats = None
        self.pool_cashflows = None
        self.tranches = None
        self.ce_stats = None
        
        # 最终分析
        self.three_party = None
        self.mc_analysis = None
        self.stress_results = None
        self.mc_results = None
    
    def load_data(self):
        print("【步骤1】加载数据...")
        self.prices = pd.read_csv(f'{self.work_dir}/data/cleaned_hotel_prices.csv')
        self.hotel_info = pd.read_csv(f'{self.work_dir}/data/hotel_info.csv')
        
        fp_path = f'{self.work_dir}/data/hotel_future_prices.csv'
        if os.path.exists(fp_path):
            self.future_prices = pd.read_csv(fp_path)
        
        print(f"  价格记录: {len(self.prices):,} 条")
        print(f"  酒店信息: {len(self.hotel_info):,} 家")
    
    def run_credit_model(self, min_records=50):
        print("\n【步骤2】运行酒店信用评级模型...")
        model = HotelCreditModel(self.prices, self.hotel_info, self.future_prices)
        self.credit_df = model.compute_hotel_credit_metrics(min_records=min_records)
        
        print(f"  成功评级 {len(self.credit_df)} 家酒店")
        print(f"  信用分布: {dict(self.credit_df['rating'].value_counts().sort_index())}")
        
        print("  计算违约相关性矩阵...")
        self.corr_matrix = model.compute_correlation_matrix(self.credit_df)
        
        return self.credit_df
    
    def build_time_right_pool(self, target_size=80):
        print("\n【步骤3】构建时权池...")
        builder = TimeRightPoolBuilder(self.credit_df, self.hotel_info, self.prices, self.future_prices)
        self.pool_df, self.pool_stats = builder.build_pool(target_size=target_size)
        
        print_time_right_pool_characteristics(self.pool_df, self.pool_stats)
        
        self.pool_cashflows = builder.compute_monthly_cashflows(
            self.pool_df, n_months=36, base_occupancy=0.62
        )
        
        return self.pool_df, self.pool_stats
    
    def design_tranche_structure(self):
        print("\n【步骤4】设计时权ABS分层结构...")
        struct = TimeRightTrancheStructure(
            pool_notional=self.pool_stats['total_notional'],
            total_rights=self.pool_stats['total_rights'],
            wtd_pd=self.pool_stats['wtd_pd'],
            wtd_lgd=self.pool_stats['wtd_lgd'],
            wtd_el=self.pool_stats['wtd_el'],
            avg_base_price=self.pool_stats['avg_base_price']
        )
        
        self.tranches = struct.design_tranches()
        self.ce_stats = struct.compute_credit_enhancement()
        
        print_time_right_tranche_structure(self.tranches, self.ce_stats, self.pool_df)
        
        # 兑付成本分析
        print("\n【兑付成本分析】")
        print(f"{'分层':<12} {'现金成本':>14} {'实物成本':>14} {'总成本':>14} {'vs全现金节省':>14}")
        print("-" * 75)
        for t in self.tranches:
            cost = struct.compute_redemption_cost(t, self.pool_df)
            print(f"{t['name']:<12} ¥{cost['cash_cost']:>12,.0f} "
                  f"¥{cost['physical_cost']:>12,.0f} ¥{cost['total_cost']:>12,.0f} "
                  f"¥{cost['cost_saving_vs_all_cash']:>12,.0f}")
        
        return self.tranches, self.ce_stats
    
    def run_three_party_analysis(self):
        print("\n【步骤5】三方收益分析...")
        engine = TimeRightWaterfallEngine(self.tranches, self.pool_df)
        self.three_party = engine.compute_three_party_economics()
        
        print_three_party_summary(self.three_party)
        
        return self.three_party
    
    def run_monte_carlo(self, n_paths=10000, n_months=36):
        print(f"\n【步骤6】蒙特卡洛模拟 ({n_paths} 路径)...")
        
        pool_codes = self.pool_df['hotelCode'].tolist()
        credit_codes = self.credit_df['hotelCode'].tolist()
        indices = [credit_codes.index(c) for c in pool_codes if c in credit_codes]
        
        if len(indices) > 0 and self.corr_matrix is not None and self.corr_matrix.shape[0] > max(indices):
            pool_corr = self.corr_matrix[np.ix_(indices, indices)]
        else:
            n = len(pool_codes)
            pool_corr = np.eye(n) * 0.7 + np.ones((n, n)) * 0.15
            np.fill_diagonal(pool_corr, 1.0)
        
        n_pool = len(self.pool_df)
        if pool_corr.shape[0] != n_pool:
            pool_corr = np.eye(n_pool) * 0.7 + np.ones((n_pool, n_pool)) * 0.15
            np.fill_diagonal(pool_corr, 1.0)
        
        # 适配pool_df格式给蒙特卡洛模拟器
        mc_pool_df = self.pool_df[['hotelCode', 'pd', 'lgd']].copy()
        
        # 构建蒙特卡洛可用的tranches格式
        mc_tranches = []
        for t in self.tranches:
            mc_tranches.append({
                'name': t['name'],
                'notional': t['notional'],
                'coupon_monthly': t['coupon_monthly']
            })
        
        sim = MonteCarloSimulator(
            mc_pool_df, pool_corr, mc_tranches, self.pool_cashflows,
            n_paths=n_paths, n_months=n_months, seed=42
        )
        
        print("  生成违约路径...")
        sim.generate_defaults()
        
        default_rates = []
        for path in range(n_paths):
            cumulative_defaults = np.sum(np.any(sim.default_matrix[path, :, :], axis=1))
            default_rates.append(cumulative_defaults / n_pool)
        
        print(f"  平均累计违约率: {np.mean(default_rates)*100:.2f}%")
        
        print("  运行现金流瀑布...")
        self.mc_results = sim.run_waterfall_all_paths()
        
        print("  分析损失分布...")
        self.mc_analysis = sim.analyze_tranche_losses(self.mc_results)
        
        print("  运行压力测试...")
        self.stress_results = sim.stress_test(self.mc_results)
        
        # 打印摘要
        print("\n" + "=" * 80)
        print("蒙特卡洛模拟分析摘要")
        print("=" * 80)
        print(f"\n{'分层':<12} {'预期损失':>10} {'VaR 95%':>10} {'VaR 99%':>10} {'隐含评级':>8}")
        print("-" * 65)
        for name, stats in self.mc_analysis.items():
            print(f"{name:<12} {stats['mean_loss_rate']*100:>9.2f}% {stats['var_95']*100:>9.2f}% "
                  f"{stats['var_99']*100:>9.2f}% {stats['implied_rating']:>8s}")
        
        return self.mc_analysis, self.stress_results
    
    def compile_report(self):
        print("\n【步骤7】编译完整报告...")
        
        report = {
            'report_metadata': {
                'version': 'V7',
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'title': '酒店订单时权ABS/RWA资产证券化分析报告',
                'methodology': '时权池超发 + Merton PD + Gaussian Copula + 现金/实物双轨兑付 + 三方收益分析'
            },
            'time_right_pool': {
                'hotels': self.pool_df.to_dict('records'),
                'statistics': self.pool_stats
            },
            'tranche_structure': self.tranches,
            'credit_enhancement': self.ce_stats,
            'three_party_analysis': self.three_party,
            'monte_carlo': {
                'n_paths': 10000,
                'tranche_analysis': self.mc_analysis,
                'stress_test': self.stress_results
            }
        }
        
        output_path = f'{self.work_dir}/output/time_right_abs_report_v7.json'
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        def convert(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert(i) for i in obj]
            return obj
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(convert(report), f, ensure_ascii=False, indent=2)
        
        print(f"  报告已保存: {output_path}")
        return report
    
    def run_full_analysis(self, pool_size=80, n_paths=10000):
        print("=" * 80)
        print("酒店订单时权ABS/RWA资产证券化引擎 V7")
        print("=" * 80)
        print("设计理念：V6的金融工程严谨性 + V5的产品创新（时权+超发+双轨兑付+三方共赢）")
        print(f"分析日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.load_data()
        self.run_credit_model(min_records=50)
        self.build_time_right_pool(target_size=pool_size)
        self.design_tranche_structure()
        self.run_three_party_analysis()
        self.run_monte_carlo(n_paths=n_paths, n_months=36)
        report = self.compile_report()
        
        print("\n" + "=" * 80)
        print("分析完成！")
        print("=" * 80)
        print("\n核心创新点：")
        print("  1. 时权池：每份证券对应真实的可入住间夜")
        print("  2. 统计超发：基于入住率冗余提升融资效率")
        print("  3. 双轨兑付：现金收益 OR 优惠入住，投资者自选")
        print("  4. 三方共赢：酒店提前拿钱、平台赚手续费、投资者赚收益或优惠住")
        print("  5. 专业风控：Merton模型 + Gaussian Copula + 10,000路径蒙特卡洛")
        
        return report


def main():
    engine = HotelTimeRightABSEngine()
    engine.run_full_analysis(pool_size=80, n_paths=10000)


if __name__ == '__main__':
    main()
