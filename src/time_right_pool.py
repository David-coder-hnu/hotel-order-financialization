"""
时权池构建引擎 (Time Right Pool Builder V7)

核心创新：
1. 每份时权 = 1间夜 × 1晚的实实在在的可入住权益
2. 超发机制：基于历史入住率的统计冗余
   超发倍数 = 1 / 入住率 × 安全系数
3. 资产池由80+家酒店的时权组成，实现分散化
4. 单份时权有发行价（面值）和底价（远期价格）

输出对标：ABS发行说明书"基础资产池特征" + 时权产品说明书
"""

import pandas as pd
import numpy as np
from scipy import stats


class TimeRightPoolBuilder:
    """时权池构建器：把酒店未来入住间夜打包成可金融化的时权资产池"""
    
    # 酒店等级权重配比
    LEVEL_WEIGHTS = {
        '经济': 0.40,
        '舒适': 0.30,
        '高档': 0.20,
        '豪华': 0.10
    }
    
    # 地理集中度限制
    MAX_DISTRICT_CONCENTRATION = 0.25
    
    # 数据质量门槛
    MIN_RECORDS = 60
    MIN_PRICE_VOL = 0.001
    
    # 时权超发安全系数
    SAFETY_FACTOR = 0.80
    
    def __init__(self, credit_df, hotel_info_df, prices_df, future_prices_df=None):
        self.credit_df = credit_df.copy()
        self.hotel_info = hotel_info_df.copy()
        self.prices = prices_df.copy()
        self.prices['date'] = pd.to_datetime(self.prices['date'])
        self.future_prices = future_prices_df
        
        self._parse_geography()
        self._merge_future_prices()
    
    def _parse_geography(self):
        """解析酒店经纬度到区县级别"""
        self.credit_df = self.credit_df.merge(
            self.hotel_info[['hotelCode', 'lon经度', 'lat纬度']],
            on='hotelCode', how='left'
        )
        
        lon_bins = np.linspace(103.0, 105.0, 9)
        lat_bins = np.linspace(30.0, 31.5, 7)
        
        self.credit_df['district'] = (
            pd.cut(self.credit_df['lon经度'], bins=lon_bins, labels=False).astype(str) + '_' +
            pd.cut(self.credit_df['lat纬度'], bins=lat_bins, labels=False).astype(str)
        )
        self.credit_df['district'] = self.credit_df['district'].fillna('unknown')
    
    def _merge_future_prices(self):
        """合并远期价格（底价）"""
        if self.future_prices is not None:
            self.credit_df = self.credit_df.merge(
                self.future_prices[['hotelCode', 'futurePrice']],
                on='hotelCode', how='left'
            )
        else:
            self.credit_df['futurePrice'] = self.credit_df['avgPrice'] * 0.7
    
    def _apply_quality_filters(self):
        """数据质量过滤"""
        df = self.credit_df.copy()
        df = df[df['recordCount'] >= self.MIN_RECORDS]
        df = df[df['avgPrice'] > 1000]
        df = df[df['avgPrice'] < 500000]
        df = df[df['priceVolatility'] > self.MIN_PRICE_VOL]
        df = df[(df['pd'] > 0.0001) & (df['pd'] < 0.50)]
        return df.reset_index(drop=True)
    
    @staticmethod
    def _estimate_room_count(hotel_level):
        """根据酒店等级估算房间数"""
        room_estimate = {
            '经济': 60,
            '舒适': 80,
            '高档': 120,
            '豪华': 200
        }
        return room_estimate.get(hotel_level, 80)
    
    def _compute_hotel_time_rights(self, row, occupancy=0.65):
        """
        计算单家酒店的时权发行参数
        
        核心公式：
        - 物理间夜 = 房间数 × 365
        - 超发倍数 = 1 / 入住率 × 安全系数
        - 发行总量 = 物理间夜 × 超发倍数
        - 单份时权发行价 = 预期年现金流 / 发行总量
        - 单份时权底价 = 远期价格（实物兑付时酒店承担的成本）
        """
        rooms = self._estimate_room_count(row['hotelLevel'])
        
        # 物理可售间夜
        physical_rights = rooms * 365
        
        # 超发倍数
        overbooking_multiplier = (1.0 / occupancy) * self.SAFETY_FACTOR
        
        # 发行总量（必须是整数）
        issued_rights = int(physical_rights * overbooking_multiplier)
        
        # 预期年现金流 = 房间数 × 入住率 × 平均房价 × 365
        expected_cashflow = rooms * occupancy * row['avgPrice'] * 365
        
        # 单份时权发行价格
        issue_price = expected_cashflow / issued_rights if issued_rights > 0 else 0
        
        # 底价 = 远期价格（实物兑付时酒店的实际成本）
        base_price = row.get('futurePrice', row['avgPrice'] * 0.70)
        
        return {
            'hotelCode': row['hotelCode'],
            'hotelName': row['hotelName'],
            'hotelLevel': row['hotelLevel'],
            'room_count': rooms,
            'occupancy_rate': occupancy,
            'avg_price': row['avgPrice'],
            'base_price': base_price,
            'physical_rights': physical_rights,
            'issued_rights': issued_rights,
            'overbooking_multiplier': overbooking_multiplier,
            'issue_price': issue_price,
            'expected_cashflow': expected_cashflow,
            'pd': row['pd'],
            'lgd': row['lgd'],
            'rating': row['rating'],
            'district': row['district']
        }
    
    def _stratified_sampling(self, df, target_pool_size=80):
        """分层抽样构建时权池"""
        selected = []
        
        for level, weight in self.LEVEL_WEIGHTS.items():
            level_df = df[df['hotelLevel'] == level].copy()
            if len(level_df) == 0:
                continue
            
            target_n = max(int(target_pool_size * weight), 5)
            
            # 优先选BBB-A级
            level_df['quality_score'] = level_df['pd'].apply(
                lambda x: 1.0 if 0.005 <= x <= 0.04 else 0.3
            )
            level_df['diversity_score'] = (
                (level_df['avgPrice'] - level_df['avgPrice'].min()) /
                (level_df['avgPrice'].max() - level_df['avgPrice'].min() + 1)
            )
            level_df['select_score'] = level_df['quality_score'] + level_df['diversity_score'] * 0.3
            level_df = level_df.sort_values('select_score', ascending=False)
            
            level_selected = []
            district_counts = {}
            
            for _, row in level_df.iterrows():
                if len(level_selected) >= target_n:
                    break
                
                district = row['district']
                district_ratio = district_counts.get(district, 0) / target_pool_size
                
                if district_ratio < self.MAX_DISTRICT_CONCENTRATION:
                    tr_info = self._compute_hotel_time_rights(row)
                    level_selected.append(tr_info)
                    district_counts[district] = district_counts.get(district, 0) + 1
            
            selected.extend(level_selected)
        
        pool_df = pd.DataFrame(selected)
        
        # 补充不足
        if len(pool_df) < target_pool_size * 0.8:
            selected_codes = set(pool_df['hotelCode'].tolist())
            remaining = df[~df['hotelCode'].isin(selected_codes)].copy()
            remaining = remaining.sort_values('pd')
            needed = target_pool_size - len(pool_df)
            extra_rows = remaining.head(min(needed, len(remaining)))
            extra = [self._compute_hotel_time_rights(row) for _, row in extra_rows.iterrows()]
            if extra:
                pool_df = pd.concat([pool_df, pd.DataFrame(extra)], ignore_index=True)
        
        return pool_df.reset_index(drop=True)
    
    def build_pool(self, target_size=80):
        """构建时权池"""
        filtered = self._apply_quality_filters()
        print(f"  质量过滤后剩余: {len(filtered)} 家酒店")
        
        pool_df = self._stratified_sampling(filtered, target_size)
        print(f"  分层抽样后资产池规模: {len(pool_df)} 家酒店")
        
        pool_stats = self._compute_pool_statistics(pool_df)
        
        return pool_df, pool_stats
    
    def _compute_pool_statistics(self, pool_df):
        """计算时权池统计摘要"""
        total_rights = pool_df['issued_rights'].sum()
        total_physical = pool_df['physical_rights'].sum()
        total_notional = (pool_df['issued_rights'] * pool_df['issue_price']).sum()
        
        stats_dict = {
            'pool_size': len(pool_df),
            'total_rights': int(total_rights),
            'total_physical_rights': int(total_physical),
            'overbooking_ratio': total_rights / total_physical if total_physical > 0 else 0,
            'total_notional': total_notional,
            'avg_issue_price': pool_df['issue_price'].mean(),
            'avg_base_price': pool_df['base_price'].mean(),
            'avg_price_spread': (pool_df['avg_price'] - pool_df['base_price']).mean(),
            
            'wtd_pd': np.average(pool_df['pd'], weights=pool_df['issued_rights']),
            'wtd_lgd': np.average(pool_df['lgd'], weights=pool_df['issued_rights']),
            'wtd_el': np.average(pool_df['pd'] * pool_df['lgd'], weights=pool_df['issued_rights']),
            
            'level_diversity': pool_df['hotelLevel'].value_counts().to_dict(),
            'district_diversity': len(pool_df['district'].unique()),
            'district_herfindahl': self._herfindahl_index(pool_df['district'].value_counts()),
            'rating_distribution': pool_df['rating'].value_counts().to_dict(),
            
            'top5_concentration': pool_df.nlargest(5, 'issued_rights')['issued_rights'].sum() / total_rights,
            'top10_concentration': pool_df.nlargest(10, 'issued_rights')['issued_rights'].sum() / total_rights,
        }
        
        return stats_dict
    
    @staticmethod
    def _herfindahl_index(counts):
        total = counts.sum()
        if total == 0:
            return 0
        shares = counts / total
        return (shares ** 2).sum()
    
    def compute_monthly_cashflows(self, pool_df, n_months=36, base_occupancy=0.62):
        """
        计算时权池的月度现金流
        
        每期现金流 = 被实际行权的时权 × 平均房价
                   + 未被行权但产生的空房收入（简化：空房也产生部分收入）
        """
        n_hotels = len(pool_df)
        cashflows = np.zeros((n_hotels, n_months))
        
        for i, (_, row) in enumerate(pool_df.iterrows()):
            rooms = row['room_count']
            avg_price = row['avg_price']
            base_price = row['base_price']
            
            # 月度物理间夜
            monthly_nights = rooms * 30
            
            # 被实物行权的间夜（时权持有者来住）
            exercised_nights = monthly_nights * base_occupancy
            
            # 未被行权但作为散客销售的间夜
            unsold_nights = monthly_nights * (1 - base_occupancy)
            
            # 月收入 = 行权部分按avg_price + 散客部分按base_price
            monthly_revenue = exercised_nights * avg_price + unsold_nights * base_price
            
            # 季节性波动
            seasonal = 1 + 0.15 * np.sin(2 * np.pi * np.arange(n_months) / 12)
            growth = (1 + 0.02) ** (np.arange(n_months) / 12)
            
            cashflows[i, :] = monthly_revenue * seasonal * growth
        
        return cashflows


def print_time_right_pool_characteristics(pool_df, pool_stats):
    """打印时权池特征表"""
    print("\n" + "=" * 80)
    print("时权池特征表 (Time Right Pool Characteristics)")
    print("=" * 80)
    
    print(f"\n【基本规模】")
    print(f"  资产池酒店数量: {pool_stats['pool_size']} 家")
    print(f"  物理可售间夜: {pool_stats['total_physical_rights']:,} 间夜")
    print(f"  时权发行总量: {pool_stats['total_rights']:,} 份")
    print(f"  超发比例: {pool_stats['overbooking_ratio']:.2f}x")
    print(f"  时权池总面值: ¥{pool_stats['total_notional']:,.0f}")
    print(f"  单份时权平均发行价: ¥{pool_stats['avg_issue_price']:,.0f}")
    print(f"  单份时权平均底价: ¥{pool_stats['avg_base_price']:,.0f}")
    
    print(f"\n【等级分布】")
    for level, count in sorted(pool_stats['level_diversity'].items()):
        pct = count / pool_stats['pool_size'] * 100
        print(f"  {level}: {count}家 ({pct:.1f}%)")
    
    print(f"\n【地理分散度】")
    print(f"  覆盖区县数: {pool_stats['district_diversity']} 个")
    print(f"  地区赫芬达尔指数: {pool_stats['district_herfindahl']:.3f}")
    
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
    
    print("\n【前10大时权发行方】")
    top10 = pool_df.nlargest(10, 'issued_rights')[['hotelCode', 'hotelName', 'hotelLevel',
                                                     'issued_rights', 'issue_price', 'rating', 'pd']]
    for idx, row in top10.iterrows():
        print(f"  {row['hotelCode']}: {row['hotelName'][:20]:20s} | "
              f"{row['hotelLevel']:4s} | {row['issued_rights']:>6,}份 | "
              f"¥{row['issue_price']:>6,.0f} | {row['rating']:3s} | PD={row['pd']*100:.2f}%")
