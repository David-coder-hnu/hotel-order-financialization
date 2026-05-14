"""
Phase 1: Flight Data EDA for FSR Adaptation
Exploratory analysis of DB1B US DOT flight data vs hotel price data
"""
import pandas as pd
import numpy as np
from pathlib import Path
import json
import warnings
warnings.filterwarnings('ignore')

DATA = Path("C:/Users/weida/Desktop/酒店研究/data")
OUTPUT = Path("C:/Users/weida/Desktop/酒店研究/output")

# ─── 1. Load & summarize all DB1B quarters ───
print("=" * 80)
print("1. DB1B DATA LOADING & SUMMARY")
print("=" * 80)

db1b_quarters = sorted(DATA.glob("flight_prices_real/db1b_*/Origin_and_Destination_Survey_DB1BMarket_*.csv"))
# Also check the newer directory structure
db1b_new = sorted(DATA.glob("flight_prices_real/Origin_and_Destination_Survey_DB1BMarket_*/Origin_and_Destination_Survey_DB1BMarket_*.csv"))
all_db1b = db1b_quarters + db1b_new
print(f"Found {len(all_db1b)} DB1B files")

quarterly_stats = []
for f in all_db1b:
    df = pd.read_csv(f, low_memory=False)
    quarterly_stats.append({
        'file': f.parent.name,
        'rows': len(df),
        'unique_itins': df['ItinID'].nunique(),
        'unique_markets': df['MktID'].nunique(),
        'unique_origins': df['Origin'].nunique(),
        'unique_dests': df['Dest'].nunique(),
        'unique_carriers': df['OpCarrier'].nunique(),
        'avg_fare': df['MktFare'].mean(),
        'median_fare': df['MktFare'].median(),
        'total_passengers': df['Passengers'].sum(),
        'avg_distance': df['MktDistance'].mean(),
        'pct_nonstop': (df['MktCoupons'] == 1).mean() * 100,
    })

qdf = pd.DataFrame(quarterly_stats)
print(qdf.to_string())
print(f"\nTotal rows across all quarters: {qdf['rows'].sum():,}")
print(f"Total passengers: {qdf['total_passengers'].sum():,}")

# ─── 2. Load a representative sample for deep analysis ───
print("\n" + "=" * 80)
print("2. DEEP PRICE ANALYSIS (2024 Q1 sample)")
print("=" * 80)

# Use 2024 Q1 as representative
sample_f = [f for f in all_db1b if '2024' in str(f) and ('q1' in str(f).lower() or '_1.' in str(f).lower() or '2024_1' in str(f))]
# Try broader search
sample_f = [f for f in all_db1b if '2024' in str(f) and '_1.' in str(f)]
if not sample_f:
    sample_f = [f for f in all_db1b if '2024_1' in str(f)]
if not sample_f:
    sample_f = [all_db1b[0]]  # fallback

print(f"Using: {sample_f[0]}")
df = pd.read_csv(sample_f[0], low_memory=False)
print(f"Rows: {len(df):,}")

# ─── Price distribution ───
print("\n--- Fare Distribution ---")
fares = df[df['MktFare'] > 0]['MktFare']
print(f"Count: {len(fares):,}")
print(f"Mean: ${fares.mean():.2f}")
print(f"Median: ${fares.median():.2f}")
print(f"Std: ${fares.std():.2f}")
for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
    print(f"  P{p}: ${fares.quantile(p/100):.2f}")

# ─── Fare by distance group ───
print("\n--- Fare by Distance Group ---")
dist_groups = df.groupby('MktDistanceGroup').agg(
    count=('MktFare', 'count'),
    avg_fare=('MktFare', 'mean'),
    median_fare=('MktFare', 'median'),
    std_fare=('MktFare', 'std'),
    avg_distance=('MktDistance', 'mean'),
).round(2)
print(dist_groups.to_string())

# ─── Fare by carrier ───
print("\n--- Top 10 Carriers by Passenger Volume ---")
carrier_stats = df.groupby('OpCarrier').agg(
    passengers=('Passengers', 'sum'),
    itineraries=('ItinID', 'count'),
    avg_fare=('MktFare', 'mean'),
    median_fare=('MktFare', 'median'),
    avg_distance=('MktDistance', 'mean'),
).sort_values('passengers', ascending=False).head(10)
print(carrier_stats.to_string())

# ─── Fare by number of coupons (segments) ───
print("\n--- Fare by Segments (MktCoupons) ---")
seg_stats = df.groupby('MktCoupons').agg(
    count=('MktFare', 'count'),
    pct=('MktFare', lambda x: len(x)/len(df)*100),
    avg_fare=('MktFare', 'mean'),
    median_fare=('MktFare', 'median'),
).round(2)
print(seg_stats.to_string())

# ─── Seasonality: fare by quarter ───
print("\n" + "=" * 80)
print("3. SEASONALITY ANALYSIS (All Available Quarters)")
print("=" * 80)

# Load a summary across all quarters
seasonal_fares = []
for f in all_db1b:
    df_q = pd.read_csv(f, low_memory=False)
    yr = df_q['Year'].iloc[0]
    qtr = df_q['Quarter'].iloc[0]
    seasonal_fares.append({
        'year': yr,
        'quarter': qtr,
        'avg_fare': df_q['MktFare'].mean(),
        'median_fare': df_q['MktFare'].median(),
        'p25': df_q['MktFare'].quantile(0.25),
        'p75': df_q['MktFare'].quantile(0.75),
        'total_passengers': df_q['Passengers'].sum(),
    })

sf = pd.DataFrame(seasonal_fares).sort_values(['year', 'quarter'])
print(sf.to_string())

# ─── 4. TOP ROUTES ANALYSIS ───
print("\n" + "=" * 80)
print("4. TOP ROUTES ANALYSIS")
print("=" * 80)

df['route'] = df['Origin'] + '-' + df['Dest']
route_stats = df.groupby('route').agg(
    passengers=('Passengers', 'sum'),
    avg_fare=('MktFare', 'mean'),
    median_fare=('MktFare', 'median'),
    std_fare=('MktFare', 'std'),
    avg_distance=('MktDistance', 'mean'),
).sort_values('passengers', ascending=False)

print("\nTop 20 Routes by Volume:")
print(route_stats.head(20).to_string())

# Coefficient of variation (volatility proxy) by route
route_stats['cv'] = route_stats['std_fare'] / route_stats['avg_fare']
print(f"\n--- CV (volatility) stats across routes ---")
print(route_stats[route_stats['passengers'] > 100]['cv'].describe())

# ─── 5. GEOGRAPHY TYPE BREAKDOWN ───
print("\n" + "=" * 80)
print("5. GEOGRAPHY & MARKET TYPE")
print("=" * 80)

geo_labels = {1: 'Domestic', 2: 'International (US-origin)', 3: 'International (foreign-origin)'}
for geo in sorted(df['ItinGeoType'].dropna().unique()):
    subset = df[df['ItinGeoType'] == geo]
    print(f"GeoType {int(geo)} ({geo_labels.get(int(geo), 'Unknown')}): {len(subset):,} rows, "
          f"avg fare ${subset['MktFare'].mean():.2f}, median ${subset['MktFare'].median():.2f}")

# ─── 6. COMPARISON WITH HOTEL DATA ───
print("\n" + "=" * 80)
print("6. HOTEL DATA COMPARISON")
print("=" * 80)

hotel_files = [
    DATA / '2024_3.csv',
    DATA / '2024_4.csv',
    DATA / '2024_5.csv',
    DATA / '2024_6.csv',
]
hotel_all = []
for hf in hotel_files:
    if hf.exists():
        hdf = pd.read_csv(hf, usecols=['date', 'hotelCode', 'price'])
        hdf['month'] = pd.to_datetime(hdf['date']).dt.month
        hotel_all.append(hdf)

hotel_df = pd.concat(hotel_all, ignore_index=True)
print(f"Hotel records: {len(hotel_df):,}")
print(f"Unique hotels: {hotel_df['hotelCode'].nunique():,}")
print(f"Date range: {hotel_df['date'].min()} to {hotel_df['date'].max()}")

# Hotel price distribution
hprices = hotel_df[hotel_df['price'] > 0]['price']
print(f"\nHotel Price Distribution:")
print(f"  Mean: CNY {hprices.mean():.2f}")
print(f"  Median: CNY {hprices.median():.2f}")
print(f"  Std: CNY {hprices.std():.2f}")
for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
    print(f"  P{p}: CNY {hprices.quantile(p/100):.2f}")

# Hotel price by month
print("\nHotel Avg Price by Month:")
monthly_hotel = hotel_df.groupby('month')['price'].agg(['mean', 'median', 'std', 'count']).round(2)
print(monthly_hotel.to_string())

# Hotel levels
hotel_info = pd.read_csv(DATA / 'hotel_info.csv')
print(f"\nHotel Info: {len(hotel_info):,} records")
print(f"Levels: {hotel_info['hotelLevel'].value_counts().to_string()}")

# Cross-walk: hotel price volatility per hotel
hotel_cv = hotel_df.groupby('hotelCode')['price'].agg(['mean', 'std', 'count'])
hotel_cv['cv'] = hotel_cv['std'] / hotel_cv['mean']
hotel_cv_valid = hotel_cv[hotel_cv['count'] > 1]
print(f"\nHotel-level CV (volatility):")
print(f"  Mean CV: {hotel_cv_valid['cv'].mean():.4f}")
print(f"  Median CV: {hotel_cv_valid['cv'].median():.4f}")
print(f"  P90 CV: {hotel_cv_valid['cv'].quantile(0.9):.4f}")

# ─── 7. STRUCTURAL COMPARISON TABLE ───
print("\n" + "=" * 80)
print("7. FLIGHT vs HOTEL: STRUCTURAL COMPARISON")
print("=" * 80)

comparison = {
    'Metric': [
        'Annual sample size',
        'Unique assets (flights = routes, hotels = properties)',
        'Price mean',
        'Price median',
        'Price CV (volatility proxy)',
        'Asset-level CV (median)',
        'Booking window observability',
        'Cancellation/default visibility',
        'Perishability',
        'Capacity granularity',
        'Seasonality pattern',
    ],
    'Flights (DB1B 2024)': [
        f'{df["Passengers"].sum():,.0f} passengers',
        f'{df["route"].nunique():,} routes',
        f'USD {fares.mean():.2f}',
        f'USD {fares.median():.2f}',
        f'{fares.std()/fares.mean():.4f}',
        f'{route_stats[route_stats["passengers"] > 100]["cv"].median():.4f}',
        'Indirect (via advance purchase)',
        'Low (ticket non-refund / change fee)',
        '100% (seat departs)',
        'Per seat (150-350 per flight)',
        'Quarterly + holiday peaks',
    ],
    'Hotels (Chengdu 2024)': [
        f'{len(hotel_df):,} records',
        f'{hotel_df["hotelCode"].nunique():,} properties',
        f'CNY {hprices.mean():.2f}',
        f'CNY {hprices.median():.2f}',
        f'{hprices.std()/hprices.mean():.4f}',
        f'{hotel_cv_valid["cv"].median():.4f}',
        'Direct (daily price scraping)',
        'Moderate (platform exit tracked)',
        '100% (night passes)',
        'Per room (50-500 per hotel)',
        'Monthly + holiday peaks',
    ]
}
comp_df = pd.DataFrame(comparison)
print(comp_df.to_string())

# ─── 8. SAVE SUMMARY ───
summary = {
    'db1b_total_rows': int(qdf['rows'].sum()),
    'db1b_total_passengers': float(qdf['total_passengers'].sum()),
    'db1b_quarters': len(all_db1b),
    'flight_avg_fare': float(fares.mean()),
    'flight_median_fare': float(fares.median()),
    'flight_cv': float(fares.std() / fares.mean()),
    'flight_routes': int(df['route'].nunique()),
    'flight_carriers': int(df['OpCarrier'].nunique()),
    'hotel_count': int(hotel_df['hotelCode'].nunique()),
    'hotel_avg_price': float(hprices.mean()),
    'hotel_median_price': float(hprices.median()),
    'hotel_cv': float(hprices.std() / hprices.mean()),
}

with open(OUTPUT / 'flight_eda_summary.json', 'w') as f:
    json.dump(summary, f, indent=2, default=str)

print(f"\nSummary saved to {OUTPUT / 'flight_eda_summary.json'}")
print("\nPhase 1 EDA complete.")
