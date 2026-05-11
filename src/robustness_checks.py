"""
稳健性检验模块 (Robustness Checks Module)

实现:
1. KMV简化模型 → 替代 Merton DD 的 PD 估计
2. Bootstrap 置信区间 → tranche EL 的统计显著性
3. Copula 敏感性分析 → ρ_sys, ρ_idio, copula family 的影响
4. 假设验证报告生成
"""

import numpy as np
import pandas as pd
from scipy import stats
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')


class KMVCreditModel:
    """KMV简化信用模型 —— 替代 Merton DD 作为稳健性检验"""

    def __init__(self, prices_df, hotel_info_df):
        self.prices = prices_df.copy()
        self.prices['date'] = pd.to_datetime(self.prices['date'])
        self.hotel_info = hotel_info_df.copy()

    def compute_kmv_pd(self, returns, avg_price, hotel_level):
        """
        KMV简化方法计算 PD:
        - 使用资产价值波动率(非股票波动率)
        - 基于历史违约频率校准违约点
        - 不依赖 Merton 的结构性假设

        KMV 的核心改进:
        1. 违约点(default point) = 短期负债 + 0.5 × 长期负债, 而非固定 55%
        2. DD = (V - DPT) / (V × σ), 而非 Merton 的 ln(V/D)/σ
        3. 使用经验映射 DD → EDF, 而非正态分布假设
        """
        if returns is None or len(returns) < 20:
            return None, None

        # 年化波动率 (日度收益率 → 年化: sqrt(252))
        sigma_annual = np.std(returns) * np.sqrt(252)

        # 等级调整 (KMV 使用行业分类调整)
        level_multiplier = {'经济': 1.25, '舒适': 1.05, '高档': 0.85, '豪华': 0.65}
        mult = level_multiplier.get(hotel_level, 1.0)
        sigma_annual *= mult

        # KMV 违约点: 短期负债(经营成本) + 0.5 × 长期负债
        # 对酒店: 短期 = 日均运营成本 ≈ avg_price × 0.35
        #         长期 = 固定成本 ≈ avg_price × 0.25
        short_term_liability = avg_price * 0.35
        long_term_liability = avg_price * 0.25
        default_point = short_term_liability + 0.5 * long_term_liability

        V = avg_price
        sigma_annual = max(sigma_annual, 0.03)

        # KMV Distance-to-Default
        dd_kmv = (V - default_point) / (V * sigma_annual)

        # KMV 经验映射: DD → EDF (Expected Default Frequency)
        # 使用分段线性映射替代正态分布
        if dd_kmv >= 3.0:
            edf = 0.001
        elif dd_kmv >= 2.0:
            edf = 0.001 + (3.0 - dd_kmv) * 0.004
        elif dd_kmv >= 1.5:
            edf = 0.005 + (2.0 - dd_kmv) * 0.01
        elif dd_kmv >= 1.0:
            edf = 0.01 + (1.5 - dd_kmv) * 0.04
        elif dd_kmv >= 0.5:
            edf = 0.03 + (1.0 - dd_kmv) * 0.08
        elif dd_kmv >= 0.0:
            edf = 0.07 + (0.5 - dd_kmv) * 0.12
        else:
            edf = 0.15 + abs(dd_kmv) * 0.10

        pd = min(max(edf, 0.001), 0.50)
        return pd, dd_kmv

    def compute_all(self, hotel_codes, min_records=30):
        """计算所有指定酒店的 KMV PD"""
        results = []
        # 构建信息映射 - 兼容列名差异
        info_cols = list(self.hotel_info.columns)
        code_col = [c for c in info_cols if 'hotelCode' in c or 'hotelcode' in c.lower()]
        level_col = [c for c in info_cols if 'Level' in c or 'level' in c.lower()]
        name_col = [c for c in info_cols if 'Name' in c or 'name' in c.lower()]
        code_col = code_col[0] if code_col else info_cols[0]
        level_col = level_col[0] if level_col else info_cols[2] if len(info_cols) > 2 else info_cols[0]
        name_col = name_col[0] if name_col else info_cols[1] if len(info_cols) > 1 else info_cols[0]

        info_map = {}
        for _, row in self.hotel_info.iterrows():
            info_map[row[code_col]] = {
                'level': row.get(level_col, '经济'),
                'name': row.get(name_col, str(row[code_col]))
            }

        for code in tqdm(hotel_codes, desc="  KMV credit scoring", unit="hotel"):
            df = self.prices[self.prices['hotelCode'] == code].sort_values('date')
            if len(df) < min_records:
                continue

            # 使用日度对数收益率（保留更多数据点）
            daily_returns = np.log(df['price'] / df['price'].shift(1)).dropna()

            if len(daily_returns) < 30:
                continue
            returns = daily_returns

            avg_price = df['price'].mean()
            info = info_map.get(code, {})
            level = info.get('level', '经济')
            name = info.get('name', code)

            pd_val, dd_val = self.compute_kmv_pd(returns, avg_price, level)
            if pd_val is None or np.isnan(pd_val):
                continue

            results.append({
                'hotelCode': code,
                'hotelName': name,
                'hotelLevel': level,
                'avgPrice': avg_price,
                'kmv_pd': pd_val,
                'kmv_dd': dd_val,
            })

        return pd.DataFrame(results)


class CopulaSensitivityAnalyzer:
    """Copula 敏感性分析: Gaussian vs t-Copula + 参数扫描"""

    def __init__(self, n_hotels, base_corr_matrix, pds, lgds, n_months=36):
        self.n_hotels = n_hotels
        self.base_corr = base_corr_matrix
        self.pds = np.array(pds)
        self.lgds = np.array(lgds)
        self.n_months = n_months

    def generate_defaults_gaussian(self, n_paths, rho_sys, rho_idio, seed=42):
        """Gaussian Copula 违约生成 (可调参数版)"""
        np.random.seed(seed)
        monthly_pds = 1 - (1 - self.pds) ** (1 / 12)
        monthly_pds = np.clip(monthly_pds, 0.00001, 0.5)

        # 构建参数化相关矩阵
        corr = np.eye(self.n_hotels) * (1 - rho_sys) + np.ones((self.n_hotels, self.n_hotels)) * rho_sys
        np.fill_diagonal(corr, 1.0)

        try:
            L = np.linalg.cholesky(corr + np.eye(self.n_hotels) * 0.001)
        except np.linalg.LinAlgError:
            eigvals, eigvecs = np.linalg.eigh(corr)
            eigvals = np.maximum(eigvals, 0.001)
            corr = eigvecs @ np.diag(eigvals) @ eigvecs.T
            corr = (corr + corr.T) / 2
            L = np.linalg.cholesky(corr)

        default_matrix = np.zeros((n_paths, self.n_hotels, self.n_months), dtype=bool)

        Z = np.random.standard_normal((n_paths, self.n_hotels))
        correlated_Z = Z @ L.T

        for t in range(self.n_months):
            epsilon = np.random.standard_normal((n_paths, self.n_hotels)) * rho_idio
            u = correlated_Z * rho_sys + epsilon * (1 - rho_sys)
            uniform = stats.norm.cdf(u)
            defaulted = uniform < monthly_pds.reshape(1, -1)
            if t > 0:
                defaulted = defaulted | default_matrix[:, :, t-1]
            default_matrix[:, :, t] = defaulted

        return default_matrix

    def generate_defaults_tcopula(self, n_paths, rho_sys, rho_idio, nu=5, seed=42):
        """
        t-Copula 违约生成 —— 捕捉尾部依赖

        t-Copula vs Gaussian Copula 的关键区别:
        - Gaussian: 尾部独立 —— 极端事件不相关
        - t-Copula (ν 自由度): 尾部依赖 —— 极端事件同时发生的概率更高
          - ν → ∞ → 趋近 Gaussian
          - ν = 3-5 → 显著尾部依赖
          - ν = 1 → Cauchy (最重尾)

        这是 2008 年金融危机后 Basel III 从 Gaussian 转向 t-Copula 的核心原因。
        """
        np.random.seed(seed)
        monthly_pds = 1 - (1 - self.pds) ** (1 / 12)
        monthly_pds = np.clip(monthly_pds, 0.00001, 0.5)

        corr = np.eye(self.n_hotels) * (1 - rho_sys) + np.ones((self.n_hotels, self.n_hotels)) * rho_sys
        np.fill_diagonal(corr, 1.0)

        try:
            L = np.linalg.cholesky(corr + np.eye(self.n_hotels) * 0.001)
        except np.linalg.LinAlgError:
            eigvals, eigvecs = np.linalg.eigh(corr)
            eigvals = np.maximum(eigvals, 0.001)
            corr = eigvecs @ np.diag(eigvals) @ eigvecs.T
            corr = (corr + corr.T) / 2
            L = np.linalg.cholesky(corr)

        default_matrix = np.zeros((n_paths, self.n_hotels, self.n_months), dtype=bool)

        # t-Copula: 从多元t分布采样
        Z = np.random.standard_normal((n_paths, self.n_hotels))
        correlated_Z = Z @ L.T

        # χ² 随机变量 / ν 作为缩放因子 → t分布
        chi_sq = np.random.chisquare(nu, (n_paths, 1)) / nu
        t_samples = correlated_Z / np.sqrt(chi_sq)

        for t in range(self.n_months):
            epsilon = np.random.standard_normal((n_paths, self.n_hotels)) * rho_idio
            u = t_samples * rho_sys + epsilon * (1 - rho_sys)
            uniform = stats.t.cdf(u, df=nu)
            defaulted = uniform < monthly_pds.reshape(1, -1)
            if t > 0:
                defaulted = defaulted | default_matrix[:, :, t-1]
            default_matrix[:, :, t] = defaulted

        return default_matrix

    def compute_loss_rates(self, default_matrix, pool_cashflows, tranche_structure):
        """从违约矩阵计算各分层损失率"""
        n_paths = default_matrix.shape[0]
        results = {t['name']: [] for t in tranche_structure}

        for path in range(n_paths):
            path_defaults = default_matrix[path]
            total_loss = 0
            for h in range(self.n_hotels):
                if path_defaults[h].any():
                    first_default_month = np.argmax(path_defaults[h])
                    remaining_cf = pool_cashflows[h, first_default_month:].sum()
                    total_loss += remaining_cf * self.lgds[h]

            remaining_pool = pool_cashflows.sum()
            for t in tranche_structure:
                attachment = t.get('loss_attachment', 0)
                detachment = t.get('loss_detachment', 1)
                tranche_notional = t['notional']
                pool_loss_rate = total_loss / remaining_pool if remaining_pool > 0 else 0
                tranche_loss = max(0, min(pool_loss_rate, detachment) - attachment) / (detachment - attachment) if detachment > attachment else 0
                results[t['name']].append(tranche_loss)

        return {name: np.array(losses) for name, losses in results.items()}


class BootstrapAnalyzer:
    """Bootstrap 置信区间分析"""

    @staticmethod
    def bootstrap_tranche_el(loss_rates, n_bootstrap=2000, ci_level=0.95):
        """
        对分层损失率做 Bootstrap 重采样
        计算 EL 的置信区间
        """
        rng = np.random.RandomState(42)
        n_original = len(loss_rates)
        bootstrap_means = []

        for _ in range(n_bootstrap):
            idx = rng.randint(0, n_original, n_original)
            bootstrap_means.append(np.mean(loss_rates[idx]))

        bootstrap_means = np.array(bootstrap_means)
        alpha = (1 - ci_level) / 2
        ci_lower = np.percentile(bootstrap_means, alpha * 100)
        ci_upper = np.percentile(bootstrap_means, (1 - alpha) * 100)
        return {
            'mean': np.mean(loss_rates),
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'ci_level': ci_level,
            'bootstrap_mean': np.mean(bootstrap_means),
            'bootstrap_std': np.std(bootstrap_means),
        }


def run_full_robustness_suite(credit_df, pool_df, tranches, pool_cashflows,
                               n_paths=2000, n_months=36):
    """
    运行完整稳健性检验套件

    Returns:
    --------
    dict: 包含所有稳健性检验结果
    """
    print("\n" + "=" * 70)
    print("稳健性检验套件 (Robustness Suite)")
    print("=" * 70)

    n_hotels = len(pool_df)
    pds = pool_df['pd'].values
    lgds = pool_df['lgd'].values

    # 构建基准相关矩阵
    rho_sys = 0.7
    corr = np.eye(n_hotels) * (1 - rho_sys) + np.ones((n_hotels, n_hotels)) * rho_sys
    np.fill_diagonal(corr, 1.0)

    analyzer = CopulaSensitivityAnalyzer(n_hotels, corr, pds, lgds, n_months)

    results = {}
    results['parameters'] = {
        'n_hotels': n_hotels,
        'n_paths': n_paths,
        'n_months': n_months,
        'weighted_pd': float(np.average(pds)),
        'weighted_lgd': float(np.average(lgds)),
    }

    # =========== Test 1: Copula Family Comparison ===========
    print("\n[1/4] Copula Family 对比: Gaussian vs t-Copula (ν=3,5,10)...")
    family_results = {}

    # Gaussian benchmark
    dm_gauss = analyzer.generate_defaults_gaussian(n_paths, rho_sys=0.7, rho_idio=0.3)
    lr_gauss = analyzer.compute_loss_rates(dm_gauss, pool_cashflows, tranches)
    family_results['Gaussian'] = {name: float(np.mean(l)) for name, l in lr_gauss.items()}
    family_results['_detail_Gaussian'] = {name: {
        'mean': float(np.mean(l)), 'var95': float(np.percentile(l, 95)),
        'var99': float(np.percentile(l, 99)), 'max': float(np.max(l))
    } for name, l in lr_gauss.items()}

    # t-Copula variants
    for nu, label in [(3, 't-Copula ν=3'), (5, 't-Copula ν=5'), (10, 't-Copula ν=10')]:
        dm_t = analyzer.generate_defaults_tcopula(n_paths, rho_sys=0.7, rho_idio=0.3, nu=nu)
        lr_t = analyzer.compute_loss_rates(dm_t, pool_cashflows, tranches)
        family_results[label] = {name: float(np.mean(l)) for name, l in lr_t.items()}
        family_results[f'_detail_{label}'] = {name: {
            'mean': float(np.mean(l)), 'var95': float(np.percentile(l, 95)),
            'var99': float(np.percentile(l, 99)), 'max': float(np.max(l))
        } for name, l in lr_t.items()}

    results['copula_family_comparison'] = family_results

    # Print comparison
    print(f"\n  {'Copula':<20} {'Senior EL':>12} {'Mezz EL':>12} {'Junior EL':>12} {'Equity EL':>12}")
    print("  " + "-" * 68)
    for model in ['Gaussian', 't-Copula ν=3', 't-Copula ν=5', 't-Copula ν=10']:
        f = family_results[model]
        print(f"  {model:<20} {f['Senior']*100:>11.4f}% {f['Mezzanine']*100:>11.4f}% {f['Junior']*100:>11.4f}% {f['Equity']*100:>11.4f}%")

    # =========== Test 2: ρ_sys Sensitivity ===========
    print("\n[2/4] ρ_sys 敏感性扫描 (0.5 → 0.9)...")
    rho_values = [0.5, 0.6, 0.7, 0.8, 0.9]
    rho_results = {}
    for rho in rho_values:
        dm = analyzer.generate_defaults_gaussian(n_paths, rho_sys=rho, rho_idio=0.3)
        lr = analyzer.compute_loss_rates(dm, pool_cashflows, tranches)
        rho_results[f'rho={rho}'] = {name: float(np.mean(l)) for name, l in lr.items()}
        rho_results[f'_detail_rho={rho}'] = {name: {
            'mean': float(np.mean(l)), 'var95': float(np.percentile(l, 95)),
            'var99': float(np.percentile(l, 99))
        } for name, l in lr.items()}

    results['rho_sensitivity'] = rho_results

    print(f"\n  {'ρ_sys':<10} {'Senior EL':>12} {'Mezz EL':>12} {'Junior EL':>12} {'Equity EL':>12}")
    print("  " + "-" * 58)
    for rho in rho_values:
        f = rho_results[f'rho={rho}']
        print(f"  {rho:<10} {f['Senior']*100:>11.4f}% {f['Mezzanine']*100:>11.4f}% {f['Junior']*100:>11.4f}% {f['Equity']*100:>11.4f}%")

    # =========== Test 3: Bootstrap CI ===========
    print("\n[3/4] Bootstrap 置信区间 (2,000 重采样)...")
    bootstrap = BootstrapAnalyzer()
    bootstrap_results = {}
    for name, losses in lr_gauss.items():
        ci = bootstrap.bootstrap_tranche_el(losses, n_bootstrap=2000)
        bootstrap_results[name] = ci
        print(f"  {name:<12}: EL={ci['mean']*100:.4f}%  CI95=[{ci['ci_lower']*100:.4f}%, {ci['ci_upper']*100:.4f}%]")

    results['bootstrap_ci'] = bootstrap_results

    # =========== Test 4: Tail Risk Assessment ===========
    print("\n[4/4] 尾部风险评估: Gaussian vs t-Copula...")
    tail_results = {}
    for copula_name, detail_key in [('Gaussian', '_detail_Gaussian'), ('t-Copula ν=3', '_detail_t-Copula ν=3')]:
        d = family_results[detail_key]
        tail_results[copula_name] = {}
        for tranche in ['Senior', 'Mezzanine', 'Junior', 'Equity']:
            td = d[tranche]
            tail_results[copula_name][tranche] = {
                'var95': td['var95'],
                'var99': td['var99'],
                'max': td['max'],
                'tail_ratio': td['var99'] / max(td['var95'], 1e-10) if td['var95'] > 1e-10 else float('inf'),
            }

    results['tail_risk'] = tail_results

    print(f"\n  {'Tranche':<12} {'Gauss VaR99':>13} {'t-Cop VaR99':>13} {'Tail Ratio':>11}")
    print("  " + "-" * 50)
    for tranche in ['Senior', 'Mezzanine', 'Junior', 'Equity']:
        gv99 = tail_results['Gaussian'][tranche]['var99']
        tv99 = tail_results['t-Copula ν=3'][tranche]['var99']
        ratio = tv99 / max(gv99, 1e-10) if gv99 > 1e-10 else float('inf')
        print(f"  {tranche:<12} {gv99*100:>12.6f}% {tv99*100:>12.6f}% {ratio:>10.1f}x")

    print("\n" + "=" * 70)
    print("稳健性检验完成")
    print("=" * 70)

    return results


if __name__ == '__main__':
    print("稳健性检验模块已就绪。")
    print("用法: from robustness_checks import run_full_robustness_suite")
