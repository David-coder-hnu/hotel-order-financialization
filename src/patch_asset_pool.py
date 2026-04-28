with open('asset_pool.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

insert_idx = None
for i, line in enumerate(lines):
    if 'def compute_monthly_cashflows' in line:
        insert_idx = i
        break

if insert_idx:
    new_method = '''    def compute_time_right_params(self, pool_df, discount_rate=0.08,
                                    safety_factor=0.8, issue_discount=0.25,
                                    time_to_maturity_months=36):
        """
        计算时权(Time-Right)参数
        单份时权 = "未来T时段一晚住宿权利"
        """
        room_estimate = {'经济': 60, '舒适': 80, '高档': 120, '豪华': 200}
        params = []
        for _, row in pool_df.iterrows():
            level = row['hotelLevel']
            rooms = room_estimate.get(level, 80)
            avg_price = row['avgPrice']
            min_price = row['minPrice']
            base_price = min_price if min_price > 0 else avg_price * 0.5
            occupancy = 0.62
            overbooking = 1.0 / max(occupancy, 0.3) * safety_factor
            issue_quantity = int(rooms * 365 * overbooking)
            T = time_to_maturity_months / 12.0
            forward_discount = np.exp(-discount_rate * T)
            issue_price = base_price * forward_discount * (1 - issue_discount)
            total_face_value = issue_price * issue_quantity
            spot_predicted = avg_price * (1 + 0.03 * T)
            params.append({
                'hotelCode': row['hotelCode'],
                'rooms': rooms,
                'occupancy': occupancy,
                'overbooking_multiplier': overbooking,
                'issue_quantity': issue_quantity,
                'issue_price': issue_price,
                'base_price': base_price,
                'avg_price': avg_price,
                'spot_predicted': spot_predicted,
                'total_face_value': total_face_value,
                'time_to_maturity': T,
                'hotelLevel': level,
            })
        return pd.DataFrame(params)

'''
    lines.insert(insert_idx, new_method)
    with open('asset_pool.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print('Added compute_time_right_params')
else:
    print('Method not found')
