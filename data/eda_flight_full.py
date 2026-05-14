import pandas as pd, numpy as np

csv_path = r"C:\Users\weida\Desktop\酒店研究\data\flight_prices_real\db1b_2024q1\Origin_and_Destination_Survey_DB1BMarket_2024_1.csv"

# Read all 7.4M rows in chunks, compute streaming stats
print("Processing full 7.4M rows in chunks...")

# Accumulators
n = 0
sum_fare = 0.0; sum_fare2 = 0.0
sum_dist = 0.0; sum_dist2 = 0.0
sum_fpm = 0.0; sum_fpm2 = 0.0
min_fare = float('inf'); max_fare = 0
carrier_counts = {}
coupon_counts = {}
geo_counts = {}
route_stats = {}  # (origin,dest) -> [sum_fare, sum_fare2, n, carriers_set]

# For correlation
dist_fare_cov = 0.0

chunk_n = 0
for chunk in pd.read_csv(csv_path, chunksize=500000, low_memory=False):
    chunk_n += 1
    fares = chunk['MktFare'].values
    dists = chunk['MktMilesFlown'].values
    paxs = chunk['Passengers'].values
    carriers = chunk['RPCarrier'].values
    coupons = chunk['MktCoupons'].values
    geos = chunk['ItinGeoType'].values
    origins = chunk['Origin'].values
    dests = chunk['Dest'].values

    mask = ~np.isnan(fares) & ~np.isnan(dists) & (dists > 0)
    fares = fares[mask]; dists = dists[mask]; paxs = paxs[mask]

    m = len(fares)
    n += m
    sum_fare += fares.sum()
    sum_fare2 += (fares**2).sum()
    sum_dist += dists.sum()
    sum_dist2 += (dists**2).sum()

    fpm = fares / dists
    sum_fpm += fpm.sum()
    sum_fpm2 += (fpm**2).sum()

    min_fare = min(min_fare, fares.min())
    max_fare = max(max_fare, fares.max())

    # Carrier counts
    for c in carriers[mask]:
        carrier_counts[c] = carrier_counts.get(c, 0) + 1

    # Coupon counts
    for c in coupons[mask]:
        coupon_counts[c] = coupon_counts.get(c, 0) + 1

    # Geo
    for g in geos[mask]:
        geo_counts[g] = geo_counts.get(g, 0) + 1

    # Route stats (aggregated)
    for i in range(m):
        key = (origins[i], dests[i])
        if key not in route_stats:
            route_stats[key] = {'sum_fare': 0.0, 'sum_fare2': 0.0, 'n': 0, 'carriers': set()}
        rs = route_stats[key]
        rs['sum_fare'] += fares[i]
        rs['sum_fare2'] += fares[i]**2
        rs['n'] += 1
        rs['carriers'].add(carriers[i])

    if chunk_n % 4 == 0:
        print(f"  Processed {chunk_n*0.5:.0f}M rows...")

print(f"\nTotal: {n:,} valid rows")

# Compute final stats
mean_fare = sum_fare / n
var_fare = sum_fare2/n - mean_fare**2
std_fare = np.sqrt(var_fare)

mean_dist = sum_dist / n
var_dist = sum_dist2/n - mean_dist**2
std_dist = np.sqrt(var_dist)

mean_fpm = sum_fpm / n
var_fpm = sum_fpm2/n - mean_fpm**2
std_fpm = np.sqrt(var_fpm)

print(f"\n{'='*60}")
print(f"FULL DATASET STATS ({n:,} rows)")
print(f"{'='*60}")
print(f"Fare: mean=${mean_fare:.2f}, std=${std_fare:.2f}, range ${min_fare:.2f}-${max_fare:.2f}")
print(f"  Mean/Median check: mean=${mean_fare:.0f} (need chunked median)")
print(f"Distance: mean={mean_dist:.0f}, std={std_dist:.0f} miles")
print(f"Fare/mile: mean=${mean_fpm:.4f}, std=${std_fpm:.4f}")

# Carriers
print(f"\n=== ALL CARRIERS (sorted by volume) ===")
total_rows = sum(carrier_counts.values())
for c, cnt in sorted(carrier_counts.items(), key=lambda x: -x[1]):
    pct = cnt/total_rows*100
    print(f"  {c:4s}: {cnt:>10,} ({pct:5.1f}%)")

# Coupons
print(f"\n=== COUPONS ===")
for c, cnt in sorted(coupon_counts.items()):
    print(f"  {c} segment(s): {cnt:>10,} ({cnt/n*100:.1f}%)")

# Geo
print(f"\n=== GEOGRAPHY ===")
for g, cnt in sorted(geo_counts.items()):
    print(f"  Type {g}: {cnt:>10,} ({cnt/n*100:.1f}%)")

# Route stats
print(f"\n=== ROUTE-LEVEL ANALYSIS ===")
total_routes = len(route_stats)
# Compute route CVs and competition
route_cvs = []
route_competition = []
for key, rs in route_stats.items():
    if rs['n'] >= 5:
        mean_r = rs['sum_fare'] / rs['n']
        var_r = rs['sum_fare2']/rs['n'] - mean_r**2
        if var_r > 0 and mean_r > 0:
            cv = np.sqrt(var_r) / mean_r
            route_cvs.append(cv)
    if rs['n'] >= 1:
        route_competition.append(len(rs['carriers']))

print(f"Total OD pairs: {total_routes:,}")
print(f"Routes with >=5 observations: {len(route_cvs):,}")
if route_cvs:
    route_cvs = np.array(route_cvs)
    print(f"Intra-route CV distribution:")
    print(f"  Mean: {np.mean(route_cvs):.3f}, Median: {np.median(route_cvs):.3f}")
    print(f"  P25: {np.percentile(route_cvs,25):.3f}, P75: {np.percentile(route_cvs,75):.3f}")
    print(f"  P10: {np.percentile(route_cvs,10):.3f}, P90: {np.percentile(route_cvs,90):.3f}")

if route_competition:
    rc = np.array(route_competition)
    for ncar in sorted(set(rc)):
        cnt = (rc == ncar).sum()
        print(f"  {ncar} carrier(s): {cnt:,} routes ({cnt/len(rc)*100:.1f}%)")

# Competition vs CV relationship
print(f"\n=== COMPETITION vs PRICE DISPERSION ===")
comp_cv = {}
for key, rs in route_stats.items():
    ncar = len(rs['carriers'])
    if rs['n'] >= 5:
        mean_r = rs['sum_fare'] / rs['n']
        var_r = rs['sum_fare2']/rs['n'] - mean_r**2
        if var_r > 0 and mean_r > 0:
            cv = np.sqrt(var_r) / mean_r
            if ncar not in comp_cv:
                comp_cv[ncar] = []
            comp_cv[ncar].append(cv)

for ncar in sorted(comp_cv.keys()):
    cvs = np.array(comp_cv[ncar])
    print(f"  {ncar} carrier(s): {len(cvs):,} routes, mean CV={np.mean(cvs):.3f}, median CV={np.median(cvs):.3f}")
