import pandas as pd
import numpy as np
import os

# 设置工作目录
work_dir = r'c:\Users\weida\Desktop\酒店研究'
os.chdir(work_dir)

# Task 1: 读取并合并所有价格数据文件
print("Task 1: 读取并合并所有价格数据文件...")

# 读取四个CSV文件
df_march = pd.read_csv('2024_3.csv')
df_april = pd.read_csv('2024_4.csv')
df_may = pd.read_csv('2024_5.csv')
df_june = pd.read_csv('2024_6.csv')

print(f"3月数据: {len(df_march)} 条")
print(f"4月数据: {len(df_april)} 条")
print(f"5月数据: {len(df_may)} 条")
print(f"6月数据: {len(df_june)} 条")

# 合并数据
df_all = pd.concat([df_march, df_april, df_may, df_june], ignore_index=True)
print(f"合并后总数据: {len(df_all)} 条")

# 查看数据结构
print("\n数据列名:", df_all.columns.tolist())
print("\n数据前5行:")
print(df_all.head())

# 数据类型转换（价格转为数值型）
df_all['price'] = pd.to_numeric(df_all['price'], errors='coerce')

# 删除价格为空的数据
df_all = df_all.dropna(subset=['price'])
print(f"\n删除空价格后数据: {len(df_all)} 条")

print("Task 1 完成！\n")

# Task 2: 实现异常值检测与清洗
print("Task 2: 实现异常值检测与清洗...")

# 按酒店分组计算价格统计量
def clean_outliers(group):
    prices = group['price']
    Q1 = prices.quantile(0.25)
    Q3 = prices.quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    median_price = prices.median()
    
    # 识别异常值
    outliers = (prices < lower_bound) | (prices > upper_bound)
    outlier_count = outliers.sum()
    
    if outlier_count > 0:
        print(f"酒店 {group['hotelCode'].iloc[0]}: 发现 {outlier_count} 个异常值，范围 [{lower_bound:.0f}, {upper_bound:.0f}]，中位数 {median_price:.0f}")
        # 用中位数替换异常值
        group.loc[outliers, 'price'] = median_price
        group.loc[outliers, 'is_outlier'] = True
    else:
        group['is_outlier'] = False
    
    return group

# 应用异常值清洗
print("开始检测异常值...")
df_cleaned = df_all.groupby('hotelCode', group_keys=False).apply(clean_outliers)

# 统计异常值
outlier_count = df_cleaned['is_outlier'].sum()
print(f"\n总共发现并清洗了 {outlier_count} 个异常值")

# 保存清洗后的数据
df_cleaned_to_save = df_cleaned[['date', 'hotelCode', 'price']].copy()
df_cleaned_to_save.to_csv('cleaned_hotel_prices.csv', index=False)
print(f"清洗后的数据已保存到 cleaned_hotel_prices.csv，共 {len(df_cleaned_to_save)} 条记录")

print("Task 2 完成！\n")

# Task 3: 计算每个酒店的最低价格
print("Task 3: 计算每个酒店的最低价格...")

# 按酒店分组找出最低价格
hotel_min_prices = df_cleaned.groupby('hotelCode')['price'].min().reset_index()
hotel_min_prices.columns = ['hotelCode', 'minPrice']

print(f"共有 {len(hotel_min_prices)} 个酒店")
print("\n最低价格统计:")
print(hotel_min_prices['minPrice'].describe())

print("Task 3 完成！\n")

# Task 4: 生成远期价格CSV文件
print("Task 4: 生成远期价格CSV文件...")

# 创建远期价格DataFrame
# 远期价格 = 该酒店的最低价格（作为一年后的预测价格）
df_future = hotel_min_prices.copy()
df_future.columns = ['hotelCode', 'futurePrice']

# 保存为CSV
df_future.to_csv('hotel_future_prices.csv', index=False)
print(f"远期价格文件已生成: hotel_future_prices.csv")
print(f"包含 {len(df_future)} 个酒店的远期价格")
print("\n前10个酒店的远期价格:")
print(df_future.head(10))

print("\nTask 4 完成！")
print("\n所有任务已完成！")
