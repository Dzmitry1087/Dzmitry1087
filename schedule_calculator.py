import json
from collections import defaultdict
import requests
import tkinter as tk

class ScheduleCalculator:
    def __init__(self):
        self.weekday_error_coeffs = {h: 0.0 for h in range(24)}
        self.weekend_error_coeffs = {h: 0.0 for h in range(24)}
        self.load_settings()
    
    def load_settings(self):
        """Загружает коэффициенты погрешности из настроек"""
        try:
            settings_url = "https://raw.githubusercontent.com/Dzmitry1087/Dzmitry1087/refs/heads/main/schedule_calculator_settings.json"
            response = requests.get(settings_url)
            if response.status_code == 200:
                settings = response.json()
                for hour_str, coeff in settings.get("weekday_error_coeffs", {}).items():
                    self.weekday_error_coeffs[int(hour_str)] = float(coeff)
                
                for hour_str, coeff in settings.get("weekend_error_coeffs", {}).items():
                    self.weekend_error_coeffs[int(hour_str)] = float(coeff)
            else:
                self.set_default_coeffs()
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")
            self.set_default_coeffs()

    def set_default_coeffs(self):
        """Устанавливает коэффициенты по умолчанию"""
        self.weekday_error_coeffs = {
            5: -1.5, 6: -1.0, 7: -0.5, 8: 0.5, 9: 1.0,
            10: 1.5, 11: 1.0, 12: 0.5, 13: 0.0, 14: -0.5,
            15: 0.0, 16: 0.5, 17: 1.0, 18: 1.5, 19: 2.0,
            20: 1.5, 21: 1.0, 22: 0.5, 23: 0.0, 0: -1.0
        }
        
        self.weekend_error_coeffs = {
            5: -2.0, 6: -1.5, 7: -1.0, 8: -0.5, 9: 0.0,
            10: 0.5, 11: 1.0, 12: 1.5, 13: 1.0, 14: 0.5,
            15: 0.0, 16: -0.5, 17: 0.0, 18: 0.5, 19: 1.0,
            20: 1.5, 21: 1.0, 22: 0.5, 23: 0.0, 0: -0.5
        }

    def calculate_time_with_carryover(self, hour, minute, time_diff, is_weekend=False):
        """Рассчитывает время с учетом коэффициентов погрешности"""
        error_coeff = self.weekend_error_coeffs[hour] if is_weekend else self.weekday_error_coeffs[hour]
        
        corrected_minute = minute + time_diff - 6
        corrected_minute += error_coeff
        
        if corrected_minute >= 60:
            hour += 1
            corrected_minute -= 60
        elif corrected_minute < 0:
            hour -= 1
            corrected_minute += 60
        
        if hour >= 24:
            hour -= 24
        elif hour < 0:
            hour += 24
        
        return hour, max(0, min(59, int(round(corrected_minute))))

    def calculate_schedule_for_stop(self, tab, new_stop_id, transport_cache):
        """Расчет расписания с учетом интервалов между остановками"""
        if not tab.original_schedule["weekdays"] or not tab.original_schedule["weekends"]:
            return False
        
        # Проверяем наличие reference_direction и его совпадение
        reference_direction = getattr(tab, 'reference_direction', None)
        current_direction = getattr(tab, 'current_direction', None)
        
        if reference_direction and current_direction != reference_direction:
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
        
        new_weekdays = self.calculate_new_schedule(tab.original_schedule["weekdays"], time_diff, is_weekend=False)
        new_weekends = self.calculate_new_schedule(tab.original_schedule["weekends"], time_diff, is_weekend=True)
        
        self.update_schedule_in_ui(tab, new_weekdays, new_weekends)
        
        tab.calculated_schedule = {
            "weekdays": new_weekdays.copy(),
            "weekends": new_weekends.copy()
        }
        
        return True
    
    def calculate_new_schedule(self, schedule, time_diff, is_weekend=False):
        """Расчет с учетом коэффициентов погрешности"""
        new_schedule = defaultdict(list)
        
        for hour, minutes_str in schedule.items():
            if not minutes_str:
                continue
                
            for minute in minutes_str.split():
                try:
                    m = int(minute)
                    new_hour, new_min = self.calculate_time_with_carryover(int(hour), m, time_diff, is_weekend)
                    new_schedule[new_hour].append(f"{new_min:02d}")
                except ValueError:
                    continue
        
        result = {}
        for h in sorted(new_schedule.keys()):
            result[h] = ' '.join(sorted(new_schedule[h], key=lambda x: int(x)))
        
        return result
    
    def update_schedule_in_ui(self, tab, weekdays, weekends):
        """Обновление интерфейса"""
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
        
        if 0 in weekends:
            tab.weekends[19].delete(0, tk.END)
            tab.weekends[19].insert(0, weekends[0])
    
    def get_interval_for_stop(self, transport_type, transport_number, stop_id, transport_cache):
        """Получение интервала между остановками"""
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
