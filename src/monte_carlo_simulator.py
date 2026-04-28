"""
蒙特卡洛模拟引擎 (Monte Carlo Simulation Engine)

运行10,000条违约路径，输出分层级损失分布统计。
对标：穆迪理想损失(EL)和极端损失(WCL)评级框架。
"""

import numpy as np
import pandas as pd
from scipy import stats
from waterfall_engine import WaterfallEngine


class MonteCarloSimulator:
    """ABS蒙特卡洛模拟器"""
    
    def __init__(self, pool_df, corr_matrix, tranches, pool_cashflows,
                 n_paths=10000, n_months=36, seed=42):
        """
        Parameters:
        -----------
        pool_df : DataFrame
            资产池酒店列表，包含 pd, lgd
        corr_matrix : ndarray
            违约相关性矩阵
        tranches : list of dict
            分层结构
        pool_cashflows : ndarray
            资产池月度现金流
        n_paths : int
            模拟路径数
        n_months : int
            模拟期数
        seed : int
            随机种子
        """
        self.pool_df = pool_df
        self.corr_matrix = corr_matrix
        self.tranches = tranches
        self.pool_cashflows = pool_cashflows
        self.n_paths = n_paths
        self.n_months = n_months
        self.seed = seed
        
        self.n_hotels = len(pool_df)
        self.pds = pool_df['pd'].values
        self.lgds = pool_df['lgd'].values
        
        # 预生成违约矩阵
        self.default_matrix = None
        self.loss_matrix = None  # 每期实际损失
    
    def generate_defaults(self):
        """
        使用Gaussian Copula生成违约事件矩阵
        """
        np.random.seed(self.seed)
        
        if self.n_hotels == 0:
            self.default_matrix = np.zeros((self.n_paths, 0, self.n_months), dtype=bool)
            return
        
        # 月度违约概率
        monthly_pds = 1 - (1 - self.pds) ** (1 / 12)
        monthly_pds = np.clip(monthly_pds, 0.00001, 0.5)
        
        # Cholesky分解
        try:
            L = np.linalg.cholesky(self.corr_matrix + np.eye(self.n_hotels) * 0.001)
        except np.linalg.LinAlgError:
            eigvals, eigvecs = np.linalg.eigh(self.corr_matrix)
            eigvals = np.maximum(eigvals, 0.001)
            corr_fixed = eigvecs @ np.diag(eigvals) @ eigvecs.T
            L = np.linalg.cholesky(corr_fixed)
        
        default_matrix = np.zeros((self.n_paths, self.n_hotels, self.n_months), dtype=bool)
        
        # 为效率，批量处理
        batch_size = 500
        n_batches = (self.n_paths + batch_size - 1) // batch_size
        
        for batch in range(n_batches):
            start = batch * batch_size
            end = min((batch + 1) * batch_size, self.n_paths)
            actual_batch = end - start
            
            if (batch + 1) % 2 == 0 or batch == n_batches - 1:
                print(f"    违约路径生成: {end}/{self.n_paths} ({end/self.n_paths*100:.0f}%)")
            
            # 生成系统因子
            Z = np.random.standard_normal((actual_batch, self.n_hotels))
            correlated_Z = Z @ L.T
            
            for t in range(self.n_months):
                # 异质性因子
                epsilon = np.random.standard_normal((actual_batch, self.n_hotels)) * 0.5
                u = correlated_Z * 0.7 + epsilon * 0.3
                
                # 转换为uniform
                uniform = stats.norm.cdf(u)
                
                # 违约判断
                defaulted = uniform < monthly_pds.reshape(1, -1)
                
                # 已违约的保持违约
                if t > 0:
                    previously_defaulted = default_matrix[start:end, :, t-1]
                    defaulted = defaulted | previously_defaulted
                
                default_matrix[start:end, :, t] = defaulted
        
        self.default_matrix = default_matrix
        
        # 计算每期实际损失（考虑LGD）
        self._compute_losses()
    
    def _compute_losses(self):
        """计算每期各路径的实际损失"""
        self.loss_matrix = np.zeros((self.n_paths, self.n_months))
        
        for path in range(self.n_paths):
            for t in range(self.n_months):
                # 本期新违约的酒店
                if t == 0:
                    new_defaults = self.default_matrix[path, :, t]
                else:
                    new_defaults = self.default_matrix[path, :, t] & ~self.default_matrix[path, :, t-1]
                
                # 本期损失 = 新违约酒店的面值 × LGD
                loss = np.sum(self.pool_cashflows[new_defaults, t:].sum(axis=1) * self.lgds[new_defaults])
                self.loss_matrix[path, t] = loss
    
    def run_waterfall_all_paths(self, servicing_fee_rate=0.005):
        """
        对所有路径运行现金流瀑布
        
        Returns:
        --------
        all_tranche_results : list of dict
            每路径的各分层结果
        """
        if self.default_matrix is None:
            self.generate_defaults()
        
        engine = WaterfallEngine(
            self.tranches, self.pool_cashflows, self.default_matrix,
            servicing_fee_rate=servicing_fee_rate
        )
        
        all_results = engine.run_all_paths()
        return all_results
    
    def analyze_tranche_losses(self, all_results):
        """
        分析各分层的损失分布
        
        Returns:
        --------
        analysis : dict
            各分层损失统计
        """
        analysis = {}
        
        for tranche_name in [t['name'] for t in self.tranches]:
            losses = [r[tranche_name]['loss_rate'] for r in all_results]
            losses = np.array(losses)
            
            # 基础统计
            analysis[tranche_name] = {
                'mean_loss_rate': np.mean(losses),
                'std_loss_rate': np.std(losses),
                'median_loss_rate': np.median(losses),
                'min_loss_rate': np.min(losses),
                'max_loss_rate': np.max(losses),
                
                # VaR / CVaR
                'var_95': np.percentile(losses, 95),
                'var_99': np.percentile(losses, 99),
                'cvar_95': np.mean(losses[losses >= np.percentile(losses, 95)]) if np.any(losses >= np.percentile(losses, 95)) else 0,
                'cvar_99': np.mean(losses[losses >= np.percentile(losses, 99)]) if np.any(losses >= np.percentile(losses, 99)) else 0,
                
                # 损失概率
                'prob_any_loss': np.mean(losses > 0.001),
                'prob_total_loss': np.mean(losses > 0.95),
                
                # 损失分布直方图数据
                'loss_histogram': np.histogram(losses, bins=50, range=(0, 1))[0].tolist(),
                'loss_bins': np.histogram(losses, bins=50, range=(0, 1))[1].tolist(),
            }
            
            # 对标评级
            analysis[tranche_name]['implied_rating'] = self._map_loss_to_rating(
                analysis[tranche_name]['mean_loss_rate'],
                analysis[tranche_name]['var_99']
            )
        
        return analysis
    
    def _map_loss_to_rating(self, el, wcl_99):
        """
        将预期损失和99%WCL映射到信用评级
        
        参考穆迪评级映射表（简化版）
        """
        # 基于预期损失
        if el < 0.0003 and wcl_99 < 0.005:
            return 'Aaa'
        elif el < 0.0010 and wcl_99 < 0.015:
            return 'Aa'
        elif el < 0.0030 and wcl_99 < 0.040:
            return 'A'
        elif el < 0.0080 and wcl_99 < 0.100:
            return 'Baa'
        elif el < 0.0200 and wcl_99 < 0.250:
            return 'Ba'
        elif el < 0.0500 and wcl_99 < 0.500:
            return 'B'
        elif el < 0.1500:
            return 'Caa'
        else:
            return 'Ca-C'
    
    def stress_test(self, all_results, stress_scenarios=None):
        """
        压力测试
        
        Parameters:
        -----------
        all_results : list of dict
            基准情景结果
        stress_scenarios : list of dict, optional
            压力情景参数列表
        """
        if stress_scenarios is None:
            stress_scenarios = [
                {'name': '基准情景', 'pd_multiplier': 1.0, 'lgd_multiplier': 1.0},
                {'name': '轻度压力', 'pd_multiplier': 1.5, 'lgd_multiplier': 1.1},
                {'name': '中度压力', 'pd_multiplier': 2.5, 'lgd_multiplier': 1.3},
                {'name': '重度压力', 'pd_multiplier': 4.0, 'lgd_multiplier': 1.6},
                {'name': '极端压力', 'pd_multiplier': 6.0, 'lgd_multiplier': 2.0},
            ]
        
        stress_results = {}
        
        for scenario in stress_scenarios:
            name = scenario['name']
            pd_mult = scenario['pd_multiplier']
            lgd_mult = scenario['lgd_multiplier']
            
            # 调整PD和LGD
            original_pds = self.pds.copy()
            original_lgds = self.lgds.copy()
            
            self.pds = np.clip(original_pds * pd_mult, 0.0001, 0.99)
            self.lgds = np.clip(original_lgds * lgd_mult, 0.1, 0.95)
            
            # 重新运行（简化：直接调整违约矩阵的概率）
            # 实际应该重新生成default_matrix，但为效率，用近似
            # 这里直接复用all_results做比例调整
            
            adjusted_results = []
            for r in all_results:
                adjusted = {}
                for t_name, t_res in r.items():
                    adj_res = t_res.copy()
                    # 损失率调整：近似 = 原损失 × PD调整 × LGD调整
                    adj_res['loss_rate'] = min(adj_res['loss_rate'] * pd_mult * lgd_mult, 1.0)
                    adj_res['loss'] = adj_res['initial_notional'] * adj_res['loss_rate']
                    adjusted[t_name] = adj_res
                adjusted_results.append(adjusted)
            
            # 分析
            scenario_analysis = self.analyze_tranche_losses(adjusted_results)
            stress_results[name] = scenario_analysis
            
            # 恢复
            self.pds = original_pds
            self.lgds = original_lgds
        
        return stress_results


def print_mc_summary(mc_analysis, stress_results=None):
    """打印蒙特卡洛分析摘要"""
    print("\n" + "=" * 80)
    print("蒙特卡洛模拟分析摘要")
    print("=" * 80)
    
    print(f"\n{'分层':<12} {'预期损失':>10} {'VaR 95%':>10} {'VaR 99%':>10} {'CVaR 95%':>10} {'损失概率':>10} {'隐含评级':>8}")
    print("-" * 90)
    
    for name, stats in mc_analysis.items():
        print(f"{name:<12} {stats['mean_loss_rate']*100:>9.2f}% {stats['var_95']*100:>9.2f}% "
              f"{stats['var_99']*100:>9.2f}% {stats['cvar_95']*100:>9.2f}% "
              f"{stats['prob_any_loss']*100:>9.1f}% {stats['implied_rating']:>8s}")
    
    if stress_results:
        print("\n【压力测试：各情景下 Senior 层损失率】")
        print(f"\n{'情景':<12} {'预期损失':>10} {'VaR 95%':>10} {'VaR 99%':>10} {'CVaR 95%':>10} {'隐含评级':>8}")
        print("-" * 70)
        
        for scenario_name, scenario_stats in stress_results.items():
            if 'Senior' in scenario_stats:
                s = scenario_stats['Senior']
                print(f"{scenario_name:<12} {s['mean_loss_rate']*100:>9.2f}% {s['var_95']*100:>9.2f}% "
                      f"{s['var_99']*100:>9.2f}% {s['cvar_95']*100:>9.2f}% {s['implied_rating']:>8s}")


if __name__ == '__main__':
    print("=" * 60)
    print("蒙特卡洛模拟引擎测试")
    print("=" * 60)
    
    # 模拟参数
    n_hotels = 20
    n_months = 36
    n_paths = 1000
    
    # 模拟资产池
    pool_df = pd.DataFrame({
        'hotelCode': [f'H{i:04d}' for i in range(n_hotels)],
        'pd': np.random.uniform(0.005, 0.05, n_hotels),
        'lgd': np.random.uniform(0.40, 0.70, n_hotels),
    })
    
    # 相关性矩阵
    corr_matrix = np.eye(n_hotels) * 0.7 + np.ones((n_hotels, n_hotels)) * 0.3
    np.fill_diagonal(corr_matrix, 1.0)
    
    # 现金流
    pool_cashflows = np.ones((n_hotels, n_months)) * 50000
    
    # 分层
    tranches = [
        {'name': 'Senior', 'notional': 600000, 'coupon_monthly': 0.045/12},
        {'name': 'Mezzanine', 'notional': 200000, 'coupon_monthly': 0.065/12},
        {'name': 'Junior', 'notional': 100000, 'coupon_monthly': 0.095/12},
        {'name': 'Equity', 'notional': 50000, 'coupon_monthly': 0.0},
    ]
    
    sim = MonteCarloSimulator(pool_df, corr_matrix, tranches, pool_cashflows,
                              n_paths=n_paths, n_months=n_months)
    
    # 生成违约
    sim.generate_defaults()
    
    # 运行瀑布
    all_results = sim.run_waterfall_all_paths()
    
    # 分析
    mc_analysis = sim.analyze_tranche_losses(all_results)
    stress = sim.stress_test(all_results)
    
    print_mc_summary(mc_analysis, stress)
