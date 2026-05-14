"""
Flight Carrier Credit Model — carrier-level PD/LGD/rating.

Key difference from hotel credit model:
- Credit entity = CARRIER (25), not individual asset
- Base PD from carrier type + market position (NOT fare CV directly)
- Fare CV provides MODEST volatility adjustment (yield management ≠ bankruptcy risk)
- t-Copula correlation matrix built from carrier business model similarity

RATIONALE: Airline fare CV is dominated by yield management (hundreds of fare classes,
dynamic pricing), not financial distress. Using fare CV as primary PD driver would
give Delta (CV=0.75) the same PD as a distressed airline. Instead, we use:
  Base PD (carrier type, historically calibrated) + CV adjustment (limited to ±40%)
"""
import numpy as np
import pandas as pd
from scipy import stats
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')


# ─── Historically calibrated base PDs for US airlines ───
# Based on: US airline bankruptcies 2000-2025 (11 major filings),
# current credit ratings (S&P/Moody's), and market-implied CDS spreads.
# Key reference: Delta, United, American all filed Ch.11 in 2002-2005 and
# again (some) in 2008-2013. Post-consolidation, major airline PDs are lower.

CARRIER_BASE_PD = {
    # Major carriers — post-consolidation era (2013+), IG or near-IG
    # Actual history: only Spirit (2024) filed Ch.11 since 2013 among US majors
    # Ch.11 ≠ liquidation — airlines continue flying, ticket holders minimally affected
    'WN': 0.001,   # Southwest: 50+ years, never filed, strongest balance sheet
    'DL': 0.003,   # Delta: filed 2005, now solidly IG, 19+ years clean
    'AA': 0.004,   # American: filed 2011, post-US Airways merger, 14+ years clean
    'UA': 0.003,   # United: filed 2002, now IG, 23+ years clean
    'AS': 0.002,   # Alaska: never filed, strong niche, acquired HA
    # LCC — higher margin pressure, but still surviving
    'B6': 0.015,   # JetBlue: never filed, margin challenges
    'NK': 0.050,   # Spirit: filed Ch.11 Nov 2024 (priced IN — this is known)
    'F9': 0.020,   # Frontier: never filed, ultra-low-cost model
    'G4': 0.012,   # Allegiant: never filed, profitable niche
    'HA': 0.010,   # Hawaiian: acquired by Alaska 2024 (already absorbed)
    # Regional — operate under CPA, parent carriers bear most risk
    'OO': 0.008,   # SkyWest: largest regional, contracts with DL/UA/AA
    'YX': 0.015,   # Republic: filed 2016, emerged 2017, clean since
    'MQ': 0.010,   # Envoy: wholly owned by AA, AA bears default risk
    '9E': 0.010,   # Endeavor: wholly owned by DL, DL bears default risk
    'OH': 0.010,   # PSA: wholly owned by AA, AA bears default risk
    # Default
    'default': 0.025,
}

# Median fare CV across all carriers for normalization
MEDIAN_FARE_CV = 0.65


class CarrierCreditModel:
    """Carrier-level credit rating: base PD from type + CV adjustment + market position."""

    def __init__(self, carrier_stats: dict, params=None):
        self.carrier_stats = carrier_stats
        if params is None:
            from flight_fsr_params import CarrierCreditParams
            params = CarrierCreditParams()
        self.p = params

    def compute_all_carriers(self):
        """Compute PD, LGD, rating for all carriers."""
        results = []
        total_pax = sum(s['sum_pax'] for s in self.carrier_stats.values())

        for carrier, d in self.carrier_stats.items():
            if d['n'] < 100:
                continue

            mean_fare = d['sum_fare'] / d['n']
            var_fare = max(0, d['sum2_fare'] / d['n'] - mean_fare**2)
            fare_cv = np.sqrt(var_fare) / mean_fare if mean_fare > 0 else MEDIAN_FARE_CV
            market_share = d['sum_pax'] / total_pax

            ctype = self.p.carrier_types.get(carrier, 'other')

            # Step 1: Base PD from carrier type + historical calibration
            base_pd = CARRIER_BASE_PD.get(carrier, CARRIER_BASE_PD['default'])

            # Step 2: Market share adjustment — larger carriers are SAFER (lower PD)
            # Historically, no US major carrier (post-consolidation) has filed Ch.11 except Spirit
            size_factor = 1.0 / max(0.4, 1.0 + 0.4 * np.log(max(market_share * 100, 0.1)))

            # Step 3: Fare CV adjustment — limited impact (±40% range)
            # Higher CV → some additional risk, but NOT the primary driver
            # Rationale: CV=0.55 (very stable yield mgmt) vs CV=0.85 (aggressive) matters,
            # but both are within normal airline operations
            cv_deviation = (fare_cv - MEDIAN_FARE_CV) / MEDIAN_FARE_CV
            cv_factor = 1.0 + np.clip(cv_deviation, -0.4, 0.4)
            # CV=0.55 → cv_deviation=-0.15 → cv_factor=0.85 (lower risk)
            # CV=0.85 → cv_deviation=+0.31 → cv_factor=1.31 (higher risk)

            # Step 4: Final PD
            pd_cal = base_pd * size_factor * cv_factor
            pd_cal = max(self.p.pd_lower_floor, min(self.p.pd_upper_cap, pd_cal))

            # Step 5: LGD by carrier type
            lgd = self.p.lgd_by_type.get(ctype, 0.50)

            # Step 6: Rating
            rating = 'Ca-C'
            for threshold, r in self.p.rating_pd_thresholds:
                if pd_cal <= threshold:
                    rating = r
                    break

            n_routes = len(d['routes']) if isinstance(d['routes'], set) else d['routes']

            results.append({
                'carrier': carrier,
                'carrier_type': ctype,
                'n_obs': d['n'],
                'passengers_m': round(d['sum_pax'] / 1e6, 2),
                'market_share': round(market_share * 100, 2),
                'mean_fare': round(mean_fare, 0),
                'fare_cv': round(fare_cv, 4),
                'base_pd': round(base_pd, 4),
                'size_factor': round(size_factor, 3),
                'cv_factor': round(cv_factor, 3),
                'pd_calibrated': round(pd_cal, 4),
                'lgd': round(lgd, 2),
                'el': round(pd_cal * lgd, 4),
                'rating': rating,
                'n_routes': n_routes,
            })

        self.carrier_df = pd.DataFrame(results).sort_values('pd_calibrated', ascending=False)
        return self.carrier_df

    def compute_correlation_matrix(self):
        """Build t-Copula correlation matrix for carriers.

        Structure:
        - Base correlation ρ₀ between all carriers
        - Same-type bonus (majors correlate more with majors, etc.)
        - Distance decay based on business model similarity

        Returns: (corr_matrix, carrier_order)
        """
        carriers = self.carrier_df['carrier'].tolist()
        n = len(carriers)
        corr = np.full((n, n), self.p.base_correlation)

        for i, c1 in enumerate(carriers):
            for j, c2 in enumerate(carriers):
                if i == j:
                    corr[i, j] = 1.0
                elif i < j:
                    t1 = self.p.carrier_types.get(c1, 'other')
                    t2 = self.p.carrier_types.get(c2, 'other')
                    r = self.p.base_correlation
                    if t1 == t2:
                        r += self.p.same_type_bonus
                    corr[i, j] = r
                else:
                    corr[i, j] = corr[j, i]

        # Ensure positive semi-definite
        eigvals = np.linalg.eigvalsh(corr)
        if eigvals[0] < 0:
            corr += np.eye(n) * (-eigvals[0] + self.p.cholesky_jitter)

        return corr, carriers

    def simulate_correlated_defaults(self, n_paths, n_months, seed=42):
        """
        Generate t-Copula correlated default indicators.

        t-Copula(v) = multivariate t with v degrees of freedom.
        P(default_i) = P(t_i < F^{-1}(PD_i)) where t is from multivariate t.

        For fat-tailed t with low df, joint extreme events are much more likely
        than under Gaussian copula — this is the key innovation for flight FSR.

        Returns: (n_paths, n_carriers, n_months) boolean array
        """
        np.random.seed(seed)
        corr, carriers = self.compute_correlation_matrix()
        n_carriers = len(carriers)
        df = self.p.t_copula_df  # degrees of freedom (None = Gaussian)

        L = np.linalg.cholesky(corr)

        pd_array = np.array([self.carrier_df[self.carrier_df['carrier'] == c]['pd_calibrated'].values[0]
                             for c in carriers])
        pd_monthly = 1 - (1 - pd_array) ** (1 / 12)

        default_matrix = np.zeros((n_paths, n_carriers, n_months), dtype=bool)

        for month in range(n_months):
            Z = np.random.randn(n_paths, n_carriers)
            correlated = Z @ L.T

            if df is None:
                # Gaussian copula
                uniforms = stats.norm.cdf(correlated)
            else:
                # t-Copula: scale by chi-squared, then use t CDF
                chi = np.random.chisquare(df, n_paths) / df
                T = correlated / np.sqrt(chi[:, np.newaxis])
                uniforms = stats.t.cdf(T, df)

            default_matrix[:, :, month] = uniforms < pd_monthly[np.newaxis, :]

        self.default_matrix = default_matrix
        self.carrier_order = carriers
        self.corr_matrix = corr
        return default_matrix, carriers

    def print_summary(self):
        """Pretty-print carrier credit summary."""
        df = self.carrier_df
        print(f"\n  {'Carrier':<6} {'Type':<9} {'Pax(M)':>7} {'Share':>6} {'FareCV':>7} "
              f"{'BasePD':>7} {'SizeAdj':>7} {'CVAdj':>7} {'PD':>7} {'Rating':<6}")
        print(f"  {'-'*75}")
        for _, row in df.iterrows():
            print(f"  {row['carrier']:<6} {row['carrier_type']:<9} {row['passengers_m']:>6.1f}M "
                  f"{row['market_share']:>5.1f}% {row['fare_cv']:>7.3f} "
                  f"{row['base_pd']*100:>6.2f}% {row['size_factor']:>7.3f} "
                  f"{row['cv_factor']:>7.3f} {row['pd_calibrated']*100:>6.2f}% "
                  f"{row['rating']:<6}")

        # Pool-level stats
        wtd_pd = np.average(df['pd_calibrated'], weights=df['passengers_m'])
        wtd_lgd = np.average(df['lgd'], weights=df['passengers_m'])
        wtd_el = wtd_pd * wtd_lgd
        print(f"\n  Pool weighted PD: {wtd_pd*100:.2f}%")
        print(f"  Pool weighted LGD: {wtd_lgd*100:.1f}%")
        print(f"  Pool weighted EL: {wtd_el*100:.2f}%")
        print(f"  Carrier count: {len(df)}")
