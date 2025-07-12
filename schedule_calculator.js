// Этот файл должен быть загружен по адресу:
// https://raw.githubusercontent.com/Dzmitry1087/Dzmitry1087/refs/heads/main/schedule_calculator.js

function calculateSchedule(originalSchedule, timeDiff, errorCoeff) {
    const newSchedule = {};
    
    for (const [hour, minutes] of Object.entries(originalSchedule)) {
        const newMinutes = [];
        
        for (const minute of minutes.split(' ')) {
            let m = parseInt(minute, 10);
            m += Math.round(timeDiff * (1 + errorCoeff));
            
            // Игнорируем минуты, которые выходят за пределы часа
            if (m >= 0 && m < 60) {
                newMinutes.push(m.toString().padStart(2, '0'));
            }
        }
        
        if (newMinutes.length > 0) {
            newSchedule[hour] = newMinutes.join(' ');
        }
    }
    
    return newSchedule;
}

function calculateScheduleForStop(params) {
    const {
        originalWeekdays,
        originalWeekends,
        currentStopId,
        newStopId,
        transportType,
        transportNumber,
        weekdayErrorCoeff,
        weekendErrorCoeff,
        stopsData
    } = params;
    
    // Находим текущую и новую остановку
    const currentStop = stopsData.stops.find(s => s.id == currentStopId);
    const newStop = stopsData.stops.find(s => s.id == newStopId);
    
    if (!currentStop || !newStop || currentStop.direction !== newStop.direction) {
        return null;
    }
    
    const direction = currentStop.direction;
    const stopsInDirection = stopsData.stops.filter(s => s.direction === direction);
    
    const currentIndex = stopsInDirection.findIndex(s => s.id == currentStopId);
    const newIndex = stopsInDirection.findIndex(s => s.id == newStopId);
    
    if (currentIndex === -1 || newIndex === -1) {
        return null;
    }
    
    // Рассчитываем время перемещения между остановками
    const timeDiff = Math.abs(newIndex - currentIndex) * 2; // Примерное время между остановками
    
    // Рассчитываем новое расписание
    const newWeekdays = calculateSchedule(originalWeekdays, timeDiff, weekdayErrorCoeff);
    const newWeekends = calculateSchedule(originalWeekends, timeDiff, weekendErrorCoeff);
    
    return {
        weekdays: newWeekdays,
        weekends: newWeekends
    };
}

// Экспортируем функции для использования в других скриптах
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        calculateSchedule,
        calculateScheduleForStop
    };
}