"""
分层结构设计与信用增级 (Tranching & Credit Enhancement)

对标：标准ABS/REITs的分层结构设计
- Senior (优先级): AAA目标
- Mezzanine (夹层): A-BBB
- Junior (次级): BB-B
- Equity (权益级): 无评级，剩余收益
"""

import pandas as pd
import numpy as np


class TrancheStructure:
    """ABS分层结构设计器"""
    
    def __init__(self, pool_notional, wtd_pd, wtd_lgd, wtd_el):
        """
        Parameters:
        -----------
        pool_notional : float
            资产池总面值
        wtd_pd : float
            加权平均违约概率
        wtd_lgd : float
            加权平均违约损失率
        wtd_el : float
            加权平均预期损失
        """
        self.pool_notional = pool_notional
        self.wtd_pd = wtd_pd
        self.wtd_lgd = wtd_lgd
        self.wtd_el = wtd_el
        
        # 分层结构参数
        self.tranches = []
        
    def design_tranches(self, senior_pct=0.68, mezz_pct=0.20, junior_pct=0.08, 
                        equity_pct=0.04):
        """
        设计标准分层结构
        
        Parameters:
        -----------
        senior_pct : float
            Senior占比
        mezz_pct : float
            Mezzanine占比
        junior_pct : float
            Junior占比
        equity_pct : float
            Equity占比
        
        Returns:
        --------
        tranches : list of dict
            各分层详细信息
        """
        assert abs(senior_pct + mezz_pct + junior_pct + equity_pct - 1.0) < 0.001
        
        # 票息设计（年化）
        # Senior: 接近无风险利率 + 小利差
        # Mezz: 中等利差
        # Junior: 高收益
        # Equity: 剩余收益，无固定票息
        
        tranche_configs = [
            {
                'name': 'Senior',
                'subordination': junior_pct + mezz_pct + equity_pct,
                'coupon_annual': 0.045,  # 4.5%
                'target_rating': 'AAA',
                'payment_priority': 1,
            },
            {
                'name': 'Mezzanine',
                'subordination': junior_pct + equity_pct,
                'coupon_annual': 0.065,  # 6.5%
                'target_rating': 'BBB',
                'payment_priority': 2,
            },
            {
                'name': 'Junior',
                'subordination': equity_pct,
                'coupon_annual': 0.095,  # 9.5%
                'target_rating': 'B',
                'payment_priority': 3,
            },
            {
                'name': 'Equity',
                'subordination': 0.0,
                'coupon_annual': 0.0,  # 无固定票息，剩余收益
                'target_rating': 'NR',
                'payment_priority': 4,
            }
        ]
        
        sizes = {
            'Senior': senior_pct,
            'Mezzanine': mezz_pct,
            'Junior': junior_pct,
            'Equity': equity_pct
        }
        
        tranches = []
        cumulative_ce = 0.0
        
        for cfg in tranche_configs:
            name = cfg['name']
            size_pct = sizes[name]
            notional = self.pool_notional * size_pct
            
            # 信用支持 = 下层所有分层 + 超额抵押 + 储备金
            # 简化：信用支持 = 下层分层占比 + 超额利差积累
            credit_support = cfg['subordination']
            
            # 该分层承受的违约损失上限
            # 当损失超过上层保护时，该层开始承担
            loss_attachment = cumulative_ce
            loss_detachment = cumulative_ce + size_pct
            
            tranche = {
                'name': name,
                'size_pct': size_pct,
                'notional': notional,
                'coupon_annual': cfg['coupon_annual'],
                'coupon_monthly': cfg['coupon_annual'] / 12,
                'target_rating': cfg['target_rating'],
                'payment_priority': cfg['payment_priority'],
                'subordination': cfg['subordination'],
                'credit_support_pct': credit_support,
                'loss_attachment': loss_attachment,
                'loss_detachment': loss_detachment,
                'expected_loss': self._estimate_tranche_el(
                    loss_attachment, loss_detachment, self.wtd_pd, self.wtd_lgd
                )
            }
            
            tranches.append(tranche)
            cumulative_ce += size_pct
        
        self.tranches = tranches
        return tranches
    
    def _estimate_tranche_el(self, attach, detach, pd, lgd):
        """
        简化估计某分层的预期损失
        
        使用对数正态近似损失分布
        """
        # 资产池总损失分布的均值和标准差
        mean_loss = pd * lgd
        # 简化：std ≈ mean * 2（高度右偏）
        std_loss = mean_loss * 2.5
        
        if std_loss < 1e-6:
            return 0.0
        
        # 对数正态参数
        sigma2 = np.log(1 + (std_loss / max(mean_loss, 1e-6)) ** 2)
        mu = np.log(max(mean_loss, 1e-6)) - 0.5 * sigma2
        
        # 该分层承担的期望损失
        # E[min(max(L - attach, 0), detach - attach)]
        # 简化：用正态近似
        from scipy import stats
        
        # 正态近似
        a = attach
        d = detach
        
        # E[(L-a)+] - E[(L-d)+]
        def truncated_mean(mean, std, threshold):
            if std < 1e-6:
                return max(mean - threshold, 0)
            z = (threshold - mean) / std
            return std * stats.norm.pdf(z) + (mean - threshold) * (1 - stats.norm.cdf(z))
        
        el = truncated_mean(mean_loss, std_loss, a) - truncated_mean(mean_loss, std_loss, d)
        
        # 限制在分层厚度内
        el = min(max(el, 0), d - a)
        
        # 转换为分层的百分比损失
        tranche_el_pct = el / max(d - a, 1e-6)
        
        return tranche_el_pct
    
    def compute_credit_enhancement(self, reserve_pct=0.03, excess_spread_annual=0.015):
        """
        计算信用增级量化指标
        
        Returns:
        --------
        ce_stats : dict
            信用增级统计
        """
        # 超额抵押
        oc_pct = 0.02  # 2%超额抵押（资产池面值 > 证券发行面值）
        
        # 储备金账户
        reserve_target = self.pool_notional * reserve_pct
        
        # 超额利差
        # 资产池收益率 - 证券加权平均票息
        pool_yield = 0.08  # 假设资产池年化收益率8%
        wac_coupon = sum(t['size_pct'] * t['coupon_annual'] for t in self.tranches)
        excess_spread = pool_yield - wac_coupon
        
        # 12个月超额利差积累
        excess_spread_buffer = excess_spread_annual
        
        ce_stats = {
            'overcollateralization_pct': oc_pct,
            'overcollateralization_amount': self.pool_notional * oc_pct,
            'reserve_target_pct': reserve_pct,
            'reserve_target_amount': reserve_target,
            'excess_spread_annual': excess_spread,
            'excess_spread_buffer_12m': excess_spread_buffer,
            'total_credit_support_pct': oc_pct + reserve_pct + excess_spread_buffer,
            'total_credit_support_amount': self.pool_notional * (oc_pct + reserve_pct + excess_spread_buffer),
            'senior_credit_support': self.tranches[0]['subordination'] if self.tranches else 0,
            'mezz_credit_support': self.tranches[1]['subordination'] if len(self.tranches) > 1 else 0,
        }
        
        return ce_stats
    
    def run_oc_ic_tests(self, pool_balance, pool_income, delinquency_rate=0.0):
        """
        运行超额抵押测试(OC Test)和利息覆盖测试(IC Test)
        
        Parameters:
        -----------
        pool_balance : float
            当前资产池余额
        pool_income : float
            当期资产池收入
        delinquency_rate : float
            逾期率
            
        Returns:
        --------
        tests : dict
            测试结果
        """
        # 证券总余额（简化：按初始面值）
        security_balance = self.pool_notional
        
        # OC Test
        oc_ratio = pool_balance / security_balance if security_balance > 0 else 0
        oc_threshold = 1.02  # 102%
        oc_pass = oc_ratio >= oc_threshold
        
        # IC Test
        # 当期需要支付的利息
        monthly_interest_due = sum(
            t['notional'] * t['coupon_monthly'] for t in self.tranches
        )
        ic_ratio = pool_income / monthly_interest_due if monthly_interest_due > 0 else float('inf')
        ic_threshold = 1.20  # 120%
        ic_pass = ic_ratio >= ic_threshold
        
        # 逾期率测试
        delinquency_threshold = 0.05  # 5%
        delinquency_pass = delinquency_rate < delinquency_threshold
        
        return {
            'oc_ratio': oc_ratio,
            'oc_threshold': oc_threshold,
            'oc_pass': oc_pass,
            'ic_ratio': ic_ratio,
            'ic_threshold': ic_threshold,
            'ic_pass': ic_pass,
            'delinquency_rate': delinquency_rate,
            'delinquency_threshold': delinquency_threshold,
            'delinquency_pass': delinquency_pass,
            'all_pass': oc_pass and ic_pass and delinquency_pass
        }


def print_tranche_structure(tranches, ce_stats):
    """打印分层结构表（对标ABS发行说明书）"""
    print("\n" + "=" * 80)
    print("分层结构设计表")
    print("=" * 80)
    
    print(f"\n{'层级':<12} {'规模(%)':>8} {'规模(元)':>14} {'票息':>8} {'目标评级':>8} {'信用支持':>10} {'预期损失':>10}")
    print("-" * 80)
    
    total_notional = sum(t['notional'] for t in tranches)
    
    for t in tranches:
        print(f"{t['name']:<12} {t['size_pct']*100:>7.1f}% CNY {t['notional']:>12,.0f} "
              f"{t['coupon_annual']*100:>7.2f}% {t['target_rating']:>8s} "
              f"{t['credit_support_pct']*100:>9.1f}% {t['expected_loss']*100:>9.2f}%")
    
    print("-" * 80)
    print(f"{'合计':<12} {'100.0%':>8} CNY {total_notional:>12,.0f}")
    
    print("\n【信用增级机制】")
    print(f"  超额抵押(OC): {ce_stats['overcollateralization_pct']*100:.1f}% "
          f"(CNY {ce_stats['overcollateralization_amount']:,.0f})")
    print(f"  储备金账户: {ce_stats['reserve_target_pct']*100:.1f}% "
          f"(CNY {ce_stats['reserve_target_amount']:,.0f})")
    print(f"  超额利差(年化): {ce_stats['excess_spread_annual']*100:.2f}%")
    print(f"  12个月超额利差缓冲: {ce_stats['excess_spread_buffer_12m']*100:.1f}%")
    print(f"  总信用支持: {ce_stats['total_credit_support_pct']*100:.1f}%")
    
    print("\n【触发器设置】")
    print(f"  OC测试阈值: 102% (加速清偿触发: <100%)")
    print(f"  IC测试阈值: 120% (加速清偿触发: <100%)")
    print(f"  逾期率阈值: 5%")


if __name__ == '__main__':
    print("=" * 60)
    print("分层结构设计测试")
    print("=" * 60)
    
    # 模拟资产池参数
    pool_notional = 500_000_000  # 5亿
    wtd_pd = 0.025
    wtd_lgd = 0.55
    wtd_el = wtd_pd * wtd_lgd
    
    struct = TrancheStructure(pool_notional, wtd_pd, wtd_lgd, wtd_el)
    tranches = struct.design_tranches()
    ce_stats = struct.compute_credit_enhancement()
    
    print_tranche_structure(tranches, ce_stats)
    
    # 测试OC/IC
    pool_balance = pool_notional * 1.03
    pool_income = pool_notional * 0.08 / 12
    tests = struct.run_oc_ic_tests(pool_balance, pool_income)
    
    print("\n【覆盖测试】")
    print(f"  OC比率: {tests['oc_ratio']*100:.1f}% {'通过OK' if tests['oc_pass'] else '不通过FAIL'}")
    print(f"  IC比率: {tests['ic_ratio']*100:.1f}% {'通过OK' if tests['ic_pass'] else '不通过FAIL'}")
