import random
import matplotlib.pyplot as plt
from datetime import datetime
import csv
import os
import time

# 設置中文字體
plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP', 'Noto Serif CJK JP', 'DejaVu Sans']  # 按優先順序嘗試
plt.rcParams['axes.unicode_minus'] = False  # 解決負號顯示問題

# 參數設置
config = {}

with open("config.txt", "r", encoding="utf-8") as file:
    exec(file.read(), config)

# 讀取變數
METER_NO = config["METER_NO"]
BASE_DEMAND_RANGE = config["BASE_DEMAND_RANGE"]
MONTHS = config["MONTHS"]
SEASONAL_ADJUSTMENT = config["SEASONAL_ADJUSTMENT"]
BASIC_CHARGE_RATES = config["BASIC_CHARGE_RATES"]
ENERGY_RATES = config["ENERGY_RATES"]

LOW_DEMAND_START = config["LOW_DEMAND_START"]
LOW_DEMAND_END = config["LOW_DEMAND_END"]
LOW_DEMAND_RANGE = config["LOW_DEMAND_RANGE"]

PEAK_VALUES_DICT = {
    4: config["PEAK_VALUES_APRIL"],
    5: config["PEAK_VALUES_MAY"],
    7: config["PEAK_VALUES_JULY"]
}

REFERENCE_TOTAL_DEMANDS_DICT = {
    4: config["REFERENCE_TOTAL_DEMANDS_APRIL"],
    5: config["REFERENCE_TOTAL_DEMANDS_MAY"],
    7: config["REFERENCE_TOTAL_DEMANDS_JULY"]
}

MAX_DEMAND_LIMITS_DICT = {
    4: config["MAX_DEMAND_LIMITS_APRIL"],
    5: config["MAX_DEMAND_LIMITS_MAY"],
    7: config["MAX_DEMAND_LIMITS_JULY"]
}

def time_to_minutes(time_str):
    hour, minute = map(int, time_str.split(":"))
    return hour * 60 + minute

def generate_random_demand(period, peak_value, max_demand_limits, is_low_demand=False):
    """
    根據時段生成隨機需求量，確保不超過 peak_value 和時段最高需量限制。

    參數：
        period (str): 時段類型 ("Peak", "Half_Peak", "Saturday_Half_Peak", "Off_Peak")
        peak_value (float): 當日高峰值 (kW)
        is_low_demand (bool): 是否為低需求時段

    返回：
        float: 隨機生成的需求量 (kW)
    """
    # 獲取時段的最高需量限制（從 config.txt 讀取）
    max_demand_limit = max_demand_limits[period]

    # 根據時段設置隨機範圍
    if is_low_demand:
        # 低需求時段使用 LOW_DEMAND_RANGE，但不超過 peak_value 和時段限制
        upper_bound = min(LOW_DEMAND_RANGE[1], peak_value, max_demand_limit)
        lower_bound = min(LOW_DEMAND_RANGE[0], peak_value, max_demand_limit)
    else:
        # 根據時段調整範圍
        if period == "Peak":
            # 尖峰時段：接近 peak_value，但不超過時段限制
            lower_bound = min(BASE_DEMAND_RANGE[0], peak_value, max_demand_limit)
            upper_bound = min(BASE_DEMAND_RANGE[1], peak_value, max_demand_limit)
        elif period == "Half_Peak":
            # 半尖峰時段：中等範圍
            lower_bound = min(BASE_DEMAND_RANGE[0], peak_value, max_demand_limit)
            upper_bound = min(BASE_DEMAND_RANGE[1], peak_value, max_demand_limit)
        elif period == "Saturday_Half_Peak":
            # 週六半尖峰：略低於半尖峰
            lower_bound = min(BASE_DEMAND_RANGE[0], peak_value, max_demand_limit)
            upper_bound = min(BASE_DEMAND_RANGE[1], peak_value, max_demand_limit)
        else:  # Off_Peak
            # 離峰時段：降低範圍
            lower_bound = min(BASE_DEMAND_RANGE[0], peak_value, max_demand_limit)  # 降低下限
            upper_bound = min(BASE_DEMAND_RANGE[1], peak_value, max_demand_limit)  # 降低上限

    # 確保下限不超過上限
    lower_bound = min(lower_bound, upper_bound)
    demand = random.uniform(lower_bound, upper_bound)

    return round(demand, 2)

def compare_energy_with_reference(stats, reference_totals, year, month):
    """
    比較整個月的總用電度數（kWh）與參考值，計算超出或不足的量，並顯示百分比。

    參數：
        stats (dict): 包含各時段總用電度數的統計數據（整個月的數據，單位：kWh）
        reference_totals (dict): 各時段的參考用電度數（從 config.txt 讀取，代表整個月的數據，單位：kWh）
        year, month (int): 用於打印年份和月份

    返回：
        dict: 每個時段的差額（kWh），例如 {"Peak": 80720.00, "Half_Peak": 62880.00, ...}
    """

    periods = [
        ("Peak", "total_peak_demand", "尖峰時段"),
        ("Half_Peak", "total_half_peak_demand", "半尖峰時段"),
        ("Saturday_Half_Peak", "total_saturday_half_peak_demand", "週六半尖峰時段"),
        ("Off_Peak", "total_off_peak_demand", "離峰時段")
    ]

    reference_totals_kw = {}
    for key,value in reference_totals.items():
        reference_totals_kw[key] = round(value/0.25,2)

    differences = {}

    print(f"\n用電度數比較（{year}-{month:02d} 整月）：")
    for period_key, stats_key, period_name in periods:
        total_energy = stats[stats_key]
        reference = reference_totals_kw[period_key]
        difference = round(total_energy - reference, 2)  # 保留 2 位小數
        differences[period_key] = difference

        # 計算百分比（避免除以 0 的情況）
        percentage = round((difference / reference) * 100, 2) if reference != 0 else 0.00

        if difference > 0:
            print(f"  {period_name}：總用電kW {total_energy:,.2f} kW，超出參考值 {difference:,.2f} kW ({percentage:+.2f}%) (參考值: {reference:,.2f} kW)")
        elif difference < 0:
            print(f"  {period_name}：總用電kW {total_energy:,.2f} kW，不足參考值 {-difference:,.2f} kW ({percentage:+.2f}%) (參考值: {reference:,.2f} kW)")
        else:
            print(f"  {period_name}：總用電kW {total_energy:,.2f} kW，與參考值相等 ({percentage:+.2f}%) (參考值: {reference:,.2f} kW)")

    # 動態計算總計參考值
    reference_total = round(sum(reference_totals_kw[period_key] for period_key, _, _ in periods), 2)
    total_energy = round(stats["total_demand"], 2)
    difference = round(total_energy - reference_total, 2)
    differences["Total"] = difference

    # 計算總計的百分比
    total_percentage = round((difference / reference_total) * 100, 2) if reference_total != 0 else 0.00

    print("\n總計比較：")
    if difference > 0:
        print(f"  總計：總用電kW {total_energy:,.2f} kW，超出參考值 {difference:,.2f} kW ({total_percentage:+.2f}%) (參考值: {reference_total:,.2f} kW)")
    elif difference < 0:
        print(f"  總計：總用電kW {total_energy:,.2f} kW，不足參考值 {-difference:,.2f} kW ({total_percentage:+.2f}%) (參考值: {reference_total:,.2f} kW)")
    else:
        print(f"  總計：總用電kW {total_energy:,.2f} kW，與參考值相等 ({total_percentage:+.2f}%) (參考值: {reference_total:,.2f} kW)")

    return differences


def generate_daily_demand_data(year=2024, month=4, start_day=1, end_day=None, peak_time=None, peak_value=None):
    """
    生成指定日期範圍的需量數據，允許設定特定時間的峰值需量，並計算各時段的最大需量和總需量（kW 和 kWh）。
    確保隨機生成的需求量不超過當日的 peak_value。同時與參考用電度數比較，調整數據以匹配參考值。

    參數：
        year (int): 年份，預設 2024
        month (int): 月份，預設 4
        start_day (int): 起始日期，預設 1
        end_day (int): 結束日期，若為 None 則預設為該月最後一天
        peak_time (str): 指定的高峰時間，例如 "12:30"
        peak_value (float): 指定的高峰發電量 (kW)

    返回：
        tuple: (list: 調整後的需量數據, dict: 調整後的各時段最大需量和總需量/總能量)
    """
    # Initialize totals and maximums
    max_demand_limits = MAX_DEMAND_LIMITS_DICT[month]
    total_peak_demand = 0
    total_off_peak_demand = 0
    total_half_peak_demand = 0
    total_saturday_half_peak_demand = 0

    total_peak_energy = 0
    total_off_peak_energy = 0
    total_half_peak_energy = 0
    total_saturday_half_peak_energy = 0

    max_peak_demand = 0
    max_off_peak_demand = 0
    max_half_peak_demand = 0
    max_saturday_half_peak_demand = 0
    
    days = MONTHS.get(month, 31)

    if end_day is None:
        end_day = days

    start_day = max(1, start_day)
    end_day = min(days, end_day)

    data = []

    for day in range(start_day, end_day + 1):
        record_date = datetime(year, month, day)
        weekday = record_date.weekday()
        day_type = classify_day_of_week(year, month, day)
        is_summer = (month > 5 or (month == 5 and day >= 16)) and (month < 10 or (month == 10 and day <= 15))
        season = "Summer" if is_summer else "Non_Summer"

        for hour in range(24):
            for minute in [0, 15, 30, 45]:
                record_time = f"{hour:02d}:{minute:02d}"
                time_minutes = time_to_minutes(record_time)
                is_low_demand = LOW_DEMAND_START <= record_time <= LOW_DEMAND_END

                # Classify the period based on the new table
                if day_type == "Weekday":
                    if season == "Summer":
                        if 16 * 60 <= time_minutes < 22 * 60:  # 16:00-22:00
                            period = "Peak"
                        elif (9 * 60 <= time_minutes < 16 * 60) or (22 * 60 <= time_minutes < 24 * 60):  # 09:00-16:00, 22:00-24:00
                            period = "Half_Peak"
                        else:  # 00:00-09:00
                            period = "Off_Peak"
                    else:  # Non-Summer
                        if 9 * 60 <= time_minutes < 24 * 60:  # 09:00-24:00
                            period = "Half_Peak"
                        else:  # 00:00-09:00
                            period = "Off_Peak"
                elif day_type == "Saturday":
                    if 9 * 60 <= time_minutes < 24 * 60:  # 09:00-24:00
                        period = "Saturday_Half_Peak"
                    else:  # 00:00-09:00
                        period = "Off_Peak"
                else:  # Sunday
                    period = "Off_Peak"

                # Generate demand based on period
                demand = generate_random_demand(period, peak_value, max_demand_limits, is_low_demand)

                # Calculate energy (kWh) for this 15-minute interval
                energy_kWh = demand * (15 / 60)  # 15 minutes = 0.25 hours

                # Update statistics based on period
                if period == "Peak":
                    total_peak_demand += demand
                    total_peak_energy += energy_kWh
                    max_peak_demand = max(max_peak_demand, demand)
                elif period == "Half_Peak":
                    total_half_peak_demand += demand
                    total_half_peak_energy += energy_kWh
                    max_half_peak_demand = max(max_half_peak_demand, demand)
                elif period == "Saturday_Half_Peak":
                    total_saturday_half_peak_demand += demand
                    total_saturday_half_peak_energy += energy_kWh
                    max_saturday_half_peak_demand = max(max_saturday_half_peak_demand, demand)
                else:  # Off_Peak
                    total_off_peak_demand += demand
                    total_off_peak_energy += energy_kWh
                    max_off_peak_demand = max(max_off_peak_demand, demand)

                entry = {
                    "meter_no": METER_NO,
                    "date": record_date.strftime("%Y-%m-%d"),
                    "weekday": weekday,
                    "time": record_time,
                    "demand_kW": demand,
                    "period": period  # Add period to the data for reference
                }
                data.append(entry)

    # 平滑處理
    to_do = []
    for i in data:
        to_do.append(i["demand_kW"])   
    smoothed_demand = moving_average(to_do, window_size=5)
    for i in range(len(data)):
        data[i]["demand_kW"] = smoothed_demand[i]

    peak_values = {f"{year}-{month:02d}-{start_day:02d} {peak_time}": peak_value}
    enforce_peak_values(data, peak_values)

    return data

def classify_day_of_week(year, month, day):
    """
    Classify the given date as 'Weekday', 'Saturday', or 'Sunday'.
    
    Parameters:
        year (int): Year
        month (int): Month
        day (int): Day
    
    Returns:
        str: 'Weekday', 'Saturday', or 'Sunday'
    """
    record_date = datetime(year, month, day)
    weekday = record_date.weekday()
    if weekday < 5:  # Monday (0) to Friday (4)
        return "Weekday"
    elif weekday == 5:  # Saturday
        return "Saturday"
    else:  # Sunday
        return "Sunday"

def calculate_basic_charge(contract_capacity, year=2024, month=4, day=12):
    is_summer = (month > 5 or (month == 5 and day >= 16)) and (month < 10 or (month == 10 and day <= 15))
    season = "Summer" if is_summer else "Non_Summer"
    
    day_type = classify_day_of_week(year, month, day)
    
    if season == "Summer":
        if day_type == "Weekday":
            rate = BASIC_CHARGE_RATES[season]["Contract"]
        elif day_type == "Saturday":
            rate = BASIC_CHARGE_RATES[season]["Sat_Half_Peak"]
        else:  # Sunday
            rate = BASIC_CHARGE_RATES[season]["Off_Peak"]
    else:
        if day_type == "Weekday":
            rate = BASIC_CHARGE_RATES[season]["Half_Peak"]
        elif day_type == "Saturday":
            rate = BASIC_CHARGE_RATES[season]["Sat_Half_Peak"]
        else:  # Sunday
            rate = BASIC_CHARGE_RATES[season]["Off_Peak"]
    
    # Note: The /1000 seems incorrect based on the table (rates are per kW, not MW)
    basic_charge = contract_capacity * rate  # Removed /1000
    return round(basic_charge, 2)

def calculate_energy_charge(data, year, month, day):
    """
    Calculate the energy charge for a day's demand data based on time-of-use rates.
    
    Parameters:
        data (list): List of demand data entries
        year (int): Year
        month (int): Month
        day (int): Day
    
    Returns:
        float: Total energy charge (NTD)
    """
    is_summer = (month > 5 or (month == 5 and day >= 16)) and (month < 10 or (month == 10 and day <= 15))
    season = "Summer" if is_summer else "Non_Summer"
    
    day_type = classify_day_of_week(year, month, day)
    
    total_energy_charge = 0.0
    
    for entry in data:
        time_str = entry["time"]
        hour, minute = map(int, time_str.split(":"))
        time_minutes = hour * 60 + minute
        
        rates = ENERGY_RATES[season][day_type]
        
        if day_type == "Weekday":
            if season == "Summer":
                if 16 * 60 <= time_minutes < 22 * 60:  # 16:00-22:00
                    rate = rates["Peak"]
                elif (6 * 60 <= time_minutes < 11 * 60) or (14 * 60 <= time_minutes < 24 * 60):  # 06:00-11:00, 14:00-24:00
                    rate = rates["Half_Peak"]
                else:  # 00:00-09:00, 11:00-14:00
                    rate = rates["Off_Peak"]
            else:  # Non-Summer
                if (6 * 60 <= time_minutes < 11 * 60) or (14 * 60 <= time_minutes < 24 * 60):  # 06:00-11:00, 14:00-24:00
                    rate = rates["Half_Peak"]
                else:  # 00:00-09:00, 11:00-14:00
                    rate = rates["Off_Peak"]
        elif day_type == "Saturday":
            if 6 * 60 <= time_minutes < 24 * 60:  # 06:00-24:00
                rate = rates["Half_Peak"]
            else:  # 00:00-06:00
                rate = rates["Off_Peak"]
        else:  # Sunday
            rate = rates["Off_Peak"]
        
        # Calculate energy (kWh) for this 15-minute interval
        demand_kW = entry["demand_kW"]
        energy_kWh = demand_kW * (15 / 60)  # 15 minutes = 0.25 hours
        
        # Calculate cost for this interval
        cost = energy_kWh * rate
        total_energy_charge += cost
    
    return round(total_energy_charge, 2)

def plot_demand_data(filename, year=2024, month=4):
    """
    從 CSV 檔案讀取需量數據，並為每一天繪製圖表，時段背景顏色與需求曲線對齊。

    參數：
        filename (str): CSV 檔案路徑，例如 "factory_demand_data2024_7.csv"
        year (int): 年份，預設 2024
        month (int): 月份，預設 4
    """
    # 1. 從 CSV 檔案讀取數據
    try:
        with open(filename, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            data = []
            for row in reader:
                # 確保 demand_kW 是浮點數
                row["demand_kW"] = float(row["demand_kW"])
                data.append(row)
    except FileNotFoundError:
        print(f"錯誤：找不到檔案 {filename}")
        return
    except Exception as e:
        print(f"讀取檔案時發生錯誤：{e}")
        return

    # 2. 按日期分組數據
    daily_data = {}
    for entry in data:
        date = entry["date"]
        if date not in daily_data:
            daily_data[date] = []
        daily_data[date].append(entry)

    # 檢查每一天的數據點數量
    for date, entries in daily_data.items():
        if len(entries) != 96:  # 每一天應有 96 個數據點（24 小時 × 4）
            print(f"警告：{date} 的數據點數量為 {len(entries)}，預期為 96，可能數據不完整！")

    # 3. 為每一天繪製圖表
    for date, entries in daily_data.items():
        # 提取該天的時間和需量數據
        times = [entry["time"] for entry in entries]
        demands = [entry["demand_kW"] for entry in entries]
        periods = [entry["period"] for entry in entries]  # 提取時段分類

        # 創建 x 軸數據點
        x = range(len(demands))  # 0 到 95，對應 96 個數據點

        # 繪製折線圖
        fig, ax = plt.subplots(figsize=(12, 6))

        # 追蹤每個時段是否已添加過圖例標籤
        labeled_periods = {
            "Peak": False,
            "Half_Peak": False,
            "Saturday_Half_Peak": False,
            "Off_Peak": False
        }

        # 定義時段顏色對應
        period_color_mapping = {
            "Peak": "orange",
            "Half_Peak": "green",
            "Saturday_Half_Peak": "yellow",
            "Off_Peak": "pink"
        }

        # 動態填充時段背景，確保連續性
        current_period = periods[0]
        start_idx = 0

        for i in range(1, len(periods)):
            if periods[i] != current_period or i == len(periods) - 1:
                end_idx = i + 1 if i != len(periods) - 1 else i + 1
                color = period_color_mapping.get(current_period, "white")
                label = None

                # 設置圖例標籤
                if not labeled_periods[current_period]:
                    label = {
                        "Peak": "尖峰",
                        "Half_Peak": "半尖峰",
                        "Saturday_Half_Peak": "週六半尖峰",
                        "Off_Peak": "離峰"
                    }.get(current_period, "")
                    labeled_periods[current_period] = True

                ax.fill_between(x[start_idx:end_idx], 0, demands[start_idx:end_idx],
                                color=color, alpha=0.3, label=label)

                # 更新起始點和當前時段
                start_idx = i
                current_period = periods[i]

        # 確保最後一段填充完整 (最右邊)
        ax.fill_between(x[start_idx:len(x)], 0, demands[start_idx:len(x)],
                        color=period_color_mapping.get(current_period, 'white'), alpha=0.3)

        # 繪製需求曲線
        ax.plot(x, demands, color='blue', label="需量 (kW)")

        # 標註最高需量點
        max_demand = max(demands)
        max_index = demands.index(max_demand)
        ax.plot(max_index, max_demand, "b^", label=f"最高需量: {max_demand:.0f} kW")
        ax.text(max_index, max_demand, f"{max_demand:.0f} kW", fontsize=9, ha="right", va="bottom")

        # 設置圖表標題和標籤
        day = int(date.split("-")[-1])
        ax.set_title(f"{year} - 年 {month} - 月 {day} - 日")
        ax.set_xlabel("時間 (15 分鐘)")
        ax.set_ylabel("需量 (kW)")

        # 設置 X 軸刻度（從 00:00 到 23:45，顯示每小時）
        ax.set_xticks(range(0, len(times), 4))
        ax.set_xticklabels(times[::4], rotation=45)
        # 設置 X 軸範圍
        ax.set_xlim([0, 95])
        ax.margins(x=0)  # 消除左右邊距

        # 設置 Y 軸刻度範圍
        ax.set_ylim(0, 40000)
        ax.set_yticks(range(0, 45000, 10000))

        # 添加契約容量紅線
        contract_capacity = 38000
        ax.axhline(y=contract_capacity, color='red', linestyle='--', label=f"契約電力: {contract_capacity} kW")
        ax.text(90, contract_capacity + 500, f"契約電力 {contract_capacity} kW", color='red', ha="right")

        # 添加圖例
        ax.legend(loc='upper right')

        # 添加網格
        ax.grid(True)

        # 調整布局
        plt.tight_layout()

        # 保存圖表
        plt.savefig(f"demand_plot_{year}_{month:02d}_{day:02d}.png")
        plt.close()

def moving_average(data, window_size=3):
    smoothed_data = []
    for i in range(len(data)):
        start = max(0, i - window_size // 2)
        end = min(len(data), i + window_size // 2 + 1)
        smoothed_value = sum(data[start:end]) / (end - start)
        smoothed_data.append(round(smoothed_value, 2))  # 保留 2 位小數
    return smoothed_data

def adjust_demand_to_reference(all_data, differences, max_demand_limits):
    """
    根據差值調整 demand_kW，使每個時段的用電度數符合參考值。

    參數：
        all_data (list): 包含整個月數據的列表，每個元素是一個字典，包含 "demand_kW" 和 "period"
        differences (dict): 每個時段的用電度數差值（kWh），例如 {"Peak": 80720, "Half_Peak": 62880, ...}
        max_demand_limits (dict): 每個時段的最大需量限制，例如 {"Peak": 40000, ...}

    返回：
        tuple: (調整後的 all_data, 調整後的 monthly_stats)
    """
    # 計算每個時段的數據點數量
    period_counts = {
        "Peak": 0,
        "Half_Peak": 0,
        "Saturday_Half_Peak": 0,
        "Off_Peak": 0
    }
    for entry in all_data:
        period = entry["period"]
        period_counts[period] += 1

    # 調整 demand_kW
    for entry in all_data:
        period = entry["period"]
        if period in differences and period_counts[period] > 0:
            # 計算每個數據點需要調整的能量（kWh）
            energy_adjustment_per_point = differences[period] / period_counts[period]
            # 轉換為 demand_kW 調整量
            # 每個數據點的能量（kWh） = demand_kW × (15 / 60)
            # 因此，demand_kW 調整量 = 能量調整量 ÷ (15 / 60)
            demand_adjustment = energy_adjustment_per_point / (15 / 60)
            entry["demand_kW"] += demand_adjustment
            # 確保 demand_kW 在合理範圍內
            max_demand_limit = max_demand_limits[period]
            entry["demand_kW"] = max(0, min(max_demand_limit, round(entry["demand_kW"])))

    # 重新計算 monthly_stats
    monthly_stats = {
        "max_peak_demand": 0,
        "max_off_peak_demand": 0,
        "max_half_peak_demand": 0,
        "max_saturday_half_peak_demand": 0,
        "total_peak_demand": 0,
        "total_off_peak_demand": 0,
        "total_half_peak_demand": 0,
        "total_saturday_half_peak_demand": 0,
        "total_demand":0,
        "total_energy": 0,
        "total_peak_energy": 0,
        "total_off_peak_energy": 0,
        "total_half_peak_energy": 0,
        "total_saturday_half_peak_energy": 0
    }

    for entry in all_data:
        demand = entry["demand_kW"]
        energy_kWh = demand * (15 / 60)  # 15 minutes = 0.25 hours
        period = entry["period"]

        if period == "Peak":
            monthly_stats["total_peak_demand"] += demand
            monthly_stats["total_peak_energy"] += energy_kWh
            monthly_stats["max_peak_demand"] = max(monthly_stats["max_peak_demand"], demand)
        elif period == "Half_Peak":
            monthly_stats["total_half_peak_demand"] += demand
            monthly_stats["total_half_peak_energy"] += energy_kWh
            monthly_stats["max_half_peak_demand"] = max(monthly_stats["max_half_peak_demand"], demand)
        elif period == "Saturday_Half_Peak":
            monthly_stats["total_saturday_half_peak_demand"] += demand
            monthly_stats["total_saturday_half_peak_energy"] += energy_kWh
            monthly_stats["max_saturday_half_peak_demand"] = max(monthly_stats["max_saturday_half_peak_demand"], demand)
        else:  # Off_Peak
            monthly_stats["total_off_peak_demand"] += demand
            monthly_stats["total_off_peak_energy"] += energy_kWh
            monthly_stats["max_off_peak_demand"] = max(monthly_stats["max_off_peak_demand"], demand)

    # 計算總能量
    monthly_stats["total_energy"] = (
        monthly_stats["total_peak_energy"] +
        monthly_stats["total_half_peak_energy"] +
        monthly_stats["total_off_peak_energy"] +
        monthly_stats["total_saturday_half_peak_energy"]
    )
    monthly_stats["total_demand"] = (
        monthly_stats["total_peak_demand"] +
        monthly_stats["total_half_peak_demand"] +
        monthly_stats["total_off_peak_demand"] +
        monthly_stats["total_saturday_half_peak_demand"]
    )

    return all_data, monthly_stats

# 1. 讀取 CSV 檔案並統計各時段數據點數量
def read_and_count_periods(filename):
    all_data = []
    period_counts = {
        "Peak": 0,
        "Half_Peak": 0,
        "Saturday_Half_Peak": 0,
        "Off_Peak": 0
    }

    with open(filename, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            all_data.append(row)
            period = row["period"]
            period_counts[period] += 1

    return all_data, period_counts

def adjust_demand(all_data, period_counts, differences, max_demand_limits):
    """
    簡單調整 demand_kW，將各時段的總需量差值（kW）平均分配到數據點。

    參數：
        all_data (list): 包含需求數據的列表
        period_counts (dict): 每個時段的數據點數
        differences (dict): 每個時段的總需量差值（kW）
        max_demand_limits (dict): 每個時段的最大需量限制（kW）

    返回：
        list: 調整後的 all_data
    """
    for entry in all_data:
        period = entry["period"]
        if period in differences and period_counts[period] > 0:
            # 計算每個數據點的調整量（kW）
            demand_adjustment = differences[period] / period_counts[period]
            # 調整 demand_kW（差值正則減，負則加）
            new_demand = float(entry["demand_kW"]) - demand_adjustment  # 注意：減去差值，因為正差表示需減少
            max_demand_limit = max_demand_limits[period]
            # 限制在 [0, max_demand_limit] 範圍內
            entry["demand_kW"] = round(max(0, min(max_demand_limit, new_demand)), 2)

    return all_data
# 3. 確保 PEAK_VALUES 的指定值
def enforce_peak_values(all_data, peak_values):
    for time_str, peak_value in peak_values.items():
        # 解析時間字串，例如 "2024-07-01 23:45"
        date, time = time_str.split(" ")
        for entry in all_data:
            if entry["date"] == date and entry["time"] == time:
                entry["demand_kW"] = round(float(peak_value), 2)
                break

# 4. 寫回 CSV 檔案
def write_to_csv(filename, new_data):
    """
    確保每個時間點的數據只出現一次，若時間點已存在則更新數據。
    """
    file_exists = os.path.exists(filename)
    fieldnames = ["meter_no", "date", "weekday", "time", "demand_kW", "period"]

    # **1. 讀取現有數據**，確保唯一性
    existing_data = {}
    if file_exists:
        with open(filename, "r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                key = (row["meter_no"], row["date"], row["time"])  # 以 (電表編號, 日期, 時間) 作為唯一鍵
                existing_data[key] = row

    # **2. 合併新數據**
    for entry in new_data:
        key = (entry["meter_no"], entry["date"], entry["time"])
        entry["demand_kW"] = round(float(entry["demand_kW"]), 2)  # 確保格式一致
        existing_data[key] = entry  # 如果時間點已存在，則更新數據

    # **3. 寫回去 CSV（覆寫）**
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing_data.values())  # 只寫入最新的數據

# 主調整流程
def adjust_demand_from_csv(filename, differences, max_demand_limits, peak_values):
    # 1. 讀取並統計
    all_data, period_counts = read_and_count_periods(filename)

    # 2. 調整 demand_kW
    all_data = adjust_demand(all_data, period_counts, differences, max_demand_limits)

    # 3. 確保 PEAK_VALUES 的指定值
    enforce_peak_values(all_data, peak_values)

    # 4. 寫回 CSV
    write_to_csv(filename, all_data)

def calculate_monthly_stats_from_csv(filename, year, month):
    """
    從 CSV 檔案讀取數據，統計指定月份的需量和用電度數數據。

    參數：
        filename (str): CSV 檔案路徑，例如 "factory_demand_data2024_7.csv"
        year (int): 要統計的年份，例如 2024
        month (int): 要統計的月份，例如 7

    返回：
        dict: 包含各時段統計數據的字典
    """
    # 初始化統計數據
    monthly_stats = {
        "max_peak_demand": 0,
        "max_off_peak_demand": 0,
        "max_half_peak_demand": 0,
        "max_saturday_half_peak_demand": 0,
        "total_peak_demand": 0,
        "total_off_peak_demand": 0,
        "total_half_peak_demand": 0,
        "total_saturday_half_peak_demand": 0,
        "total_energy": 0,  # 月總用電度數 (kWh)
        "total_peak_energy": 0,
        "total_off_peak_energy": 0,
        "total_half_peak_energy": 0,
        "total_saturday_half_peak_energy": 0
    }

    try:
        with open(filename, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                # 解析日期並過濾指定年月
                record_date = datetime.strptime(row["date"], "%Y-%m-%d")
                if record_date.year != year or record_date.month != month:
                    continue  # 跳過不屬於指定月份的數據

                # 提取需量並轉換為浮點數
                demand = float(row["demand_kW"])
                period = row["period"]

                # 計算用電度數（kWh），假設每筆數據為 15 分鐘間隔
                energy_kWh = demand * (15 / 60) # 15 分鐘 = 0.25 小時

                # 根據時段更新統計數據
                if period == "Peak":
                    monthly_stats["max_peak_demand"] = max(monthly_stats["max_peak_demand"], demand)
                    monthly_stats["total_peak_demand"] += demand
                    monthly_stats["total_peak_energy"] += energy_kWh
                elif period == "Half_Peak":
                    monthly_stats["max_half_peak_demand"] = max(monthly_stats["max_half_peak_demand"], demand)
                    monthly_stats["total_half_peak_demand"] += demand
                    monthly_stats["total_half_peak_energy"] += energy_kWh
                elif period == "Saturday_Half_Peak":
                    monthly_stats["max_saturday_half_peak_demand"] = max(monthly_stats["max_saturday_half_peak_demand"], demand)
                    monthly_stats["total_saturday_half_peak_demand"] += demand
                    monthly_stats["total_saturday_half_peak_energy"] += energy_kWh
                else:  # Off_Peak
                    monthly_stats["max_off_peak_demand"] = max(monthly_stats["max_off_peak_demand"], demand)
                    monthly_stats["total_off_peak_demand"] += demand
                    monthly_stats["total_off_peak_energy"] += energy_kWh

        # 計算總用電度數
        monthly_stats["total_energy"] = (
            monthly_stats["total_peak_energy"] +
            monthly_stats["total_half_peak_energy"] +
            monthly_stats["total_saturday_half_peak_energy"] +
            monthly_stats["total_off_peak_energy"]
        )

        monthly_stats["total_demand"] = (
            monthly_stats["total_peak_demand"] +
            monthly_stats["total_half_peak_demand"] +
            monthly_stats["total_off_peak_demand"] +
            monthly_stats["total_saturday_half_peak_demand"]
        )
        for key in monthly_stats:
            monthly_stats[key] = round(monthly_stats[key], 2)

    except FileNotFoundError:
        print(f"錯誤：找不到檔案 {filename}")
    except Exception as e:
        print(f"讀取檔案時發生錯誤：{e}")

    return monthly_stats

# 主程序
def main():
    # 處理 4 月、5 月和 7 月
    for month in [4, 5, 7]:
        PEAK_VALUES = PEAK_VALUES_DICT[month]
        REFERENCE_TOTAL_DEMANDS = REFERENCE_TOTAL_DEMANDS_DICT[month]

        # 遍歷該月的 PEAK_VALUES
        for time, value in PEAK_VALUES.items():
            dt = datetime.strptime(time, "%Y-%m-%d %H:%M")
            year = dt.year
            month = dt.month
            day = dt.day
            hour = dt.hour
            minute = dt.minute
            peak_time = f"{hour:02d}:{minute:02d}"

            # 生成整個月數據
            days_in_month = MONTHS.get(month, 31)
            all_month_data = generate_daily_demand_data(
                year=year,
                month=month,
                start_day=1,
                end_day=days_in_month,
                peak_time=peak_time,
                peak_value=value
            )

            filename = f"factory_demand_data{year}_{month}.csv"
            write_to_csv(filename, all_month_data)

        print(f"數據已保存到 {filename}")

        monthly_stats = calculate_monthly_stats_from_csv(filename, year, month)
        differences = compare_energy_with_reference(monthly_stats, REFERENCE_TOTAL_DEMANDS, year, month)
        max_demand_limits = MAX_DEMAND_LIMITS_DICT[month]
        adjust_demand_from_csv(filename, differences, max_demand_limits, PEAK_VALUES)
        monthly_stats = calculate_monthly_stats_from_csv(filename, year, month)
        differences = compare_energy_with_reference(monthly_stats, REFERENCE_TOTAL_DEMANDS, year, month)
        plot_demand_data(filename, year, month)

if __name__ == "__main__":
    main()