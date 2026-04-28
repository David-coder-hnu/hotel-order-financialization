"""
酒店级信用评级与违约模型 (Hotel-Level Credit Model)
基于真实价格数据推导 PD / LGD / 违约相关性

方法学参考：
- Merton 模型思路：用价格波动率推导 distance-to-default
- 穆迪企业债 PD 曲线映射
- 酒店行业 LGD 统计 (40%-60%)
"""

import pandas as pd
import numpy as np
from scipy import stats
from scipy.optimize import minimize_scalar
import warnings
warnings.filterwarnings('ignore')


class HotelCreditModel:
    """酒店信用评级模型"""
    
    def __init__(self, prices_df, hotel_info_df, future_prices_df=None):
        """
        Parameters:
        -----------
        prices_df : DataFrame
            清洗后的价格数据，列: date, hotelCode, price
        hotel_info_df : DataFrame
            酒店信息，列: hotelCode, hotelName, hotelLevel, lon经度, lat纬度
        future_prices_df : DataFrame, optional
            远期价格，列: hotelCode, futurePrice
        """
        self.prices = prices_df.copy()
        self.prices['date'] = pd.to_datetime(self.prices['date'])
        self.hotel_info = hotel_info_df.copy()
        self.future_prices = future_prices_df.copy() if future_prices_df is not None else None
        
        # 模型参数
        self.annual_risk_free_rate = 0.025  # 年化无风险利率 2.5%
        self.hotel_asset_volatility = 0.25  # 酒店资产价值波动率基准
        self.liability_ratio = 0.65  # 资产负债率基准
        self.lgd_base = 0.55  # 基准违约损失率 55%
        self.lgd_range = (0.35, 0.75)  # LGD 合理区间
        
    def _compute_price_returns(self, hotel_code):
        """计算单家酒店的价格收益率序列"""
        df = self.prices[self.prices['hotelCode'] == hotel_code].sort_values('date')
        if len(df) < 30:
            return None
        
        # 按周聚合取中位数价格（减少噪声）
        df['week'] = df['date'].dt.to_period('W')
        weekly = df.groupby('week')['price'].median()
        
        # 计算对数收益率
        log_returns = np.log(weekly / weekly.shift(1)).dropna()
        return log_returns
    
    def _estimate_garch_volatility(self, returns, omega=0.00001, alpha=0.10, beta=0.85):
        """
        简化GARCH(1,1)估计条件波动率
        使用固定参数（文献常用值），避免优化不收敛
        """
        if returns is None or len(returns) < 20:
            return None
        
        var = np.var(returns)
        vols = [np.sqrt(var)]
        
        for r in returns:
            var = omega + alpha * (r ** 2) + beta * var
            vols.append(np.sqrt(var))
        
        return vols[-1]  # 返回最新条件波动率
    
    def _merton_distance_to_default(self, price_vol, avg_price, min_price, hotel_level):
        """
        简化 Merton Distance-to-Default 模型
        
        违约边界设定为平均价格的 50-70%（反映经营底线）
        而非历史最低价，避免边界高于平均值导致所有酒店DD为负
        """
        if price_vol is None or avg_price <= 0 or min_price <= 0:
            return 1.0
        
        # 年化波动率
        sigma_annual = price_vol * np.sqrt(52)
        
        # 根据酒店等级调整波动率
        level_multiplier = {
            '经济': 1.2,
            '舒适': 1.0,
            '高档': 0.80,
            '豪华': 0.65
        }
        mult = level_multiplier.get(hotel_level, 1.0)
        sigma_annual *= mult
        sigma_annual = max(sigma_annual, 0.05)  # 波动率下限5%
        
        # 资产价值
        V = avg_price
        
        # 违约边界：平均价格的55%（保守估计）
        # 当收入下降到平均水平的55%时触发经营困难
        default_barrier = avg_price * 0.55
        
        # 漂移率
        mu = 0.03
        T = 1.0
        
        # Distance to Default
        dd = (np.log(V / default_barrier) + (mu - 0.5 * sigma_annual ** 2) * T) / (sigma_annual * np.sqrt(T))
        
        return max(dd, 0.1)  # 下限0.1，避免DD过小导致PD过高
    
    def _dd_to_pd(self, distance_to_default):
        """将 Distance-to-Default 映射为违约概率 (PD)"""
        # 基于历史实证：DD ~ N(-DD) 是标准正态CDF
        # 但需要做校准（Merton模型倾向于低估PD）
        base_pd = stats.norm.cdf(-distance_to_default)
        # 校准：乘以经验调整因子（文献中通常为1.5-3.0）
        calibrated_pd = min(base_pd * 2.5, 0.50)  # 上限50%
        return max(calibrated_pd, 0.001)  # 下限0.1%
    
    def _compute_lgd(self, hotel_code, avg_price, min_price, price_vol, hotel_level):
        """
        计算违约损失率 (LGD)
        
        方法：
        1. 基础值由酒店等级决定
        2. 价格稳定性调整：波动率越高 → LGD越高（回收越困难）
        3. 价格缓冲调整：avg/min 比率越大 → LGD越低（有更多缓冲）
        """
        # 等级基准LGD
        level_lgd = {
            '经济': 0.60,
            '舒适': 0.55,
            '高档': 0.50,
            '豪华': 0.40
        }
        base = level_lgd.get(hotel_level, 0.55)
        
        # 波动率调整：高波动 = 高LGD（±10%）
        if price_vol is not None:
            vol_annual = price_vol * np.sqrt(52)
            vol_adj = (vol_annual - 0.20) * 0.5  # 以20%为基准
        else:
            vol_adj = 0.0
        
        # 价格缓冲调整：avg/min 比率
        if min_price > 0:
            buffer_ratio = avg_price / min_price
            buffer_adj = -0.05 * (buffer_ratio - 2.0)  # 以2倍为基准
        else:
            buffer_adj = 0.0
        
        lgd = base + vol_adj + buffer_adj
        return np.clip(lgd, self.lgd_range[0], self.lgd_range[1])
    
    def _assign_rating(self, pd):
        """根据违约概率映射信用评级"""
        if pd < 0.0002:
            return 'AAA'
        elif pd < 0.0005:
            return 'AA'
        elif pd < 0.0015:
            return 'A'
        elif pd < 0.0040:
            return 'BBB'
        elif pd < 0.0100:
            return 'BB'
        elif pd < 0.0300:
            return 'B'
        elif pd < 0.1000:
            return 'CCC'
        elif pd < 0.3000:
            return 'CC'
        else:
            return 'C'
    
    def compute_hotel_credit_metrics(self, min_records=30):
        """计算所有酒店的信用指标"""
        codes = self.prices['hotelCode'].unique()
        return self.compute_hotel_credit_metrics_for_codes(codes, min_records)
    
    def compute_hotel_credit_metrics_for_codes(self, hotel_codes, min_records=30):
        """
        计算指定酒店列表的信用指标（优化版）
        
        Returns:
        --------
        DataFrame: 包含 hotelCode, PD, LGD, EL, DD, Rating, price_vol 等
        """
        results = []
        total = len(hotel_codes)
        
        if total > 50:
            print(f"  开始计算 {total} 家酒店的信用指标...")
        
        # 预加载酒店信息映射（加速查询）
        info_map = self.hotel_info.set_index('hotelCode')[['hotelName', 'hotelLevel']].to_dict('index')
        
        for idx, code in enumerate(hotel_codes):
            if total > 50 and (idx + 1) % 50 == 0:
                print(f"    进度: {idx+1}/{total} ({(idx+1)/total*100:.0f}%)")
            
            returns = self._compute_price_returns(code)
            if returns is None or len(returns) < min_records:
                continue
            
            hotel_prices = self.prices[self.prices['hotelCode'] == code]['price']
            avg_price = hotel_prices.mean()
            min_price = hotel_prices.min()
            max_price = hotel_prices.max()
            
            info = info_map.get(code, {})
            hotel_level = info.get('hotelLevel', '经济')
            hotel_name = info.get('hotelName', code)
            
            price_vol = self._estimate_garch_volatility(returns)
            if price_vol is None:
                price_vol = np.std(returns)
            
            dd = self._merton_distance_to_default(price_vol, avg_price, min_price, hotel_level)
            prob_default = self._dd_to_pd(dd)
            lgd = self._compute_lgd(code, avg_price, min_price, price_vol, hotel_level)
            el = prob_default * lgd
            rating = self._assign_rating(prob_default)
            
            results.append({
                'hotelCode': code,
                'hotelName': hotel_name,
                'hotelLevel': hotel_level,
                'avgPrice': avg_price,
                'minPrice': min_price,
                'maxPrice': max_price,
                'priceVolatility': price_vol,
                'annualVolatility': price_vol * np.sqrt(52) if price_vol else None,
                'distanceToDefault': dd,
                'pd': prob_default,
                'lgd': lgd,
                'expectedLoss': el,
                'rating': rating,
                'recordCount': len(hotel_prices)
            })
        
        df = pd.DataFrame(results)
        if len(df) > 0:
            df = df.sort_values('pd').reset_index(drop=True)
        return df
    
    def compute_correlation_matrix(self, credit_df, min_records=30):
        """
        计算酒店间违约相关性矩阵
        
        方法：
        1. 计算各酒店收益率序列的相关性作为代理
        2. 同一区县、同一等级的酒店赋予更高相关性
        """
        codes = credit_df['hotelCode'].tolist()
        n = len(codes)
        
        if n < 2:
            return np.array([[1.0]])
        
        # 收集收益率序列
        returns_dict = {}
        for code in codes:
            r = self._compute_price_returns(code)
            if r is not None and len(r) >= min_records:
                returns_dict[code] = r
        
        # 如果序列长度不同，取共同时间段
        corr_matrix = np.eye(n)
        
        for i in range(n):
            for j in range(i + 1, n):
                code_i, code_j = codes[i], codes[j]
                
                if code_i in returns_dict and code_j in returns_dict:
                    # 对收益率序列做对齐（简单取最小长度）
                    ri = returns_dict[code_i].values
                    rj = returns_dict[code_j].values
                    min_len = min(len(ri), len(rj))
                    if min_len >= 10:
                        corr = np.corrcoef(ri[:min_len], rj[:min_len])[0, 1]
                        if not np.isnan(corr):
                            # 违约相关性通常低于收益率相关性（转换）
                            default_corr = corr * 0.3  # 经验转换因子
                            corr_matrix[i, j] = max(default_corr, 0.0)
                            corr_matrix[j, i] = max(default_corr, 0.0)
                else:
                    # 无法计算时，基于等级和地理位置赋予基础相关性
                    level_i = credit_df[credit_df['hotelCode'] == code_i]['hotelLevel'].values[0]
                    level_j = credit_df[credit_df['hotelCode'] == code_j]['hotelLevel'].values[0]
                    
                    if level_i == level_j:
                        base_corr = 0.08  # 同等级基础相关
                    else:
                        base_corr = 0.03  # 不同等级基础相关
                    
                    corr_matrix[i, j] = base_corr
                    corr_matrix[j, i] = base_corr
        
        return corr_matrix


def simulate_default_events(credit_df, corr_matrix, n_periods=36, n_paths=10000, seed=42):
    """
    使用 Gaussian Copula 模拟违约事件
    
    Parameters:
    -----------
    credit_df : DataFrame
        包含 hotelCode, pd 列
    corr_matrix : ndarray
        违约相关性矩阵
    n_periods : int
        模拟期数（月）
    n_paths : int
        模拟路径数
    seed : int
        随机种子
    
    Returns:
    --------
    default_matrix : ndarray, shape (n_paths, n_hotels, n_periods)
        违约指示矩阵，1=违约，0=未违约
    """
    np.random.seed(seed)
    n_hotels = len(credit_df)
    
    if n_hotels == 0:
        return np.zeros((n_paths, 0, n_periods), dtype=bool)
    
    pds = credit_df['pd'].values
    
    # 计算Copula的相关性矩阵（转换为Gaussian Copula参数）
    # 使用多变量正态分布抽样
    
    # Cholesky分解
    try:
        L = np.linalg.cholesky(corr_matrix + np.eye(n_hotels) * 0.001)
    except np.linalg.LinAlgError:
        # 如果矩阵不正定，做特征值修正
        eigvals, eigvecs = np.linalg.eigh(corr_matrix)
        eigvals = np.maximum(eigvals, 0.001)
        corr_matrix = eigvecs @ np.diag(eigvals) @ eigvecs.T
        L = np.linalg.cholesky(corr_matrix)
    
    # 每期的违约阈值（假设违约在时间上是均匀分布的）
    # 简化：使用月度违约概率
    monthly_pd = 1 - (1 - pds) ** (1 / 12)
    monthly_pd = np.clip(monthly_pd, 0.00001, 0.5)
    
    default_matrix = np.zeros((n_paths, n_hotels, n_periods), dtype=bool)
    
    for path in range(n_paths):
        # 为每家酒店生成 correlated uniform 变量
        # 每期使用相同的系统因子 + 异质性因子
        z = np.random.standard_normal((n_hotels,))
        correlated_z = L @ z
        
        # 每期增加一些随机性
        for t in range(n_periods):
            # 异质性因子
            epsilon = np.random.standard_normal(n_hotels) * 0.5
            u = correlated_z * 0.7 + epsilon * 0.3
            
            # 转换为均匀分布
            uniform = stats.norm.cdf(u)
            
            # 判断违约
            default_matrix[path, :, t] = uniform < monthly_pd
        
        # 一旦违约，后续期数保持违约状态
        for i in range(n_hotels):
            if np.any(default_matrix[path, i, :]):
                first_default = np.where(default_matrix[path, i, :])[0][0]
                default_matrix[path, i, first_default:] = True
    
    return default_matrix


if __name__ == '__main__':
    # 快速测试
    import os
    work_dir = r'C:\Users\weida\Desktop\酒店研究'
    
    prices = pd.read_csv(f'{work_dir}/data/cleaned_hotel_prices.csv')
    info = pd.read_csv(f'{work_dir}/data/hotel_info.csv')
    
    print("=" * 60)
    print("酒店信用评级模型测试")
    print("=" * 60)
    
    model = HotelCreditModel(prices, info)
    credit_df = model.compute_hotel_credit_metrics(min_records=50)
    
    print(f"\n成功计算 {len(credit_df)} 家酒店的信用指标")
    print("\n信用分布:")
    print(credit_df['rating'].value_counts().sort_index())
    
    print("\nPD 统计:")
    print(credit_df['pd'].describe())
    
    print("\nLGD 统计:")
    print(credit_df['lgd'].describe())
    
    print("\n前10家最优信用酒店:")
    print(credit_df.head(10)[['hotelCode', 'hotelName', 'rating', 'pd', 'lgd', 'expectedLoss']])
