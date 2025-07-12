import json
from collections import defaultdict
import requests
import tkinter as tk

class ScheduleCalculator:
    def __init__(self):
        self.weekday_error_coeffs = {
            5: -0.1,    # 5:00 - коррекция -10%
            6: -0.1,
            7: -0.1,
            8: -0.1,
            9: -0.05,
            10: -0.05,
            11: -0.05,
            12: -0.05,
            13: -0.05,
            14: -0.05,
            15: -0.05,
            16: -0.1,   # 16:00 - усиленная коррекция
            17: -0.1,
            18: -0.05,
            19: -0.05,
            20: -0.05,
            21: -0.05,
            22: -0.05,
            23: -0.05,
            0: -0.05
        }
        
        self.weekend_error_coeffs = {
            5: -0.1,
            6: -0.1,
            7: -0.1,
            8: -0.1,
            9: -0.1,
            10: -0.1,
            11: -0.1,
            12: -0.1,
            13: -0.1,
            14: -0.1,
            15: -0.1,
            16: -0.1,
            17: -0.1,
            18: -0.1,
            19: -0.1,
            20: -0.1,
            21: -0.1,
            22: -0.1,
            23: -0.1,
            0: -0.1
        }
        
        self.load_settings()
    
    def load_settings(self):
        """Загружает настройки коэффициентов из интернета"""
        try:
            settings_url = "https://raw.githubusercontent.com/Dzmitry1087/Dzmitry1087/refs/heads/main/schedule_calculator_settings.json"
            response = requests.get(settings_url)
            if response.status_code == 200:
                settings = response.json()
                if 'weekday_error_coeffs' in settings:
                    self.weekday_error_coeffs = {int(k): float(v) for k, v in settings['weekday_error_coeffs'].items()}
                if 'weekend_error_coeffs' in settings:
                    self.weekend_error_coeffs = {int(k): float(v) for k, v in settings['weekend_error_coeffs'].items()}
        except Exception as e:
            print(f"Ошибка загрузки настроек калькулятора: {e}")
    
    def calculate_time_with_carryover(self, hour, minute, time_diff):
        """Рассчитывает время с переносом минут на следующий час"""
        new_minute = minute + time_diff
        
        if new_minute >= 60:
            hour += 1
            new_minute -= 60
        elif new_minute < 0:
            hour -= 1
            new_minute += 60
        
        if hour >= 24:
            hour -= 24
        elif hour < 0:
            hour += 24
        
        return hour, new_minute
    
    def calculate_schedule_for_stop(self, tab, new_stop_id, transport_cache):
        if not tab.original_schedule["weekdays"] or not tab.original_schedule["weekends"]:
            return False
        
        transport_number = tab.number_var.get()
        transport_type = tab.transport_type if tab.transport_type else tab.app.transport_type.get()
        
        route_data = transport_cache.get(f"{transport_type}_{transport_number}")
        if not route_data:
            return False
        
        current_stop = None
        new_stop = None
        stops = route_data.get("stops", [])
        
        for stop in stops:
            if str(stop.get("id")) == tab.current_stop_id:
                current_stop = stop
            if str(stop.get("id")) == new_stop_id:
                new_stop = stop
        
        if not current_stop or not new_stop:
            return False
        
        if current_stop.get("direction") != new_stop.get("direction"):
            return False
        
        direction = current_stop.get("direction")
        stops_in_direction = [s for s in stops if s.get("direction") == direction]
        
        current_index = next((i for i, s in enumerate(stops_in_direction) if str(s.get("id")) == tab.current_stop_id), None)
        new_index = next((i for i, s in enumerate(stops_in_direction) if str(s.get("id")) == new_stop_id), None)
        
        if current_index is None or new_index is None:
            return False
        
        time_diff = 0
        step = 1 if new_index > current_index else -1
        
        for i in range(current_index, new_index, step):
            stop_id = stops_in_direction[i].get("id")
            interval = self.get_interval_for_stop(transport_type, transport_number, stop_id, transport_cache)
            time_diff += interval * step
        
        new_weekdays = self.calculate_new_schedule(tab.original_schedule["weekdays"], time_diff, self.weekday_error_coeffs)
        new_weekends = self.calculate_new_schedule(tab.original_schedule["weekends"], time_diff, self.weekend_error_coeffs)
        
        self.update_schedule_in_ui(tab, new_weekdays, new_weekends)
        
        tab.calculated_schedule = {
            "weekdays": new_weekdays.copy(),
            "weekends": new_weekends.copy()
        }
        
        return True
    
    def calculate_new_schedule(self, schedule, time_diff, error_coeffs):
        new_schedule = defaultdict(list)
        
        for hour, minutes_str in schedule.items():
            if not minutes_str:
                continue
                
            for minute in minutes_str.split():
                try:
                    m = int(minute)
                    coeff = max(-0.5, min(0.5, error_coeffs.get(hour, 0.0)))  # Ограничение от -50% до +50%
                    adjusted_time_diff = int(round(time_diff * (1 + coeff)))
                    
                    # Гарантируем минимальную разницу в 1 минуту
                    if time_diff > 0:
                        adjusted_time_diff = max(1, adjusted_time_diff)
                    else:
                        adjusted_time_diff = min(-1, adjusted_time_diff)
                    
                    new_hour, new_min = self.calculate_time_with_carryover(hour, m, adjusted_time_diff)
                    new_schedule[new_hour].append(f"{new_min:02d}")
                except ValueError:
                    continue
        
        result = {}
        for h in sorted(new_schedule.keys()):
            sorted_minutes = sorted(new_schedule[h], key=lambda x: int(x))
            result[h] = ' '.join(sorted_minutes)
        
        return result
    
    def update_schedule_in_ui(self, tab, weekdays, weekends):
        for hour in range(5, 24):
            idx = hour - 5
            if hour in weekdays:
                tab.weekdays[idx].delete(0, tk.END)
                tab.weekdays[idx].insert(0, weekdays[hour])
            else:
                tab.weekdays[idx].delete(0, tk.END)
            
            if hour in weekends:
                tab.weekends[idx].delete(0, tk.END)
                tab.weekends[idx].insert(0, weekends[hour])
            else:
                tab.weekends[idx].delete(0, tk.END)
        
        if 0 in weekdays:
            tab.weekdays[19].delete(0, tk.END)
            tab.weekdays[19].insert(0, weekdays[0])
        else:
            tab.weekdays[19].delete(0, tk.END)
        
        if 0 in weekends:
            tab.weekends[19].delete(0, tk.END)
            tab.weekends[19].insert(0, weekends[0])
        else:
            tab.weekends[19].delete(0, tk.END)
    
    def get_interval_for_stop(self, transport_type, transport_number, stop_id, transport_cache):
        try:
            route_key = f"{transport_type}_{transport_number}"
            route_data = transport_cache.get(route_key)
            if route_data and isinstance(route_data, dict):
                for stop in route_data.get("stops", []):
                    if str(stop.get("id")) == str(stop_id):
                        return stop.get("interval_to_next", 2)
            return 2
        except:
            return 2
