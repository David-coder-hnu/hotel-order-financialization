"""
酒店订单ABS/RWA资产证券化专业金融模拟引擎 V6

主控模块，串联：
1. 资产池构建 (AssetPoolBuilder)
2. 信用模型 (HotelCreditModel)
3. 分层结构 (TrancheStructure)
4. 现金流瀑布 (WaterfallEngine)
5. 蒙特卡洛模拟 (MonteCarloSimulator)

输出：完整ABS分析数据集
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from credit_model import HotelCreditModel, simulate_default_events
from asset_pool import AssetPoolBuilder, print_pool_characteristics
from tranche_structure import TrancheStructure, print_tranche_structure
from waterfall_engine import WaterfallEngine, print_waterfall_summary
from monte_carlo_simulator import MonteCarloSimulator, print_mc_summary


class HotelABSEngine:
    """酒店订单ABS引擎"""
    
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
        
        # 最终结果
        self.mc_results = None
        self.mc_analysis = None
        self.stress_results = None
        self.baseline_waterfall = None
        self.baseline_tranche_results = None
        
    def load_data(self):
        """加载数据"""
        print("【步骤1】加载数据...")
        self.prices = pd.read_csv(f'{self.work_dir}/data/cleaned_hotel_prices.csv')
        self.hotel_info = pd.read_csv(f'{self.work_dir}/data/hotel_info.csv')
        
        # 尝试加载远期价格
        fp_path = f'{self.work_dir}/data/hotel_future_prices.csv'
        if os.path.exists(fp_path):
            self.future_prices = pd.read_csv(fp_path)
        
        print(f"  价格记录: {len(self.prices):,} 条")
        print(f"  酒店信息: {len(self.hotel_info):,} 家")
        
    def run_credit_model(self, min_records=50, max_hotels=500):
        """运行信用评级模型（带预筛选）"""
        print("\n【步骤2】运行酒店信用评级模型...")
        
        # 步骤2a: 快速预筛选（向量化，极快）
        print("  步骤2a: 快速预筛选候选酒店...")
        quick_stats = self.prices.groupby('hotelCode').agg({
            'price': ['count', 'mean', 'std', 'min', 'max']
        }).reset_index()
        quick_stats.columns = ['hotelCode', 'recordCount', 'avgPrice', 'priceStd', 'minPrice', 'maxPrice']
        
        # 应用过滤条件
        candidates = quick_stats[
            (quick_stats['recordCount'] >= min_records) &
            (quick_stats['avgPrice'] > 1000) &
            (quick_stats['avgPrice'] < 500000) &
            (quick_stats['priceStd'] > 0)
        ].copy()
        
        # 如果候选太多，按价格标准差排序选前max_hotels（波动性越大越有意思）
        if len(candidates) > max_hotels:
            candidates = candidates.nlargest(max_hotels, 'priceStd')
        
        candidate_codes = candidates['hotelCode'].tolist()
        print(f"  预筛选后候选酒店: {len(candidate_codes)} 家")
        
        # 步骤2b: 对候选酒店详细计算信用指标
        print("  步骤2b: 详细信用分析...")
        model = HotelCreditModel(self.prices, self.hotel_info, self.future_prices)
        
        # min_records=8: 4个月约17周，要求至少8周有效数据即可
        self.credit_df = model.compute_hotel_credit_metrics_for_codes(candidate_codes, min_records=8)
        
        print(f"  成功评级 {len(self.credit_df)} 家酒店")
        print(f"  信用分布: {dict(self.credit_df['rating'].value_counts().sort_index())}")
        
        # 相关性矩阵推迟到资产池构建后计算
        self.corr_matrix = None
        
        return self.credit_df
    
    def build_asset_pool(self, target_size=80):
        """构建资产池"""
        print("\n【步骤3】构建资产池...")
        
        builder = AssetPoolBuilder(self.credit_df, self.hotel_info, self.prices)
        self.pool_df, self.pool_stats = builder.build_pool(target_size=target_size)
        
        # 打印资产池特征
        print_pool_characteristics(self.pool_df, self.pool_stats)
        
        # 计算月度现金流
        self.pool_cashflows = builder.compute_monthly_cashflows(
            self.pool_df, n_months=36, base_occupancy=0.62
        )
        
        print(f"\n  资产池月度现金流范围: CNY {self.pool_cashflows.sum(axis=0).min():,.0f} - "
              f"CNY {self.pool_cashflows.sum(axis=0).max():,.0f}")
        
        return self.pool_df, self.pool_stats
    
    def design_tranche_structure(self):
        """设计分层结构"""
        print("\n【步骤4】设计ABS分层结构...")
        
        struct = TrancheStructure(
            pool_notional=self.pool_stats['total_notional'],
            wtd_pd=self.pool_stats['wtd_pd'],
            wtd_lgd=self.pool_stats['wtd_lgd'],
            wtd_el=self.pool_stats['wtd_el']
        )
        
        self.tranches = struct.design_tranches(
            senior_pct=0.68, mezz_pct=0.20, junior_pct=0.08, equity_pct=0.04
        )
        self.ce_stats = struct.compute_credit_enhancement(reserve_pct=0.03)
        
        print_tranche_structure(self.tranches, self.ce_stats)
        
        # OC/IC测试
        pool_balance = self.pool_stats['total_notional'] * 1.05
        pool_income = self.pool_cashflows.sum(axis=0)[0]
        tests = struct.run_oc_ic_tests(pool_balance, pool_income)
        
        print(f"\n【初始覆盖测试】")
        print(f"  OC比率: {tests['oc_ratio']*100:.1f}% {'通过OK' if tests['oc_pass'] else '不通过FAIL'}")
        print(f"  IC比率: {tests['ic_ratio']*100:.1f}% {'通过OK' if tests['ic_pass'] else '不通过FAIL'}")
        
        return self.tranches, self.ce_stats
    
    def run_monte_carlo(self, n_paths=5000, n_months=36):
        """运行蒙特卡洛模拟"""
        print(f"\n【步骤5】蒙特卡洛模拟 ({n_paths} 路径 × {n_months} 期)...")
        
        # 只对资产池酒店计算相关性矩阵
        pool_codes = self.pool_df['hotelCode'].tolist()
        print(f"  计算资产池({len(pool_codes)}家)违约相关性矩阵...")
        
        model = HotelCreditModel(self.prices, self.hotel_info, self.future_prices)
        pool_credit_df = self.credit_df[self.credit_df['hotelCode'].isin(pool_codes)].copy()
        pool_corr = model.compute_correlation_matrix(pool_credit_df)
        
        n_pool = len(self.pool_df)
        if pool_corr.shape[0] != n_pool:
            pool_corr = np.eye(n_pool) * 0.7 + np.ones((n_pool, n_pool)) * 0.15
            np.fill_diagonal(pool_corr, 1.0)
        
        sim = MonteCarloSimulator(
            self.pool_df, pool_corr, self.tranches, self.pool_cashflows,
            n_paths=n_paths, n_months=n_months, seed=42
        )
        
        # 生成违约
        print("  生成违约路径...")
        sim.generate_defaults()
        
        # 统计违约率
        default_rates = []
        for path in range(n_paths):
            cumulative_defaults = np.sum(np.any(sim.default_matrix[path, :, :], axis=1))
            default_rates.append(cumulative_defaults / n_pool)
        
        print(f"  平均累计违约率: {np.mean(default_rates)*100:.2f}%")
        print(f"  违约率范围: {np.min(default_rates)*100:.2f}% - {np.max(default_rates)*100:.2f}%")
        
        # 运行瀑布
        print("  运行现金流瀑布...")
        self.mc_results = sim.run_waterfall_all_paths()
        
        # 分析损失
        print("  分析损失分布...")
        self.mc_analysis = sim.analyze_tranche_losses(self.mc_results)
        
        # 压力测试
        print("  运行压力测试...")
        self.stress_results = sim.stress_test(self.mc_results)
        
        print_mc_summary(self.mc_analysis, self.stress_results)
        
        return self.mc_analysis, self.stress_results
    
    def run_baseline_waterfall(self):
        """运行基准情景（无违约）的现金流瀑布"""
        print("\n【步骤6】基准情景现金流瀑布...")
        
        n_hotels = len(self.pool_df)
        n_months = 36
        
        # 无违约矩阵
        default_matrix = np.zeros((1, n_hotels, n_months), dtype=bool)
        
        engine = WaterfallEngine(
            self.tranches, self.pool_cashflows, default_matrix
        )
        
        self.baseline_waterfall, self.baseline_tranche_results = engine.run_waterfall(path=0)
        
        print_waterfall_summary(self.baseline_waterfall, self.baseline_tranche_results)
        
        return self.baseline_waterfall, self.baseline_tranche_results
    
    def generate_rwa_architecture(self):
        """生成RWA代币化架构描述"""
        print("\n【步骤7】RWA代币化架构设计...")
        
        rwa = {
            'architecture': {
                'off_chain': {
                    'spv': {
                        'name': '酒店订单ABS特殊目的载体(SPV)',
                        'jurisdiction': '开曼群岛 / 新加坡',
                        'purpose': '破产隔离、持有基础资产、发行证券',
                        'assets': '酒店未来住宿订单收益权',
                        'custodian': '独立托管银行'
                    },
                    'servicer': {
                        'name': '酒店运营服务商',
                        'responsibilities': [
                            '月度现金流归集',
                            '违约监控与报告',
                            '储备金管理'
                        ]
                    },
                    'trustee': {
                        'name': '信托受托人',
                        'responsibilities': [
                            '代表投资者利益',
                            '监督SPV运营',
                            '触发器执行'
                        ]
                    }
                },
                'on_chain': {
                    'token_standard': 'ERC-3643 (T-REX Protocol)',
                    'blockchain': 'Ethereum / Polygon',
                    'tokens': [
                        {
                            'name': 'HT-Senior',
                            'symbol': 'HT-SEN',
                            'tranche': 'Senior',
                            'compliance': '合格投资者(KYC/AML)',
                            'transfer_restriction': '白名单制度'
                        },
                        {
                            'name': 'HT-Mezzanine',
                            'symbol': 'HT-MEZ',
                            'tranche': 'Mezzanine',
                            'compliance': '合格投资者',
                            'transfer_restriction': '白名单制度'
                        },
                        {
                            'name': 'HT-Junior',
                            'symbol': 'HT-JUN',
                            'tranche': 'Junior',
                            'compliance': '合格投资者',
                            'transfer_restriction': '锁定期6个月'
                        },
                        {
                            'name': 'HT-Equity',
                            'symbol': 'HT-EQU',
                            'tranche': 'Equity',
                            'compliance': '专业投资者',
                            'transfer_restriction': '锁定期12个月'
                        }
                    ],
                    'oracle': {
                        'provider': 'Chainlink / 自建预言机',
                        'data_feeds': [
                            '月度服务报告(Servicer Report)',
                            '酒店入住率数据',
                            '违约事件通知',
                            'OC/IC测试结果'
                        ],
                        'update_frequency': '每月一次'
                    },
                    'smart_contracts': {
                        'token_contract': '安全代币发行合约',
                        'waterfall_contract': '现金流瀑布分配合约',
                        'reserve_contract': '储备金管理合约',
                        'trigger_contract': '触发器监控合约'
                    }
                }
            },
            'smart_contract_logic': {
                'monthly_waterfall': [
                    '1. 预言机推送月度服务报告',
                    '2. 触发器合约检查OC/IC测试',
                    '3. 如果触发加速清偿，更新分配模式',
                    '4. 瀑布合约按优先级分配代币持有人',
                    '5. 储备金合约自动补充/释放',
                    '6. 事件日志记录所有分配'
                ],
                'triggers': [
                    'OC测试失败 (<100%) → 启动Early Amortization',
                    'IC测试失败 (<100%) → 启动Early Amortization',
                    '累计违约率 > 15% → Event of Default',
                    '连续3期IC失败 → Event of Default'
                ]
            },
            'legal_structure': {
                'asset_transfer': '真实出售(True Sale)给SPV',
                'bankruptcy_remote': '发起人破产不影响SPV',
                'perfected_security_interest': '完善担保权益登记',
                'regulatory_compliance': '符合当地证券法和代币监管要求'
            }
        }
        
        print("  RWA架构设计完成")
        print(f"  代币标准: {rwa['architecture']['on_chain']['token_standard']}")
        print(f"  代币数量: {len(rwa['architecture']['on_chain']['tokens'])} 种")
        
        return rwa
    
    def compile_report(self):
        """编译完整报告数据"""
        print("\n【步骤8】编译完整报告数据...")
        
        report = {
            'report_metadata': {
                'version': 'V6',
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'title': '酒店订单ABS/RWA资产证券化专业分析报告',
                'methodology': '基于Merton模型的PD推导 + Gaussian Copula违约相关 + 现金流瀑布分配 + 10,000路径蒙特卡洛'
            },
            'asset_pool': {
                'hotels': self.pool_df.to_dict('records'),
                'statistics': self.pool_stats,
            },
            'credit_model': {
                'methodology': 'Merton Distance-to-Default + GARCH波动率',
                'pool_credit_summary': {
                    'wtd_pd': self.pool_stats['wtd_pd'],
                    'wtd_lgd': self.pool_stats['wtd_lgd'],
                    'wtd_el': self.pool_stats['wtd_el'],
                }
            },
            'tranche_structure': self.tranches,
            'credit_enhancement': self.ce_stats,
            'baseline_waterfall': {
                'monthly_summary': self.baseline_waterfall.to_dict('records'),
                'tranche_results': self.baseline_tranche_results
            },
            'monte_carlo': {
                'n_paths': 10000,
                'n_months': 36,
                'tranche_analysis': self.mc_analysis,
                'stress_test': self.stress_results
            },
            'rwa_architecture': self.generate_rwa_architecture()
        }
        
        # 保存JSON
        output_path = f'{self.work_dir}/output/abs_report_v6.json'
        
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
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_serializable, f, ensure_ascii=False, indent=2)
        
        print(f"  报告已保存: {output_path}")
        
        return report
    
    def run_full_analysis(self, pool_size=80, n_paths=10000):
        """运行完整分析流程"""
        print("=" * 80)
        print("酒店订单ABS/RWA资产证券化专业金融模拟 V6")
        print("=" * 80)
        print(f"分析日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"蒙特卡洛路径: {n_paths:,}")
        print(f"资产池目标规模: {pool_size} 家酒店")
        
        self.load_data()
        self.run_credit_model(min_records=50)
        self.build_asset_pool(target_size=pool_size)
        self.design_tranche_structure()
        self.run_monte_carlo(n_paths=n_paths, n_months=36)
        self.run_baseline_waterfall()
        report = self.compile_report()
        
        print("\n" + "=" * 80)
        print("分析完成！")
        print("=" * 80)
        
        return report


def main():
    engine = HotelABSEngine()
    engine.run_full_analysis(pool_size=80, n_paths=10000)


if __name__ == '__main__':
    main()
