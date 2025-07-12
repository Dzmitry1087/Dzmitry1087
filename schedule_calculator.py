import json
from collections import defaultdict

class ScheduleCalculator:
    def __init__(self):
        self.weekday_error_coeffs = {
            5: 0.01,    # 5:00 - коэффициент 1%
            6: 0.01,
            7: 0.015,   # 7:00 - коэффициент 1.5% (час пик)
            8: 0.015,
            9: 0.01,
            10: 0.01,
            11: 0.01,
            12: 0.01,
            13: 0.01,
            14: 0.01,
            15: 0.01,
            16: 0.015,  # 16:00 - час пик
            17: 0.015,
            18: 0.01,
            19: 0.01,
            20: 0.01,
            21: 0.01,
            22: 0.01,
            23: 0.01,
            0: 0.01     # 00:00
        }
        
        self.weekend_error_coeffs = {
            5: 0.015,   # 5:00 - коэффициент 1.5%
            6: 0.015,
            7: 0.015,
            8: 0.015,
            9: 0.015,
            10: 0.015,
            11: 0.015,
            12: 0.015,
            13: 0.015,
            14: 0.015,
            15: 0.015,
            16: 0.015,
            17: 0.015,
            18: 0.015,
            19: 0.015,
            20: 0.015,
            21: 0.015,
            22: 0.015,
            23: 0.015,
            0: 0.015    # 00:00
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
                    self.weekday_error_coeffs = settings['weekday_error_coeffs']
                if 'weekend_error_coeffs' in settings:
                    self.weekend_error_coeffs = settings['weekend_error_coeffs']
        except Exception as e:
            print(f"Ошибка загрузки настроек калькулятора: {e}")
    
    def calculate_time_with_carryover(self, hour, minute, time_diff):
        """Рассчитывает время с переносом минут на следующий час"""
        new_minute = minute + time_diff
        
        # Переносим избыточные минуты на следующий час
        if new_minute >= 60:
            hour += 1
            new_minute -= 60
        elif new_minute < 0:
            hour -= 1
            new_minute += 60
        
        return hour, new_minute
    
    def calculate_schedule_for_stop(self, tab, new_stop_id, transport_cache):
        """Рассчитывает расписание для новой остановки на основе загруженного"""
        if not tab.original_schedule["weekdays"] or not tab.original_schedule["weekends"]:
            return False
        
        transport_number = tab.number_var.get()
        transport_type = tab.transport_type if tab.transport_type else tab.app.transport_type.get()
        
        # Получаем данные о маршруте
        route_data = transport_cache.get(f"{transport_type}_{transport_number}")
        if not route_data:
            return False
        
        # Находим текущую и новую остановку
        current_stop = None
        new_stop = None
        stops = route_data.get("stops", [])
        
        for stop in stops:
            if str(stop.get("id")) == tab.current_stop_id:
                current_stop = stop
            if str(stop.get("id")) == new_stop_id:
                new_stop = stop
        
        if not current_stop or not new_stop or current_stop.get("direction") != new_stop.get("direction"):
            return False
        
        direction = current_stop.get("direction")
        stops_in_direction = [s for s in stops if s.get("direction") == direction]
        
        # Находим позиции остановок в маршруте
        current_index = next((i for i, s in enumerate(stops_in_direction) if str(s.get("id")) == tab.current_stop_id), None)
        new_index = next((i for i, s in enumerate(stops_in_direction) if str(s.get("id")) == new_stop_id), None)
        
        if current_index is None or new_index is None:
            return False
        
        # Рассчитываем время перемещения между остановками
        time_diff = 0
        if new_index > current_index:
            # Движение вперед по маршруту
            for i in range(current_index, new_index):
                stop_id = stops_in_direction[i].get("id")
                interval = self.get_interval_for_stop(transport_type, transport_number, stop_id, transport_cache)
                time_diff += interval
        else:
            # Движение назад по маршруту
            for i in range(new_index, current_index):
                stop_id = stops_in_direction[i].get("id")
                interval = self.get_interval_for_stop(transport_type, transport_number, stop_id, transport_cache)
                time_diff += interval
        
        # Рассчитываем новое расписание (не изменяя исходное)
        new_weekdays = {}
        new_weekends = {}
        
        def calculate_new_times(hour, minutes_str, time_diff, error_coeffs):
            new_minutes_dict = defaultdict(list)
            for minute in minutes_str.split():
                try:
                    m = int(minute)
                    # Получаем коэффициент погрешности для текущего часа
                    coeff = error_coeffs.get(hour, 0.01)
                    adjusted_time_diff = int(time_diff * (1 + coeff))
                    new_hour, new_min = self.calculate_time_with_carryover(hour, m, adjusted_time_diff)
                    new_minutes_dict[new_hour].append(f"{new_min:02d}")
                except ValueError:
                    continue
            
            # Сортируем минуты по возрастанию и объединяем в строку
            result = {}
            for h in sorted(new_minutes_dict.keys()):
                sorted_minutes = sorted(new_minutes_dict[h], key=lambda x: int(x))
                result[h] = ' '.join(sorted_minutes)
            
            return result
        
        # Обрабатываем будние дни
        temp_weekdays = {}
        for hour, minutes in tab.original_schedule["weekdays"].items():
            calculated = calculate_new_times(hour, minutes, time_diff, self.weekday_error_coeffs)
            for h, m in calculated.items():
                if h in temp_weekdays:
                    temp_weekdays[h] += ' ' + m
                else:
                    temp_weekdays[h] = m
        
        # Объединяем и сортируем минуты для каждого часа
        for hour in sorted(temp_weekdays.keys()):
            minutes_list = sorted(list(set(temp_weekdays[hour].split())), key=lambda x: int(x))
            new_weekdays[hour] = ' '.join(minutes_list)
        
        # Обрабатываем выходные дни
        temp_weekends = {}
        for hour, minutes in tab.original_schedule["weekends"].items():
            calculated = calculate_new_times(hour, minutes, time_diff, self.weekend_error_coeffs)
            for h, m in calculated.items():
                if h in temp_weekends:
                    temp_weekends[h] += ' ' + m
                else:
                    temp_weekends[h] = m
        
        # Объединяем и сортируем минуты для каждого часа
        for hour in sorted(temp_weekends.keys()):
            minutes_list = sorted(list(set(temp_weekends[hour].split())), key=lambda x: int(x))
            new_weekends[hour] = ' '.join(minutes_list)
        
        # Обновляем поля в интерфейсе
        for hour in range(5, 24):
            if hour in new_weekdays:
                tab.weekdays[hour-5].delete(0, tk.END)
                tab.weekdays[hour-5].insert(0, new_weekdays[hour])
            else:
                tab.weekdays[hour-5].delete(0, tk.END)
            
            if hour in new_weekends:
                tab.weekends[hour-5].delete(0, tk.END)
                tab.weekends[hour-5].insert(0, new_weekends[hour])
            else:
                tab.weekends[hour-5].delete(0, tk.END)
        
        if 0 in new_weekdays:
            tab.weekdays[19].delete(0, tk.END)
            tab.weekdays[19].insert(0, new_weekdays[0])
        else:
            tab.weekdays[19].delete(0, tk.END)
        
        if 0 in new_weekends:
            tab.weekends[19].delete(0, tk.END)
            tab.weekends[19].insert(0, new_weekends[0])
        else:
            tab.weekends[19].delete(0, tk.END)
        
        # Сохраняем рассчитанное расписание
        tab.calculated_schedule = {
            "weekdays": new_weekdays.copy(),
            "weekends": new_weekends.copy()
        }
        
        return True
    
    def get_interval_for_stop(self, transport_type, transport_number, stop_id, transport_cache):
        """Получает интервал между остановками из базы данных"""
        try:
            stop_key = f"{transport_type}_{transport_number}_{stop_id}"
            stop_data = transport_cache.get(stop_key)
            if stop_data and isinstance(stop_data, dict):
                interval = stop_data.get("interval_to_next", 2)
                return max(1, min(interval, 5))  # Ограничиваем интервал разумными пределами
            return 2  # Значение по умолчанию, если данные не найдены
        except:
            return 2