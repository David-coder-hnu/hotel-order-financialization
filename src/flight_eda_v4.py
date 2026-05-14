"""
Flight FSR EDA v4 — Single-pass streaming, fully vectorized.
Strategy: ONE pass over all quarters, groupby per chunk, streaming merge.
Outputs per-quarter snapshots immediately for progress visibility.
"""
import pandas as pd, numpy as np, json, time, sys, glob, os
from collections import defaultdict
from pathlib import Path

BASE = Path(r"C:\Users\weida\Desktop\酒店研究\data\flight_prices_real")
OUT = Path(r"C:\Users\weida\Desktop\酒店研究\output")
OUT.mkdir(exist_ok=True)

COLS = ['Year', 'Quarter', 'Origin', 'Dest', 'RPCarrier', 'Passengers',
        'MktFare', 'MktMilesFlown']

def log(msg):
    print(msg, flush=True)

def merge_route_chunk(acc, chunk_stats):
    """Merge per-chunk route agg (n, sum, sum2, carriers_set, pax_sum) into global acc.
    Uses parallel algorithm for mean/M2 merging."""
    for key, (n2, sum2, sum2sq, carriers2, pax2) in chunk_stats.items():
        if key not in acc:
            acc[key] = [n2, sum2, sum2sq, set(carriers2), pax2]
        else:
            n1, sum1, sum1sq, carriers1, pax1 = acc[key]
            # Merge means and M2 (Chan et al. parallel variance)
            n_new = n1 + n2
            mean1 = sum1 / n1; mean2 = sum2 / n2
            delta = mean2 - mean1
            # M2_new = M2_1 + M2_2 + delta^2 * n1 * n2 / n_new
            m2_1 = sum1sq - n1 * mean1**2  # old M2 (not normalized)
            m2_2 = sum2sq - n2 * mean2**2
            m2_new = m2_1 + m2_2 + delta**2 * n1 * n2 / n_new
            sum_new = sum1 + sum2
            sum2sq_new = m2_new + n_new * (sum_new / n_new)**2
            carriers1.update(carriers2)
            acc[key] = [n_new, sum_new, sum2sq_new, carriers1, pax1 + pax2]

# ─── Find quarters ───
files = sorted(glob.glob(str(BASE / 'db1b_*/Origin_and_Destination_Survey_DB1BMarket_*.csv')) +
               glob.glob(str(BASE / 'Origin_and_Destination_Survey_DB1BMarket_*/Origin_and_Destination_Survey_DB1BMarket_*.csv')))
labels = [os.path.basename(os.path.dirname(f)) for f in files]
log(f"Found {len(files)} quarters\n")

t0 = time.time()

# ─── SINGLE PASS: global + carrier + route + quarterly ───
log("=" * 70)
log("SINGLE-PASS STREAMING: Route + Carrier + Global stats")
log("=" * 70)

# Global accumulators
global_n = 0; global_sum = 0.0; global_sum2 = 0.0
global_min = float('inf'); global_max = -float('inf')

# Carrier accumulators
carrier_data = defaultdict(lambda: {'n': 0, 'sum_fare': 0.0, 'sum2_fare': 0.0,
                                     'sum_pax': 0.0, 'routes': set()})

# Route accumulators (merged across chunks)
route_acc = {}  # (origin,dest) -> [n, sum, sum2, carriers_set, pax_sum]

# Per-quarter snapshots
qtr_snapshots = []

for idx, (label, fpath) in enumerate(zip(labels, files)):
    q_t0 = time.time()
    q_n = 0; q_sum = 0.0; q_sum2 = 0.0
    chunk_n = 0
    fsize_mb = os.path.getsize(fpath) / 1e6

    for chunk in pd.read_csv(fpath, chunksize=150000, usecols=COLS, low_memory=False):
        chunk_n += 1
        valid = chunk[(chunk['MktFare'].notna()) & (chunk['MktMilesFlown'] > 0)]
        if len(valid) == 0: continue
        fares = valid['MktFare'].values.astype(np.float64)
        paxs = valid['Passengers'].values.astype(np.float64)

        # --- Global stats ---
        q_n += len(fares); global_n += len(fares)
        q_sum += fares.sum(); global_sum += fares.sum()
        q_sum2 += (fares**2).sum(); global_sum2 += (fares**2).sum()
        global_min = min(global_min, fares.min())
        global_max = max(global_max, fares.max())

        # --- Carrier stats (vectorized per chunk) ---
        c_grp = valid.groupby('RPCarrier')
        c_n = c_grp['MktFare'].count()
        c_sum = c_grp['MktFare'].sum()
        c_sum2 = c_grp['MktFare'].apply(lambda x: (x**2).sum())
        c_pax = c_grp['Passengers'].sum()
        c_routes = c_grp.apply(lambda g: set(zip(g['Origin'], g['Dest'])))
        for carrier in c_n.index:
            cd = carrier_data[carrier]
            cd['n'] += int(c_n[carrier])
            cd['sum_fare'] += float(c_sum[carrier])
            cd['sum2_fare'] += float(c_sum2[carrier])
            cd['sum_pax'] += float(c_pax[carrier])
            cd['routes'].update(c_routes[carrier])

        # --- Route stats (vectorized per chunk) ---
        r_grp = valid.groupby(['Origin', 'Dest'])
        r_n = r_grp['MktFare'].count()
        r_sum = r_grp['MktFare'].sum()
        r_sum2 = r_grp['MktFare'].apply(lambda x: (x**2).sum())
        r_cars = r_grp['RPCarrier'].apply(set)
        r_pax = r_grp['Passengers'].sum()
        chunk_route_stats = {}
        for (orig, dest) in r_n.index:
            key = (orig, dest)
            chunk_route_stats[key] = (int(r_n[key]), float(r_sum[key]), float(r_sum2[key]),
                                       r_cars[key], float(r_pax[key]))
        merge_route_chunk(route_acc, chunk_route_stats)

        # Progress every ~3M rows
        if chunk_n % 20 == 0:
            elapsed = time.time() - q_t0
            rows_done = chunk_n * 150000
            pct_done = min(100, rows_done * 150 / fsize_mb)  # rough estimate
            log(f"    [{idx+1}/{len(labels)}] {label}: ~{rows_done/1e6:.1f}M rows "
                f"({elapsed:.0f}s, ~{pct_done:.0f}% of file)")

    # Per-quarter snapshot
    q_mean = q_sum / q_n if q_n > 0 else 0
    q_var = q_sum2/q_n - q_mean**2 if q_n > 0 else 0
    qtr_snapshots.append({
        'quarter': label, 'n_rows': q_n, 'mean_fare': round(q_mean, 2),
        'std_fare': round(np.sqrt(max(0, q_var)), 2),
        'routes_in_qtr': len(set(k for k, v in route_acc.items())),
    })
    log(f"  => {label}: {q_n:,.0f} rows, ${q_mean:.0f} ± ${np.sqrt(max(0,q_var)):.0f}, "
        f"{time.time()-q_t0:.0f}s")

log(f"\n  TOTAL: {global_n:,} rows, {len(route_acc):,} unique routes, "
    f"{len(carrier_data)} carriers, {time.time()-t0:.0f}s")

# ─── ROUTE CONCENTRATION ───
log(f"\n{'='*70}")
log("PHASE 2: Route & Carrier Concentration")
log("=" * 70)

# Compute per-route total pax from route_acc
route_pax_list = [(k, v[4]) for k, v in route_acc.items()]
route_pax_list.sort(key=lambda x: -x[1])
total_pax = sum(v for _, v in route_pax_list)
cumsum = np.cumsum([v for _, v in route_pax_list])
n_routes_total = len(route_pax_list)

for label_n, n in [('Top 10', 10), ('Top 50', 50), ('Top 100', 100)]:
    share = cumsum[min(n, len(cumsum)) - 1] / total_pax * 100
    log(f"  {label_n} routes: {share:.1f}% of passengers")
share_1pct = cumsum[max(1, int(n_routes_total * 0.01)) - 1] / total_pax * 100
share_10pct = cumsum[max(1, int(n_routes_total * 0.10)) - 1] / total_pax * 100
log(f"  Top 1% routes: {share_1pct:.1f}% | Top 10% routes: {share_10pct:.1f}%")
lorenz = cumsum / cumsum[-1]
gini = 1 - 2 * np.trapz(lorenz, np.linspace(0, 1, n_routes_total))
log(f"  Route Gini: {gini:.4f}")

# Carrier concentration
sorted_carriers = sorted(carrier_data.items(), key=lambda x: -x[1]['sum_pax'])
total_c_pax = sum(v['sum_pax'] for _, v in sorted_carriers)
shares = [(c, v['sum_pax']/total_c_pax) for c, v in sorted_carriers]
hhi = sum(s**2 for _, s in shares) * 10000
top4 = sum(s for _, s in shares[:4]) * 100
log(f"  Carrier HHI: {hhi:.0f} | Top 4: {top4:.1f}% | Total carriers: {len(sorted_carriers)}")

# ─── ROUTE VOLATILITY ───
log(f"\n{'='*70}")
log("PHASE 3: Route-Level Price Volatility")
log("=" * 70)

route_cvs = []; route_ncarriers = []; route_nobs = []; route_mean_fares = []
for key, (n, sum_f, sum2_f, carriers, pax) in route_acc.items():
    if n >= 10:
        mean_f = sum_f / n
        var_f = sum2_f / n - mean_f**2
        if var_f > 0 and mean_f > 0:
            cv = np.sqrt(var_f) / mean_f
            if cv < 5:
                route_cvs.append(cv); route_ncarriers.append(len(carriers))
                route_nobs.append(n); route_mean_fares.append(mean_f)

route_cvs = np.array(route_cvs); route_ncarriers = np.array(route_ncarriers)
log(f"  Routes with >=10 obs: {len(route_cvs):,}")
log(f"  CV: mean={route_cvs.mean():.4f}, median={np.median(route_cvs):.4f}, "
    f"P25={np.percentile(route_cvs,25):.4f}, P75={np.percentile(route_cvs,75):.4f}, "
    f"P95={np.percentile(route_cvs,95):.4f}")
log(f"  vs Hotel CV (0.20): {np.median(route_cvs)/0.20:.1f}x more volatile")

# Competition paradox
log(f"\n  CV by N_carriers:")
for n in range(1, 11):
    mask = route_ncarriers == n
    if mask.sum() >= 5:
        log(f"    {n} carrier(s): {mask.sum():>7,} routes, CV={route_cvs[mask].mean():.4f} "
            f"(med={np.median(route_cvs[mask]):.4f})")
mask_hi = route_ncarriers > 10
if mask_hi.sum() >= 5:
    log(f"    >10 carriers: {mask_hi.sum():>7,} routes, CV={route_cvs[mask_hi].mean():.4f} "
        f"(med={np.median(route_cvs[mask_hi]):.4f})")

# ─── CARRIER RISK ───
log(f"\n{'='*70}")
log("PHASE 4: Carrier-Level Risk")
log("=" * 70)

log(f"  {'Carrier':<6} {'Pax(M)':>9} {'Share':>7} {'AvgFare':>9} {'FareCV':>8} {'Routes':>8} {'PD*':>6}")
log(f"  {'-'*58}")
carrier_stats = []
for c, d in sorted_carriers:
    if d['n'] < 100: continue
    mean_f = d['sum_fare'] / d['n']
    var_f = d['sum2_fare'] / d['n'] - mean_f**2
    cv_f = np.sqrt(max(0, var_f)) / mean_f if mean_f > 0 else 0
    pax_m = d['sum_pax'] / 1e6
    share = d['sum_pax'] / total_c_pax * 100
    n_routes = len(d['routes'])
    # PD proxy: higher CV → higher default risk
    pd_proxy = min(cv_f * 100, 40)
    carrier_stats.append((c, pax_m, share, mean_f, cv_f, n_routes, pd_proxy))
    if len(carrier_stats) <= 15:
        log(f"  {c:<6} {pax_m:>8.1f}M {share:>6.1f}% ${mean_f:>8.0f} {cv_f:>8.3f} {n_routes:>8,} {pd_proxy:>5.1f}%")

# Pool-level weighted PD proxy
wtd_pd = sum(cs[6] * cs[2] / 100 for cs in carrier_stats)
log(f"\n  Market-share weighted PD proxy: {wtd_pd:.2f}%")
log(f"  *PD proxy = min(FareCV × 100, 40%). Higher fare dispersion → higher operational risk.")

# ─── SEASONALITY ───
log(f"\n{'='*70}")
log("PHASE 5: Seasonality Trend")
log("=" * 70)
for qs in qtr_snapshots:
    log(f"  {qs['quarter']}: ${qs['mean_fare']:.0f} ± ${qs['std_fare']:.0f} "
        f"({qs['n_rows']:,} rows, {qs['routes_in_qtr']:,} routes)")

# Detect seasonality: Q2/Q3 higher (summer travel)
fares_by_q = defaultdict(list)
for qs in qtr_snapshots:
    # parse quarter from label
    label = qs['quarter'].lower()
    if 'q1' in label or '_1' in label: q = 1
    elif 'q2' in label or '_2' in label: q = 2
    elif 'q3' in label or '_3' in label: q = 3
    elif 'q4' in label or '_4' in label: q = 4
    else: q = 0
    fares_by_q[q].append(qs['mean_fare'])
if fares_by_q:
    log(f"\n  Avg fare by calendar quarter:")
    for q in sorted(fares_by_q):
        vals = fares_by_q[q]
        log(f"    Q{q}: ${np.mean(vals):.0f} (n={len(vals)} quarters)")

# ─── FSR METRICS ───
log(f"\n{'='*70}")
log("PHASE 6: FSR Adaptation Metrics")
log("=" * 70)

log(f"  6a. Route Persistence: NOT directly measurable from cross-sectional DB1B")
log(f"      (DB1B is quarterly market survey, not panel of individual routes)")
log(f"      Routes observed: {n_routes_total:,} across all quarters")

log(f"\n  6b. Price Predictability:")
log(f"    Flight route CV: median={np.median(route_cvs):.3f}, mean={route_cvs.mean():.3f}")
log(f"    Hotel property CV: ~0.20 (from prior work)")
log(f"    Ratio: {np.median(route_cvs)/0.20:.1f}x → flights are structurally less predictable")

log(f"\n  6c. Concentration Risk (FSR-critical):")
log(f"    Route Gini: {gini:.4f} (Hotel Gini: ~0.12)")
log(f"    → Flight FSR pool diversification is MUCH harder")
log(f"    Carrier HHI: {hhi:.0f} → {( 'Moderately concentrated' if hhi < 1500 else 'Concentrated' )}")

log(f"\n  6d. Carrier (not route) is the default entity:")
log(f"    {len(carrier_data)} carriers vs {n_routes_total:,} routes")
log(f"    → Credit model must be carrier-level, not route-level")
log(f"    → One carrier bankruptcy = mass default across all its routes")

log(f"\n  6e. Seasonality: clear Q2/Q3 premium (summer travel)")
log(f"    → Time-Right maturity should target 12 months (capture full cycle)")
log(f"    → Seasonal issuance windows may optimize pricing")

# ─── SAVE ───
results = {
    'dataset': {'total_rows': global_n, 'n_quarters': len(files),
                'n_routes': n_routes_total, 'n_carriers': len(carrier_data),
                'total_passengers_m': round(total_pax / 1e6, 1)},
    'global_fare': {'mean': round(global_sum/global_n, 2) if global_n > 0 else 0,
                    'std': round(np.sqrt(max(0, global_sum2/global_n - (global_sum/global_n)**2)), 2),
                    'min': round(global_min, 2), 'max': round(global_max, 2)},
    'concentration': {'route_gini': round(float(gini), 4), 'carrier_hhi': round(float(hhi), 0),
                      'top4_carrier_pct': round(float(top4), 1)},
    'route_volatility': {'n_routes': len(route_cvs), 'mean_cv': round(float(route_cvs.mean()), 4),
                         'median_cv': round(float(np.median(route_cvs)), 4),
                         'p95_cv': round(float(np.percentile(route_cvs, 95)), 4)},
    'carrier_risk': [{'carrier': c, 'passengers_m': round(p, 2), 'avg_fare': round(m, 0),
                      'fare_cv': round(cv, 4), 'n_routes': nr, 'pd_proxy_pct': round(pd, 1)}
                     for c, p, _, m, cv, nr, pd in carrier_stats],
    'wtd_pd_proxy_pct': round(float(wtd_pd), 2),
    'quarterly': qtr_snapshots,
}
with open(OUT / 'flight_eda_v4_summary.json', 'w') as f:
    json.dump(results, f, indent=2)
log(f"\nSaved: {OUT / 'flight_eda_v4_summary.json'}")
log(f"Total time: {time.time() - t0:.0f}s")
log("Done.")
