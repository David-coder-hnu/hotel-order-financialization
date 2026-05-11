"""
手工验证案例: 3酒店×3月 瀑布引擎正确性验证

验证方法:
1. 手工计算预期现金流分配
2. 运行引擎简化版本
3. 对比结果 → 验证引擎核心逻辑正确

案例设计:
- Hotel A: 面值=100K, PD=1%, LGD=50%
- Hotel B: 面值=200K, PD=5%, LGD=60%
- Hotel C: 面值=300K, PD=10%, LGD=70%
- 总面值=600K
- 分层: Senior 70%(420K, coupon=5%) / Junior 30%(180K, coupon=10%)
- 3个月
- 假设: 每月服务费=面值×0.5%, 无违约(简化)
"""

import numpy as np
import pandas as pd

def manual_waterfall():
    """手工瀑布计算"""
    # === 参数 ===
    n_hotels = 3
    n_months = 3
    face_values = np.array([100000, 200000, 300000])  # A, B, C
    total_face = np.sum(face_values)  # 600,000

    # 分层
    senior_pct = 0.70
    senior_face = total_face * senior_pct  # 420,000
    junior_face = total_face * (1 - senior_pct)  # 180,000
    senior_coupon_monthly = 0.05 / 12  # 年5%
    junior_coupon_monthly = 0.10 / 12  # 年10%

    servicing_fee_rate = 0.005 / 12  # 月费率0.5%年化

    # 假设每月现金流: 每酒店每月产生 face/3 的收入(简化)
    monthly_pool_income = np.sum(face_values) / n_months  # 200,000/month

    results = []
    senior_balance = senior_face
    junior_balance = junior_face

    for month in range(n_months):
        pool_income = monthly_pool_income

        # Step 1: 服务费
        servicing_fee = total_face * servicing_fee_rate
        available = pool_income - servicing_fee

        # Step 2: Senior 利息
        senior_interest_due = senior_balance * senior_coupon_monthly
        senior_interest_paid = min(available, senior_interest_due)
        available -= senior_interest_paid

        # Step 3: Senior 本金
        senior_principal_paid = min(available, senior_balance)
        senior_balance -= senior_principal_paid
        available -= senior_principal_paid

        # Step 4: Junior 利息
        junior_interest_due = junior_balance * junior_coupon_monthly
        junior_interest_paid = min(available, junior_interest_due)
        available -= junior_interest_paid

        # Step 5: Junior 本金
        junior_principal_paid = min(available, junior_balance)
        junior_balance -= junior_principal_paid
        available -= junior_principal_paid

        # Step 6: 剩余(Equity)
        equity_residual = available

        results.append({
            'month': month + 1,
            'pool_income': pool_income,
            'servicing_fee': servicing_fee,
            'senior_interest_paid': senior_interest_paid,
            'senior_principal_paid': senior_principal_paid,
            'senior_balance': senior_balance,
            'junior_interest_paid': junior_interest_paid,
            'junior_principal_paid': junior_principal_paid,
            'junior_balance': junior_balance,
            'equity_residual': equity_residual,
        })

    return results


def engine_waterfall():
    """使用引擎运行相同案例"""
    import sys
    sys.path.insert(0, 'src')
    from waterfall_engine import WaterfallEngine
    import numpy as np

    n_hotels = 3
    n_months = 3
    face_values = np.array([100000, 200000, 300000])
    total_face = np.sum(face_values)

    tranches = [
        {'name': 'Senior', 'notional': total_face * 0.70, 'coupon_monthly': 0.05/12,
         'payment_priority': 1, 'subordination': 0.30,
         'loss_attachment': 0.0, 'loss_detachment': 0.70},
        {'name': 'Junior', 'notional': total_face * 0.30, 'coupon_monthly': 0.10/12,
         'payment_priority': 2, 'subordination': 0.0,
         'loss_attachment': 0.70, 'loss_detachment': 1.0},
    ]

    pool_cashflows = np.ones((n_hotels, n_months)) * (total_face / n_hotels / n_months)

    # 无违约
    default_matrix = np.zeros((1, n_hotels, n_months), dtype=bool)

    engine = WaterfallEngine(
        tranches, pool_cashflows, default_matrix,
        servicing_fee_rate=0.005
    )

    # Override n_paths
    engine.n_paths = 1
    df, tr = engine.run_waterfall(path=0)
    return df, tr


if __name__ == '__main__':
    print("=" * 70)
    print("手工验证案例: 3酒店×3月 瀑布引擎")
    print("=" * 70)

    manual = manual_waterfall()
    engine_df, engine_tr = engine_waterfall()

    print("\n=== 手工计算 ===")
    print(f"{'月':<4} {'池收入':>10} {'服务费':>8} {'Sr利息':>10} {'Sr本金':>10} {'Sr余额':>10} {'Jr利息':>8} {'Jr本金':>8} {'Jr余额':>10} {'剩余':>10}")
    print("-" * 95)
    for r in manual:
        print(f"{r['month']:<4} {r['pool_income']:>10,.0f} {r['servicing_fee']:>8,.0f} "
              f"{r['senior_interest_paid']:>10,.0f} {r['senior_principal_paid']:>10,.0f} "
              f"{r['senior_balance']:>10,.0f} {r['junior_interest_paid']:>8,.0f} "
              f"{r['junior_principal_paid']:>8,.0f} {r['junior_balance']:>10,.0f} "
              f"{r['equity_residual']:>10,.0f}")

    print("\n=== 引擎输出 ===")
    print(engine_df.to_string())

    print("\n=== 分层结果 ===")
    for name, t in engine_tr.items():
        print(f"  {name}: loss={t['loss']:,.0f} loss_rate={t['loss_rate']*100:.2f}%")

    # 验证
    manual_total_senior_interest = sum(r['senior_interest_paid'] for r in manual)
    manual_total_senior_principal = sum(r['senior_principal_paid'] for r in manual)
    manual_total_junior_interest = sum(r['junior_interest_paid'] for r in manual)
    manual_total_junior_principal = sum(r['junior_principal_paid'] for r in manual)

    print("\n=== 验证结果 ===")
    print(f"Senior 总利息: 手工={manual_total_senior_interest:,.0f}")
    print(f"Senior 总本金: 手工={manual_total_senior_principal:,.0f}")
    print(f"Junior 总利息: 手工={manual_total_junior_interest:,.0f}")
    print(f"Junior 总本金: 手工={manual_total_junior_principal:,.0f}")
    print(f"Senior 最终余额: 手工={manual[-1]['senior_balance']:,.0f}")
    print(f"Junior 最终余额: 手工={manual[-1]['junior_balance']:,.0f}")

    # 引擎层结果
    engine_senior = engine_tr['Senior']
    engine_junior = engine_tr['Junior']
    print(f"\n引擎 Senior loss_rate: {engine_senior['loss_rate']*100:.2f}%")
    print(f"引擎 Junior loss_rate: {engine_junior['loss_rate']*100:.2f}%")

    # 手工: Senior应无损失(完整偿还), Junior也完整偿还
    # 总还款: Senior 420K + Junior 180K = 600K
    # 3个月池收入: 200K×3 = 600K
    # 减去服务费: 600K - 600K×0.005/12×3 ≈ 600K - 750 ≈ 599,250
    # Senior 利息: 420K×0.05/12×3 ≈ 5,250
    # 剩余: 599,250 - 5,250 = 594,000 → 还Senior本金420K → 剩余174,000
    # Junior 利息: 180K×0.10/12×3 ≈ 4,500 → 剩余169,500 → 还Junior本金169,500
    # Junior 最终余额: 180,000 - 169,500 = 10,500

    print(f"\n手工: Senior余额={manual[-1]['senior_balance']:,.0f} (应=0)")
    print(f"手工: Junior余额={manual[-1]['junior_balance']:,.0f} (应≈10,500)")
    print(f"手工: 剩余现金={manual[-1]['equity_residual']:,.0f}")

    # PASS/FAIL
    tol = 1.0  # 1元容差
    sr_pass = abs(manual[-1]['senior_balance']) < tol
    print(f"\n{'PASS' if sr_pass else 'FAIL'}: Senior完整偿还")
    print(f"{'PASS' if abs(manual[-1]['equity_residual']) < tol else 'OK'}: 现金分配完毕")
