import pandas as pd, numpy as np
import os

csv_path = r"C:\Users\weida\Desktop\酒店研究\data\flight_prices_real\db1b_2024q1\Origin_and_Destination_Survey_DB1BMarket_2024_1.csv"

# Read different chunks to get carrier diversity + full stats
print("Reading 2M rows (chunked)...")
chunks = []
for i, chunk in enumerate(pd.read_csv(csv_path, chunksize=500000, low_memory=False)):
    chunks.append(chunk)
    if i >= 3:  # 4 chunks = 2M rows
        break
df = pd.concat(chunks, ignore_index=True)
print(f"Loaded: {len(df):,} rows\n")

# === MORE CARRIERS ===
print("=== ALL CARRIERS (by count) ===")
cs = df.groupby('RPCarrier').agg(
    count=('Origin','count'),
    avg_fare=('MktFare','mean'),
    med_fare=('MktFare','median'),
    total_pax=('Passengers','sum'),
    avg_dist=('MktMilesFlown','mean')
).sort_values('count', ascending=False)
print(cs.to_string())
print(f"\nTotal carriers: {len(cs)}")

# === FARE DISTRIBUTION (2M sample) ===
print("\n=== FARE DISTRIBUTION (2M rows) ===")
fares = df['MktFare'].dropna()
print(f"Mean: ${fares.mean():.2f}  Median: ${fares.median():.2f}  Std: ${fares.std():.2f}")
print(f"Skewness: {fares.skew():.2f}  Kurtosis: {fares.kurtosis():.2f}")
# Log-normal test
log_fares = np.log(fares[fares > 0])
print(f"Log-fare mean: {log_fares.mean():.2f}  std: {log_fares.std():.2f}")

# === FARE PER MILE BY CARRIER TYPE ===
print("\n=== FARE PER MILE — LCC vs LEGACY ===")
lcc = ['WN', 'B6', 'F9', 'NK', 'G4']  # Southwest, JetBlue, Frontier, Spirit, Allegiant
legacy = ['AA', 'DL', 'UA', 'AS']  # American, Delta, United, Alaska
for label, codes in [('LCC', lcc), ('Legacy', legacy)]:
    mask = df['RPCarrier'].isin(codes)
    s = df.loc[mask, 'MktFare'] / df.loc[mask, 'MktMilesFlown'].replace(0, np.nan)
    print(f"  {label}: {mask.sum():,} rows, fare/mile mean=${s.mean():.4f}, median=${s.median():.4f}")

# === DISTANCE BINS vs FARE ===
print("\n=== FARE BY DISTANCE BAND ===")
bins = [0, 300, 600, 1000, 1500, 2500, 5000, 10000]
labels = ['0-300', '300-600', '600-1000', '1000-1500', '1500-2500', '2500-5000', '5000+']
df['DistBand'] = pd.cut(df['MktMilesFlown'], bins=bins, labels=labels)
db = df.groupby('DistBand', observed=False).agg(
    count=('Origin','count'),
    avg_fare=('MktFare','mean'),
    med_fare=('MktFare','median'),
    fare_per_mile=('MktFare', lambda x: (x / df.loc[x.index, 'MktMilesFlown'].replace(0, np.nan)).mean())
)
print(db.to_string())

# === ROUTE COMPETITION vs FARE ===
print("\n=== COMPETITION vs FARE ===")
rc = df.groupby(['Origin','Dest']).agg(
    carriers=('RPCarrier', 'nunique'),
    avg_fare=('MktFare', 'mean'),
    pax=('Passengers', 'sum')
)
# By competition level
for n_carriers in range(1, 5):
    s = rc[rc['carriers'] == n_carriers]
    if len(s) > 0:
        print(f"  {n_carriers} carrier(s): {len(s):,} routes, avg route fare=${s['avg_fare'].mean():.2f}")

# === PRICE DISPERSION (within same route) ===
print("\n=== PRICE DISPERSION (same route, same quarter) ===")
route_disp = df.groupby(['Origin','Dest']).agg(
    fare_min=('MktFare','min'),
    fare_max=('MktFare','max'),
    fare_std=('MktFare','std'),
    fare_cv=('MktFare', lambda x: x.std()/x.mean() if x.mean() > 0 else 0),
    n=('ItinID','nunique')
).query('n >= 10')  # Routes with at least 10 itineraries
print(f"Routes with >=10 itineraries: {len(route_disp):,}")
print(f"Mean price range within route: ${route_disp['fare_max'].mean() - route_disp['fare_min'].mean():.2f}")
print(f"Mean CV (coefficient of variation): {route_disp['fare_cv'].mean():.3f}")
print(f"Median CV: {route_disp['fare_cv'].median():.3f}")

# === PASSENGER vs FARE (bulk discount?) ===
print("\n=== PASSENGER COUNT vs AVG FARE ===")
df['PaxGroup'] = pd.cut(df['Passengers'], bins=[0,1,2,3,5,100], labels=['1','2','3','4-5','6+'])
pg = df.groupby('PaxGroup', observed=False).agg(
    count=('Origin','count'),
    avg_fare=('MktFare','mean'),
    med_fare=('MktFare','median')
)
print(pg.to_string())

# === KEY COMPARISON WITH HOTEL FSR ===
print("\n" + "="*60)
print("=== KEY INSIGHTS: FLIGHT FSR vs HOTEL FSR ===")
print("="*60)
print(f"1. Price distribution: right-skewed (skew={fares.skew():.1f})")
print(f"   Mean/Median ratio: {fares.mean()/fares.median():.2f}x — more spread than hotels")
print(f"2. Distance-fare correlation: r={df['MktMilesFlown'].corr(df['MktFare']):.3f} — weak!")
print(f"   → Flight FSR pricing needs a different primary factor than distance")
print(f"3. Intra-route dispersion CV: {route_disp['fare_cv'].median():.3f}")
print(f"   → Same route, same quarter — big price variation")
print(f"4. Non-stop premium: {(df[df['MktCoupons']==1]['MktFare'].mean() / df[df['MktCoupons']==2]['MktFare'].mean() - 1)*100:.1f}% cheaper than 1-stop")
print(f"5. Carrier effect: LCC avg ${df[df['RPCarrier'].isin(lcc)]['MktFare'].mean():.0f} vs Legacy ${df[df['RPCarrier'].isin(legacy)]['MktFare'].mean():.0f}")
