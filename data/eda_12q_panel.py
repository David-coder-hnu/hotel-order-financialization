"""
12-Quarter DB1B Panel EDA: Competition Paradox Validation.
Validates CV ~ N_carriers across all 13 available quarters (2022Q1-2025Q1).
Outputs: per-quarter competition paradox stats + pooled summary.
"""
import pandas as pd, numpy as np, os, glob, json

BASE = r"C:\Users\weida\Desktop\酒店研究\data\flight_prices_real"
OUTPUT = os.path.join(BASE, "panel_results")
os.makedirs(OUTPUT, exist_ok=True)

# Find all quarter directories
quarters = sorted(glob.glob(os.path.join(BASE, "db1b_*")))
print(f"Found {len(quarters)} quarter directories:\n")
for q in quarters:
    print(f"  {os.path.basename(q)}")

results = []

for qdir in quarters:
    qname = os.path.basename(qdir)
    csv_files = glob.glob(os.path.join(qdir, "*.csv"))
    if not csv_files:
        print(f"\n[SKIP] {qname}: no CSV found", flush=True)
        continue

    csv_path = csv_files[0]
    print(f"\n{'='*60}")
    print(f"Processing {qname} ({os.path.basename(csv_path)})")
    print(f"{'='*60}")

    # Read in chunks, aggregate at route level
    route_data = {}  # (origin, dest) -> {fares: [], carriers: set, pax: 0}
    total_rows = 0
    chunk_n = 0

    try:
        for chunk in pd.read_csv(csv_path, chunksize=500000, low_memory=False):
            chunk_n += 1
            total_rows += len(chunk)

            mask = chunk['MktFare'].notna() & (chunk['MktMilesFlown'] > 0)
            chunk = chunk[mask]

            for _, row in chunk.iterrows():
                key = (row['Origin'], row['Dest'])
                if key not in route_data:
                    route_data[key] = {'fares': [], 'carriers': set(), 'pax': 0.0}
                route_data[key]['fares'].append(row['MktFare'])
                route_data[key]['carriers'].add(row['RPCarrier'])
                route_data[key]['pax'] += row['Passengers']

            if chunk_n % 5 == 0:
                print(f"  {chunk_n * 0.5:.0f}M rows, {len(route_data):,} routes...", flush=True)

        print(f"  Total: {total_rows:,} rows, {len(route_data):,} routes")

        # Aggregate: compute CV per route
        route_stats = []
        for (orig, dest), data in route_data.items():
            fares = np.array(data['fares'])
            if len(fares) >= 10:  # Require at least 10 observations
                mean_f = np.mean(fares)
                std_f = np.std(fares)
                cv = std_f / mean_f if mean_f > 0 else np.nan
                route_stats.append({
                    'origin': orig, 'dest': dest,
                    'n_obs': len(fares),
                    'n_carriers': len(data['carriers']),
                    'total_pax': data['pax'],
                    'mean_fare': mean_f,
                    'median_fare': np.median(fares),
                    'std_fare': std_f,
                    'cv': cv,
                    'min_fare': np.min(fares),
                    'max_fare': np.max(fares),
                })

        df_routes = pd.DataFrame(route_stats).dropna(subset=['cv'])
        print(f"  Routes with >=10 obs: {len(df_routes):,}")

        # Competition paradox check: CV by N_carriers
        cv_by_n = df_routes.groupby('n_carriers').agg(
            n_routes=('cv', 'count'),
            mean_cv=('cv', 'mean'),
            median_cv=('cv', 'median'),
            std_cv=('cv', 'std'),
            mean_fare=('mean_fare', 'mean'),
        ).reset_index()

        print(f"\n  Competition Paradox ({qname}):", flush=True)
        for _, row in cv_by_n.iterrows():
            print(f"    {int(row['n_carriers'])} carrier(s): {int(row['n_routes']):,} routes, CV={row['mean_cv']:.3f} (med={row['median_cv']:.3f})")

        # OLS: CV ~ n_carriers
        from sklearn.linear_model import LinearRegression
        X = df_routes[['n_carriers']].values
        y = df_routes['cv'].values
        reg = LinearRegression().fit(X, y)

        # Also with log(n_carriers)
        X_log = np.log(df_routes[['n_carriers']].values)
        reg_log = LinearRegression().fit(X_log, y)

        results.append({
            'quarter': qname,
            'total_rows': total_rows,
            'n_routes': len(df_routes),
            'n_carriers_unique': df_routes['n_carriers'].nunique(),
            'mean_cv': df_routes['cv'].mean(),
            'median_cv': df_routes['cv'].median(),
            'cv_n1': cv_by_n[cv_by_n['n_carriers']==1]['mean_cv'].values[0] if 1 in cv_by_n['n_carriers'].values else np.nan,
            'cv_n4': cv_by_n[cv_by_n['n_carriers']==4]['mean_cv'].values[0] if 4 in cv_by_n['n_carriers'].values else np.nan,
            'cv_n8': cv_by_n[cv_by_n['n_carriers']==8]['mean_cv'].values[0] if 8 in cv_by_n['n_carriers'].values else np.nan,
            'cv_n_max': cv_by_n['mean_cv'].iloc[-1],
            'beta_linear': reg.coef_[0],
            'beta_log': reg_log.coef_[0],
            'r2_linear': reg.score(X, y),
            'r2_log': reg_log.score(X_log, y),
        })

        print(f"  beta (linear): {reg.coef_[0]:.6f}, R^2={reg.score(X,y):.4f}", flush=True)
        print(f"  beta (log): {reg_log.coef_[0]:.6f}, R^2={reg_log.score(X_log,y):.4f}", flush=True)

    except Exception as e:
        print(f"  [ERROR] {qname}: {e}")
        results.append({'quarter': qname, 'error': str(e)})

# === CROSS-QUARTER SUMMARY ===
print(f"\n{'='*60}")
print("12-QUARTER CROSS-SECTION SUMMARY")
print(f"{'='*60}")

valid = [r for r in results if 'beta_linear' in r]
print(f"\nQuarters with valid results: {len(valid)}/{len(quarters)}")

if valid:
    betas = [r['beta_linear'] for r in valid]
    r2s = [r['r2_linear'] for r in valid]
    cv1s = [r['cv_n1'] for r in valid if not np.isnan(r['cv_n1'])]
    cv_maxs = [r['cv_n_max'] for r in valid]

    print(f"\n  beta (CV ~ N_carriers):", flush=True)
    print(f"    Mean: {np.mean(betas):.6f}, Std: {np.std(betas):.6f}", flush=True)
    print(f"    Min: {np.min(betas):.6f} ({valid[np.argmin(betas)]['quarter']})", flush=True)
    print(f"    Max: {np.max(betas):.6f} ({valid[np.argmax(betas)]['quarter']})", flush=True)
    print(f"    All beta > 0: {all(b > 0 for b in betas)}", flush=True)

    print(f"\n  R^2:", flush=True)
    print(f"    Mean: {np.mean(r2s):.4f}, Range: [{np.min(r2s):.4f}, {np.max(r2s):.4f}]", flush=True)

    if cv1s and cv_maxs:
        print(f"\n  CV range:", flush=True)
        print(f"    Monopoly (N=1): mean CV = {np.mean(cv1s):.3f}", flush=True)
        print(f"    Max competition: mean CV = {np.mean(cv_maxs):.3f}", flush=True)
        print(f"    deltaCV: {np.mean(cv_maxs) - np.mean(cv1s):.3f}", flush=True)

    # Save full results
    df_results = pd.DataFrame(valid)
    csv_path = os.path.join(OUTPUT, "competition_paradox_12q.csv")
    df_results.to_csv(csv_path, index=False)
    print(f"\nResults saved: {csv_path}", flush=True)

    # Per-quarter detail
    print(f"\n{'Quarter':<15} {'Routes':>10} {'beta_lin':>10} {'R^2':>8} {'CV(N=1)':>10} {'CV(max)':>10} {'beta>0':>8}", flush=True)
    print("-" * 73, flush=True)
    for r in valid:
        print(f"{r['quarter']:<15} {r['n_routes']:>10,} {r['beta_linear']:>10.6f} {r['r2_linear']:>8.4f} {r['cv_n1']:>10.3f} {r['cv_n_max']:>10.3f} {'YES' if r['beta_linear'] > 0 else 'NO':>8}", flush=True)

print("\nDone.")
