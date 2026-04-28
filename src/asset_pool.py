"""
资产池构建引擎 (Asset Pool Construction Engine)

从 16,000+ 酒店中，按多维度分层抽样构建具备分散化效应的资产池。
输出对标：ABS 发行说明书中的"基础资产池特征"章节。
"""

import pandas as pd
import numpy as np
from scipy import stats


class AssetPoolBuilder:
    """资产池构建器"""
    
    # 酒店等级权重配比（对标 CMBS 中不同业态配比）
    LEVEL_WEIGHTS = {
        '经济': 0.40,
        '舒适': 0.30,
        '高档': 0.20,
        '豪华': 0.10
    }
    
    # 地理集中度限制（单个区县不超过资产池的 X%）
    MAX_DISTRICT_CONCENTRATION = 0.25
    
    # 数据质量门槛
    MIN_RECORDS = 60  # 至少60天有效价格数据
    MIN_PRICE_VOL = 0.001  # 最低价格收益率波动
    
    def __init__(self, credit_df, hotel_info_df, prices_df):
        """
        Parameters:
        -----------
        credit_df : DataFrame
            信用模型输出，包含 hotelCode, hotelName, hotelLevel, pd, lgd, rating,
            avgPrice, minPrice, priceVolatility, expectedLoss, recordCount
        hotel_info_df : DataFrame
            酒店原始信息
        prices_df : DataFrame
            清洗后的价格数据
        """
        self.credit_df = credit_df.copy()
        self.hotel_info = hotel_info_df.copy()
        self.prices = prices_df.copy()
        self.prices['date'] = pd.to_datetime(self.prices['date'])
        
        # 解析地理位置
        self._parse_geography()
    
    def _parse_geography(self):
        """解析酒店经纬度到区县级别（简化版：按经纬度网格聚类）"""
        # 合并经纬度
        self.credit_df = self.credit_df.merge(
            self.hotel_info[['hotelCode', 'lon经度', 'lat纬度']],
            on='hotelCode', how='left'
        )
        
        # 用经纬度网格聚类模拟"区县"
        # 成都范围大致：lon 103.5-104.5, lat 30.3-31.3
        lon_bins = np.linspace(103.0, 105.0, 9)  # 8个网格
        lat_bins = np.linspace(30.0, 31.5, 7)    # 6个网格
        
        self.credit_df['district'] = (
            pd.cut(self.credit_df['lon经度'], bins=lon_bins, labels=False).astype(str) + '_' +
            pd.cut(self.credit_df['lat纬度'], bins=lat_bins, labels=False).astype(str)
        )
        
        # 处理缺失值
        self.credit_df['district'] = self.credit_df['district'].fillna('unknown')
    
    def _apply_quality_filters(self):
        """应用数据质量过滤"""
        df = self.credit_df.copy()
        
        # 记录数门槛
        df = df[df['recordCount'] >= self.MIN_RECORDS]
        
        # 排除极端异常值
        df = df[df['avgPrice'] > 1000]  # 排除明显错误数据
        df = df[df['avgPrice'] < 500000]  # 排除极端高价
        
        # 价格必须有波动（否则无法计算风险）
        df = df[df['priceVolatility'] > self.MIN_PRICE_VOL]
        
        # PD 必须在合理范围内（允许上限到0.50，包括边界）
        df = df[(df['pd'] > 0.0001) & (df['pd'] <= 0.50)]
        
        return df.reset_index(drop=True)
    
    def _stratified_sampling(self, df, target_pool_size=80):
        """
        分层抽样构建资产池
        
        策略：
        1. 按等级分层，每层按目标权重抽样
        2. 每层内按信用质量排序，优先选择PD适中（不太高也不太低）的酒店
        3. 控制地理集中度
        """
        selected = []
        
        for level, weight in self.LEVEL_WEIGHTS.items():
            level_df = df[df['hotelLevel'] == level].copy()
            
            if len(level_df) == 0:
                continue
            
            # 该层目标数量
            target_n = max(int(target_pool_size * weight), 5)
            
            # 按信用质量排序（优先选择BBB-A级，PD在0.5%-4%之间）
            # 这样的酒店既有风险可分析，又不会太高风险
            level_df['quality_score'] = level_df['pd'].apply(
                lambda x: 1.0 if 0.005 <= x <= 0.04 else 0.3
            )
            
            # 加入价格分散度奖励（价格越高、越分散越好）
            level_df['diversity_score'] = (
                (level_df['avgPrice'] - level_df['avgPrice'].min()) /
                (level_df['avgPrice'].max() - level_df['avgPrice'].min() + 1)
            )
            
            level_df['select_score'] = level_df['quality_score'] + level_df['diversity_score'] * 0.3
            level_df = level_df.sort_values('select_score', ascending=False)
            
            # 抽取，同时控制地理集中度
            level_selected = []
            district_counts = {}
            
            for _, row in level_df.iterrows():
                if len(level_selected) >= target_n:
                    break
                
                district = row['district']
                district_ratio = district_counts.get(district, 0) / target_pool_size
                
                if district_ratio < self.MAX_DISTRICT_CONCENTRATION:
                    level_selected.append(row)
                    district_counts[district] = district_counts.get(district, 0) + 1
            
            selected.extend(level_selected)
        
        pool_df = pd.DataFrame(selected)
        
        # 如果数量不足，从剩余酒店中补充
        if len(pool_df) < target_pool_size * 0.8:
            selected_codes = set(pool_df['hotelCode'].tolist())
            remaining = df[~df['hotelCode'].isin(selected_codes)].copy()
            remaining = remaining.sort_values('pd')
            
            needed = target_pool_size - len(pool_df)
            extra = remaining.head(min(needed, len(remaining)))
            pool_df = pd.concat([pool_df, extra], ignore_index=True)
        
        return pool_df.reset_index(drop=True)
    
    def build_pool(self, target_size=80):
        """
        构建资产池
        
        Returns:
        --------
        pool_df : DataFrame
            资产池酒店列表，包含所有信用指标 + 地理位置
        pool_stats : dict
            资产池统计摘要
        """
        # 质量过滤
        filtered = self._apply_quality_filters()
        print(f"  质量过滤后剩余: {len(filtered)} 家酒店")
        
        # 分层抽样
        pool_df = self._stratified_sampling(filtered, target_size)
        print(f"  分层抽样后资产池规模: {len(pool_df)} 家酒店")
        
        # 计算资产池统计
        pool_stats = self._compute_pool_statistics(pool_df)
        
        return pool_df, pool_stats
    
    def _compute_pool_statistics(self, pool_df):
        """计算资产池统计摘要"""
        total_notional = pool_df['avgPrice'].sum()
        
        stats_dict = {
            'pool_size': len(pool_df),
            'total_notional': total_notional,
            'avg_hotel_price': pool_df['avgPrice'].mean(),
            'median_hotel_price': pool_df['avgPrice'].median(),
            'min_hotel_price': pool_df['avgPrice'].min(),
            'max_hotel_price': pool_df['avgPrice'].max(),
            
            # 加权平均指标
            'wac': pool_df['avgPrice'].mean(),  # 简化：用平均价格代替
            'wtd_pd': np.average(pool_df['pd'], weights=pool_df['avgPrice']),
            'wtd_lgd': np.average(pool_df['lgd'], weights=pool_df['avgPrice']),
            'wtd_el': np.average(pool_df['expectedLoss'], weights=pool_df['avgPrice']),
            
            # 分散化指标
            'level_diversity': pool_df['hotelLevel'].value_counts().to_dict(),
            'district_diversity': len(pool_df['district'].unique()),
            'district_herfindahl': self._herfindahl_index(pool_df['district'].value_counts()),
            
            # 信用分布
            'rating_distribution': pool_df['rating'].value_counts().to_dict(),
            
            # 集中度
            'top5_concentration': pool_df.nlargest(5, 'avgPrice')['avgPrice'].sum() / total_notional,
            'top10_concentration': pool_df.nlargest(10, 'avgPrice')['avgPrice'].sum() / total_notional,
        }
        
        return stats_dict
    
    @staticmethod
    def _herfindahl_index(counts):
        """计算赫芬达尔指数（集中度指标，越低越分散）"""
        total = counts.sum()
        if total == 0:
            return 0
        shares = counts / total
        return (shares ** 2).sum()
    
    def compute_time_right_params(self, pool_df, discount_rate=0.08,
                                    safety_factor=0.8, issue_discount=0.25,
                                    time_to_maturity_months=36):
        """
        计算时权(Time-Right)参数
        单份时权 = "未来T时段一晚住宿权利"
        """
        room_estimate = {'经济': 60, '舒适': 80, '高档': 120, '豪华': 200}
        params = []
        for _, row in pool_df.iterrows():
            level = row['hotelLevel']
            rooms = room_estimate.get(level, 80)
            avg_price = row['avgPrice']
            min_price = row['minPrice']
            base_price = min_price if min_price > 0 else avg_price * 0.5
            occupancy = 0.62
            overbooking = 1.0 / max(occupancy, 0.3) * safety_factor
            issue_quantity = int(rooms * 365 * overbooking)
            T = time_to_maturity_months / 12.0
            forward_discount = np.exp(-discount_rate * T)
            issue_price = base_price * forward_discount * (1 - issue_discount)
            total_face_value = issue_price * issue_quantity
            spot_predicted = avg_price * (1 + 0.03 * T)
            params.append({
                'hotelCode': row['hotelCode'],
                'rooms': rooms,
                'occupancy': occupancy,
                'overbooking_multiplier': overbooking,
                'issue_quantity': issue_quantity,
                'issue_price': issue_price,
                'base_price': base_price,
                'avg_price': avg_price,
                'spot_predicted': spot_predicted,
                'total_face_value': total_face_value,
                'time_to_maturity': T,
                'hotelLevel': level,
            })
        return pd.DataFrame(params)

    def compute_monthly_cashflows(self, pool_df, n_months=36, base_occupancy=0.65):
        """
        计算资产池的月度预期现金流
        
        假设每家酒店每月现金流 = 房间数(估计) × 入住率 × 平均房价 × 30天
        
        Returns:
        --------
        cashflow_matrix : ndarray, shape (n_hotels, n_months)
            每家酒店每期的预期现金流
        """
        n_hotels = len(pool_df)
        cashflows = np.zeros((n_hotels, n_months))
        
        # 估算房间数（根据酒店等级）
        room_estimate = {
            '经济': 60,
            '舒适': 80,
            '高档': 120,
            '豪华': 200
        }
        
        for i, (_, row) in enumerate(pool_df.iterrows()):
            level = row['hotelLevel']
            rooms = room_estimate.get(level, 80)
            avg_price = row['avgPrice']
            
            # 月度现金流基础值
            monthly_base = rooms * base_occupancy * avg_price * 30
            
            # 加入季节性波动（简化：正弦波）
            seasonal = 1 + 0.15 * np.sin(2 * np.pi * np.arange(n_months) / 12)
            
            # 加入轻微随机增长趋势（年化2%）
            growth = (1 + 0.02) ** (np.arange(n_months) / 12)
            
            cashflows[i, :] = monthly_base * seasonal * growth
        
        return cashflows


def print_pool_characteristics(pool_df, pool_stats):
    """打印资产池特征表（对标 ABS 发行说明书格式）"""
    print("\n" + "=" * 80)
    print("资产池特征表")
    print("=" * 80)
    
    print(f"\n【基本规模】")
    print(f"  资产池酒店数量: {pool_stats['pool_size']} 家")
    print(f"  资产池总面值: CNY {pool_stats['total_notional']:,.0f}")
    print(f"  单家酒店平均面值: CNY {pool_stats['avg_hotel_price']:,.0f}")
    print(f"  单家酒店面值中位数: CNY {pool_stats['median_hotel_price']:,.0f}")
    
    print(f"\n【等级分布】")
    for level, count in sorted(pool_stats['level_diversity'].items()):
        pct = count / pool_stats['pool_size'] * 100
        print(f"  {level}: {count}家 ({pct:.1f}%)")
    
    print(f"\n【地理分散度】")
    print(f"  覆盖区县数: {pool_stats['district_diversity']} 个")
    print(f"  地区赫芬达尔指数: {pool_stats['district_herfindahl']:.3f} (越低越分散)")
    
    print(f"\n【信用分布】")
    for rating, count in sorted(pool_stats['rating_distribution'].items()):
        pct = count / pool_stats['pool_size'] * 100
        print(f"  {rating}: {count}家 ({pct:.1f}%)")
    
    print(f"\n【加权平均信用指标】")
    print(f"  加权平均PD: {pool_stats['wtd_pd']*100:.2f}%")
    print(f"  加权平均LGD: {pool_stats['wtd_lgd']*100:.1f}%")
    print(f"  加权平均预期损失(EL): {pool_stats['wtd_el']*100:.2f}%")
    
    print(f"\n【集中度指标】")
    print(f"  Top 5 集中度: {pool_stats['top5_concentration']*100:.1f}%")
    print(f"  Top 10 集中度: {pool_stats['top10_concentration']*100:.1f}%")
    
    print("\n【前10大借款人】")
    top10 = pool_df.nlargest(10, 'avgPrice')[['hotelCode', 'hotelName', 'hotelLevel', 
                                                'avgPrice', 'rating', 'pd']]
    for idx, row in top10.iterrows():
        print(f"  {row['hotelCode']}: {row['hotelName'][:20]:20s} | "
              f"{row['hotelLevel']:4s} | CNY {row['avgPrice']:>8,.0f} | "
              f"{row['rating']:3s} | PD={row['pd']*100:.2f}%")


if __name__ == '__main__':
    import os
    from credit_model import HotelCreditModel
    
    work_dir = r'C:\Users\weida\Desktop\酒店研究'
    
    prices = pd.read_csv(f'{work_dir}/data/cleaned_hotel_prices.csv')
    info = pd.read_csv(f'{work_dir}/data/hotel_info.csv')
    
    print("=" * 60)
    print("资产池构建引擎测试")
    print("=" * 60)
    
    # 先计算信用指标
    credit_model = HotelCreditModel(prices, info)
    credit_df = credit_model.compute_hotel_credit_metrics(min_records=50)
    
    # 构建资产池
    builder = AssetPoolBuilder(credit_df, info, prices)
    pool_df, pool_stats = builder.build_pool(target_size=80)
    
    print_pool_characteristics(pool_df, pool_stats)
