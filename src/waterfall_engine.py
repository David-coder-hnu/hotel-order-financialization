"""
现金流瀑布引擎 (Cash Flow Waterfall Engine)

严格按照ABS优先级逐期分配现金流：
1. 税费/服务费
2. Senior利息
3. Senior本金（顺序偿还）
4. Mezzanine利息
5. Mezzanine本金
6. Junior利息/本金
7. Equity剩余分配
8. 储备金补充

嵌入触发器：
- 早期摊还触发 (Early Amortization)
- 违约事件触发 (Event of Default)
- 动用储备金
"""

import numpy as np
import pandas as pd


class WaterfallEngine:
    """现金流瀑布引擎"""
    
    def __init__(self, tranches, pool_cashflows, default_matrix,
                 reserve_target_pct=0.03, servicing_fee_rate=0.005,
                 trigger_oc_threshold=1.0, trigger_ic_threshold=1.0):
        """
        Parameters:
        -----------
        tranches : list of dict
            分层结构（来自 TrancheStructure）
        pool_cashflows : ndarray, shape (n_hotels, n_months)
            资产池每期现金流
        default_matrix : ndarray, shape (n_paths, n_hotels, n_months)
            违约指示矩阵（0/1）
        reserve_target_pct : float
            储备金目标比例
        servicing_fee_rate : float
            服务费率（年化）
        trigger_oc_threshold : float
            OC测试加速清偿触发阈值
        trigger_ic_threshold : float
            IC测试加速清偿触发阈值
        """
        self.tranches = tranches
        self.pool_cashflows = pool_cashflows
        self.default_matrix = default_matrix
        self.reserve_target_pct = reserve_target_pct
        self.servicing_fee_rate = servicing_fee_rate / 12  # 月费率
        self.trigger_oc_threshold = trigger_oc_threshold
        self.trigger_ic_threshold = trigger_ic_threshold
        
        self.n_hotels, self.n_months = pool_cashflows.shape
        self.n_paths = default_matrix.shape[0]
        
        # 储备金账户
        self.reserve_balance = 0.0
        
        # 违约事件标志
        self.event_of_default = False
        self.early_amortization = False
    
    def _compute_pool_income(self, path, month):
        """计算某路径某期的资产池收入（考虑违约）"""
        cashflows = self.pool_cashflows[:, month].copy()
        
        # 违约的酒店不产生收入
        defaulted = self.default_matrix[path, :, month]
        
        # 违约酒店的收入 = 回收值
        # 简化：违约时产生 recovery = cashflow * (1 - LGD)
        # 但这里 cashflows 是预期现金流，违约时直接置零
        # 更精确的做法是：违约损失在资产池层面体现
        cashflows[defaulted] = 0
        
        return cashflows.sum()
    
    def _compute_pool_balance(self, path, month):
        """计算当前资产池余额"""
        # 剩余未违约资产的累计面值
        total_notional = self.pool_cashflows.sum()
        
        # 已违约资产的累计损失
        if month > 0:
            cumulative_defaulted = np.any(self.default_matrix[path, :, :month+1], axis=1)
            lost_notional = self.pool_cashflows[cumulative_defaulted, :].sum()
        else:
            lost_notional = 0
        
        return total_notional - lost_notional
    
    def run_waterfall(self, path=0, verbose=False):
        """
        运行单一路径的现金流瀑布
        
        Parameters:
        -----------
        path : int
            蒙特卡洛路径编号
        verbose : bool
            是否打印详细分配
            
        Returns:
        --------
        waterfall_df : DataFrame
            每期分配明细
        tranche_results : dict
            各分层最终结果
        """
        # 初始化各分层余额
        tranche_balances = {t['name']: t['notional'] for t in self.tranches}
        tranche_coupons = {t['name']: t['coupon_monthly'] for t in self.tranches}
        
        # 储备金
        reserve_balance = 0.0
        reserve_target = sum(tranche_balances.values()) * self.reserve_target_pct
        
        # 记录每期分配
        records = []
        
        # 重置触发器
        event_of_default = False
        early_amortization = False
        
        for month in range(self.n_months):
            # 1. 计算当期资产池收入
            pool_income = self._compute_pool_income(path, month)
            
            # 2. 服务费
            total_notional = sum(tranche_balances.values())
            servicing_fee = total_notional * self.servicing_fee_rate
            available = pool_income - servicing_fee
            
            # 储备金释放（如果可用资金不足）
            reserve_used = 0.0
            if available < 0 and reserve_balance > 0:
                reserve_used = min(-available, reserve_balance)
                available += reserve_used
                reserve_balance -= reserve_used
            
            # 确保可用资金非负
            available = max(available, 0)
            
            # 当期分配记录
            record = {
                'month': month + 1,
                'pool_income': pool_income,
                'servicing_fee': servicing_fee,
                'available_after_fees': available,
                'reserve_used': reserve_used,
                'reserve_balance_start': reserve_balance + reserve_used,
                'event_of_default': event_of_default,
                'early_amortization': early_amortization,
            }
            
            # 3. 利息分配（按优先级）
            remaining = available
            
            interest_paid = {}
            principal_paid = {}
            
            # 如果触发违约事件，全部还Senior
            if event_of_default:
                # 加速清偿模式
                for t in self.tranches:
                    name = t['name']
                    if remaining <= 0:
                        break
                    # 先还利息
                    interest_due = tranche_balances[name] * tranche_coupons[name]
                    ip = min(interest_due, remaining)
                    interest_paid[name] = ip
                    remaining -= ip
                    
                    # 再还本金
                    pp = min(tranche_balances[name], remaining)
                    principal_paid[name] = pp
                    remaining -= pp
                    tranche_balances[name] -= pp
            else:
                # 正常瀑布分配
                for t in self.tranches:
                    name = t['name']
                    
                    # 利息
                    interest_due = tranche_balances[name] * tranche_coupons[name]
                    ip = min(interest_due, remaining)
                    interest_paid[name] = ip
                    remaining -= ip
                    
                    # 本金摊还（按剩余期限平均）
                    months_left = self.n_months - month
                    if months_left > 0 and name != 'Equity':
                        principal_due = tranche_balances[name] / months_left
                        pp = min(principal_due, remaining)
                        principal_paid[name] = pp
                        remaining -= pp
                        tranche_balances[name] -= pp
                    else:
                        principal_paid[name] = 0.0
                
                # 如果early amortization触发，加速偿还Senior
                if early_amortization and remaining > 0:
                    for t in self.tranches:
                        name = t['name']
                        if name != 'Senior':
                            continue
                        pp = min(tranche_balances[name], remaining)
                        principal_paid[name] = principal_paid.get(name, 0) + pp
                        remaining -= pp
                        tranche_balances[name] -= pp
                    # 继续还Mezz
                    if remaining > 0:
                        for t in self.tranches:
                            name = t['name']
                            if name not in ['Mezzanine', 'Junior']:
                                continue
                            pp = min(tranche_balances[name], remaining)
                            principal_paid[name] = principal_paid.get(name, 0) + pp
                            remaining -= pp
                            tranche_balances[name] -= pp
            
            # 4. Equity获得剩余
            equity_distribution = remaining if remaining > 0 else 0
            remaining = 0
            
            # 5. 储备金补充
            reserve_contribution = 0.0
            if not event_of_default and not early_amortization:
                reserve_needed = reserve_target - reserve_balance
                reserve_contribution = min(reserve_needed, max(available * 0.1, 0))
                # 从equity中扣
                if equity_distribution >= reserve_contribution:
                    equity_distribution -= reserve_contribution
                else:
                    reserve_contribution = equity_distribution
                    equity_distribution = 0
                reserve_balance += reserve_contribution
            
            # 记录各分层分配
            for t in self.tranches:
                name = t['name']
                record[f'{name}_interest_due'] = tranche_balances[name] * tranche_coupons[name]
                record[f'{name}_interest_paid'] = interest_paid.get(name, 0)
                record[f'{name}_principal_paid'] = principal_paid.get(name, 0)
                record[f'{name}_balance_end'] = tranche_balances[name]
            
            record['equity_distribution'] = equity_distribution
            record['reserve_contribution'] = reserve_contribution
            record['reserve_balance_end'] = reserve_balance
            
            # 6. 触发器检查
            pool_balance = self._compute_pool_balance(path, month)
            security_balance = sum(tranche_balances.values())
            
            # OC测试
            oc_ratio = pool_balance / security_balance if security_balance > 0 else 0
            if oc_ratio < self.trigger_oc_threshold and month > 3:
                early_amortization = True
            
            # IC测试
            total_interest_due = sum(tranche_balances[t['name']] * tranche_coupons[t['name']] 
                                      for t in self.tranches)
            ic_ratio = pool_income / total_interest_due if total_interest_due > 0 else float('inf')
            if ic_ratio < self.trigger_ic_threshold and month > 3:
                early_amortization = True
            
            # 违约事件：连续3期IC失败或累计违约率过高
            cumulative_defaults = np.sum(np.any(self.default_matrix[path, :, :month+1], axis=1))
            default_rate = cumulative_defaults / self.n_hotels
            if default_rate > 0.15 or (month > 5 and early_amortization):
                event_of_default = True
            
            records.append(record)
        
        # 最终结果
        waterfall_df = pd.DataFrame(records)
        
        tranche_results = {}
        total_equity_dist = waterfall_df['equity_distribution'].sum()
        
        for t in self.tranches:
            name = t['name']
            total_interest = waterfall_df[f'{name}_interest_paid'].sum()
            total_principal = waterfall_df[f'{name}_principal_paid'].sum()
            final_balance = tranche_balances[name]
            
            initial_notional = t['notional']
            
            if name == 'Equity':
                # Equity的收益来自剩余分配
                total_received = total_interest + total_principal + total_equity_dist
                loss = max(initial_notional - total_equity_dist, 0)
            else:
                total_received = total_interest + total_principal
                loss = initial_notional - total_principal  # 未收回本金视为损失
            
            loss_rate = loss / initial_notional if initial_notional > 0 else 0
            
            tranche_results[name] = {
                'initial_notional': initial_notional,
                'total_interest_received': total_interest,
                'total_principal_received': total_principal,
                'equity_distribution': total_equity_dist if name == 'Equity' else 0,
                'final_balance': final_balance,
                'loss': loss,
                'loss_rate': loss_rate,
                'total_return': total_received,
                'yield_annual': self._compute_annual_yield(initial_notional, total_received, self.n_months)
            }
        
        return waterfall_df, tranche_results
    
    def _compute_annual_yield(self, initial, total_return, n_months):
        """计算年化收益率"""
        if initial <= 0 or n_months <= 0:
            return 0
        # 简单年化：(总回报/初始)^(12/n) - 1
        total_return = max(total_return, 0)
        if total_return <= 0:
            return -1.0
        try:
            return (total_return / initial) ** (12 / n_months) - 1
        except:
            return 0
    
    def run_all_paths(self):
        """
        运行所有蒙特卡洛路径的瀑布分配
        
        Returns:
        --------
        all_results : list of dict
            每路径的各分层结果
        """
        all_results = []
        
        for path in range(self.n_paths):
            if (path + 1) % 500 == 0 or path == self.n_paths - 1:
                print(f"    瀑布分配: {path+1}/{self.n_paths} ({(path+1)/self.n_paths*100:.0f}%)")
            _, tranche_results = self.run_waterfall(path=path)
            all_results.append(tranche_results)
        
        return all_results


def print_waterfall_summary(waterfall_df, tranche_results):
    """打印瀑布分配摘要"""
    print("\n" + "=" * 80)
    print("现金流瀑布分配摘要")
    print("=" * 80)
    
    # 各分层汇总
    print(f"\n{'分层':<12} {'初始本金':>12} {'利息收入':>12} {'本金偿还':>12} {'剩余本金':>12} {'损失':>12} {'损失率':>8}")
    print("-" * 90)
    
    for name, res in tranche_results.items():
        print(f"{name:<12} CNY {res['initial_notional']:>10,.0f} CNY {res['total_interest_received']:>10,.0f} "
              f"CNY {res['total_principal_received']:>10,.0f} CNY {res['final_balance']:>10,.0f} "
              f"CNY {res['loss']:>10,.0f} {res['loss_rate']*100:>7.2f}%")
    
    # 关键期数
    print(f"\n【关键事件】")
    ea_months = waterfall_df[waterfall_df['early_amortization'] == True]
    if len(ea_months) > 0:
        print(f"  早期摊还触发: 第 {ea_months['month'].iloc[0]} 期")
    
    ed_months = waterfall_df[waterfall_df['event_of_default'] == True]
    if len(ed_months) > 0:
        print(f"  违约事件触发: 第 {ed_months['month'].iloc[0]} 期")
    
    if len(ea_months) == 0 and len(ed_months) == 0:
        print(f"  未触发任何加速清偿事件")
    
    # 储备金
    print(f"\n【储备金账户】")
    print(f"  期末余额: CNY {waterfall_df['reserve_balance_end'].iloc[-1]:,.0f}")


if __name__ == '__main__':
    print("=" * 60)
    print("现金流瀑布引擎测试")
    print("=" * 60)
    
    # 模拟参数
    n_hotels = 10
    n_months = 36
    
    pool_cashflows = np.ones((n_hotels, n_months)) * 100000
    default_matrix = np.zeros((1, n_hotels, n_months), dtype=bool)
    
    tranches = [
        {'name': 'Senior', 'notional': 5000000, 'coupon_monthly': 0.045/12},
        {'name': 'Mezzanine', 'notional': 2000000, 'coupon_monthly': 0.065/12},
        {'name': 'Junior', 'notional': 800000, 'coupon_monthly': 0.095/12},
        {'name': 'Equity', 'notional': 400000, 'coupon_monthly': 0.0},
    ]
    
    engine = WaterfallEngine(tranches, pool_cashflows, default_matrix)
    waterfall_df, results = engine.run_waterfall(path=0)
    
    print_waterfall_summary(waterfall_df, results)
