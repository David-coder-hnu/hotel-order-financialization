"""
模型参数集中管理 (Model Parameters — Single Source of Truth)

所有可调参数集中在此文件。每个参数标注：
- CALIBRATED: 基于外部数据/文献校准
- ASSUMPTION: 合理假设，有文献支撑但未直接校准
- JUDGMENT: 主观判断，需要敏感性分析
- DERIVED: 从其他参数推导

使用方法: from model_params import Params; p = Params()
"""

from dataclasses import dataclass, field


@dataclass
class CreditRiskParams:
    """信用风险模型参数"""
    # Merton DD 模型
    annual_risk_free_rate: float = 0.025       # ASSUMPTION: 中国10年期国债 ~2.5%
    liability_ratio: float = 0.55              # JUDGMENT: 违约边界 = 均价×55%
    drift_rate: float = 0.03                   # JUDGMENT: 资产漂移率
    pd_calibration_factor: float = 2.5         # ASSUMPTION: 文献范围 1.5-3.0 (Bharath & Shumway 2008)
    pd_upper_cap: float = 0.50                 # JUDGMENT: PD上限 (避免个体酒店主导池子)
    pd_lower_cap: float = 0.001                # JUDGMENT: PD下限 0.1%
    dd_lower_bound: float = 0.1                # JUDGMENT: DD下限
    vol_lower_bound: float = 0.05              # JUDGMENT: 年化波动率下限 5%

    # 酒店等级波动率乘数
    level_vol_multiplier: dict = field(default_factory=lambda: {
        '经济': 1.20, '舒适': 1.00, '高档': 0.80, '豪华': 0.65
    })                                          # JUDGMENT: 高星酒店价格更稳定

    # 酒店等级 LGD 基准
    level_lgd_base: dict = field(default_factory=lambda: {
        '经济': 0.60, '舒适': 0.55, '高档': 0.50, '豪华': 0.40
    })                                          # JUDGMENT: 高星酒店回收率更高

    lgd_vol_adjustment: float = 0.20           # JUDGMENT: LGD 波动率调整幅度
    lgd_vol_coefficient: float = 0.5           # JUDGMENT: 波动率→LGD 系数
    lgd_price_buffer_coefficient: float = -0.05 # JUDGMENT: 价格缓冲→LGD 系数

    # GARCH(1,1) 参数
    garch_omega: float = 0.00001               # ASSUMPTION: 金融时间序列文献常用值
    garch_alpha: float = 0.10                  # ASSUMPTION: 同上
    garch_beta: float = 0.85                   # ASSUMPTION: 同上

    # 评级映射 (对标 Moody's)
    rating_pd_thresholds: list = field(default_factory=lambda: [
        (0.0002, 'Aaa'), (0.0005, 'Aa'), (0.0015, 'A'),
        (0.0040, 'Baa'), (0.0100, 'Ba'), (0.0300, 'B'),
        (0.1000, 'Caa'), (0.3000, 'Ca-C'),
    ])                                          # ASSUMPTION: 简化自穆迪评级映射表

    # Copula 违约相关性
    rho_sys: float = 0.70                      # JUDGMENT: 系统因子权重
    rho_idio: float = 0.30                     # DERIVED: = 1 - rho_sys
    within_grade_correlation: float = 0.08     # JUDGMENT: 同等级基础相关
    cross_grade_correlation: float = 0.03      # JUDGMENT: 不同等级基础相关
    cholesky_jitter: float = 0.001             # DERIVED: 数值稳定性


@dataclass
class StructuringParams:
    """分层结构参数"""
    senior_pct: float = 0.68                   # JUDGMENT: Senior 占比
    mezzanine_pct: float = 0.20                # DERIVED
    junior_pct: float = 0.08                   # DERIVED
    equity_pct: float = 0.04                   # DERIVED

    senior_coupon: float = 0.045               # JUDGMENT: 对标 AAA 企业债
    mezzanine_coupon: float = 0.065            # JUDGMENT: 对标 BBB 企业债
    junior_coupon: float = 0.095               # JUDGMENT: 对标 B 级企业债

    reserve_pct: float = 0.03                  # JUDGMENT: 储备金比例
    excess_spread_annual: float = 0.015        # JUDGMENT: 超额利差缓冲
    overcollateralization_pct: float = 0.02    # JUDGMENT: 超额抵押

    # 瀑布触发器
    oc_threshold: float = 1.0                  # ASSUMPTION: OC 测试阈值
    ic_threshold: float = 1.0                  # ASSUMPTION: IC 测试阈值
    trigger_wait_months: int = 3               # JUDGMENT: 触发前等待月数
    cumulative_default_threshold: float = 0.15 # JUDGMENT: 违约事件阈值
    default_observation_months: int = 5        # JUDGMENT: 违约观察期


@dataclass
class PoolParams:
    """资产池参数"""
    # 分层抽样
    level_weights: dict = field(default_factory=lambda: {
        '经济': 0.40, '舒适': 0.30, '高档': 0.20, '豪华': 0.10
    })                                          # JUDGMENT: 对标成都市场分布
    district_concentration_limit: float = 0.25 # JUDGMENT: 地理集中度上限
    min_hotels_per_level: int = 5              # JUDGMENT: 每层最少酒店数
    preferred_pd_range: tuple = (0.005, 0.04)  # JUDGMENT: 优选 PD 范围

    # 酒店房间数估算
    rooms_by_level: dict = field(default_factory=lambda: {
        '经济': 60, '舒适': 80, '高档': 120, '豪华': 200
    })                                          # JUDGMENT: 行业经验值
    occupancy_default: float = 0.62            # JUDGMENT: 成都酒店平均入住率
    occupancy_denominator: float = 0.3         # JUDGMENT: 入住率分母下限(超发计算)

    # 价格过滤
    price_lower: float = 1000                  # JUDGMENT: 价格下限(分), 排除异常数据
    price_upper: float = 500000               # JUDGMENT: 价格上限(分)
    min_price_volatility: float = 0.001        # JUDGMENT: 最低价格波动率
    pd_filter_range: tuple = (0.0001, 0.50)    # DERIVED: 与 PD 上下限一致
    min_price_records: int = 30                # JUDGMENT: 最小价格记录数

    # 季节性参数
    seasonal_amplitude: float = 0.15           # JUDGMENT: 月度季节性波幅
    annual_growth_trend: float = 0.02          # JUDGMENT: 年化增长趋势

    # 目标池规模
    target_pool_size: int = 80                 # JUDGMENT: 蒙特卡洛可处理规模


@dataclass
class TimeRightParams:
    """时权发行与定价参数"""
    # 发行定价
    time_value_discount_rate: float = 0.08     # JUDGMENT: 年化时间价值折现率
    issue_discount: float = 0.10              # JUDGMENT: 发行折扣 (IPO 抑价类比)
    safety_factor: float = 0.80               # JUDGMENT: 超发安全系数
    time_to_maturity_months: int = 36          # DERIVED: 时权覆盖期限

    # 二级市场
    convergence_speed_beta: float = 0.8        # JUDGMENT: 价格收敛速度
    price_noise_std: float = 0.05              # JUDGMENT: 价格噪声标准差
    price_floor_ratio: float = 0.5             # JUDGMENT: 价格下限 = 发行价 × 0.5
    turnover_rate: float = 0.05                # JUDGMENT: 时权月度周转率
    trading_fee_rate: float = 0.005            # JUDGMENT: 交易手续费 0.5%

    # 做市商参数
    market_maker_premiums: dict = field(default_factory=lambda: {
        'near': 0.25, 'mid': 0.15, 'far': 0.08
    })                                          # JUDGMENT: 时段溢价率
    platform_acquisition_discount: float = 0.95 # JUDGMENT: 平台收购折扣率

    # 三元兑付
    redemption_start_month: int = 6            # JUDGMENT: 兑付起始月
    physical_redemption_discount: float = 0.30 # JUDGMENT: 实物兑付折扣 (7折)
    cash_ratio_mean: float = 0.25             # JUDGMENT: 现金兑付比例均值
    physical_ratio_mean: float = 0.50         # JUDGMENT: 实物兑付比例均值
    physical_variable_cost_rate: float = 0.35 # JUDGMENT: 实物兑付变动成本率

    # 平台经济
    platform_operating_cost_rate: float = 0.08 # JUDGMENT: 平台运营成本率
    working_capital_boost_rate: float = 0.35   # JUDGMENT: 营运资金提升率


@dataclass
class MonteCarloParams:
    """蒙特卡洛模拟参数"""
    n_paths: int = 5000                        # JUDGMENT: 精度 vs 性能权衡
    n_months: int = 36                         # DERIVED: 3年模拟期
    seed: int = 42                             # DERIVED: 可复现性
    batch_size: int = 500                      # DERIVED: 性能调优

    # 压力测试情景
    stress_multipliers: list = field(default_factory=lambda: [
        ('Baseline', 1.0, 1.0),
        ('Mild Stress', 1.5, 1.1),
        ('Moderate Stress', 2.5, 1.3),
        ('Severe Stress', 4.0, 1.6),
        ('Extreme Stress', 6.0, 2.0),
    ])                                          # JUDGMENT: 情景参数

    # VaR / CVaR
    var_levels: tuple = (95, 99)               # ASSUMPTION: 行业标准


@dataclass
class DCFParams:
    """DCF 估值参数"""
    wacc: float = 0.08                         # JUDGMENT: 中国酒店行业 WACC 估算
    sensitivity_range: tuple = (0.05, 0.12)    # DERIVED: 敏感性分析范围
    fen_to_yuan: float = 100.0                 # DERIVED: 货币单位转换


@dataclass
class RiskAssessmentParams:
    """风险评估评分参数"""
    # 评分权重 (百分制)
    credit_quality_weight: float = 20          # JUDGMENT
    profit_potential_weight: float = 25        # JUDGMENT
    risk_control_weight: float = 23            # JUDGMENT
    technical_feasibility_weight: float = 23   # JUDGMENT

    # 评级阈值
    rating_a_threshold: float = 80             # JUDGMENT: A 级最低分
    rating_b_threshold: float = 65             # JUDGMENT: B 级最低分
    rating_c_threshold: float = 50             # JUDGMENT: C 级最低分
