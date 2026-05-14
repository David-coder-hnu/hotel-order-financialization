"""
Extract real route-level statistics for flight FSR pool construction.
Reads a representative quarter (2024 Q2), computes per-route stats,
outputs CSV with enough detail for stratified sampling.
"""
import pandas as pd, numpy as np, json, time, sys
from collections import defaultdict
from pathlib import Path

BASE = Path(r"C:\Users\weida\Desktop\酒店研究\data\flight_prices_real")
OUT = Path(r"C:\Users\weida\Desktop\酒店研究\output")

def log(msg):
    print(msg, flush=True)

log("Extracting real route statistics for FSR pool construction...")
log("Using 2024 Q2 as representative quarter\n")

# Find 2024 Q2
import glob
files = sorted(glob.glob(str(BASE / 'Origin_and_Destination_Survey_DB1BMarket_2024_2/Origin_and_Destination_Survey_DB1BMarket_2024_2.csv')))
if not files:
    log("ERROR: 2024 Q2 file not found")
    sys.exit(1)

fpath = files[0]
log(f"Source: {fpath}")

# Streaming route aggregation
route_data = defaultdict(lambda: {'n': 0, 'sum_fare': 0.0, 'sum2_fare': 0.0,
                                    'sum_pax': 0.0, 'carriers': set(),
                                    'sum_dist': 0.0, 'sum_coupons': 0.0})

chunk_n = 0; t0 = time.time()
for chunk in pd.read_csv(fpath, chunksize=200000, low_memory=False,
                         usecols=['Origin', 'Dest', 'RPCarrier', 'MktFare',
                                  'Passengers', 'MktMilesFlown', 'MktCoupons']):
    chunk_n += 1
    valid = chunk[chunk['MktFare'].notna() & (chunk['MktMilesFlown'] > 0)]
    for _, row in valid.iterrows():
        key = (row['Origin'], row['Dest'])
        d = route_data[key]
        d['n'] += 1
        f = row['MktFare']
        d['sum_fare'] += f
        d['sum2_fare'] += f**2
        d['sum_pax'] += row['Passengers']
        d['carriers'].add(row['RPCarrier'])
        d['sum_dist'] += row['MktMilesFlown']
        d['sum_coupons'] += row['MktCoupons']
    if chunk_n % 10 == 0:
        log(f"  {chunk_n*200000/1e6:.1f}M rows, {len(route_data):,} routes...")

log(f"\n  Total: {len(route_data):,} routes extracted ({time.time()-t0:.0f}s)")

# Compile to DataFrame
routes = []
for (origin, dest), d in route_data.items():
    if d['n'] < 20:  # minimum observations
        continue
    mean_fare = d['sum_fare'] / d['n']
    var_fare = max(0, d['sum2_fare'] / d['n'] - mean_fare**2)
    cv = np.sqrt(var_fare) / mean_fare if mean_fare > 0 else 0
    n_carriers = len(d['carriers'])
    avg_dist = d['sum_dist'] / d['n']
    avg_coupons = d['sum_coupons'] / d['n']

    # Distance band
    if avg_dist <= 500:
        dist_band = 'short'
    elif avg_dist <= 1500:
        dist_band = 'medium'
    else:
        dist_band = 'long'

    routes.append({
        'origin': origin, 'dest': dest,
        'route': f'{origin}-{dest}',
        'n_obs': d['n'],
        'total_pax': d['sum_pax'],
        'mean_fare': round(mean_fare, 2),
        'std_fare': round(np.sqrt(max(0, var_fare)), 2),
        'fare_cv': round(cv, 4),
        'n_carriers': n_carriers,
        'avg_distance': round(avg_dist, 0),
        'avg_coupons': round(avg_coupons, 2),
        'dist_band': dist_band,
        'carriers_list': ','.join(sorted(d['carriers'])),
    })

df = pd.DataFrame(routes)
# Filter extreme CV
df = df[df['fare_cv'] < 1.5]
# Filter very low fares (data errors)
df = df[df['mean_fare'] >= 50]

# Save
csv_path = OUT / 'flight_routes_real.csv'
df.to_csv(csv_path, index=False)

log(f"\nSaved {len(df):,} routes to {csv_path}")
log(f"\nRoute statistics:")
log(f"  Mean fare:   ${df['mean_fare'].mean():.0f} (median: ${df['mean_fare'].median():.0f})")
log(f"  Fare CV:     mean={df['fare_cv'].mean():.3f}, median={df['fare_cv'].median():.3f}")
log(f"  N carriers:  mean={df['n_carriers'].mean():.1f}")
log(f"  Distance bands: short={(df['dist_band']=='short').sum():,}, "
    f"medium={(df['dist_band']=='medium').sum():,}, long={(df['dist_band']=='long').sum():,}")
log(f"  Top 5 routes by pax:")
for _, r in df.nlargest(5, 'total_pax').iterrows():
    log(f"    {r['route']}: {r['total_pax']:,.0f} pax, ${r['mean_fare']:.0f}, CV={r['fare_cv']:.3f}, {r['n_carriers']} carriers")
log("Done.")
