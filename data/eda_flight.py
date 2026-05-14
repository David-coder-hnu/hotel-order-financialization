import pandas as pd, numpy as np, os
os.chdir(r"C:\Users\weida\Desktop\酒店研究")

csv_path = r"data\flight_prices_real\db1b_2024q1\Origin_and_Destination_Survey_DB1BMarket_2024_1.csv"

print("Reading DB1B 2024 Q1 (500K sample)...")
df = pd.read_csv(csv_path, nrows=500000, low_memory=False)
print(f"Loaded: {len(df):,} rows, {len(df.columns)} columns\n")

# === FARE DISTRIBUTION ===
fares = df['MktFare'].dropna()
print("=== FARE (MktFare) DISTRIBUTION ===")
print(f"Mean: ${fares.mean():.2f}  |  Median: ${fares.median():.2f}  |  Std: ${fares.std():.2f}")
print(f"Min: ${fares.min():.2f}  |  Max: ${fares.max():.2f}")
for p in [1,5,10,25,50,75,90,95,99]:
    print(f"  P{p}: ${fares.quantile(p/100):.2f}")
print()

# === FARE PER MILE ===
df['FarePerMile'] = df['MktFare'] / df['MktMilesFlown'].replace(0, np.nan)
fpm = df['FarePerMile'].dropna()
print(f"=== FARE PER MILE ===")
print(f"Mean: ${fpm.mean():.4f}/mile  |  Median: ${fpm.median():.4f}/mile")
print(f"P5: ${fpm.quantile(0.05):.4f}  |  P95: ${fpm.quantile(0.95):.4f}")
print()

# === DISTANCE ===
dist = df['MktMilesFlown'].dropna()
print(f"=== DISTANCE (miles) ===")
print(f"Mean: {dist.mean():.0f}  |  Median: {dist.median():.0f}  |  Range: {dist.min():.0f}-{dist.max():.0f}")
print()

# === COUPONS ===
print("=== COUPONS (航段数) ===")
print(df['MktCoupons'].value_counts().sort_index().to_string())
print()

# === GEO ===
print("=== GEOGRAPHY TYPE ===")
print(df['ItinGeoType'].value_counts().to_string())
print()

# === TOP CARRIERS ===
print("=== TOP 15 CARRIERS ===")
cs = df.groupby('RPCarrier').agg(
    count=('Origin','count'),
    avg_fare=('MktFare','mean'),
    med_fare=('MktFare','median'),
    total_pax=('Passengers','sum')
).sort_values('count', ascending=False)
print(cs.head(15).to_string())
print()

# === TOP ROUTES ===
print("=== TOP 15 ROUTES (by passenger volume) ===")
rs = df.groupby(['Origin','Dest']).agg(
    pax=('Passengers','sum'),
    avg_fare=('MktFare','mean'),
    med_fare=('MktFare','median'),
    n=('ItinID','nunique')
).sort_values('pax', ascending=False)
print(rs.head(15).to_string())
print()

# === DISTANCE-FARE CORRELATION ===
print(f"=== DISTANCE vs FARE ===")
print(f"Pearson r = {df['MktMilesFlown'].corr(df['MktFare']):.4f}")
print(f"Spearman rho = {df['MktMilesFlown'].corr(df['MktFare'], method='spearman'):.4f}")
print()

# === FARES BY SEGMENTS ===
print("=== FARES BY COUPON COUNT ===")
for c in sorted(df['MktCoupons'].unique()):
    s = df[df['MktCoupons'] == c]['MktFare']
    print(f"  {c} seg(s): n={len(s):,}, mean=${s.mean():.2f}, median=${s.median():.2f}")
print()

# === DOMESTIC vs INT'L ===
print("=== DOMESTIC vs INTERNATIONAL ===")
for gt in df['ItinGeoType'].unique():
    s = df[df['ItinGeoType'] == gt]['MktFare']
    print(f"  {gt}: n={len(s):,}, mean=${s.mean():.2f}, median=${s.median():.2f}")
print()

# === BULK FARE ===
print("=== BULK FARE vs REGULAR ===")
for bf in sorted(df['BulkFare'].dropna().unique()):
    s = df[df['BulkFare'] == bf]['MktFare']
    pct = len(s)/len(df)*100
    print(f"  BulkFare={bf:.0f}: n={len(s):,} ({pct:.1f}%), mean=${s.mean():.2f}, median=${s.median():.2f}")
print()

# === PASSENGER WEIGHTING ===
print("=== PASSENGER-WEIGHTED FARE ===")
weighted_fare = np.average(df['MktFare'].dropna(), weights=df.loc[df['MktFare'].notna(), 'Passengers'])
print(f"Unweighted mean: ${fares.mean():.2f}")
print(f"Passenger-weighted mean: ${weighted_fare:.2f}")
print()

# === UNIQUE STATS ===
print(f"Unique itineraries: {df['ItinID'].nunique():,}")
print(f"Unique origin airports: {df['Origin'].nunique()}")
print(f"Unique dest airports: {df['Dest'].nunique()}")
print(f"OD pairs: {df.groupby(['Origin','Dest']).ngroups:,}")
print(f"Carriers: {df['RPCarrier'].nunique()}")
