import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime, timedelta
import json
from scipy import optimize

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

print("=" * 80)
print("酒店订单金融化可行性分析 V5")
print("基于ABS/RWA金融模型的可行性研究 - 优化版")
print("=" * 80)

# ========================
# 1. 数据准备与酒店筛选
# ========================
print("\n【步骤1：数据准备与酒店筛选】")
print("-" * 80)

# 读取数据
work_dir = r'c:\Users\weida\Desktop\酒店研究'
cleaned_prices = pd.read_csv(f'{work_dir}/data/cleaned_hotel_prices.csv')
future_prices = pd.read_csv(f'{work_dir}/data/hotel_future_prices.csv')
hotel_info = pd.read_csv(f'{work_dir}/data/hotel_info.csv')

# 日期转换
cleaned_prices['date'] = pd.to_datetime(cleaned_prices['date'])

# 筛选数据完整的酒店
hotel_stats = cleaned_prices.groupby('hotelCode').agg({
    'date': ['count', 'nunique'],
    'price': ['mean', 'min', 'max', 'std']
}).reset_index()
hotel_stats.columns = ['hotelCode', 'record_count', 'date_count', 'avg_price', 'min_price', 'max_price', 'price_std']

# 选择数据最完整、价格最稳定的酒店（取前5个）
best_hotels = hotel_stats[
    (hotel_stats['date_count'] >= 100) &
    (hotel_stats['price_std'] > 0) &
    (~hotel_stats['avg_price'].isna())
].sort_values(['date_count', 'price_std'], ascending=[False, False]).head(5)

print(f"选定 {len(best_hotels)} 个数据状况最良好的酒店：")
for idx, row in best_hotels.iterrows():
    hotel_name = hotel_info[hotel_info['hotelCode'] == row['hotelCode']]['hotelName'].values
    hotel_name = hotel_name[0] if len(hotel_name) > 0 else "未知"
    print(f"  酒店 {row['hotelCode']}: {int(row['date_count'])}天数据, 均价 ¥{row['avg_price']:.0f}")
    print(f"    名称: {hotel_name}")

# 获取远期价格（底价）
future_map = future_prices.set_index('hotelCode')['futurePrice'].to_dict()

# 计算酒店经营指标（基于真实数据）
hotel_codes = list(best_hotels['hotelCode'])
hotel_metrics = {}

for hotel_code in hotel_codes:
    hotel_data = cleaned_prices[cleaned_prices['hotelCode'] == hotel_code]
    
    # 计算实际入住率（基于价格数据点的密度）
    total_days = (hotel_data['date'].max() - hotel_data['date'].min()).days
    data_points = len(hotel_data)
    actual_occupancy = min(data_points / total_days, 1.0) if total_days > 0 else 0.7
    
    avg_price = best_hotels[best_hotels['hotelCode'] == hotel_code]['avg_price'].values[0]
    base_price = future_map.get(hotel_code, avg_price)
    
    # 计算RevPAR（每间可售房收入）
    revpar = avg_price * actual_occupancy
    
    hotel_metrics[hotel_code] = {
        'avg_price': avg_price,
        'base_price': base_price,
        'occupancy_rate': actual_occupancy,
        'revpar': revpar,
        'room_count': 100,  # 假设每家酒店100间房
        'total_days': total_days,
        'data_points': data_points
    }

print(f"\n酒店经营指标（基于真实数据）：")
for hotel_code, metrics in hotel_metrics.items():
    print(f"  {hotel_code}: 均价¥{metrics['avg_price']:.0f}, 底价¥{metrics['base_price']:.0f}, "
          f"实际入住率{metrics['occupancy_rate']*100:.1f}%, RevPAR¥{metrics['revpar']:.0f}")

# ========================
# 2. 对照组模拟（传统模式财务分析）
# ========================
print("\n" + "=" * 80)
print("【步骤2：对照组模拟 - 传统模式财务分析】")
print("=" * 80)

# 参数设置
np.random.seed(42)
control_group_users = 5000
experiment_group_users = 5000
discount_rate = 0.08  # 折现率8%
project_years = 1
months = 12

print(f"\n对照组用户数量: {control_group_users:,}名")
print(f"分析期限: {project_years}年（{months}个月）")
print(f"折现率: {discount_rate*100:.1f}%")

# 计算传统模式现金流（按月）
traditional_cashflows = []
monthly_data = []

for month in range(1, months + 1):
    # 基于实际入住率模拟月度波动
    monthly_revenue = 0
    monthly_cost = 0
    
    for hotel_code in hotel_codes:
        metrics = hotel_metrics[hotel_code]
        # 月度波动（基于实际入住率的±10%）
        monthly_occupancy = metrics['occupancy_rate'] * (1 + np.random.uniform(-0.10, 0.10))
        monthly_occupancy = max(0.3, min(1.0, monthly_occupancy))
        
        # 月度收入 = 房间数 × 入住率 × 平均房价 × 30天
        hotel_monthly_revenue = metrics['room_count'] * monthly_occupancy * metrics['avg_price'] * 30
        # 月度成本 = 收入 × 65%（变动成本35% + 固定成本30%）
        hotel_monthly_cost = hotel_monthly_revenue * 0.65
        
        monthly_revenue += hotel_monthly_revenue
        monthly_cost += hotel_monthly_cost
    
    monthly_profit = monthly_revenue - monthly_cost
    
    traditional_cashflows.append({
        'month': month,
        'revenue': monthly_revenue,
        'cost': monthly_cost,
        'profit': monthly_profit
    })
    
    monthly_data.append(monthly_profit)

traditional_df = pd.DataFrame(traditional_cashflows)

# 计算传统模式财务指标
traditional_total_revenue = traditional_df['revenue'].sum()
traditional_total_cost = traditional_df['cost'].sum()
traditional_total_profit = traditional_df['profit'].sum()

# 计算NPV（使用月折现率）
monthly_discount_rate = (1 + discount_rate) ** (1/12) - 1
traditional_npv = sum([cf / ((1 + monthly_discount_rate) ** (i+1)) for i, cf in enumerate(monthly_data)])

# 计算IRR（使用现金流序列，转换为年化收益率）
def calculate_irr(cashflows, periods_per_year=12):
    """计算IRR并转换为年化收益率
    
    注意：IRR需要现金流有符号变化（投资+回报）
    对于酒店金融化模式，我们计算的是投资回报率而非传统IRR
    """
    try:
        # 过滤掉零值
        non_zero_cashflows = [cf for cf in cashflows if abs(cf) > 1]
        
        if len(non_zero_cashflows) < 2:
            return 0
        
        # 检查现金流符号变化
        signs = [np.sign(cf) for cf in non_zero_cashflows]
        unique_signs = set(signs)
        
        # 如果所有现金流同号，使用ROI作为替代指标
        if len(unique_signs) == 1:
            # 计算简单年化收益率
            total_inflow = sum([cf for cf in non_zero_cashflows if cf > 0])
            total_outflow = abs(sum([cf for cf in non_zero_cashflows if cf < 0]))
            
            if total_outflow == 0:
                # 只有流入，没有流出，无法计算IRR
                return 0
            
            # 计算投资回报率（年化）
            net_profit = total_inflow - total_outflow
            roi = (net_profit / total_outflow) * 100
            return roi
        
        # 有符号变化，使用二分法计算IRR
        def npv(rate, cashflows):
            if rate <= -1:
                return float('inf')
            return sum([cf / ((1 + rate) ** i) for i, cf in enumerate(cashflows)])
        
        rate_low, rate_high = -0.9, 5.0
        target_npv = 0
        
        npv_low = npv(rate_low, non_zero_cashflows)
        npv_high = npv(rate_high, non_zero_cashflows)
        
        # 检查是否有根
        if npv_low * npv_high > 0:
            # 没有根，使用ROI
            total_positive = sum([cf for cf in non_zero_cashflows if cf > 0])
            total_negative = abs(sum([cf for cf in non_zero_cashflows if cf < 0]))
            if total_negative > 0:
                return ((total_positive - total_negative) / total_negative) * 100
            return 0
        
        for _ in range(100):
            rate_mid = (rate_low + rate_high) / 2
            npv_mid = npv(rate_mid, non_zero_cashflows)
            
            if abs(npv_mid - target_npv) < 1e-10:
                break
            
            if npv_low * npv_mid < 0:
                rate_high = rate_mid
                npv_high = npv_mid
            else:
                rate_low = rate_mid
                npv_low = npv_mid
        
        monthly_irr = (rate_low + rate_high) / 2
        
        # 检查IRR是否合理
        if monthly_irr <= -1 or monthly_irr > 10:
            # 不合理的IRR，使用ROI
            total_positive = sum([cf for cf in non_zero_cashflows if cf > 0])
            total_negative = abs(sum([cf for cf in non_zero_cashflows if cf < 0]))
            if total_negative > 0:
                return ((total_positive - total_negative) / total_negative) * 100
            return 0
        
        # 转换为年化收益率
        annual_irr = ((1 + monthly_irr) ** periods_per_year - 1) * 100
        return annual_irr
    except Exception as e:
        return 0

# 传统模式现金流：第0期为0（无初始投资），之后为月度利润
traditional_cashflow_series = [0] + monthly_data
traditional_irr = calculate_irr(traditional_cashflow_series)

# 计算ROI
traditional_roi = (traditional_total_profit / traditional_total_revenue) * 100 if traditional_total_revenue > 0 else 0

print(f"\n【传统模式财务指标】")
print(f"  总收入: ¥{traditional_total_revenue:,.0f}")
print(f"  总成本: ¥{traditional_total_cost:,.0f}")
print(f"  净利润: ¥{traditional_total_profit:,.0f}")
print(f"  NPV: ¥{traditional_npv:,.0f}")
print(f"  IRR: {traditional_irr:.2f}%")
print(f"  ROI: {traditional_roi:.2f}%")

# ========================
# 3. 时权ABS发行定价模型（收益法）
# ========================
print("\n" + "=" * 80)
print("【步骤3：时权ABS发行定价模型（收益法）】")
print("=" * 80)

# 参数设置
safety_factor = 0.8  # 安全系数
# 超发倍数 = 1 / 实际入住率 × 安全系数
avg_occupancy = np.mean([m['occupancy_rate'] for m in hotel_metrics.values()])
overbooking_multiplier = 1 / avg_occupancy * safety_factor

print(f"\n定价参数：")
print(f"  平均实际入住率: {avg_occupancy*100:.1f}%")
print(f"  安全系数: {safety_factor}")
print(f"  超发倍数: {overbooking_multiplier:.2f}")

# 计算各酒店时权ABS发行价格
abs_pricing = {}
total_physical_rooms = 0
total_issue_quantity = 0

for hotel_code in hotel_codes:
    metrics = hotel_metrics[hotel_code]
    total_physical_rooms += metrics['room_count']
    
    # 预期未来现金流 = 房间数 × 实际入住率 × 平均房价 × 365天
    expected_cashflow = (metrics['room_count'] * metrics['occupancy_rate'] * 
                        metrics['avg_price'] * 365)
    
    # 发行价格 = 预期现金流 / (1 + 折现率)（单份时权价格）
    issue_price_per_right = expected_cashflow / (1 + discount_rate) / metrics['room_count']
    
    # 实际发行数量 = 物理房间数 × 超发倍数
    issue_quantity = int(metrics['room_count'] * overbooking_multiplier)
    total_issue_quantity += issue_quantity
    
    # 总发行价格
    total_issue_price = issue_price_per_right * issue_quantity
    
    abs_pricing[hotel_code] = {
        'expected_cashflow': expected_cashflow,
        'issue_price_per_right': issue_price_per_right,
        'total_issue_price': total_issue_price,
        'issue_quantity': issue_quantity,
        'base_price': metrics['base_price'],
        'avg_price': metrics['avg_price'],
        'room_count': metrics['room_count']
    }
    
    print(f"\n  酒店 {hotel_code}:")
    print(f"    预期年现金流: ¥{expected_cashflow:,.0f}")
    print(f"    单份时权价格: ¥{issue_price_per_right:,.0f}")
    print(f"    发行数量: {issue_quantity}份")
    print(f"    总发行价格: ¥{total_issue_price:,.0f}")

print(f"\n  物理房间总数: {total_physical_rooms}间")
print(f"  时权发行总量: {total_issue_quantity}份")
print(f"  超发比例: {total_issue_quantity/total_physical_rooms:.2f}倍")

# ========================
# 4. 实验组模拟（金融化模式财务分析）
# ========================
print("\n" + "=" * 80)
print("【步骤4：实验组模拟 - 金融化模式财务分析】")
print("=" * 80)

print(f"\n实验组用户数量: {experiment_group_users:,}名")

# 第一阶段：时权ABS发行
print(f"\n【第一阶段：时权ABS发行】")

total_issue_revenue = 0  # 酒店发行总收入

for hotel_code in hotel_codes:
    pricing = abs_pricing[hotel_code]
    total_issue_revenue += pricing['total_issue_price']
    
print(f"  时权ABS发行总收入: ¥{total_issue_revenue:,.0f}")

# 第二阶段：平台交易与价格形成
print(f"\n【第二阶段：平台交易与价格形成】")

# 价格形成机制（基于供需关系）
# 需求函数：价格 = 底价 × (1 + 基础溢价 + 需求弹性 × 买家比例)
base_premium = 0.05  # 基础溢价5%
price_elasticity = 0.3  # 价格弹性系数
buyer_ratio = min(experiment_group_users / 5000, 1.0)  # 买家比例

market_premium = base_premium + price_elasticity * buyer_ratio
market_price_factor = 1 + market_premium

print(f"  基础溢价: {base_premium*100:.1f}%")
print(f"  买家比例: {buyer_ratio*100:.1f}%")
print(f"  市场价格溢价: {market_premium*100:.1f}%")
print(f"  市场价格因子: {market_price_factor:.4f}")

# 计算平台交易收入
trading_fee_rate = 0.005  # 交易手续费0.5%
total_trading_fee = 0
total_market_value = 0

for hotel_code in hotel_codes:
    pricing = abs_pricing[hotel_code]
    market_price = pricing['issue_price_per_right'] * market_price_factor
    market_value = pricing['issue_quantity'] * market_price
    trading_fee = market_value * trading_fee_rate
    
    total_market_value += market_value
    total_trading_fee += trading_fee

print(f"  市场总价值: ¥{total_market_value:,.0f}")
print(f"  交易手续费收入: ¥{total_trading_fee:,.0f}")

# 第三阶段：到期兑付
print(f"\n【第三阶段：到期兑付】")

# 用户选择分布
cash_redemption_rate = 0.30  # 30%现金兑付
physical_redemption_rate = 0.70  # 70%实物兑付

# 约定收益率
promised_return_rate = 0.08  # 年化8%
physical_discount_rate = 0.30  # 7折入住（30%折扣）

# 计算兑付现金流
hotel_redemption_cost = 0
investor_cash_returns = 0
investor_physical_savings = 0

for hotel_code in hotel_codes:
    pricing = abs_pricing[hotel_code]
    
    # 现金兑付部分（30%）
    cash_quantity = int(pricing['issue_quantity'] * cash_redemption_rate)
    # 现金兑付 = 购买价格 × (1 + 约定收益率)
    cash_return_per_unit = pricing['issue_price_per_right'] * (1 + promised_return_rate)
    total_cash_return = cash_quantity * cash_return_per_unit
    
    # 实物兑付部分（70%）
    physical_quantity = pricing['issue_quantity'] - cash_quantity
    # 实物价值 = 平均房价 × 折扣
    physical_value_per_unit = pricing['avg_price'] * (1 - physical_discount_rate)
    total_physical_value = physical_quantity * physical_value_per_unit
    
    hotel_redemption_cost += total_cash_return + total_physical_value
    investor_cash_returns += total_cash_return
    investor_physical_savings += total_physical_value

print(f"  现金兑付比例: {cash_redemption_rate*100:.0f}%")
print(f"  实物兑付比例: {physical_redemption_rate*100:.0f}%")
print(f"  约定收益率: {promised_return_rate*100:.0f}%/年")
print(f"  实物折扣率: {physical_discount_rate*100:.0f}%")
print(f"  投资者现金收益: ¥{investor_cash_returns:,.0f}")
print(f"  投资者实物价值: ¥{investor_physical_savings:,.0f}")

# 计算金融化模式财务指标
print(f"\n【金融化模式财务指标】")

# 酒店方收益
hotel_financialized_revenue = total_issue_revenue  # 发行收入
hotel_financialized_cost = hotel_redemption_cost    # 兑付成本
hotel_financialized_profit = hotel_financialized_revenue - hotel_financialized_cost

print(f"\n  酒店方：")
print(f"    发行收入: ¥{hotel_financialized_revenue:,.0f}")
print(f"    兑付成本: ¥{hotel_financialized_cost:,.0f}")
print(f"    净利润: ¥{hotel_financialized_profit:,.0f}")

# 平台方收益
management_fee_rate = 0.01  # 管理费率1%
management_fee = total_issue_revenue * management_fee_rate
spread_income = total_market_value - total_issue_revenue  # 买卖价差

platform_revenue = total_trading_fee + management_fee + spread_income
platform_profit = platform_revenue

print(f"\n  平台方：")
print(f"    交易手续费: ¥{total_trading_fee:,.0f}")
print(f"    管理费用: ¥{management_fee:,.0f}")
print(f"    买卖价差: ¥{spread_income:,.0f}")
print(f"    总收入: ¥{platform_revenue:,.0f}")

# 投资者方收益
total_investor_return = investor_cash_returns + investor_physical_savings
avg_investor_return = total_investor_return / experiment_group_users if experiment_group_users > 0 else 0
investor_cost = total_market_value
investor_net_return = total_investor_return - investor_cost
investor_return_rate = (investor_net_return / investor_cost) * 100 if investor_cost > 0 else 0

print(f"\n  投资者方：")
print(f"    投资成本: ¥{investor_cost:,.0f}")
print(f"    总回报: ¥{total_investor_return:,.0f}")
print(f"    净收益: ¥{investor_net_return:,.0f}")
print(f"    收益率: {investor_return_rate:.2f}%")
print(f"    平均收益: ¥{avg_investor_return:,.0f}/人")

# 计算金融化模式NPV和IRR
# 金融化模式现金流：第0期获得发行收入，后续支付兑付成本
financialized_cashflows = [hotel_financialized_revenue] + [-hotel_redemption_cost/12] * 12
financialized_npv = sum([cf / ((1 + monthly_discount_rate) ** i) for i, cf in enumerate(financialized_cashflows)])
financialized_irr = calculate_irr(financialized_cashflows)
financialized_roi = (hotel_financialized_profit / hotel_financialized_revenue) * 100 if hotel_financialized_revenue > 0 else 0

print(f"\n  综合财务指标：")
print(f"    NPV: ¥{financialized_npv:,.0f}")
print(f"    IRR: {financialized_irr:.2f}%")
print(f"    ROI: {financialized_roi:.2f}%")

# ========================
# 5. 风险评估与压力测试
# ========================
print("\n" + "=" * 80)
print("【步骤5：风险评估与压力测试】")
print("=" * 80)

# 流动性风险评估
daily_turnover_rate = 0.05  # 日均换手率5%
bid_ask_spread = 0.02  # 买卖价差2%
liquidity_score = 100 if daily_turnover_rate > 0.03 and bid_ask_spread < 0.05 else 50

print(f"\n【流动性风险】")
print(f"  日均换手率: {daily_turnover_rate*100:.1f}%")
print(f"  买卖价差: {bid_ask_spread*100:.1f}%")
print(f"  风险评分: {liquidity_score}/100")
print(f"  评估: {'低风险' if liquidity_score >= 80 else '中风险' if liquidity_score >= 50 else '高风险'}")

# 信用风险评估
default_probability = 0.03  # 违约概率3%
credit_rating = "A"  # 信用评级
credit_score = 100 if default_probability < 0.05 else 70 if default_probability < 0.10 else 30

print(f"\n【信用风险】")
print(f"  违约概率: {default_probability*100:.1f}%")
print(f"  信用评级: {credit_rating}")
print(f"  风险评分: {credit_score}/100")
print(f"  评估: {'低风险' if credit_score >= 80 else '中风险' if credit_score >= 50 else '高风险'}")

# 市场风险评估
price_volatility = 0.15  # 价格波动率15%
var_95 = abs(investor_net_return) * 0.10  # 95%置信度VaR
market_score = 100 if price_volatility < 0.20 else 70 if price_volatility < 0.30 else 40

print(f"\n【市场风险】")
print(f"  价格波动率: {price_volatility*100:.1f}%")
print(f"  VaR(95%): ¥{var_95:,.0f}")
print(f"  风险评分: {market_score}/100")
print(f"  评估: {'低风险' if market_score >= 80 else '中风险' if market_score >= 50 else '高风险'}")

# 压力测试
print(f"\n【压力测试】")

stress_results = {}

# 场景1：入住率下降20%
stress_occupancy = avg_occupancy * 0.80
stress_cashflow_1 = sum([m['room_count'] * stress_occupancy * m['avg_price'] * 365 
                         for m in hotel_metrics.values()])
stress_npv_1 = stress_cashflow_1 / (1 + discount_rate) - hotel_redemption_cost
stress_results['occupancy_down_20'] = {
    'npv': stress_npv_1,
    'pass': stress_npv_1 > 0
}

print(f"  场景1 - 入住率下降20%:")
print(f"    NPV: ¥{stress_npv_1:,.0f}")
print(f"    评估: {'通过 ✓' if stress_npv_1 > 0 else '不通过 ✗'}")

# 场景2：折现率上升2%
stress_discount = discount_rate + 0.02
stress_npv_2 = hotel_financialized_revenue / (1 + stress_discount) - hotel_redemption_cost
stress_results['discount_up_2'] = {
    'npv': stress_npv_2,
    'pass': stress_npv_2 > 0
}

print(f"  场景2 - 折现率上升2%:")
print(f"    NPV: ¥{stress_npv_2:,.0f}")
print(f"    评估: {'通过 ✓' if stress_npv_2 > 0 else '不通过 ✗'}")

# 场景3：兑付成本上升10%
stress_redemption = hotel_redemption_cost * 1.10
stress_npv_3 = hotel_financialized_revenue - stress_redemption
stress_results['redemption_up_10'] = {
    'npv': stress_npv_3,
    'pass': stress_npv_3 > 0
}

print(f"  场景3 - 兑付成本上升10%:")
print(f"    NPV: ¥{stress_npv_3:,.0f}")
print(f"    评估: {'通过 ✓' if stress_npv_3 > 0 else '不通过 ✗'}")

# ========================
# 6. 敏感性分析
# ========================
print("\n" + "=" * 80)
print("【步骤6：敏感性分析】")
print("=" * 80)

sensitivity_results = {}

print(f"\n【入住率敏感性】")
occupancy_sensitivity = []
for occ in [0.50, 0.60, 0.70, 0.80, 0.90]:
    sens_cashflow = sum([m['room_count'] * occ * m['avg_price'] * 365 * (1/occ*0.8) 
                         for m in hotel_metrics.values()])
    sens_npv = sens_cashflow / (1 + discount_rate) - hotel_redemption_cost
    occupancy_sensitivity.append({'occupancy': occ, 'npv': sens_npv})
    print(f"  入住率{occ*100:.0f}%: NPV = ¥{sens_npv:,.0f}")

sensitivity_results['occupancy'] = occupancy_sensitivity

print(f"\n【折现率敏感性】")
discount_sensitivity = []
for rate in [0.06, 0.07, 0.08, 0.09, 0.10]:
    sens_npv = hotel_financialized_profit / (1 + rate)
    discount_sensitivity.append({'discount_rate': rate, 'npv': sens_npv})
    print(f"  折现率{rate*100:.0f}%: NPV = ¥{sens_npv:,.0f}")

sensitivity_results['discount_rate'] = discount_sensitivity

# ========================
# 7. 可行性综合评估
# ========================
print("\n" + "=" * 80)
print("【步骤7：可行性综合评估】")
print("=" * 80)

# 对照组 vs 实验组对比
print(f"\n【对照组 vs 实验组对比】")
print(f"  {'指标':<20} {'对照组':>18} {'实验组':>18} {'增量':>18}")
print(f"  {'-'*75}")
print(f"  {'NPV':<20} {f'¥{traditional_npv:,.0f}':>18} {f'¥{financialized_npv:,.0f}':>18} {f'¥{financialized_npv-traditional_npv:,.0f}':>18}")
print(f"  {'IRR':<20} {f'{traditional_irr:.2f}%':>18} {f'{financialized_irr:.2f}%':>18} {f'{financialized_irr-traditional_irr:.2f}%':>18}")
print(f"  {'ROI':<20} {f'{traditional_roi:.2f}%':>18} {f'{financialized_roi:.2f}%':>18} {f'{financialized_roi-traditional_roi:.2f}%':>18}")

# 增量收益分析
npv_increment = financialized_npv - traditional_npv
irr_increment = financialized_irr - traditional_irr

print(f"\n【增量收益分析】")
print(f"  NPV增量: ¥{npv_increment:,.0f} ({(npv_increment/traditional_npv*100):.1f}%)")
print(f"  IRR增量: {irr_increment:.2f}%")

# 可行性评估
print(f"\n【可行性评估】")

# 财务可行性
financial_feasible = (financialized_npv > 0 and 
                      financialized_irr > 10 and 
                      financialized_roi > 15)

print(f"\n  财务可行性:")
print(f"    NPV > 0: {'✓' if financialized_npv > 0 else '✗'} (¥{financialized_npv:,.0f})")
print(f"    IRR > 10%: {'✓' if financialized_irr > 10 else '✗'} ({financialized_irr:.2f}%)")
print(f"    ROI > 15%: {'✓' if financialized_roi > 15 else '✗'} ({financialized_roi:.2f}%)")
print(f"    综合评估: {'通过 ✓' if financial_feasible else '不通过 ✗'}")

# 市场可行性
market_feasible = (daily_turnover_rate > 0.03 and 
                   price_volatility < 0.20)

print(f"\n  市场可行性:")
print(f"    流动性充足: {'✓' if daily_turnover_rate > 0.03 else '✗'} ({daily_turnover_rate*100:.1f}%)")
print(f"    价格稳定: {'✓' if price_volatility < 0.20 else '✗'} ({price_volatility*100:.1f}%)")
print(f"    综合评估: {'通过 ✓' if market_feasible else '不通过 ✗'}")

# 风险可控性
risk_controllable = (default_probability < 0.05 and 
                     price_volatility < 0.20)

print(f"\n  风险可控性:")
print(f"    违约概率 < 5%: {'✓' if default_probability < 0.05 else '✗'} ({default_probability*100:.1f}%)")
print(f"    价格波动 < 20%: {'✓' if price_volatility < 0.20 else '✗'} ({price_volatility*100:.1f}%)")
print(f"    综合评估: {'通过 ✓' if risk_controllable else '不通过 ✗'}")

# 综合评分
feasibility_score = 0
if financial_feasible:
    feasibility_score += 40
if market_feasible:
    feasibility_score += 30
if risk_controllable:
    feasibility_score += 30

# 压力测试加分
stress_pass_count = sum([1 for r in stress_results.values() if r['pass']])
feasibility_score += stress_pass_count * 5

print(f"\n【综合评分】")
print(f"  总分: {feasibility_score}/100")
if feasibility_score >= 90:
    rating = "A"
    rating_desc = "强烈推荐"
elif feasibility_score >= 70:
    rating = "B"
    rating_desc = "推荐"
elif feasibility_score >= 50:
    rating = "C"
    rating_desc = "谨慎考虑"
else:
    rating = "D"
    rating_desc = "不推荐"

print(f"  评级: {rating}级（{rating_desc}）")

# 可行性结论
overall_feasible = feasibility_score >= 70
print(f"\n【可行性结论】")
print(f"  酒店订单金融化方案: {'可行 ✓' if overall_feasible else '不可行 ✗'}")
print(f"  建议: {'可以推进实施，建议先进行小规模试点' if overall_feasible else '需要优化方案或等待更好的市场时机'}")

# ========================
# 8. 可视化展示
# ========================
print("\n" + "=" * 80)
print("【步骤8：生成可视化图表】")
print("=" * 80)

# 创建图表
fig = plt.figure(figsize=(20, 12))

# 1. 对照组 vs 实验组财务指标对比
ax1 = plt.subplot(2, 3, 1)
metrics = ['NPV', 'IRR', 'ROI']
traditional_values = [traditional_npv/1e9, traditional_irr, traditional_roi]
financialized_values = [financialized_npv/1e9, financialized_irr, financialized_roi]

x = np.arange(len(metrics))
width = 0.35

bars1 = ax1.bar(x - width/2, traditional_values, width, label='传统模式', color='#3498db')
bars2 = ax1.bar(x + width/2, financialized_values, width, label='金融化模式', color='#e74c3c')

ax1.set_ylabel('数值')
ax1.set_title('对照组 vs 实验组财务指标对比')
ax1.set_xticks(x)
ax1.set_xticklabels(metrics)
ax1.legend()
ax1.grid(True, alpha=0.3)

# 添加数值标签
for bar in bars1:
    height = bar.get_height()
    ax1.annotate(f'{height:.1f}',
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha='center', va='bottom', fontsize=9)

for bar in bars2:
    height = bar.get_height()
    ax1.annotate(f'{height:.1f}',
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha='center', va='bottom', fontsize=9)

# 2. 三方收益分布
ax2 = plt.subplot(2, 3, 2)
parties = ['酒店方', '平台方', '投资者方']
revenues = [hotel_financialized_revenue/1e9, platform_revenue/1e9, total_investor_return/1e9]
colors = ['#2ecc71', '#f39c12', '#9b59b6']

wedges, texts, autotexts = ax2.pie(revenues, labels=parties, autopct='%1.1f%%', 
                                   colors=colors, startangle=90)
ax2.set_title('三方收益分布')

# 3. 月度现金流对比
ax3 = plt.subplot(2, 3, 3)
months_list = list(range(1, 13))
traditional_monthly = [cf/1e9 for cf in monthly_data]
financialized_monthly = [financialized_cashflows[0]/1e9] + [-hotel_redemption_cost/12/1e9]*11

ax3.plot(months_list, traditional_monthly, marker='o', label='传统模式', linewidth=2, color='#3498db')
ax3.plot(months_list, financialized_monthly, marker='s', label='金融化模式', linewidth=2, color='#e74c3c')
ax3.set_xlabel('月份')
ax3.set_ylabel('现金流（十亿元）')
ax3.set_title('月度现金流对比')
ax3.legend()
ax3.grid(True, alpha=0.3)
ax3.axhline(y=0, color='k', linestyle='--', alpha=0.3)

# 4. 入住率敏感性分析
ax4 = plt.subplot(2, 3, 4)
occupancy_rates = [r['occupancy']*100 for r in occupancy_sensitivity]
occupancy_npvs = [r['npv']/1e9 for r in occupancy_sensitivity]

ax4.plot(occupancy_rates, occupancy_npvs, marker='o', linewidth=2, color='#e67e22')
ax4.set_xlabel('入住率 (%)')
ax4.set_ylabel('NPV（十亿元）')
ax4.set_title('入住率敏感性分析')
ax4.grid(True, alpha=0.3)
ax4.axhline(y=0, color='r', linestyle='--', alpha=0.5)

# 5. 风险评估雷达图
ax5 = plt.subplot(2, 3, 5, projection='polar')
risk_categories = ['流动性', '信用', '市场', '操作']
risk_scores = [liquidity_score, credit_score, market_score, 85]  # 操作风险假设85分

angles = np.linspace(0, 2 * np.pi, len(risk_categories), endpoint=False).tolist()
risk_scores_plot = risk_scores + [risk_scores[0]]
angles += angles[:1]

ax5.plot(angles, risk_scores_plot, 'o-', linewidth=2, color='#e74c3c')
ax5.fill(angles, risk_scores_plot, alpha=0.25, color='#e74c3c')
ax5.set_xticks(angles[:-1])
ax5.set_xticklabels(risk_categories)
ax5.set_ylim(0, 100)
ax5.set_title('风险评估雷达图', pad=20)

# 6. 可行性评分
ax6 = plt.subplot(2, 3, 6)
feasibility_categories = ['财务可行性', '市场可行性', '风险可控性', '压力测试']
feasibility_scores = [40 if financial_feasible else 20, 
                      30 if market_feasible else 15, 
                      30 if risk_controllable else 15,
                      stress_pass_count * 5]

colors_feasibility = ['#2ecc71' if s >= 30 else '#f39c12' if s >= 15 else '#e74c3c' for s in feasibility_scores]
bars = ax6.barh(feasibility_categories, feasibility_scores, color=colors_feasibility)
ax6.set_xlabel('得分')
ax6.set_title(f'可行性评分 (总分: {feasibility_score}/100)')
ax6.set_xlim(0, 50)

# 添加数值标签
for i, (bar, score) in enumerate(zip(bars, feasibility_scores)):
    ax6.text(score + 1, i, f'{score}', va='center', fontsize=10)

plt.tight_layout()
plt.savefig(f'{work_dir}/output/simulation_visualization_v5.png', dpi=300, bbox_inches='tight')
print(f"\n可视化图表已保存至: {work_dir}/simulation_visualization_v5.png")
plt.close()

# ========================
# 9. 详细报告输出
# ========================
print("\n" + "=" * 80)
print("【步骤9：详细报告输出】")
print("=" * 80)

report = {
    "simulation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "simulation_version": "V5",
    "analysis_type": "酒店订单金融化可行性分析 - 优化版",
    "parameters": {
        "control_group_users": control_group_users,
        "experiment_group_users": experiment_group_users,
        "discount_rate": discount_rate,
        "project_years": project_years,
        "safety_factor": safety_factor,
        "overbooking_multiplier": overbooking_multiplier,
        "promised_return_rate": promised_return_rate,
        "physical_discount_rate": physical_discount_rate,
        "trading_fee_rate": trading_fee_rate,
        "management_fee_rate": management_fee_rate
    },
    "hotel_selection": [
        {
            "hotel_code": hotel_code,
            "hotel_name": hotel_info[hotel_info['hotelCode'] == hotel_code]['hotelName'].values[0] if len(hotel_info[hotel_info['hotelCode'] == hotel_code]) > 0 else "未知",
            "avg_price": round(metrics['avg_price'], 2),
            "base_price": round(metrics['base_price'], 2),
            "occupancy_rate": round(metrics['occupancy_rate'], 4),
            "revpar": round(metrics['revpar'], 2),
            "room_count": metrics['room_count']
        }
        for hotel_code, metrics in hotel_metrics.items()
    ],
    "abs_pricing": [
        {
            "hotel_code": hotel_code,
            "expected_cashflow": round(pricing['expected_cashflow'], 2),
            "issue_price_per_right": round(pricing['issue_price_per_right'], 2),
            "total_issue_price": round(pricing['total_issue_price'], 2),
            "issue_quantity": pricing['issue_quantity']
        }
        for hotel_code, pricing in abs_pricing.items()
    ],
    "control_group": {
        "total_revenue": round(traditional_total_revenue, 2),
        "total_cost": round(traditional_total_cost, 2),
        "total_profit": round(traditional_total_profit, 2),
        "npv": round(traditional_npv, 2),
        "irr": round(traditional_irr, 2),
        "roi": round(traditional_roi, 2)
    },
    "experiment_group": {
        "issue_phase": {
            "total_issue_revenue": round(total_issue_revenue, 2),
            "total_physical_rooms": total_physical_rooms,
            "total_issue_quantity": total_issue_quantity,
            "overbooking_ratio": round(total_issue_quantity/total_physical_rooms, 2)
        },
        "trading_phase": {
            "market_price_factor": round(market_price_factor, 4),
            "total_market_value": round(total_market_value, 2),
            "total_trading_fee": round(total_trading_fee, 2)
        },
        "redemption_phase": {
            "cash_redemption_rate": cash_redemption_rate,
            "physical_redemption_rate": physical_redemption_rate,
            "investor_cash_returns": round(investor_cash_returns, 2),
            "investor_physical_savings": round(investor_physical_savings, 2)
        },
        "hotel": {
            "revenue": round(hotel_financialized_revenue, 2),
            "cost": round(hotel_financialized_cost, 2),
            "profit": round(hotel_financialized_profit, 2)
        },
        "platform": {
            "trading_fee": round(total_trading_fee, 2),
            "management_fee": round(management_fee, 2),
            "spread_income": round(spread_income, 2),
            "total_revenue": round(platform_revenue, 2)
        },
        "investors": {
            "cost": round(investor_cost, 2),
            "total_return": round(total_investor_return, 2),
            "net_return": round(investor_net_return, 2),
            "return_rate": round(investor_return_rate, 2),
            "avg_return_per_user": round(avg_investor_return, 2)
        },
        "financial_metrics": {
            "npv": round(financialized_npv, 2),
            "irr": round(financialized_irr, 2),
            "roi": round(financialized_roi, 2)
        }
    },
    "incremental_analysis": {
        "npv_increment": round(npv_increment, 2),
        "npv_increment_percent": round(npv_increment/traditional_npv*100, 2) if traditional_npv > 0 else 0,
        "irr_increment": round(irr_increment, 2)
    },
    "risk_assessment": {
        "liquidity_risk": {
            "daily_turnover_rate": daily_turnover_rate,
            "bid_ask_spread": bid_ask_spread,
            "score": liquidity_score,
            "assessment": "低风险" if liquidity_score >= 80 else "中风险" if liquidity_score >= 50 else "高风险"
        },
        "credit_risk": {
            "default_probability": default_probability,
            "credit_rating": credit_rating,
            "score": credit_score,
            "assessment": "低风险" if credit_score >= 80 else "中风险" if credit_score >= 50 else "高风险"
        },
        "market_risk": {
            "price_volatility": price_volatility,
            "var_95": round(var_95, 2),
            "score": market_score,
            "assessment": "低风险" if market_score >= 80 else "中风险" if market_score >= 50 else "高风险"
        }
    },
    "stress_test": stress_results,
    "sensitivity_analysis": sensitivity_results,
    "feasibility_evaluation": {
        "financial": {
            "npv_positive": financialized_npv > 0,
            "irr_above_10": financialized_irr > 10,
            "roi_above_15": financialized_roi > 15,
            "overall": financial_feasible
        },
        "market": {
            "liquidity_sufficient": daily_turnover_rate > 0.03,
            "price_stable": price_volatility < 0.20,
            "overall": market_feasible
        },
        "risk": {
            "default_controllable": default_probability < 0.05,
            "volatility_controllable": price_volatility < 0.20,
            "overall": risk_controllable
        },
        "overall_score": feasibility_score,
        "rating": rating,
        "rating_description": rating_desc,
        "conclusion": "可行" if overall_feasible else "需优化",
        "recommendation": "可以推进实施，建议先进行小规模试点" if overall_feasible else "需要优化方案或等待更好的市场时机"
    }
}

# 转换numpy类型为Python原生类型
def convert_to_serializable(obj):
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(i) for i in obj]
    elif isinstance(obj, (np.bool_, np.integer)):
        return bool(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

serializable_report = convert_to_serializable(report)

# 保存详细报告
report_file = f'{work_dir}/output/simulation_report_v5.json'
with open(report_file, 'w', encoding='utf-8') as f:
    json.dump(serializable_report, f, ensure_ascii=False, indent=2)

print(f"\n详细报告已保存至: {report_file}")

print("\n" + "=" * 80)
print("酒店订单金融化可行性分析 V5 完成！")
print("=" * 80)
print(f"\n生成文件：")
print(f"  1. {work_dir}/simulation_report_v5.json")
print(f"  2. {work_dir}/simulation_visualization_v5.png")
