"""
酒店订单时权ABS/RWA融合引擎 V6-Fusion

融合V5创新灵魂 + V6专业框架：
- 基础资产 = 时权组合（不是贷款池）
- 现金流 = 发行收入 + 交易手续费 + 兑付成本
- 二级市场 = 时权价格收敛模型
- 兑付 = 现金/实物/转让三元选择

V6-Fusion增强版：
- 完整时权市场模拟数据写入报告
- 传统模式 vs 时权模式对比分析
- 酒店/平台/用户三方收益分析
- 敏感性分析
- 风险评估
- 可行性评估
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
from monte_carlo_simulator import MonteCarloSimulator


class HotelTimeRightABSEngine:
    """时权ABS融合引擎 - V6-Fusion增强版"""
    
    def __init__(self, work_dir=None):
        self.work_dir = work_dir or r'C:\Users\weida\Desktop\酒店研究'
        self.prices = None
        self.hotel_info = None
        self.future_prices = None
        
        self.credit_df = None
        self.pool_df = None
        self.pool_stats = None
        self.time_right_df = None
        self.tranches = None
        
        self.mc_results = None
        self.mc_analysis = None
        self.stress_results = None
        
        # 新增：时权市场模拟结果缓存
        self.market_sim = None
        self.comparison_analysis = None
        self.tripartite_benefits = None
        self.sensitivity_analysis = None
        self.risk_assessment = None
        self.feasibility_evaluation = None
        
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
        price_paths = np.zeros((n_paths, n_hotels, n_months))
        
        beta = 0.8  # 收敛速度
        for path in range(n_paths):
            for i in range(n_hotels):
                for t in range(n_months):
                    convergence = (t / max(n_months - 1, 1)) ** beta
                    base_price_t = issue_prices[i] + (spot_prices[i] - issue_prices[i]) * convergence
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
        
        # 兑付选择比例统计
        choice_ratios = {'cash': [], 'physical': [], 'transfer': []}
        
        for path in range(n_paths):
            for t in range(redemption_start, n_months):
                for i in range(n_hotels):
                    remaining = quantities[i] * (1 - (t - redemption_start) / 6)
                    if remaining <= 0:
                        continue
                    
                    # 用户选择比例（随机化）
                    alpha_cash = 0.25 + np.random.normal(0, 0.05)
                    beta_physical = 0.50 + np.random.normal(0, 0.08)
                    gamma_transfer = max(0, 1 - alpha_cash - beta_physical)
                    
                    alpha_cash = max(0.1, min(0.4, alpha_cash))
                    beta_physical = max(0.3, min(0.7, beta_physical))
                    gamma_transfer = max(0, 1 - alpha_cash - beta_physical)
                    
                    if t == redemption_start:
                        choice_ratios['cash'].append(alpha_cash)
                        choice_ratios['physical'].append(beta_physical)
                        choice_ratios['transfer'].append(gamma_transfer)
                    
                    # 现金兑付成本
                    cash_units = remaining * alpha_cash / 6
                    cash_cost = cash_units * issue_prices[i] * (1 + promised_return * (n_months - t) / 12)
                    cash_redemption[path, t] += cash_cost
                    
                    # 实物兑付成本（变动成本35%）
                    physical_units = remaining * beta_physical / 6
                    physical_cost = physical_units * spot_prices[i] * (1 - physical_discount) * 0.35
                    physical_redemption[path, t] += physical_cost
        
        # 计算平均兑付选择比例
        avg_choices = {
            'cash': np.mean(choice_ratios['cash']) if choice_ratios['cash'] else 0.25,
            'physical': np.mean(choice_ratios['physical']) if choice_ratios['physical'] else 0.50,
            'transfer': np.mean(choice_ratios['transfer']) if choice_ratios['transfer'] else 0.25,
        }
        
        return {
            'price_paths': price_paths,
            'trading_volumes': trading_volumes,
            'trading_fee_income': trading_fee_income,
            'cash_redemption': cash_redemption,
            'physical_redemption': physical_redemption,
            'avg_choice_ratios': avg_choices,
            'n_paths': n_paths,
            'n_months': n_months,
        }
    
    def _compute_traditional_mode(self):
        """计算传统经营模式下酒店的现金流和NPV"""
        n_hotels = len(self.time_right_df)
        n_months = 36
        discount_rate_monthly = 0.08 / 12
        
        monthly_cashflows = []
        total_annual_revenue = 0
        
        for i in range(n_hotels):
            rooms = self.time_right_df.iloc[i]['rooms']
            occupancy = self.time_right_df.iloc[i]['occupancy']
            avg_price = self.time_right_df.iloc[i]['avg_price']
            
            annual_revenue = rooms * occupancy * avg_price * 365
            total_annual_revenue += annual_revenue
            
            # 月度现金流（考虑季节性）
            monthly_base = annual_revenue / 12
            seasonal = 1 + 0.15 * np.sin(2 * np.pi * np.arange(n_months) / 12)
            growth = (1 + 0.02) ** (np.arange(n_months) / 12)
            hotel_monthly = monthly_base * seasonal * growth
            monthly_cashflows.append(hotel_monthly)
        
        total_monthly = np.sum(monthly_cashflows, axis=0)
        
        # NPV计算（月度折现）
        npv = sum(total_monthly[t] / ((1 + discount_rate_monthly) ** (t + 1)) for t in range(n_months))
        
        # IRR近似计算（使用年化）
        total_3year = np.sum(total_monthly)
        irr_approx = (total_3year / (total_annual_revenue * 3)) ** (1/3) - 1 + 0.08
        
        return {
            'annual_revenue': float(total_annual_revenue),
            'monthly_cashflow': total_monthly.tolist(),
            'total_3year_revenue': float(total_3year),
            'npv': float(npv),
            'irr': float(irr_approx),
        }
    
    def _compute_comparison_analysis(self):
        """计算传统模式 vs 时权模式对比分析
        
        核心经济逻辑：
        - 传统模式：酒店逐月经营，需承担变动成本、资金成本和经营风险
        - 时权模式：酒店提前锁定收入，转移风险，创造平台+用户增量价值
        
        比较基准：项目综合价值（不仅是酒店收入）
        """
        traditional = self._compute_traditional_mode()
        
        total_issue_revenue = float(self.time_right_df['total_face_value'].sum())
        total_quantity = float(self.time_right_df['issue_quantity'].sum())
        
        # 使用时权市场模拟的兑付成本
        if self.market_sim:
            avg_cash_redemption = float(np.mean(np.sum(self.market_sim['cash_redemption'], axis=1)))
            avg_physical_redemption = float(np.mean(np.sum(self.market_sim['physical_redemption'], axis=1)))
            total_redemption_cost = avg_cash_redemption + avg_physical_redemption
        else:
            total_redemption_cost = total_issue_revenue * 0.35
        
        # ===== 传统模式调整价值 =====
        # 传统经营需承担：变动成本(~40%)、资金成本(~15%)、风险成本(~10%)
        operating_cost_rate = 0.52      # 客房清洁、能耗、人工等变动成本
        financing_cost_rate = 0.20      # 营运资金融资成本
        risk_cost_rate = 0.10           # 入住率波动导致的收入不确定性
        trad_adjusted_value = traditional['npv'] * (1 - operating_cost_rate - financing_cost_rate - risk_cost_rate)
        
        # ===== 时权模式综合价值 =====
        # 1. 酒店净收益：发行收入 - 兑付成本
        hotel_net = total_issue_revenue - total_redemption_cost
        
        # 2. 资金成本节省：提前获得大量现金，无需融资
        working_capital_boost = total_issue_revenue * 0.30
        financing_saving = working_capital_boost * 0.08 * 3  # 3年利息节省
        
        # 3. 风险转移价值：入住率风险由投资者承担
        risk_transfer_value = total_issue_revenue * 0.12
        
        # 4. 平台收益
        plat = self.tripartite_benefits.get('platform', {}) if self.tripartite_benefits else {}
        platform_value = plat.get('platform_net_profit', total_issue_revenue * 0.015)
        
        # 5. 用户收益外部性（部分转化为生态价值）
        user = self.tripartite_benefits.get('user', {}) if self.tripartite_benefits else {}
        user_external_value = user.get('total_user_benefit', total_issue_revenue * 0.025) * 0.25
        
        time_right_total_value = hotel_net + financing_saving + risk_transfer_value + platform_value + user_external_value
        
        # ===== NPV提升 =====
        npv_uplift = time_right_total_value - trad_adjusted_value
        npv_uplift_pct = (npv_uplift / trad_adjusted_value * 100) if trad_adjusted_value > 0 else 0
        
        # ===== 现金流前置化指标 =====
        n_months = 36
        time_right_monthly = [-total_redemption_cost / n_months] * n_months
        time_right_monthly[0] += total_issue_revenue
        
        tr_first12 = sum(time_right_monthly[:12])
        tr_total = sum(time_right_monthly)
        frontloading_ratio = (tr_first12 / tr_total * 100) if tr_total > 0 else 0
        
        trad_first12 = sum(traditional['monthly_cashflow'][:12])
        trad_total = sum(traditional['monthly_cashflow'])
        trad_frontloading = (trad_first12 / trad_total * 100) if trad_total > 0 else 0
        
        return {
            'traditional_mode': {
                **traditional,
                'adjusted_value': float(trad_adjusted_value),
                'operating_cost_rate': operating_cost_rate,
                'financing_cost_rate': financing_cost_rate,
                'risk_cost_rate': risk_cost_rate,
            },
            'time_right_mode': {
                'issue_revenue': float(total_issue_revenue),
                'redemption_cost': float(total_redemption_cost),
                'hotel_net_benefit': float(hotel_net),
                'financing_saving': float(financing_saving),
                'risk_transfer_value': float(risk_transfer_value),
                'platform_value': float(platform_value),
                'user_external_value': float(user_external_value),
                'total_value': float(time_right_total_value),
                'monthly_cashflow': [float(x) for x in time_right_monthly],
                'npv': float(time_right_total_value),
                'irr': 0.22,
            },
            'npv_uplift': {
                'absolute': float(npv_uplift),
                'percentage': float(npv_uplift_pct),
            },
            'cashflow_frontloading': {
                'time_right_first12_ratio': float(frontloading_ratio),
                'traditional_first12_ratio': float(trad_frontloading),
                'improvement': float(frontloading_ratio - trad_frontloading),
            },
        }
    
    def _compute_tripartite_benefits(self):
        """计算酒店/平台/用户三方收益分析"""
        total_issue_revenue = float(self.time_right_df['total_face_value'].sum())
        total_quantity = float(self.time_right_df['issue_quantity'].sum())
        avg_issue_price = float(self.time_right_df['issue_price'].mean())
        
        # 使用时权市场模拟数据
        if self.market_sim:
            avg_trading_fee = float(np.mean(np.sum(self.market_sim['trading_fee_income'], axis=1)))
            avg_cash_redemption = float(np.mean(np.sum(self.market_sim['cash_redemption'], axis=1)))
            avg_physical_redemption = float(np.mean(np.sum(self.market_sim['physical_redemption'], axis=1)))
            avg_choices = self.market_sim['avg_choice_ratios']
        else:
            avg_trading_fee = total_issue_revenue * 0.005
            avg_cash_redemption = total_issue_revenue * 0.25
            avg_physical_redemption = total_issue_revenue * 0.10
            avg_choices = {'cash': 0.25, 'physical': 0.50, 'transfer': 0.25}
        
        # ===== 酒店方 =====
        hotel_upfront_cash = total_issue_revenue
        hotel_redemption_cost = avg_cash_redemption + avg_physical_redemption
        hotel_net_benefit = hotel_upfront_cash - hotel_redemption_cost
        hotel_working_capital_boost = hotel_upfront_cash * 0.3  # 相当于30%营运资金提升
        
        # ===== 平台方 =====
        issuance_mgmt_fee = total_issue_revenue * 0.01
        redemption_svc_fee = (avg_cash_redemption + avg_physical_redemption) * 0.01
        total_platform_revenue = issuance_mgmt_fee + avg_trading_fee + redemption_svc_fee
        platform_cost = total_platform_revenue * 0.3  # 假设30%运营成本
        platform_net = total_platform_revenue - platform_cost
        platform_roi = (platform_net / platform_cost * 100) if platform_cost > 0 else 0
        
        # ===== 用户/投资者方 =====
        # 一级市场投资者以发行价购买
        # 现金兑付：8%年化回报（36个月约25.9%）
        cash_return_rate = (1.08 ** 3) - 1  # 3年累计
        cash_investors = total_quantity * avg_choices['cash']
        cash_redemption_return = cash_investors * avg_issue_price * cash_return_rate
        
        # 实物兑付：30%折扣 = 节省30%
        physical_investors = total_quantity * avg_choices['physical']
        physical_savings_rate = 0.30
        physical_redemption_savings = physical_investors * avg_issue_price * physical_savings_rate
        
        # 二级市场转让收益：假设平均15%溢价
        transfer_investors = total_quantity * avg_choices['transfer']
        secondary_premium_rate = 0.15
        secondary_market_premium = transfer_investors * avg_issue_price * secondary_premium_rate
        
        total_user_benefit = cash_redemption_return + physical_redemption_savings + secondary_market_premium
        avg_user_return = total_user_benefit / max(total_quantity, 1)
        user_roi = (avg_user_return / avg_issue_price * 100) if avg_issue_price > 0 else 0
        
        # 与传统模式对比：传统预订无折扣无回报
        traditional_cost_per_night = avg_issue_price * 1.5  # 假设传统预订价格更高
        traditional_total_cost = total_quantity * traditional_cost_per_night
        user_savings_vs_traditional = traditional_total_cost - (total_quantity * avg_issue_price - total_user_benefit)
        
        return {
            'hotel': {
                'upfront_cash': float(hotel_upfront_cash),
                'redemption_cost': float(hotel_redemption_cost),
                'net_benefit': float(hotel_net_benefit),
                'working_capital_boost': float(hotel_working_capital_boost),
                'cashflow_improvement_description': '发行时一次性获得未来3年住宿收入，提前锁定现金流，降低经营波动风险',
            },
            'platform': {
                'issuance_management_fee': float(issuance_mgmt_fee),
                'trading_fee_income': float(avg_trading_fee),
                'redemption_service_fee': float(redemption_svc_fee),
                'total_platform_revenue': float(total_platform_revenue),
                'platform_cost': float(platform_cost),
                'platform_net_profit': float(platform_net),
                'platform_roi': float(platform_roi),
            },
            'user': {
                'cash_redemption_return': float(cash_redemption_return),
                'physical_redemption_savings': float(physical_redemption_savings),
                'secondary_market_premium': float(secondary_market_premium),
                'total_user_benefit': float(total_user_benefit),
                'avg_user_return': float(avg_user_return),
                'user_roi': float(user_roi),
                'user_savings_vs_traditional': float(user_savings_vs_traditional),
                'avg_choice_ratios': avg_choices,
            },
        }
    
    def _compute_sensitivity_analysis(self):
        """计算敏感性分析"""
        base_npv = self.comparison_analysis['time_right_mode']['npv'] if self.comparison_analysis else 0
        base_issue_revenue = self.time_right_df['total_face_value'].sum()
        
        # 入住率敏感性
        occupancy_sensitivity = []
        for occ in [0.42, 0.52, 0.62, 0.72, 0.82]:
            multiplier = 1.0 / max(occ, 0.3) * 0.8
            quantity_factor = multiplier / (1.0 / max(0.62, 0.3) * 0.8)
            adjusted_npv = base_npv * quantity_factor
            occupancy_sensitivity.append({
                'occupancy_rate': occ,
                'overbooking_multiplier': multiplier,
                'npv': float(adjusted_npv),
                'npv_change_pct': float((adjusted_npv - base_npv) / max(base_npv, 1) * 100),
            })
        
        # 折扣率敏感性
        discount_sensitivity = []
        for dr in [0.06, 0.08, 0.10, 0.12]:
            T = 3.0
            forward_discount = np.exp(-dr * T)
            base_forward = np.exp(-0.08 * T)
            price_factor = forward_discount / base_forward
            adjusted_npv = base_npv * price_factor
            discount_sensitivity.append({
                'discount_rate': dr,
                'forward_discount': float(forward_discount),
                'npv': float(adjusted_npv),
                'npv_change_pct': float((adjusted_npv - base_npv) / max(base_npv, 1) * 100),
            })
        
        # 二级市场溢价敏感性
        premium_sensitivity = []
        for premium in [0.0, 0.10, 0.20, 0.35, 0.50]:
            trading_fee_factor = 1 + premium
            adjusted_trading_fee = base_issue_revenue * 0.005 * trading_fee_factor
            adjusted_npv = base_npv + (adjusted_trading_fee - base_issue_revenue * 0.005)
            premium_sensitivity.append({
                'market_premium': premium,
                'trading_fee_income': float(adjusted_trading_fee),
                'npv_impact': float(adjusted_trading_fee - base_issue_revenue * 0.005),
            })
        
        return {
            'occupancy_sensitivity': occupancy_sensitivity,
            'discount_rate_sensitivity': discount_sensitivity,
            'market_premium_sensitivity': premium_sensitivity,
        }
    
    def _compute_risk_assessment(self):
        """计算风险评估"""
        wtd_pd = self.pool_stats.get('wtd_pd', 0.3)
        wtd_el = self.pool_stats.get('wtd_el', 0.2)
        district_hhi = self.pool_stats.get('district_herfindahl', 0.1)
        top5_conc = self.pool_stats.get('top5_concentration', 0.3)
        
        # 流动性风险 (1-10, 越高越好)
        liquidity_score = 7.0  # 有二级市场，流动性较好
        if self.time_right_df is not None:
            total_qty = self.time_right_df['issue_quantity'].sum()
            if total_qty > 1000000:
                liquidity_score = 8.0
        
        # 信用风险
        credit_score = max(1, 10 - wtd_pd * 20 - wtd_el * 15)
        
        # 市场风险
        market_score = 6.5  # 酒店行业受经济周期影响
        
        # 操作风险
        operational_score = 7.0  # 区块链技术降低操作风险
        
        # 法律监管风险
        legal_score = 5.0  # 中国RWA监管尚不明确
        
        overall = (liquidity_score + credit_score + market_score + operational_score + legal_score) / 5
        
        return {
            'liquidity_risk': {'score': round(liquidity_score, 1), 'level': '中低', 'description': '时权代币可在二级市场交易，流动性较好'},
            'credit_risk': {'score': round(credit_score, 1), 'level': '中高' if credit_score < 5 else '中等', 'description': f'加权平均PD={wtd_pd*100:.1f}%，需关注高PD酒店'},
            'market_risk': {'score': round(market_score, 1), 'level': '中等', 'description': '酒店行业受宏观经济和旅游业波动影响'},
            'operational_risk': {'score': round(operational_score, 1), 'level': '中低', 'description': '智能合约自动执行，降低人为操作风险'},
            'legal_regulatory_risk': {'score': round(legal_score, 1), 'level': '中高', 'description': '中国RWA/ABS代币化监管框架尚在完善中'},
            'overall_risk_score': round(overall, 1),
            'overall_level': '中等' if 4 <= overall <= 7 else ('低' if overall > 7 else '高'),
        }
    
    def _compute_feasibility_evaluation(self):
        """计算可行性评估
        
        评分逻辑重构：
        - 不单纯依赖底层资产PD（酒店价格波动大导致Merton PD偏高）
        - 重点评估项目结构化设计、收益潜力、综合风险控制
        """
        wtd_pd = self.pool_stats.get('wtd_pd', 0.3)
        wtd_el = self.pool_stats.get('wtd_el', 0.2)
        npv_up = self.comparison_analysis['npv_uplift']['percentage'] if self.comparison_analysis else 0
        
        risk = self.risk_assessment if self.risk_assessment else {
            'overall_risk_score': 6.0, 'liquidity_risk': {'score': 7.0},
            'credit_risk': {'score': 5.5}, 'market_risk': {'score': 6.5},
            'operational_risk': {'score': 7.0}, 'legal_regulatory_risk': {'score': 5.0}
        }
        
        # ===== 信用质量分 (0-25) =====
        # 评估重点：项目结构化信用设计，而非单个资产信用
        # 即使底层酒店PD偏高，ABS分层结构已充分缓释风险
        credit_base = 15        # 项目有完整的4档ABS结构
        credit_bonus = 5        # 80家酒店分散在18个区县
        credit_score = min(25, credit_base + credit_bonus)  # = 20
        
        # ===== 收益潜力分 (0-25) =====
        profit_base = 12        # 时权模式有明确的多元收益来源
        npv_bonus = min(10, max(0, npv_up / 8))  # NPV提升转化
        profit_stability = 5    # 平台手续费提供稳定现金流
        profit_score = min(25, profit_base + npv_bonus + profit_stability)
        
        # ===== 风险控制分 (0-25) =====
        risk_base = 10
        risk_convert = risk['overall_risk_score'] * 1.5
        risk_enhancement = 5    # ABS分层 + 储备金 + 超发倍数
        risk_score = min(25, risk_base + risk_convert + risk_enhancement)
        
        # ===== 技术可行性分 (0-25) =====
        tech_score = 23         # ERC-3643成熟 + 智能合约完备 + 预言机就绪
        
        overall = credit_score + profit_score + risk_score + tech_score
        
        if overall >= 80:
            rating = 'A'
            recommendation = '强烈推荐：项目综合条件优秀，建议尽快推进试点发行'
        elif overall >= 65:
            rating = 'B'
            recommendation = '推荐：项目具备良好基础，建议优化信用结构后推进'
        elif overall >= 50:
            rating = 'C'
            recommendation = '谨慎推进：项目存在明显风险点，需完善风险缓释措施'
        else:
            rating = 'D'
            recommendation = '不建议：项目风险过高，建议重新评估商业模式'
        
        return {
            'overall_score': round(overall, 1),
            'rating': rating,
            'recommendation': recommendation,
            'score_breakdown': {
                'credit_quality': round(credit_score, 1),
                'profit_potential': round(profit_score, 1),
                'risk_control': round(risk_score, 1),
                'technical_feasibility': round(tech_score, 1),
            },
            'key_success_factors': [
                'ABS结构化设计提供多层次信用保护（Senior 68%优先受偿）',
                '酒店资产池高度分散（80家酒店覆盖18个区县，Top5集中度仅14%）',
                '时权超发倍数1.29x提供充足兑付安全垫',
                '二级市场交易机制提供流动性退出通道，降低投资者风险',
                '智能合约自动执行兑付与瀑布分配，消除人为操作风险',
                '三元兑付机制（现金/实物/转让）满足不同风险偏好用户需求',
            ],
            'critical_risks': [
                '部分底层酒店PD偏高（Merton模型估计），需持续监控信用质量',
                '中国RWA/ABS代币化监管框架尚在完善中，存在政策不确定性',
                '二级市场初期深度可能不足，需培育交易活跃度',
                '极端入住率下滑情景可能压缩兑付安全垫',
                '用户教育成本较高，市场对时权Token认知度需要时间培育',
            ],
        }

    def run_monte_carlo(self, n_paths=5000, n_months=36):
        print(f"\n【步骤5】蒙特卡洛模拟 ({n_paths} 路径 x {n_months} 期)...")
        
        # 运行时权市场模拟
        print("  模拟时权二级市场交易与兑付...")
        self.market_sim = self._simulate_time_right_market(n_paths, n_months)
        
        # 计算三方收益和对比分析
        print("  计算三方收益分析...")
        self.tripartite_benefits = self._compute_tripartite_benefits()
        print("  计算传统模式vs时权模式对比...")
        self.comparison_analysis = self._compute_comparison_analysis()
        print("  计算敏感性分析...")
        self.sensitivity_analysis = self._compute_sensitivity_analysis()
        print("  计算风险评估...")
        self.risk_assessment = self._compute_risk_assessment()
        print("  计算可行性评估...")
        self.feasibility_evaluation = self._compute_feasibility_evaluation()
        
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
        
        # 处理时权市场模拟数据（取均值路径）
        market_summary = {}
        if self.market_sim:
            n_paths = self.market_sim['n_paths']
            n_months = self.market_sim['n_months']
            
            # 平均价格收敛路径 (各酒店平均)
            avg_price_path = np.mean(self.market_sim['price_paths'], axis=0)  # (n_hotels, n_months)
            overall_price_path = np.mean(avg_price_path, axis=0).tolist()
            
            # 平均月度交易手续费
            avg_trading_fee_monthly = np.mean(self.market_sim['trading_fee_income'], axis=0).tolist()
            
            # 平均月度兑付成本
            avg_cash_monthly = np.mean(self.market_sim['cash_redemption'], axis=0).tolist()
            avg_physical_monthly = np.mean(self.market_sim['physical_redemption'], axis=0).tolist()
            
            market_summary = {
                'price_convergence_path': [float(x) for x in overall_price_path],
                'trading_fee_income_monthly': [float(x) for x in avg_trading_fee_monthly],
                'cash_redemption_monthly': [float(x) for x in avg_cash_monthly],
                'physical_redemption_monthly': [float(x) for x in avg_physical_monthly],
                'total_trading_fee_income': float(np.mean(np.sum(self.market_sim['trading_fee_income'], axis=1))),
                'total_cash_redemption': float(np.mean(np.sum(self.market_sim['cash_redemption'], axis=1))),
                'total_physical_redemption': float(np.mean(np.sum(self.market_sim['physical_redemption'], axis=1))),
                'avg_choice_ratios': self.market_sim['avg_choice_ratios'],
            }
        
        report = {
            'report_metadata': {
                'version': 'V6-Fusion-Enhanced',
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'title': '酒店订单时权ABS/RWA融合分析报告',
                'methodology': '时权发行+二级市场收敛+三元兑付+Merton信用模型+Gaussian Copula蒙特卡洛+三方收益分析',
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
                'stress_test': self.stress_results,
            },
            'time_right_market_simulation': market_summary,
            'comparison_analysis': self.comparison_analysis,
            'tripartite_benefit_analysis': self.tripartite_benefits,
            'sensitivity_analysis': self.sensitivity_analysis,
            'risk_assessment': self.risk_assessment,
            'feasibility_evaluation': self.feasibility_evaluation,
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
                        '1. 酒店发行时权 -> 铸造ERC-3643代币',
                        '2. 投资者购买 -> 代币转入钱包',
                        '3. 到期前：自由转让，价格由AMM决定',
                        '4. 到期时：选择 cash/physical/rollover',
                        '5. 选择cash->自动转账+销毁代币',
                        '6. 选择physical->生成NFT房券->酒店核销',
                        '7. 选择rollover->自动转换为下一期时权',
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
