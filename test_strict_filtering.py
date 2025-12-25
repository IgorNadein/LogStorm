"""
Тест строгой фильтрации по камерам
"""
from services.sqlite_loader import SQLiteLoader
from services.attendance_service import AttendanceService
from services.person_mapper import PersonMapper
from datetime import date
import json

print('=== ТЕСТ СТРОГОЙ ФИЛЬТРАЦИИ ПО КАМЕРАМ ===\n')

# Загружаем конфиг
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
    device_mapping = config.get('device_mapping')

with open('//172.11.1.254/Face_ID/person.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    prefs = data['person_mappings'] if 'person_mappings' in data else data

print(f'Настройка камер:')
print(f'  Приход (вход): {device_mapping["arrival_devices"]}')
print(f'  Уход (выход): {device_mapping["departure_devices"]}\n')

# Загружаем данные с PersonMapper
person_mapper = PersonMapper('//172.11.1.254/Face_ID/person.json')
loader = SQLiteLoader('//172.11.1.254/Face_ID/data/events.db')
df = loader.load_events(
    start_date=date(2025, 12, 24),
    end_date=date(2025, 12, 24),
    person_mapper=person_mapper
)

# Тестируем на person_id=30
test_person_id = '30'
user_events = df[df['name'] == test_person_id].sort_values('timestamp')

if not user_events.empty:
    display_name = user_events.iloc[0]['display_name']
    print(f'События для {display_name}:')
    for idx, row in user_events.iterrows():
        device_name = row.get('_device_name', 'Unknown')
        device = row.get('_device', '?')
        marker = ''
        if device == '192.168.1.101':
            marker = ' <- КАМЕРА ВХОДА'
        elif device == '192.168.1.104':
            marker = ' -> КАМЕРА ВЫХОДА'
        else:
            marker = ' ? ДРУГАЯ КАМЕРА'
        print(f'  {row["timestamp"].time()} - {device_name}{marker}')
    
    # Анализ БЕЗ фильтрации
    print(f'\nБЕЗ фильтрации (все события):')
    service1 = AttendanceService(df, prefs, device_mapping=None)
    results1 = [r for r in service1.analyze_all() if r.user_name == test_person_id]
    if results1:
        r = results1[0]
        print(f'   Приход: {r.arrival_time}')
        print(f'   Уход: {r.departure_time}')
        print(f'   Часы: {r.work_hours:.2f}')
    
    # Анализ С СТРОГОЙ фильтрацией
    print(f'\nСО СТРОГОЙ фильтрацией (только указанные камеры):')
    service2 = AttendanceService(df, prefs, device_mapping=device_mapping)
    results2 = [r for r in service2.analyze_all() if r.user_name == test_person_id]
    if results2:
        r = results2[0]
        arrival_str = r.arrival_time if r.arrival_time else "НЕ ЗАФИКСИРОВАН"
        departure_str = r.departure_time if r.departure_time else "НЕ ЗАФИКСИРОВАН"
        print(f'   Приход: {arrival_str}')
        print(f'   Уход: {departure_str}')
        print(f'   Часы: {r.work_hours:.2f}')

# Найдём пользователя у которого есть только события с камеры входа (нет выхода)
print(f'\n\nПоиск пользователя ТОЛЬКО с камерой входа (без выхода)...')
found = False
for person_id in df['name'].unique()[:30]:  # Проверяем первых 30
    person_events = df[df['name'] == person_id]
    
    # Проверяем есть ли события только с входа
    has_arrival = any(person_events['_device'] == '192.168.1.101')
    has_departure = any(person_events['_device'] == '192.168.1.104')
    
    if has_arrival and not has_departure and len(person_events) > 0:
        display_name = person_events.iloc[0]['display_name']
        print(f'\nНайден: {display_name}')
        
        events_sorted = person_events.sort_values('timestamp')
        print('События:')
        for idx, row in events_sorted.iterrows():
            device_name = row.get('_device_name', 'Unknown')
            device = row.get('_device', '?')
            print(f'  {row["timestamp"].time()} - {device_name} ({device})')
        
        # Тест строгой фильтрации
        service_test = AttendanceService(df, prefs, device_mapping=device_mapping)
        results_test = [r for r in service_test.analyze_all() if r.user_name == person_id]
        if results_test:
            r = results_test[0]
            print(f'\nСтрогая фильтрация:')
            arrival_str = r.arrival_time if r.arrival_time else "НЕТ (не было с камеры входа)"
            departure_str = r.departure_time if r.departure_time else "НЕТ (не было с камеры выхода)"
            print(f'   Приход: {arrival_str}')
            print(f'   Уход: {departure_str}')
            print(f'   Часы: {r.work_hours:.2f}')
        
        found = True
        break

if not found:
    print('Не найдено пользователей только с камерой входа')

print('\n=== ТЕСТ ЗАВЕРШЁН ===')
