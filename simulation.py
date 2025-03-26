import random
import matplotlib.pyplot as plt
from datetime import datetime
import csv
import os

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
PEAK_VALUES = config["PEAK_VALUES"]
MAX_DEMAND_LIMITS = config["MAX_DEMAND_LIMITS"]

LOW_DEMAND_START = config["LOW_DEMAND_START"]
LOW_DEMAND_END = config["LOW_DEMAND_END"]
LOW_DEMAND_RANGE = config["LOW_DEMAND_RANGE"]



def time_to_minutes(time_str):
    hour, minute = map(int, time_str.split(":"))
    return hour * 60 + minute

def generate_random_demand(period, peak_value, is_low_demand=False):
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
    max_demand_limit = MAX_DEMAND_LIMITS[period]

    # 根據時段設置隨機範圍
    if is_low_demand:
        # 低需求時段使用 LOW_DEMAND_RANGE，但不超過 peak_value 和時段限制
        upper_bound = min(LOW_DEMAND_RANGE[1], peak_value, max_demand_limit)
        lower_bound = min(LOW_DEMAND_RANGE[0], peak_value, max_demand_limit)
    else:
        # 根據時段調整範圍
        if period == "Peak":
            # 尖峰時段：接近 peak_value，但不超過時段限制
            lower_bound = min(BASE_DEMAND_RANGE[0] * 0.9, peak_value, max_demand_limit)
            upper_bound = min(BASE_DEMAND_RANGE[1], peak_value, max_demand_limit)
        elif period == "Half_Peak":
            # 半尖峰時段：中等範圍
            lower_bound = min(BASE_DEMAND_RANGE[0] * 0.7, peak_value, max_demand_limit)
            upper_bound = min(BASE_DEMAND_RANGE[1] * 0.9, peak_value, max_demand_limit)
        elif period == "Saturday_Half_Peak":
            # 週六半尖峰：略低於半尖峰
            lower_bound = min(BASE_DEMAND_RANGE[0] * 0.6, peak_value, max_demand_limit)
            upper_bound = min(BASE_DEMAND_RANGE[1] * 0.8, peak_value, max_demand_limit)
        else:  # Off_Peak
            # 離峰時段：最低範圍
            lower_bound = min(BASE_DEMAND_RANGE[0] * 0.5, peak_value, max_demand_limit)
            upper_bound = min(BASE_DEMAND_RANGE[1] * 0.7, peak_value, max_demand_limit)

    # 確保下限不超過上限
    lower_bound = min(lower_bound, upper_bound)
    demand = random.uniform(lower_bound, upper_bound)
    return round(demand)

def generate_daily_demand_data(year=2024, month=4, start_day=1, end_day=None, peak_time=None, peak_value=None):
    """
    生成指定日期範圍的需量數據，允許設定特定時間的峰值需量，並計算各時段的最大需量和總需量（kW 和 kWh）。
    確保隨機生成的需求量不超過當日的 peak_value。

    參數：
        year (int): 年份，預設 2024
        month (int): 月份，預設 4
        start_day (int): 起始日期，預設 1
        end_day (int): 結束日期，若為 None 則預設為該月最後一天
        peak_time (str): 指定的高峰時間，例如 "12:30"
        peak_value (float): 指定的高峰發電量 (kW)

    返回：
        tuple: (list: 生成的需量數據, dict: 各時段的最大需量和總需量/總能量)
    """
    # Initialize totals and maximums
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
                if record_time == peak_time:
                    demand = peak_value
                    print(f"Setting peak demand at {record_time} to {demand} kW")
                else:
                    demand = generate_random_demand(period, peak_value, is_low_demand)

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

    # Compile statistics
    stats = {
        "max_peak_demand": max_peak_demand,
        "max_off_peak_demand": max_off_peak_demand,
        "max_half_peak_demand": max_half_peak_demand,
        "max_saturday_half_peak_demand": max_saturday_half_peak_demand,
        "total_peak_demand": total_peak_demand,
        "total_off_peak_demand": total_off_peak_demand,
        "total_half_peak_demand": total_half_peak_demand,
        "total_saturday_half_peak_demand": total_saturday_half_peak_demand,
        "total_peak_energy": round(total_peak_energy, 2),
        "total_off_peak_energy": round(total_off_peak_energy, 2),
        "total_half_peak_energy": round(total_half_peak_energy, 2),
        "total_saturday_half_peak_energy": round(total_saturday_half_peak_energy, 2),
        "total_energy": round(total_peak_energy + total_off_peak_energy + total_half_peak_energy + total_saturday_half_peak_energy, 2)
    }

    return data, stats

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

def plot_demand_data(data, year=2024, month=4):
    """
    繪製需量數據圖表，每一天生成一張圖，時段背景顏色與需求曲線對齊。
    參數：
        data (list): 需量數據
        year (int): 年份，預設 2024
        month (int): 月份，預設 4
    """
    # 按日期分組數據
    daily_data = {}
    for entry in data:
        date = entry["date"]
        if date not in daily_data:
            daily_data[date] = []
        daily_data[date].append(entry)
    
    # 為每一天繪製圖表
    for date, entries in daily_data.items():
        # 提取該天的時間和需量數據
        times = [entry["time"] for entry in entries]
        demands = [entry["demand_kW"] for entry in entries]
        periods = [entry["period"] for entry in entries]  # 提取時段分類
        
        # 創建 x 軸數據點
        x = range(len(demands))  # 0 到 95，對應 96 個數據點
        
        # 繪製折線圖
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 動態填充時段背景，確保連續性
        current_period = periods[0]
        start_idx = 0

        for i in range(1, len(periods)):
            if periods[i] != current_period or i == len(periods) - 1:
                end_idx = i if i != len(periods) - 1 else i + 1
                # 根據時段類型填充背景
                if current_period == "Peak":
                    ax.fill_between(x[start_idx:end_idx], 0, demands[start_idx:end_idx], 
                                    color='orange', alpha=0.3, label='尖峰' if start_idx == 0 else "")
                elif current_period == "Half_Peak":
                    ax.fill_between(x[start_idx:end_idx], 0, demands[start_idx:end_idx], 
                                    color='green', alpha=0.3, label='半尖峰' if start_idx == 0 else "")
                elif current_period == "Saturday_Half_Peak":
                    ax.fill_between(x[start_idx:end_idx], 0, demands[start_idx:end_idx], 
                                    color='yellow', alpha=0.3, label='週六半尖峰' if start_idx == 0 else "")
                elif current_period == "Off_Peak":
                    ax.fill_between(x[start_idx:end_idx], 0, demands[start_idx:end_idx], 
                                    color='pink', alpha=0.3, label='離峰' if start_idx == 0 else "")
                # 更新起始點和當前時段
                start_idx = i
                current_period = periods[i]
        
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
        
# 主程序
def main():
    # 用於儲存整個月份的統計數據
    monthly_stats = {
        "max_peak_demand": 0,
        "max_off_peak_demand": 0,
        "max_half_peak_demand": 0,
        "max_saturday_half_peak_demand": 0,
        "total_peak_demand": 0,
        "total_off_peak_demand": 0,
        "total_half_peak_demand": 0,
        "total_saturday_half_peak_demand": 0
    }

    # 用於儲存最後一天的日期資訊（僅用於打印）
    last_year, last_month, last_day = None, None, None

    # 遍歷 PEAK_VALUES 中的所有日期
    for time, value in PEAK_VALUES.items():
        dt = datetime.strptime(time, "%Y-%m-%d %H:%M")
        year = dt.year
        month = dt.month
        day = dt.day
        hour = dt.hour
        minute = dt.minute
        peak_time = f"{hour:02d}:{minute:02d}"

        # 更新最後一天的日期資訊
        last_year, last_month, last_day = year, month, day

        # 生成單日數據
        single_day_data, stats = generate_daily_demand_data(
            year=year, 
            month=month, 
            start_day=day, 
            end_day=day,
            peak_time=peak_time,
            peak_value=value
        )

        # 繪圖
        plot_demand_data(single_day_data, 2024, 7)

        # 計算基本電費（契約容量為 38000 kW）
        contract_capacity = 38000
        basic_charge = calculate_basic_charge(contract_capacity, year=2024, month=4, day=12)
        energy_charge = calculate_energy_charge(single_day_data, year, month, day)
        print(f"Basic Charge  ({year}-{month:02d}-{day:02d}): {basic_charge} NTD")
        print(f"Energy Charge ({year}-{month:02d}-{day:02d}): {energy_charge} NTD")
        total_charge = basic_charge + energy_charge
        print(f"Total Charge  ({year}-{month:02d}-{day:02d}): {total_charge} NTD")

        # 將數據保存到 CSV 檔案
        filename = f"factory_demand_data{year}_{month}.csv"  # 修正檔案名稱格式
        file_exists = os.path.exists(filename)
        
        with open(filename, "a+", newline="", encoding="utf-8") as file:
            fieldnames = ["meter_no", "date", "weekday", "time", "demand_kW", "period"]
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()

            # 追加寫入數據
            writer.writerows(single_day_data)
        print(f"數據已保存到 {filename}")

        # 更新整個月份的統計數據
        monthly_stats["max_peak_demand"] = max(monthly_stats["max_peak_demand"], stats["max_peak_demand"])
        monthly_stats["max_off_peak_demand"] = max(monthly_stats["max_off_peak_demand"], stats["max_off_peak_demand"])
        monthly_stats["max_half_peak_demand"] = max(monthly_stats["max_half_peak_demand"], stats["max_half_peak_demand"])
        monthly_stats["max_saturday_half_peak_demand"] = max(monthly_stats["max_saturday_half_peak_demand"], stats["max_saturday_half_peak_demand"])
        monthly_stats["total_peak_demand"] += stats["total_peak_demand"]
        monthly_stats["total_off_peak_demand"] += stats["total_off_peak_demand"]
        monthly_stats["total_half_peak_demand"] += stats["total_half_peak_demand"]
        monthly_stats["total_saturday_half_peak_demand"] += stats["total_saturday_half_peak_demand"]

    # 打印整個月份的統計數據
    print(f"Demand Statistics for {last_year}-{last_month:02d}:")
    print(f"  Max Peak Demand: {monthly_stats['max_peak_demand']} kW")
    print(f"  Max Off-Peak Demand: {monthly_stats['max_off_peak_demand']} kW")
    print(f"  Max Half-Peak Demand: {monthly_stats['max_half_peak_demand']} kW")
    print(f"  Max Saturday Half-Peak Demand: {monthly_stats['max_saturday_half_peak_demand']} kW")
    print(f"  Total Peak Demand: {monthly_stats['total_peak_demand']} kW")
    print(f"  Total Off-Peak Demand: {monthly_stats['total_off_peak_demand']} kW")
    print(f"  Total Half-Peak Demand: {monthly_stats['total_half_peak_demand']} kW")
    print(f"  Total Saturday Half-Peak Demand: {monthly_stats['total_saturday_half_peak_demand']} kW")

if __name__ == "__main__":
    main()