"""
Flight FSR Model Parameters — Centralized configuration.
All parameters labeled: CALIBRATED / ASSUMPTION / JUDGMENT / DERIVED.

Key structural differences from hotel FSR:
1. Credit model is CARRIER-level (25 carriers), not asset-level
2. t-Copula (fat tails) instead of Gaussian Copula — single carrier default = mass default
3. Booking curve pricing instead of spot convergence
4. Shorter maturity (24 months vs 36) due to dynamic flight schedules
5. More conservative structuring due to higher volatility (CV 0.56 vs 0.20)
"""
from dataclasses import dataclass, field


@dataclass
class CarrierCreditParams:
    """Carrier-level credit risk parameters."""
    # Merton-style structural model
    annual_risk_free_rate: float = 0.025       # ASSUMPTION: same as hotel model
    default_barrier_ratio: float = 0.60        # JUDGMENT: higher than hotel (0.55) — airlines have more fixed costs
    drift_rate: float = 0.02                   # JUDGMENT: airline industry lower growth than hotels
    pd_calibration_factor: float = 2.0         # ASSUMPTION: lower than hotel (2.5) — carrier PDs more stable
    pd_upper_cap: float = 0.35                 # JUDGMENT: lower cap than hotel (0.50) — major carriers rarely default
    pd_lower_floor: float = 0.003              # JUDGMENT: floor 0.3% (major carriers)

    # Carrier type adjustments (regionals operate under CPA — lower risk than fare CV suggests)
    carrier_type_multipliers: dict = field(default_factory=lambda: {
        'major': 1.0,      # AA, DL, UA, WN — public financials available
        'lcc': 1.15,       # B6, F9, NK, G4 — higher volatility, lower margin
        'regional': 0.70,  # OO, YX, MQ, 9E, OH — capacity purchase agreements
        'other': 1.0,
    })

    # Carrier classification
    carrier_types: dict = field(default_factory=lambda: {
        'WN': 'major', 'DL': 'major', 'AA': 'major', 'UA': 'major',
        'AS': 'major', 'B6': 'lcc', 'NK': 'lcc', 'F9': 'lcc', 'G4': 'lcc',
        'HA': 'lcc', 'OO': 'regional', 'YX': 'regional', 'MQ': 'regional',
        '9E': 'regional', 'OH': 'regional',
    })

    # LGD by carrier type (regionals have higher recovery due to CPA contracts)
    lgd_by_type: dict = field(default_factory=lambda: {
        # Airline Ch.11 ≠ liquidation. Flights continue, tickets honored.
        # Realized loss for ticket-like claims is low (rebooking, vouchers, partial refund).
        'major': 0.15, 'lcc': 0.30, 'regional': 0.10, 'other': 0.25,
    })

    # Rating thresholds (Moody's scale, same as hotel)
    rating_pd_thresholds: list = field(default_factory=lambda: [
        (0.0005, 'Aaa'), (0.0015, 'Aa'), (0.0040, 'A'),
        (0.0100, 'Baa'), (0.0300, 'Ba'), (0.0800, 'B'),
        (0.2000, 'Caa'), (0.3500, 'Ca-C'),
    ])

    # t-Copula parameters (key innovation vs hotel Gaussian Copula)
    t_copula_df: float = 4.0                   # JUDGMENT: degrees of freedom (lower = fatter tails)
    base_correlation: float = 0.40             # CALIBRATED: empirical equity corr 0.64 × 0.6 shrinkage ≈ 0.38, rounded up
    same_type_bonus: float = 0.17              # CALIBRATED: empirical same-type bonus from 2021-2025 daily returns
    cholesky_jitter: float = 0.001             # DERIVED: numerical stability


@dataclass
class RoutePoolParams:
    """Route pool construction parameters."""
    # Pool composition targets
    target_pool_size: int = 80                 # JUDGMENT: same as hotel for comparability
    max_routes_per_carrier: int = 8             # JUDGMENT: tighter cap at 12mo — less single-carrier tail risk
    min_routes_per_carrier: int = 2            # JUDGMENT: ensure carrier representation

    # Stratification dimensions
    distance_bands: dict = field(default_factory=lambda: {
        'short': (0, 500),        # miles
        'medium': (500, 1500),
        'long': (1500, 5000),
    })
    distance_weights: dict = field(default_factory=lambda: {
        'short': 0.30, 'medium': 0.40, 'long': 0.30,
    })

    # Route quality filters
    min_quarterly_obs: int = 20                # JUDGMENT: minimum observations per route per quarter
    max_cv: float = 1.5                        # JUDGMENT: exclude routes with absurd fare CV
    min_avg_fare: float = 50                   # JUDGMENT: exclude ultra-low-fare routes (data errors)

    # Seasonal adjustment
    seasonal_amplitude: float = 0.10           # JUDGMENT: flight seasonality ~10% amplitude


@dataclass
class TimeRightParams:
    """Flight Time-Right issuance and pricing parameters."""
    # ISSUANCE — more conservative than hotel due to higher volatility
    time_discount_rate: float = 0.08           # CALIBRATED: US airline industry WACC ~7.5-8.5% (Damodaran 2025)
    issue_discount: float = 0.08               # JUDGMENT: within hotel range (0.08-0.10) for 12mo maturity
    safety_factor: float = 0.82                # JUDGMENT: comparable to hotel (0.80) at 12mo; less uncertainty
    maturity_months: int = 12                  # JUDGMENT: 12 months captures full seasonal cycle, reduces cumulative PD exposure

    # BOOKING CURVE (replaces hotel's price convergence)
    # Model: P(t) = P_0 * exp(β * t/T), where t = months before departure
    booking_curve_beta: float = 0.22           # ASSUMPTION: ~25% price increase over 12mo (vs 35% over 24mo)
    booking_curve_noise: float = 0.06          # JUDGMENT: less noise over shorter horizon

    # SECONDARY MARKET
    trading_fee_rate: float = 0.003            # JUDGMENT: 0.3% per trade (flights more liquid than hotels)
    monthly_turnover: float = 0.08             # JUDGMENT: 8% monthly turnover (higher than hotel 5% — deeper market)

    # REDEMPTION (simplified vs hotel's tripartite — flights mainly cash settlement)
    cash_redemption_ratio: float = 0.70        # JUDGMENT: 70% cash (dominant for flights)
    voucher_redemption_ratio: float = 0.25     # JUDGMENT: 25% flight voucher/credit
    transfer_ratio: float = 0.05               # DERIVED: 5% peer transfer
    redemption_start_month: int = 9             # DERIVED: start 3 months before maturity (12mo)

    # Overbooking (similar fractional-reserve logic as hotel)
    overbooking_base: float = 1.25             # JUDGMENT: comparable to hotel at 12mo; shorter window, less cancellation risk

    # PLATFORM ECONOMICS
    platform_acquisition_discount: float = 0.93  # JUDGMENT: platform buys at 93% of issue (vs 95% hotel — more risk)
    platform_retail_markup: float = 0.10         # JUDGMENT: 10% retail markup (vs 8% hotel — higher volatility premium)
    platform_operating_cost_rate: float = 0.06   # JUDGMENT: 6% operating cost (lower than hotel 8% — more digital)


@dataclass
class MonteCarloParams:
    """Monte Carlo simulation parameters."""
    n_paths: int = 5000                        # DERIVED: same as hotel
    n_months: int = 12                         # DERIVED: matches maturity (12mo)
    seed: int = 42

    # Stress test scenarios
    stress_multipliers: list = field(default_factory=lambda: [
        ('Baseline', 1.0, 1.0),
        ('Mild Stress', 1.5, 1.15),
        ('Moderate Stress', 2.5, 1.35),
        ('Severe Stress', 4.0, 1.60),
        ('Extreme Stress', 6.0, 2.00),
    ])

    # VaR levels
    var_levels: tuple = (95, 99)


@dataclass
class StructuringParams:
    """ABS tranche structure — more conservative than hotel."""
    senior_pct: float = 0.65                   # JUDGMENT: closer to hotel (0.68) with recalibrated PD/LGD
    mezzanine_pct: float = 0.20                # DERIVED: sum to 100%
    junior_pct: float = 0.10                   # DERIVED
    equity_pct: float = 0.05                   # DERIVED: standard 5% equity for incentive alignment

    senior_coupon: float = 0.055               # JUDGMENT: higher than hotel (0.045) — risk premium
    mezzanine_coupon: float = 0.080            # JUDGMENT
    junior_coupon: float = 0.120               # JUDGMENT

    reserve_pct: float = 0.05                  # JUDGMENT: higher than hotel (0.03) — more buffer
    overcollateralization_pct: float = 0.03    # JUDGMENT: higher than hotel (0.02)


@dataclass
class RiskAssessmentParams:
    """Risk scoring weights (same framework as hotel for comparability)."""
    credit_quality_weight: float = 20
    profit_potential_weight: float = 25
    risk_control_weight: float = 23
    technical_feasibility_weight: float = 22
    regulatory_weight: float = 10              # New dimension — airline regulation adds complexity

    rating_a_threshold: float = 75             # Lower than hotel (80) — acknowledging harder environment
    rating_b_threshold: float = 60
    rating_c_threshold: float = 45
