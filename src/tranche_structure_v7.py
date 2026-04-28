"""
时权ABS分层结构设计 V7

核心创新：每层支持现金兑付 + 实物兑付双轨制
- Senior: 机构固收，100%现金
- Mezzanine: 混合配置，70%现金 + 30%实物
- Junior: 偏重消费，40%现金 + 60%实物
- Equity: 消费权益层，10%现金 + 90%实物

实物兑付的成本 = 底价（远低于现金兑付成本）
"""

import pandas as pd
import numpy as np
from scipy import stats


class TimeRightTrancheStructure:
    """时权ABS分层结构设计器"""
    
    def __init__(self, pool_notional, total_rights, wtd_pd, wtd_lgd, wtd_el, avg_base_price):
        self.pool_notional = pool_notional
        self.total_rights = total_rights
        self.wtd_pd = wtd_pd
        self.wtd_lgd = wtd_lgd
        self.wtd_el = wtd_el
        self.avg_base_price = avg_base_price
        self.tranches = []
    
    def design_tranches(self, senior_pct=0.68, mezz_pct=0.20, junior_pct=0.08, equity_pct=0.04):
        """设计支持双轨兑付的分层结构"""
        assert abs(senior_pct + mezz_pct + junior_pct + equity_pct - 1.0) < 0.001
        
        tranche_configs = [
            {
                'name': 'Senior',
                'subordination': junior_pct + mezz_pct + equity_pct,
                'coupon_annual': 0.045,
                'target_rating': 'AAA',
                'payment_priority': 1,
                'cash_redemption_pct': 1.00,
                'physical_redemption_pct': 0.00,
                'promised_return': 0.045,
                'physical_discount': 0.00,
                'investor_type': '机构投资者',
            },
            {
                'name': 'Mezzanine',
                'subordination': junior_pct + equity_pct,
                'coupon_annual': 0.065,
                'target_rating': 'BBB',
                'payment_priority': 2,
                'cash_redemption_pct': 0.70,
                'physical_redemption_pct': 0.30,
                'promised_return': 0.065,
                'physical_discount': 0.30,
                'investor_type': '高净值个人',
            },
            {
                'name': 'Junior',
                'subordination': equity_pct,
                'coupon_annual': 0.095,
                'target_rating': 'B',
                'payment_priority': 3,
                'cash_redemption_pct': 0.40,
                'physical_redemption_pct': 0.60,
                'promised_return': 0.095,
                'physical_discount': 0.35,
                'investor_type': '常旅客/小投资者',
            },
            {
                'name': 'Equity',
                'subordination': 0.0,
                'coupon_annual': 0.0,
                'target_rating': 'NR',
                'payment_priority': 4,
                'cash_redemption_pct': 0.10,
                'physical_redemption_pct': 0.90,
                'promised_return': 0.0,
                'physical_discount': 0.50,
                'investor_type': 'C端消费者',
            }
        ]
        
        sizes = {'Senior': senior_pct, 'Mezzanine': mezz_pct, 
                'Junior': junior_pct, 'Equity': equity_pct}
        
        tranches = []
        cumulative_ce = 0.0
        
        for cfg in tranche_configs:
            name = cfg['name']
            size_pct = sizes[name]
            notional = self.pool_notional * size_pct
            rights = int(self.total_rights * size_pct)
            
            tranche = {
                'name': name,
                'size_pct': size_pct,
                'notional': notional,
                'rights': rights,
                'coupon_annual': cfg['coupon_annual'],
                'coupon_monthly': cfg['coupon_annual'] / 12,
                'target_rating': cfg['target_rating'],
                'payment_priority': cfg['payment_priority'],
                'subordination': cfg['subordination'],
                'credit_support_pct': cfg['subordination'],
                'cash_redemption_pct': cfg['cash_redemption_pct'],
                'physical_redemption_pct': cfg['physical_redemption_pct'],
                'promised_return': cfg['promised_return'],
                'physical_discount': cfg['physical_discount'],
                'investor_type': cfg['investor_type'],
                'loss_attachment': cumulative_ce,
                'loss_detachment': cumulative_ce + size_pct,
                'expected_loss': self._estimate_tranche_el(
                    cumulative_ce, cumulative_ce + size_pct, self.wtd_pd, self.wtd_lgd
                )
            }
            
            tranches.append(tranche)
            cumulative_ce += size_pct
        
        self.tranches = tranches
        return tranches
    
    def _estimate_tranche_el(self, attach, detach, pd, lgd):
        """简化估计某分层的预期损失"""
        mean_loss = pd * lgd
        std_loss = mean_loss * 2.5
        
        if std_loss < 1e-6:
            return 0.0
        
        def truncated_mean(mean, std, threshold):
            if std < 1e-6:
                return max(mean - threshold, 0)
            z = (threshold - mean) / std
            return std * stats.norm.pdf(z) + (mean - threshold) * (1 - stats.norm.cdf(z))
        
        el = truncated_mean(mean_loss, std_loss, attach) - truncated_mean(mean_loss, std_loss, detach)
        el = min(max(el, 0), detach - attach)
        tranche_el_pct = el / max(detach - attach, 1e-6)
        
        return tranche_el_pct
    
    def compute_redemption_cost(self, tranche, pool_df):
        """
        计算某分层的兑付成本
        
        核心洞察：实物兑付的成本 = 底价，远低于现金兑付成本！
        """
        name = tranche['name']
        rights = tranche['rights']
        issue_price = tranche['notional'] / rights if rights > 0 else 0
        
        cash_pct = tranche['cash_redemption_pct']
        physical_pct = tranche['physical_redemption_pct']
        
        # 现金兑付部分
        cash_rights = int(rights * cash_pct)
        cash_return_per_right = issue_price * (1 + tranche['promised_return'])
        cash_cost = cash_rights * cash_return_per_right
        
        # 实物兑付部分：酒店成本 = 底价（房间本来就可能空着）
        physical_rights = rights - cash_rights
        avg_base_price = pool_df['base_price'].mean()
        physical_cost_per_right = avg_base_price * (1 - tranche['physical_discount'])
        physical_cost = physical_rights * physical_cost_per_right
        
        # 如果全部现金兑付的成本
        all_cash_cost = rights * cash_return_per_right
        
        return {
            'cash_rights': cash_rights,
            'cash_cost': cash_cost,
            'physical_rights': physical_rights,
            'physical_cost': physical_cost,
            'total_cost': cash_cost + physical_cost,
            'cost_saving_vs_all_cash': all_cash_cost - (cash_cost + physical_cost)
        }
    
    def compute_credit_enhancement(self, reserve_pct=0.03, excess_spread_annual=0.015):
        """计算信用增级量化指标"""
        oc_pct = 0.02
        reserve_target = self.pool_notional * reserve_pct
        
        pool_yield = 0.08
        wac_coupon = sum(t['size_pct'] * t['coupon_annual'] for t in self.tranches)
        excess_spread = pool_yield - wac_coupon
        
        ce_stats = {
            'overcollateralization_pct': oc_pct,
            'overcollateralization_amount': self.pool_notional * oc_pct,
            'reserve_target_pct': reserve_pct,
            'reserve_target_amount': reserve_target,
            'excess_spread_annual': excess_spread,
            'excess_spread_buffer_12m': excess_spread_annual,
            'total_credit_support_pct': oc_pct + reserve_pct + excess_spread_annual,
            'total_credit_support_amount': self.pool_notional * (oc_pct + reserve_pct + excess_spread_annual),
            'senior_credit_support': self.tranches[0]['subordination'] if self.tranches else 0,
            'mezz_credit_support': self.tranches[1]['subordination'] if len(self.tranches) > 1 else 0,
        }
        
        return ce_stats


def print_time_right_tranche_structure(tranches, ce_stats, pool_df):
    """打印时权ABS分层结构表"""
    print("\n" + "=" * 80)
    print("时权ABS分层结构设计表 (Time Right ABS Tranche Structure)")
    print("=" * 80)
    
    print(f"\n{'层级':<12} {'规模(%)':>8} {'规模(元)':>14} {'时权数':>10} {'票息':>8} {'目标评级':>8} {'信用支持':>10}")
    print("-" * 90)
    
    total_notional = sum(t['notional'] for t in tranches)
    
    for t in tranches:
        print(f"{t['name']:<12} {t['size_pct']*100:>7.1f}% ¥{t['notional']:>12,.0f} "
              f"{t['rights']:>10,} {t['coupon_annual']*100:>7.2f}% {t['target_rating']:>8s} "
              f"{t['credit_support_pct']*100:>9.1f}%")
    
    print("-" * 90)
    print(f"{'合计':<12} {'100.0%':>8} ¥{total_notional:>12,.0f}")
    
    print("\n【兑付方式设计】")
    print(f"{'层级':<12} {'现金兑付':>10} {'实物兑付':>10} {'约定收益':>10} {'入住折扣':>10} {'目标客群':>12}")
    print("-" * 80)
    for t in tranches:
        discount_display = f"{t['physical_discount']*100:.0f}%" if t['physical_discount'] > 0 else "N/A"
        print(f"{t['name']:<12} {t['cash_redemption_pct']*100:>9.0f}% {t['physical_redemption_pct']*100:>9.0f}% "
              f"{t['promised_return']*100:>9.1f}% {discount_display:>10} {t['investor_type']:>12}")
    
    print("\n【信用增级机制】")
    print(f"  超额抵押(OC): {ce_stats['overcollateralization_pct']*100:.1f}% "
          f"(¥{ce_stats['overcollateralization_amount']:,.0f})")
    print(f"  储备金账户: {ce_stats['reserve_target_pct']*100:.1f}% "
          f"(¥{ce_stats['reserve_target_amount']:,.0f})")
    print(f"  超额利差(年化): {ce_stats['excess_spread_annual']*100:.2f}%")
    print(f"  总信用支持: {ce_stats['total_credit_support_pct']*100:.1f}%")
