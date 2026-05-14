"""
Flight FSR EDA v3 — Speed-optimized streaming stats over 13 quarters (~20GB)
Strategy: chunked read + streaming moments + pre-aggregated route/carrier stats.
Only loads needed columns. Outputs JSON summary.
"""
import pandas as pd, numpy as np, os, json, glob, time, sys
from collections import defaultdict
from pathlib import Path

def log(msg):
    print(msg, flush=True)

BASE = Path(r"C:\Users\weida\Desktop\酒店研究\data\flight_prices_real")
OUT = Path(r"C:\Users\weida\Desktop\酒店研究\output")
OUT.mkdir(exist_ok=True)

COLS = ['Year', 'Quarter', 'Origin', 'Dest', 'RPCarrier', 'Passengers',
        'MktFare', 'MktDistance', 'MktMilesFlown', 'MktCoupons', 'ItinGeoType',
        'ItinID', 'MktID']

def find_quarters():
    """Find all DB1B CSV files, return sorted list of (label, path)."""
    files = []
    for pat in ['db1b_*/Origin_and_Destination_Survey_DB1BMarket_*.csv',
                'Origin_and_Destination_Survey_DB1BMarket_*/Origin_and_Destination_Survey_DB1BMarket_*.csv']:
        files.extend(glob.glob(str(BASE / pat)))
    files = sorted(files)
    labels = [os.path.basename(os.path.dirname(f)) for f in files]
    return list(zip(labels, files))

# ─── Streaming moments (Welford) ───
class StreamingStats:
    """Single-pass mean, variance, min, max."""
    __slots__ = ('n', 'mean', 'M2', 'min_val', 'max_val')
    def __init__(self):
        self.n = 0; self.mean = 0.0; self.M2 = 0.0
        self.min_val = float('inf'); self.max_val = -float('inf')
    def update(self, x):
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        self.M2 += delta * (x - self.mean)
        if x < self.min_val: self.min_val = x
        if x > self.max_val: self.max_val = x
    def update_batch(self, arr):
        """Vectorized batch update for large arrays."""
        arr = arr[np.isfinite(arr)]
        if len(arr) == 0: return
        batch_n = len(arr); batch_mean = arr.mean(); batch_var = arr.var(ddof=0)
        delta = batch_mean - self.mean
        self.mean = (self.n * self.mean + batch_n * batch_mean) / (self.n + batch_n)
        self.M2 += batch_var * (batch_n - 1) + delta**2 * self.n * batch_n / (self.n + batch_n)
        self.n += batch_n
        self.min_val = min(self.min_val, arr.min())
        self.max_val = max(self.max_val, arr.max())
    @property
    def variance(self):
        return self.M2 / self.n if self.n > 1 else 0.0
    @property
    def std(self):
        return np.sqrt(self.variance)
    def to_dict(self):
        return {'n': self.n, 'mean': round(self.mean, 4), 'std': round(self.std, 4),
                'min': round(self.min_val, 4), 'max': round(self.max_val, 4)}

# ─── Main EDA ───
def main():
    t0 = time.time()
    quarters = find_quarters()
    log(f"Found {len(quarters)} quarters\n")

    # ─── 1. PER-QUARTER SUMMARY (streaming) ───
    log("=" * 70)
    log("PHASE 1: Per-Quarter Summary (streaming)")
    log("=" * 70)

    qsummaries = []
    total_rows = 0
    global_fare = StreamingStats()
    global_dist = StreamingStats()
    global_fpm = StreamingStats()
    carrier_pax = defaultdict(float)       # carrier -> total passengers
    carrier_routes = defaultdict(set)      # carrier -> set of routes
    route_carriers = defaultdict(set)      # (origin,dest) -> set of carriers
    route_pax = defaultdict(float)         # (origin,dest) -> total passengers
    route_fare_sum = defaultdict(float)    # (origin,dest) -> sum of fares (weighted by pax)
    route_fare_n = defaultdict(float)      # (origin,dest) -> sum of passengers (for wtd avg)
    monthly_quarterly_fare = defaultdict(list)  # (year, qtr) -> list of avg fares

    for idx, (label, fpath) in enumerate(quarters):
        q_t0 = time.time()
        log(f"\n  [{idx+1}/{len(quarters)}] Processing {label}...")
        q_fare = StreamingStats(); q_dist = StreamingStats(); q_rows = 0
        q_carrier_pax = defaultdict(float)

        chunk_n = 0
        for chunk in pd.read_csv(fpath, chunksize=100000, usecols=COLS, low_memory=False):
            chunk_n += 1
            valid = chunk[chunk['MktFare'].notna() & (chunk['MktMilesFlown'] > 0)]
            if len(valid) == 0: continue
            q_rows += len(valid); total_rows += len(valid)
            if chunk_n % 20 == 0:
                log(f"    {label}: {chunk_n*100000/1e6:.1f}M rows processed...")

            fares = valid['MktFare'].values
            dists = valid['MktMilesFlown'].values
            paxs = valid['Passengers'].values

            # Streaming stats
            q_fare.update_batch(fares)
            q_dist.update_batch(dists)
            global_fare.update_batch(fares)
            global_dist.update_batch(dists)
            fpm = fares / dists
            global_fpm.update_batch(fpm)

            # Carrier aggregation (vectorized via groupby in chunk)
            for _, row in valid[['RPCarrier', 'Passengers', 'Origin', 'Dest']].iterrows():
                c = row['RPCarrier']; p = row['Passengers']
                carrier_pax[c] += p
                q_carrier_pax[c] += p
                rkey = (row['Origin'], row['Dest'])
                carrier_routes[c].add(rkey)
                route_carriers[rkey].add(c)
                route_pax[rkey] += p

            del valid

        n_routes = len(route_carriers)
        n_carriers = len(q_carrier_pax)
        qsummaries.append({
            'quarter': label, 'rows': q_rows,
            'fare_mean': round(q_fare.mean, 2), 'fare_std': round(q_fare.std, 2),
            'dist_mean': round(q_dist.mean, 0), 'routes': n_routes,
            'carriers': n_carriers,
        })
        elapsed = time.time() - t0
        log(f"  {label}: {q_rows:>10,} rows | {n_routes:>6,} routes | "
              f"${q_fare.mean:>7.1f} ± ${q_fare.std:.0f} | {elapsed:.0f}s")

    log(f"\n  TOTAL: {total_rows:,} rows across {len(quarters)} quarters")

    # ─── 2. ROUTE CONCENTRATION (top-N dominance) ───
    log(f"\n{'='*70}")
    log("PHASE 2: Route & Carrier Concentration")
    log("=" * 70)

    # Route concentration
    sorted_routes = sorted(route_pax.items(), key=lambda x: -x[1])
    total_pax = sum(v for _, v in sorted_routes)
    cumsum = np.cumsum([v for _, v in sorted_routes])
    n_routes_total = len(sorted_routes)

    for pct_label, pct_thresh in [('Top 10', 0.10), ('Top 50', None), ('Top 100', None),
                                     ('Top 1%', 0.01), ('Top 10%', 0.10)]:
        if pct_thresh:
            n_top = max(1, int(n_routes_total * pct_thresh))
        elif pct_label == 'Top 50': n_top = 50
        elif pct_label == 'Top 100': n_top = 100
        else: n_top = 10
        share = cumsum[min(n_top, len(cumsum)) - 1] / total_pax * 100
        log(f"  {pct_label} routes ({n_top:,}): {share:.1f}% of passengers")

    # Gini
    lorenz = cumsum / cumsum[-1]
    perfect = np.linspace(0, 1, n_routes_total)
    gini = 1 - 2 * np.trapz(lorenz, perfect)
    log(f"  Route Gini coefficient: {gini:.4f}")

    # Carrier concentration
    sorted_carriers = sorted(carrier_pax.items(), key=lambda x: -x[1])
    total_carrier_pax = sum(v for _, v in sorted_carriers)
    carrier_shares = [(c, p/total_carrier_pax) for c, p in sorted_carriers]
    hhi = sum(s**2 for _, s in carrier_shares) * 10000
    top4_share = sum(s for _, s in carrier_shares[:4]) * 100
    log(f"\n  Carrier HHI: {hhi:.0f} | Top 4 share: {top4_share:.1f}%")
    log(f"  Total unique carriers: {len(sorted_carriers)}")

    # ─── 3. ROUTE-LEVEL VOLATILITY ───
    log(f"\n{'='*70}")
    log("PHASE 3: Route-Level Price Volatility (across all quarters)")
    log("=" * 70)

    # Compute per-route fare stats: streaming mean/variance across all quarters
    # We need 2 passes: 1 for mean, 1 for variance. Or use Welford per route.
    route_stats_stream = defaultdict(lambda: {'n': 0, 'mean': 0.0, 'M2': 0.0,
                                                'carriers': set(), 'total_pax': 0.0})

    for label, fpath in quarters:
        for chunk in pd.read_csv(fpath, chunksize=200000, usecols=['Origin', 'Dest', 'MktFare',
                                     'Passengers', 'RPCarrier'], low_memory=False):
            valid = chunk[chunk['MktFare'].notna()]
            for _, row in valid.iterrows():
                key = (row['Origin'], row['Dest'])
                s = route_stats_stream[key]
                f = row['MktFare']
                s['n'] += 1
                delta = f - s['mean']
                s['mean'] += delta / s['n']
                s['M2'] += delta * (f - s['mean'])
                s['carriers'].add(row['RPCarrier'])
                s['total_pax'] += row['Passengers']
            del valid
        log(f"  Processed {label} for route stats...")

    # Compile route-level CVs
    route_cvs = []; route_ncarriers = []; route_means = []; route_nobs = []
    for key, s in route_stats_stream.items():
        if s['n'] >= 10 and s['mean'] > 0:
            var = s['M2'] / s['n'] if s['n'] > 1 else 0
            cv = np.sqrt(var) / s['mean'] if s['mean'] > 0 else 0
            if cv < 5:  # filter absurd CVs (data errors)
                route_cvs.append(cv)
                route_ncarriers.append(len(s['carriers']))
                route_means.append(s['mean'])
                route_nobs.append(s['n'])

    route_cvs = np.array(route_cvs); route_ncarriers = np.array(route_ncarriers)
    route_means = np.array(route_means)
    log(f"\n  Routes with >=10 obs: {len(route_cvs):,}")
    log(f"  Route CV distribution:")
    for p in [10, 25, 50, 75, 90, 95, 99]:
        log(f"    P{p}: {np.percentile(route_cvs, p):.4f}")
    log(f"  Mean CV: {route_cvs.mean():.4f} | Median CV: {np.median(route_cvs):.4f}")

    # Competition vs CV
    log(f"\n  Competition Paradox (CV by N_carriers):")
    max_carriers = min(10, int(route_ncarriers.max()))
    for n in range(1, max_carriers + 1):
        mask = route_ncarriers == n
        if mask.sum() >= 5:
            log(f"    {n} carrier(s): {mask.sum():>6,} routes, CV={route_cvs[mask].mean():.4f} "
                  f"(med={np.median(route_cvs[mask]):.4f})")
    # Aggregate all above max
    mask_high = route_ncarriers > max_carriers
    if mask_high.sum() >= 5:
        log(f"    >{max_carriers} carriers: {mask_high.sum():>6,} routes, "
              f"CV={route_cvs[mask_high].mean():.4f} (med={np.median(route_cvs[mask_high]):.4f})")

    # ─── 4. CARRIER-LEVEL ANALYSIS ───
    log(f"\n{'='*70}")
    log("PHASE 4: Carrier-Level Risk Metrics")
    log("=" * 70)

    # Carrier fare dispersion (coefficient of variation per carrier)
    carrier_fare_stream = defaultdict(lambda: StreamingStats())
    for label, fpath in quarters:
        for chunk in pd.read_csv(fpath, chunksize=200000, usecols=['RPCarrier', 'MktFare'],
                                 low_memory=False):
            for carrier, grp in chunk.groupby('RPCarrier'):
                fares = grp['MktFare'].dropna().values
                if len(fares) > 0:
                    carrier_fare_stream[carrier].update_batch(fares)

    log(f"  {'Carrier':<6} {'Pax':>12} {'Share':>7} {'AvgFare':>9} {'FareCV':>7} {'Routes':>8}")
    log(f"  {'-'*52}")
    for c, pax in sorted(carrier_pax.items(), key=lambda x: -x[1])[:15]:
        share = pax / total_carrier_pax * 100
        stats = carrier_fare_stream.get(c)
        avg_f = stats.mean if stats and stats.n > 0 else 0
        cv_f = stats.std / avg_f if stats and avg_f > 0 else 0
        n_routes = len(carrier_routes.get(c, set()))
        log(f"  {c:<6} {pax:>12,.0f} {share:>6.1f}% ${avg_f:>8.0f} {cv_f:>7.3f} {n_routes:>8,}")

    # ─── 5. SEASONALITY ───
    log(f"\n{'='*70}")
    log("PHASE 5: Seasonality & Trends")
    log("=" * 70)

    # Per-quarter average fare trend
    qtr_fare_trend = []
    for label, fpath in quarters:
        total_f = StreamingStats()
        for chunk in pd.read_csv(fpath, chunksize=200000, usecols=['MktFare'], low_memory=False):
            total_f.update_batch(chunk['MktFare'].dropna().values)
        yr = int(label.split('_')[0].replace('db1b_', '').replace('Origin_and_Destination_Survey_DB1BMarket_', ''))
        # Infer quarter from directory name
        if 'q1' in label.lower() or '_1' in label:
            q = 1
        elif 'q2' in label.lower() or '_2' in label:
            q = 2
        elif 'q3' in label.lower() or '_3' in label:
            q = 3
        elif 'q4' in label.lower() or '_4' in label:
            q = 4
        else:
            q = 0
        qtr_fare_trend.append({'year': yr, 'quarter': q, 'avg_fare': round(total_f.mean, 2),
                                'std_fare': round(total_f.std, 2), 'n': total_f.n})
        log(f"  {yr} Q{q}: ${total_f.mean:.0f} ± ${total_f.std:.0f} ({total_f.n:,} rows)")

    # ─── 6. FSR-SPECIFIC METRICS ───
    log(f"\n{'='*70}")
    log("PHASE 6: FSR Adaptation Metrics")
    log("=" * 70)

    # 6a. Route "survival" — do routes persist across quarters?
    route_quarters = defaultdict(set)
    for label, fpath in quarters:
        yr_q = label  # crude but works
        for chunk in pd.read_csv(fpath, chunksize=200000, usecols=['Origin', 'Dest'], low_memory=False):
            for _, row in chunk.drop_duplicates(subset=['Origin', 'Dest']).iterrows():
                route_quarters[(row['Origin'], row['Dest'])].add(label)
            if len(route_quarters) > 500000:
                break  # enough for survival estimates

    n_quarters_total = len(quarters)
    persistence = np.array([len(v) for v in route_quarters.values()])
    always_present = (persistence >= n_quarters_total * 0.75).sum()
    transient = (persistence <= 2).sum()
    log(f"\n  6a. Route Persistence (sampled):")
    log(f"    Routes present >=75% of quarters: {always_present:,} ({always_present/len(persistence)*100:.1f}%)")
    log(f"    Routes present <=2 quarters: {transient:,} ({transient/len(persistence)*100:.1f}%)")
    log(f"    Mean quarters present: {persistence.mean():.1f} / {n_quarters_total}")

    # 6b. Price predictability: route CV vs hotel property CV
    hotel_cv_est = 0.20  # from hotel EDA
    log(f"\n  6b. Price Predictability:")
    log(f"    Flight route CV (median): {np.median(route_cvs):.3f} vs Hotel property CV: {hotel_cv_est:.3f}")
    log(f"    Flight CV / Hotel CV ratio: {np.median(route_cvs)/hotel_cv_est:.1f}x")

    # 6c. Default risk proxy: carrier CV → implied instability
    carrier_cvs = []
    for c, stats in carrier_fare_stream.items():
        if stats.n > 100 and stats.mean > 0:
            carrier_cvs.append((c, stats.std / stats.mean, carrier_pax.get(c, 0)))
    carrier_cvs.sort(key=lambda x: -x[1])
    log(f"\n  6c. Top 5 most volatile carriers (fare CV):")
    for c, cv, pax in carrier_cvs[:5]:
        log(f"    {c}: CV={cv:.3f}, {pax:,.0f} passengers")

    # 6d. Distance-fare correlation (important for pricing model)
    fare_dist_corr = []
    n_samples = 0
    for label, fpath in quarters[:2]:  # first 2 quarters enough
        for chunk in pd.read_csv(fpath, chunksize=200000, usecols=['MktFare', 'MktMilesFlown'],
                                 low_memory=False):
            valid = chunk[(chunk['MktFare'] > 0) & (chunk['MktMilesFlown'] > 0)]
            if len(valid) > 100:
                fare_dist_corr.append(valid['MktFare'].corr(valid['MktMilesFlown']))
                n_samples += len(valid)
                if n_samples > 2000000: break
        if n_samples > 2000000: break
    log(f"\n  6d. Distance-Fare Correlation: r={np.mean(fare_dist_corr):.3f}")
    log(f"    (Hotels have no distance dimension — flights do, but correlation is weak)")

    # 6e. Coupon (segments) — nonstop premium
    coupon_fares = defaultdict(list)
    for label, fpath in quarters[:1]:
        for chunk in pd.read_csv(fpath, chunksize=200000, usecols=['MktCoupons', 'MktFare'],
                                 low_memory=False):
            for cp, grp in chunk.groupby('MktCoupons'):
                coupon_fares[cp].append(grp['MktFare'].mean())
    log(f"\n  6e. Fare by Segment Count:")
    for cp in sorted(coupon_fares.keys()):
        avg = np.mean(coupon_fares[cp])
        log(f"    {int(cp)} segment(s): ${avg:.0f}")

    # ─── SAVE ───
    results = {
        'dataset': {
            'total_rows': total_rows,
            'n_quarters': len(quarters),
            'n_routes_total': n_routes_total,
            'n_carriers_total': len(sorted_carriers),
            'total_passengers': float(total_carrier_pax),
        },
        'concentration': {
            'route_gini': round(float(gini), 4),
            'carrier_hhi': round(float(hhi), 0),
            'top4_carrier_share_pct': round(float(top4_share), 1),
            'top10_routes_share_pct': round(float(cumsum[9]/cumsum[-1]*100), 1),
            'top50_routes_share_pct': round(float(cumsum[49]/cumsum[-1]*100), 1),
        },
        'route_volatility': {
            'n_routes': len(route_cvs),
            'mean_cv': round(float(route_cvs.mean()), 4),
            'median_cv': round(float(np.median(route_cvs)), 4),
            'p25_cv': round(float(np.percentile(route_cvs, 25)), 4),
            'p75_cv': round(float(np.percentile(route_cvs, 75)), 4),
            'p95_cv': round(float(np.percentile(route_cvs, 95)), 4),
            'vs_hotel_cv_ratio': round(float(np.median(route_cvs)) / 0.20, 1),
        },
        'global_stats': {
            'fare': global_fare.to_dict(),
            'distance': global_dist.to_dict(),
        },
        'quarterly_trend': qtr_fare_trend,
        'top_carriers': [{'carrier': c, 'passengers': p, 'share_pct': round(p/total_carrier_pax*100, 2),
                          'n_routes': len(carrier_routes.get(c, set())),
                          'fare_cv': round(carrier_fare_stream[c].std / carrier_fare_stream[c].mean, 4)
                          if carrier_fare_stream.get(c) and carrier_fare_stream[c].mean > 0 else 0}
                         for c, p in sorted_carriers[:15]],
        'fsr_metrics': {
            'route_persistence_mean_qtrs': round(float(persistence.mean()), 1),
            'route_persistence_pct_always': round(float(always_present/len(persistence)*100), 1),
            'route_persistence_pct_transient': round(float(transient/len(persistence)*100), 1),
            'distance_fare_correlation': round(float(np.mean(fare_dist_corr)), 3),
        },
    }

    with open(OUT / 'flight_eda_v3_summary.json', 'w') as f:
        json.dump(results, f, indent=2)
    log(f"\n{'='*70}")
    log(f"Results saved to {OUT / 'flight_eda_v3_summary.json'}")
    log(f"Total time: {time.time() - t0:.0f}s")

if __name__ == '__main__':
    main()
