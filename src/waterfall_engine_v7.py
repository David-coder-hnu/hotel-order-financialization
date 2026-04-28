"""
时权ABS现金流瀑布引擎 V7

时权ABS的特点：
- 发行时一次性融资（酒店提前获得资金）
- 持有期：时权可在二级市场交易
- 到期：统一兑付（现金或实物）

参与方收益：
- 酒店方：发行收入 - 兑付成本（现金或实物）
- 平台方：发行手续费 + 交易手续费 + 管理费
- 投资者：现金收益 或 实物入住权益
"""

import numpy as np
import pandas as pd


class TimeRightWaterfallEngine:
    """时权ABS现金流瀑布引擎（适配双轨兑付）"""
    
    def __init__(self, tranches, pool_df, platform_fee_rate=0.005,
                 trading_fee_rate=0.005, management_fee_rate=0.01):
        self.tranches = tranches
        self.pool_df = pool_df
        self.platform_fee_rate = platform_fee_rate
        self.trading_fee_rate = trading_fee_rate
        self.management_fee_rate = management_fee_rate
        
        self.total_rights = sum(t['rights'] for t in tranches)
        self.total_notional = sum(t['notional'] for t in tranches)
    
    def simulate_issuance(self):
        """
        模拟发行阶段
        
        Returns:
            hotel_proceeds: 酒店实际获得的资金（扣除平台发行费）
            platform_issuance_fee: 平台发行手续费
        """
        gross_proceeds = self.total_notional
        platform_issuance_fee = gross_proceeds * self.platform_fee_rate
        hotel_proceeds = gross_proceeds - platform_issuance_fee
        
        return {
            'gross_proceeds': gross_proceeds,
            'platform_issuance_fee': platform_issuance_fee,
            'hotel_proceeds': hotel_proceeds
        }
    
    def simulate_trading(self, turnover_cycles=2):
        """
        模拟二级市场交易
        
        假设持有期内时权转手 turnover_cycles 次
        """
        total_trading_volume = self.total_notional * turnover_cycles
        platform_trading_fee = total_trading_volume * self.trading_fee_rate
        
        return {
            'turnover_cycles': turnover_cycles,
            'total_trading_volume': total_trading_volume,
            'platform_trading_fee': platform_trading_fee
        }
    
    def simulate_redemption(self):
        """
        模拟到期兑付阶段
        
        核心：各层投资者选择现金或实物兑付
        """
        results = {}
        total_cash_cost = 0
        total_physical_cost = 0
        
        avg_base_price = self.pool_df['base_price'].mean()
        avg_market_price = self.pool_df['avg_price'].mean()
        
        for t in self.tranches:
            name = t['name']
            rights = t['rights']
            notional = t['notional']
            issue_price = notional / rights if rights > 0 else 0
            
            cash_pct = t['cash_redemption_pct']
            physical_pct = t['physical_redemption_pct']
            
            # 现金兑付
            cash_rights = int(rights * cash_pct)
            cash_return_per = issue_price * (1 + t['promised_return'])
            cash_cost = cash_rights * cash_return_per
            
            # 实物兑付
            physical_rights = rights - cash_rights
            # 酒店实际成本 = 底价（因为房间本来就可能空着）
            physical_cost_per = avg_base_price * (1 - t['physical_discount'])
            physical_cost = physical_rights * physical_cost_per
            
            # 投资者获得的价值
            investor_cash_value = cash_rights * cash_return_per
            # 实物兑付对投资者的价值 = 市场房价 - 实际支付价
            investor_payment_per = avg_base_price * (1 - t['physical_discount'])
            investor_physical_value = physical_rights * (avg_market_price - investor_payment_per)
            
            # 如果全部现金兑付的成本（用于计算节省）
            all_cash_cost = rights * cash_return_per
            
            results[name] = {
                'rights': rights,
                'cash_rights': cash_rights,
                'physical_rights': physical_rights,
                'cash_cost': cash_cost,
                'physical_cost': physical_cost,
                'total_redemption_cost': cash_cost + physical_cost,
                'investor_cash_value': investor_cash_value,
                'investor_physical_value': investor_physical_value,
                'investor_total_value': investor_cash_value + investor_physical_value,
                'cost_saving_vs_all_cash': all_cash_cost - (cash_cost + physical_cost)
            }
            
            total_cash_cost += cash_cost
            total_physical_cost += physical_cost
        
        return results, total_cash_cost + total_physical_cost
    
    def compute_three_party_economics(self):
        """
        计算三方收益分析（酒店/平台/投资者）
        
        这是V5的核心创新，在V7中保留
        """
        # 发行阶段
        issuance = self.simulate_issuance()
        
        # 交易阶段
        trading = self.simulate_trading(turnover_cycles=2)
        
        # 兑付阶段
        redemption, total_redemption_cost = self.simulate_redemption()
        
        # 酒店方
        hotel_revenue = issuance['hotel_proceeds']
        hotel_cost = total_redemption_cost
        hotel_profit = hotel_revenue - hotel_cost
        hotel_roi = (hotel_profit / hotel_revenue) * 100 if hotel_revenue > 0 else 0
        
        # 平台方
        platform_revenue = issuance['platform_issuance_fee'] + trading['platform_trading_fee']
        platform_revenue += self.total_notional * self.management_fee_rate
        platform_profit = platform_revenue
        
        # 投资者方
        total_investor_cost = self.total_notional
        total_investor_return = sum(r['investor_total_value'] for r in redemption.values())
        investor_net_return = total_investor_return - total_investor_cost
        investor_return_rate = (investor_net_return / total_investor_cost) * 100 if total_investor_cost > 0 else 0
        
        return {
            'hotel': {
                'issuance_proceeds': hotel_revenue,
                'redemption_cost': hotel_cost,
                'profit': hotel_profit,
                'roi': hotel_roi
            },
            'platform': {
                'issuance_fee': issuance['platform_issuance_fee'],
                'trading_fee': trading['platform_trading_fee'],
                'management_fee': self.total_notional * self.management_fee_rate,
                'total_revenue': platform_revenue,
                'profit': platform_profit
            },
            'investors': {
                'total_cost': total_investor_cost,
                'total_return': total_investor_return,
                'net_return': investor_net_return,
                'return_rate': investor_return_rate,
                'by_tranche': redemption
            },
            'system_efficiency': {
                'total_value_created': hotel_profit + platform_profit + investor_net_return,
                'cash_vs_physical_saving': sum(r['cost_saving_vs_all_cash'] for r in redemption.values())
            }
        }


def print_three_party_summary(tp):
    """打印三方收益摘要"""
    print("\n" + "=" * 80)
    print("三方收益分析摘要 (Three-Party Economics)")
    print("=" * 80)
    
    print(f"\n  酒店方:")
    print(f"    发行收入: ¥{tp['hotel']['issuance_proceeds']:,.0f}")
    print(f"    兑付成本: ¥{tp['hotel']['redemption_cost']:,.0f}")
    print(f"    净利润: ¥{tp['hotel']['profit']:,.0f}")
    print(f"    ROI: {tp['hotel']['roi']:.2f}%")
    
    print(f"\n  平台方:")
    print(f"    发行手续费: ¥{tp['platform']['issuance_fee']:,.0f}")
    print(f"    交易手续费: ¥{tp['platform']['trading_fee']:,.0f}")
    print(f"    管理费: ¥{tp['platform']['management_fee']:,.0f}")
    print(f"    总收入: ¥{tp['platform']['total_revenue']:,.0f}")
    
    print(f"\n  投资者方:")
    print(f"    总投资: ¥{tp['investors']['total_cost']:,.0f}")
    print(f"    总回报: ¥{tp['investors']['total_return']:,.0f}")
    print(f"    净收益: ¥{tp['investors']['net_return']:,.0f}")
    print(f"    收益率: {tp['investors']['return_rate']:.2f}%")
    
    print(f"\n  各层兑付详情:")
    print(f"{'分层':<12} {'现金成本':>14} {'实物成本':>14} {'总成本':>14} {'vs全现金节省':>14}")
    print("-" * 75)
    for name, r in tp['investors']['by_tranche'].items():
        print(f"{name:<12} ¥{r['cash_cost']:>12,.0f} "
              f"¥{r['physical_cost']:>12,.0f} ¥{r['total_redemption_cost']:>12,.0f} "
              f"¥{r['cost_saving_vs_all_cash']:>12,.0f}")
    
    print(f"\n  系统效率:")
    print(f"    总价值创造: ¥{tp['system_efficiency']['total_value_created']:,.0f}")
    print(f"    实物兑付节省: ¥{tp['system_efficiency']['cash_vs_physical_saving']:,.0f}")
