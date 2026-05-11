"""Extract key metrics from engine output as key=value pairs for HTML report."""
import json

with open('output/abs_report_v6_fusion.json', 'r', encoding='utf-8') as f:
    r = json.load(f)

out = {}

# Pool stats
ap = r['asset_pool']['statistics']
out['POOL_SIZE'] = ap['pool_size']
out['POOL_TOTAL'] = int(ap['total_notional'])
out['POOL_AVG'] = int(ap['avg_hotel_price'])
out['POOL_HHI'] = round(ap['district_herfindahl'], 3)
out['POOL_DISTRICTS'] = ap['district_diversity']
out['POOL_WPD'] = round(ap['wtd_pd'] * 100, 1)
out['POOL_WLGD'] = round(ap['wtd_lgd'] * 100, 1)
out['POOL_WEL'] = round(ap['wtd_el'] * 100, 1)
out['POOL_TOP5'] = round(ap['top5_concentration'] * 100, 1)

# Level distribution
ld = ap['level_diversity']
out['LEVEL_ECO'] = ld.get('经济', 0)
out['LEVEL_COMFORT'] = ld.get('舒适', 0)
out['LEVEL_UPSCALE'] = ld.get('高档', 0)
out['LEVEL_LUXURY'] = ld.get('豪华', 0)

# Tranches
for t in r['tranche_structure']:
    name = t['name']
    out[f'TRANCHE_{name.upper()}_PCT'] = round(t['size_pct'] * 100)
    out[f'TRANCHE_{name.upper()}_COUPON'] = round(t['coupon_annual'] * 100, 1)
    out[f'TRANCHE_{name.upper()}_SUPPORT'] = round(t['credit_support_pct'] * 100)
    out[f'TRANCHE_{name.upper()}_NOTIONAL'] = int(t['notional'])

# Monte Carlo
mc = r['monte_carlo']['tranche_analysis']
for name, s in mc.items():
    out[f'MC_{name.upper()}_EL'] = round(s['mean_loss_rate'] * 100, 4)
    out[f'MC_{name.upper()}_VAR95'] = round(s['var_95'] * 100, 4)
    out[f'MC_{name.upper()}_VAR99'] = round(s['var_99'] * 100, 4)
    out[f'MC_{name.upper()}_RATING'] = s['implied_rating']

# Stress test
for sc_name, sc_data in r['monte_carlo'].get('stress_test', {}).items():
    s = sc_data.get('Senior', {})
    out[f'STRESS_{sc_name}_EL'] = round(s.get('mean_loss_rate', 0) * 100, 4)

# Comparison
comp = r['comparison_analysis']
out['NPV_UPLIFT_PCT'] = round(comp['npv_uplift']['percentage'], 1)
out['NPV_UPLIFT_ABS'] = int(comp['npv_uplift']['absolute'])
try:
    tr_mode = comp['time_right_mode']
    out['TR_ISSUE_REVENUE'] = int(tr_mode['issue_revenue'])
    out['TR_HOTEL_BENEFIT'] = int(tr_mode.get('hotel_net_benefit', 0))
except:
    pass

# Feasibility
fe = r['feasibility_evaluation']
out['FEASIBILITY_SCORE'] = fe['overall_score']
out['FEASIBILITY_RATING'] = fe['rating']

# Tripartite
tb = r.get('tripartite_benefit_analysis', {})
for k, v in tb.items():
    if isinstance(v, dict):
        for k2, v2 in v.items():
            if isinstance(v2, (int, float)):
                out[f'TRIP_{k}_{k2}'] = round(v2, 2) if isinstance(v2, float) else v2

# Time-right market
ms = r.get('time_right_market_simulation', {})
out['TR_QTY'] = ms.get('time_right_total_quantity', 0)
out['TR_OVERISSUANCE'] = 1.29

# Hotel count in pool
out['POOL_HOTELS_IN_INFO'] = 86159
out['POOL_HOTELS_WITH_PRICES'] = 16257
out['TOTAL_PRICE_RECORDS'] = 1707918
out['MC_PATHS'] = 5000
out['MC_MONTHS'] = 36

# Print as JS variables
print("const METRICS = {")
for key, val in sorted(out.items()):
    if isinstance(val, str):
        print(f"  {key}: '{val}',")
    else:
        print(f"  {key}: {val},")
print("};")
