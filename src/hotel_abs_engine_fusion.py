"""
酒店订单时权ABS/RWA融合引擎 V6-Fusion

融合V5创新灵魂 + V6专业框架：
- 基础资产 = 时权组合（不是贷款池）
- 现金流 = 发行收入 + 交易手续费 + 兑付成本
- 二级市场 = 时权价格收敛模型
- 兑付 = 现金/实物/转让三元选择
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from credit_model import HotelCreditModel
from asset_pool import AssetPoolBuilder, print_pool_characteristics
from tranche_structure import TrancheStructure, print_tranche_structure
from waterfall_engine import WaterfallEngine
from monte_carlo_simulator import MonteCarloSimulator


class HotelTimeRightABSEngine:
    """时权ABS融合引擎"""
    
    def __init__(self, work_dir=None):
        self.work_dir = work_dir or r'C:\Users\weida\Desktop\酒店研究'
        self.prices = None
        self.hotel_info = None
        self.future_prices = None
        
        self.credit_df = None
        self.pool_df = None
        self.pool_stats = None
        self.time_right_df = None  # 时权参数
        self.tranches = None
        
        self.mc_results = None
        self.mc_analysis = None
        self.stress_results = None
        
    def load_data(self):
        print("=" * 80)
        print("酒店订单时权ABS/RWA融合分析 V6-Fusion")
        print("=" * 80)
        print(f"分析日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n【步骤1】加载数据...")
        self.prices = pd.read_csv(f'{self.work_dir}/data/cleaned_hotel_prices.csv')
        self.hotel_info = pd.read_csv(f'{self.work_dir}/data/hotel_info.csv')
        fp_path = f'{self.work_dir}/data/hotel_future_prices.csv'
        if os.path.exists(fp_path):
            self.future_prices = pd.read_csv(fp_path)
        print(f"  价格记录: {len(self.prices):,} 条")
        print(f"  酒店信息: {len(self.hotel_info):,} 家")
        
    def run_credit_model(self, min_records=50, max_hotels=500):
        print("\n【步骤2】运行酒店信用评级模型...")
        
        print("  步骤2a: 快速预筛选候选酒店...")
        quick_stats = self.prices.groupby('hotelCode').agg({
            'price': ['count', 'mean', 'std', 'min', 'max']
        }).reset_index()
        quick_stats.columns = ['hotelCode', 'recordCount', 'avgPrice', 'priceStd', 'minPrice', 'maxPrice']
        
        candidates = quick_stats[
            (quick_stats['recordCount'] >= min_records) &
            (quick_stats['avgPrice'] > 1000) &
            (quick_stats['avgPrice'] < 500000) &
            (quick_stats['priceStd'] > 0)
        ].copy()
        
        if len(candidates) > max_hotels:
            candidates = candidates.nlargest(max_hotels, 'priceStd')
        
        candidate_codes = candidates['hotelCode'].tolist()
        print(f"  预筛选后候选酒店: {len(candidate_codes)} 家")
        
        print("  步骤2b: 详细信用分析...")
        model = HotelCreditModel(self.prices, self.hotel_info, self.future_prices)
        self.credit_df = model.compute_hotel_credit_metrics_for_codes(candidate_codes, min_records=8)
        
        print(f"  成功评级 {len(self.credit_df)} 家酒店")
        print(f"  信用分布: {dict(self.credit_df['rating'].value_counts().sort_index())}")
        return self.credit_df
    
    def build_asset_pool(self, target_size=80):
        print("\n【步骤3】构建时权资产池...")
        
        builder = AssetPoolBuilder(self.credit_df, self.hotel_info, self.prices)
        self.pool_df, self.pool_stats = builder.build_pool(target_size=target_size)
        
        print_pool_characteristics(self.pool_df, self.pool_stats)
        
        # 计算时权参数
        print("\n【步骤3b】计算时权发行参数...")
        self.time_right_df = builder.compute_time_right_params(
            self.pool_df, discount_rate=0.08, safety_factor=0.8,
            issue_discount=0.25, time_to_maturity_months=36
        )
        
        total_issue_value = self.time_right_df['total_face_value'].sum()
        total_quantity = self.time_right_df['issue_quantity'].sum()
        avg_issue_price = self.time_right_df['issue_price'].mean()
        avg_overbooking = self.time_right_df['overbooking_multiplier'].mean()
        
        print(f"  时权发行总量: {total_quantity:,} 份")
        print(f"  时权总面值: {total_issue_value:,.0f}")
        print(f"  平均单份发行价: {avg_issue_price:,.0f}")
        print(f"  平均超发倍数: {avg_overbooking:.2f}x")
        
        # 更新pool_stats以使用时权面值
        self.pool_stats['time_right_total_face_value'] = total_issue_value
        self.pool_stats['time_right_total_quantity'] = total_quantity
        self.pool_stats['time_right_avg_price'] = avg_issue_price
        
        return self.pool_df, self.pool_stats
    
    def design_tranche_structure(self):
        print("\n【步骤4】设计时权ABS分层结构...")
        
        # 使用时权总面值作为资产池面值
        pool_notional = self.pool_stats['time_right_total_face_value']
        wtd_pd = self.pool_stats['wtd_pd']
        wtd_lgd = self.pool_stats['wtd_lgd']
        wtd_el = self.pool_stats['wtd_el']
        
        struct = TrancheStructure(pool_notional, wtd_pd, wtd_lgd, wtd_el)
        self.tranches = struct.design_tranches(
            senior_pct=0.68, mezz_pct=0.20, junior_pct=0.08, equity_pct=0.04
        )
        ce_stats = struct.compute_credit_enhancement(reserve_pct=0.03)
        
        print_tranche_structure(self.tranches, ce_stats)
        
        # 更新tranches的票息为时权收益导向
        for t in self.tranches:
            if t['name'] == 'Senior':
                t['description'] = '优先获得交易手续费 + 现金兑付回收'
            elif t['name'] == 'Mezzanine':
                t['description'] = '次级手续费 + 部分实物兑付折价收益'
            elif t['name'] == 'Junior':
                t['description'] = '实物兑付房间分配权 + 违约风险承担'
            elif t['name'] == 'Equity':
                t['description'] = '二级市场价差收益 + 超额回报'
        
        return self.tranches, ce_stats
    
    def _simulate_time_right_market(self, n_paths=5000, n_months=36):
        """
        模拟时权二级市场交易和兑付
        
        核心模型：
        1. 时权价格随时间收敛到即期价格
        2. 每期产生交易手续费
        3. 到期时用户选择现金/实物/转让
        """
        np.random.seed(42)
        n_hotels = len(self.time_right_df)
        
        # 参数提取
        issue_prices = self.time_right_df['issue_price'].values
        spot_prices = self.time_right_df['spot_predicted'].values
        quantities = self.time_right_df['issue_quantity'].values
        
        # 时权价格收敛路径 (n_paths, n_hotels, n_months)
        # 价格(t) = 底价/发行价 + (1-底价/发行价) * (t/T)^beta + 噪声
        price_paths = np.zeros((n_paths, n_hotels, n_months))
        
        beta = 0.8  # 收敛速度
        for path in range(n_paths):
            for i in range(n_hotels):
                base_ratio = issue_prices[i] / max(spot_prices[i], 1)
                for t in range(n_months):
                    convergence = (t / max(n_months - 1, 1)) ** beta
                    base_price_t = issue_prices[i] + (spot_prices[i] - issue_prices[i]) * convergence
                    # 加入随机噪声 (5%波动)
                    noise = np.random.normal(1.0, 0.05)
                    price_paths[path, i, t] = max(base_price_t * noise, issue_prices[i] * 0.5)
        
        # 每期交易量（假设每期有5%的时权被交易）
        turnover_rate = 0.05
        trading_volumes = np.outer(quantities, np.ones(n_months)) * turnover_rate
        
        # 交易手续费收入 (n_paths, n_months)
        trading_fee_rate = 0.005
        trading_fee_income = np.zeros((n_paths, n_months))
        
        for path in range(n_paths):
            for t in range(n_months):
                fees = 0
                for i in range(n_hotels):
                    volume = trading_volumes[i, t]
                    price = price_paths[path, i, t]
                    fees += volume * price * trading_fee_rate
                trading_fee_income[path, t] = fees
        
        # 到期兑付 (最后6个月开始)
        redemption_start = n_months - 6
        
        cash_redemption = np.zeros((n_paths, n_months))
        physical_redemption = np.zeros((n_paths, n_months))
        
        promised_return = 0.08  # 8%年化
        physical_discount = 0.30  # 7折
        
        for path in range(n_paths):
            for t in range(redemption_start, n_months):
                for i in range(n_hotels):
                    # 剩余未兑付时权
                    remaining = quantities[i] * (1 - (t - redemption_start) / 6)
                    if remaining <= 0:
                        continue
                    
                    # 用户选择比例（随机化）
                    alpha_cash = 0.25 + np.random.normal(0, 0.05)  # 现金兑付
                    beta_physical = 0.50 + np.random.normal(0, 0.08)  # 实物兑付
                    gamma_transfer = max(0, 1 - alpha_cash - beta_physical)  # 转让
                    
                    alpha_cash = max(0.1, min(0.4, alpha_cash))
                    beta_physical = max(0.3, min(0.7, beta_physical))
                    gamma_transfer = max(0, 1 - alpha_cash - beta_physical)
                    
                    # 现金兑付成本
                    cash_units = remaining * alpha_cash / 6
                    cash_cost = cash_units * issue_prices[i] * (1 + promised_return * (n_months - t) / 12)
                    cash_redemption[path, t] += cash_cost
                    
                    # 实物兑付成本（变动成本）
                    physical_units = remaining * beta_physical / 6
                    physical_cost = physical_units * spot_prices[i] * (1 - physical_discount) * 0.35  # 变动成本35%
                    physical_redemption[path, t] += physical_cost
        
        return {
            'price_paths': price_paths,
            'trading_fee_income': trading_fee_income,
            'cash_redemption': cash_redemption,
            'physical_redemption': physical_redemption,
        }
    
    def run_monte_carlo(self, n_paths=5000, n_months=36):
        print(f"\n【步骤5】蒙特卡洛模拟 ({n_paths} 路径 x {n_months} 期)...")
        
        # 运行时权市场模拟
        print("  模拟时权二级市场交易与兑付...")
        market_sim = self._simulate_time_right_market(n_paths, n_months)
        
        # 对资产池酒店计算相关性
        pool_codes = self.pool_df['hotelCode'].tolist()
        print(f"  计算资产池({len(pool_codes)}家)违约相关性...")
        
        model = HotelCreditModel(self.prices, self.hotel_info, self.future_prices)
        pool_credit_df = self.credit_df[self.credit_df['hotelCode'].isin(pool_codes)].copy()
        pool_corr = model.compute_correlation_matrix(pool_credit_df)
        
        n_pool = len(self.pool_df)
        if pool_corr.shape[0] != n_pool:
            pool_corr = np.eye(n_pool) * 0.7 + np.ones((n_pool, n_pool)) * 0.15
            np.fill_diagonal(pool_corr, 1.0)
        
        # 运行蒙特卡洛（使用pool_cashflows作为违约损失的代理）
        pool_cashflows = AssetPoolBuilder(self.credit_df, self.hotel_info, self.prices) \
            .compute_monthly_cashflows(self.pool_df, n_months=n_months)
        
        sim = MonteCarloSimulator(
            self.pool_df, pool_corr, self.tranches, pool_cashflows,
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
        all_results = sim.run_waterfall_all_paths()
        
        print("  分析损失分布...")
        self.mc_analysis = sim.analyze_tranche_losses(all_results)
        
        print("  运行压力测试...")
        self.stress_results = sim.stress_test(all_results)
        
        # 打印结果
        print("\n【蒙特卡洛模拟分析摘要】")
        print(f"{'分层':<12} {'预期损失':>10} {'VaR 95%':>10} {'VaR 99%':>10} {'隐含评级':>8}")
        print("-" * 60)
        for name, stats in self.mc_analysis.items():
            print(f"{name:<12} {stats['mean_loss_rate']*100:>9.2f}% {stats['var_95']*100:>9.2f}% "
                  f"{stats['var_99']*100:>9.2f}% {stats['implied_rating']:>8s}")
        
        return self.mc_analysis, self.stress_results
    
    def compile_report(self):
        print("\n【步骤6】编译融合版报告...")
        
        report = {
            'report_metadata': {
                'version': 'V6-Fusion',
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'title': '酒店订单时权ABS/RWA融合分析报告',
                'methodology': '时权发行+二级市场收敛+三元兑付+Merton信用模型+Gaussian Copula蒙特卡洛'
            },
            'asset_pool': {
                'hotels': self.pool_df.to_dict('records'),
                'time_rights': self.time_right_df.to_dict('records'),
                'statistics': self.pool_stats,
            },
            'tranche_structure': self.tranches,
            'monte_carlo': {
                'n_paths': 5000,
                'n_months': 36,
                'tranche_analysis': self.mc_analysis,
                'stress_test': self.stress_results
            },
            'rwa_architecture': {
                'architecture': {
                    'off_chain': {
                        'spv': {'name': '时权ABS特殊目的载体', 'jurisdiction': '开曼群岛/新加坡'},
                        'servicer': {'name': '酒店运营服务商', 'responsibilities': ['时权发行管理', '月度现金流归集', '兑付执行']},
                    },
                    'on_chain': {
                        'token_standard': 'ERC-3643 (T-REX Protocol)',
                        'blockchain': 'Ethereum / Polygon',
                        'tokens': [
                            {'name': 'TR-Senior', 'symbol': 'TR-SEN', 'tranche': 'Senior'},
                            {'name': 'TR-Mezzanine', 'symbol': 'TR-MEZ', 'tranche': 'Mezzanine'},
                            {'name': 'TR-Junior', 'symbol': 'TR-JUN', 'tranche': 'Junior'},
                            {'name': 'TR-Equity', 'symbol': 'TR-EQU', 'tranche': 'Equity'},
                        ],
                        'oracle': {'provider': 'Chainlink', 'data_feeds': ['时权价格', '兑付比例', '违约事件']},
                    }
                },
                'smart_contract_logic': {
                    'time_right_lifecycle': [
                        '1. 酒店发行时权 → 铸造ERC-3643代币',
                        '2. 投资者购买 → 代币转入钱包',
                        '3. 到期前：自由转让，价格由AMM决定',
                        '4. 到期时：选择 cash/physical/rollover',
                        '5. 选择cash→自动转账+销毁代币',
                        '6. 选择physical→生成NFT房券→酒店核销',
                        '7. 选择rollover→自动转换为下一期时权',
                    ]
                }
            }
        }
        
        # numpy类型转换
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
        
        report_serializable = convert(report)
        
        output_path = f'{self.work_dir}/output/abs_report_v6_fusion.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_serializable, f, ensure_ascii=False, indent=2)
        
        print(f"  报告已保存: {output_path}")
        return report
    
    def run_full_analysis(self, pool_size=80, n_paths=5000):
        self.load_data()
        self.run_credit_model(min_records=50, max_hotels=500)
        self.build_asset_pool(target_size=pool_size)
        self.design_tranche_structure()
        self.run_monte_carlo(n_paths=n_paths, n_months=36)
        report = self.compile_report()
        
        print("\n" + "=" * 80)
        print("时权ABS融合分析完成！")
        print("=" * 80)
        return report


def main():
    engine = HotelTimeRightABSEngine()
    engine.run_full_analysis(pool_size=80, n_paths=5000)


if __name__ == '__main__':
    main()
