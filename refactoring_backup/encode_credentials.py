"""
Вспомогательный скрипт для кодирования Client ID и Secret в base64 для GigaChat API
"""
import base64

print("=" * 80)
print("GigaChat API - Кодировщик учетных данных")
print("=" * 80)
print()

print("У вас есть два варианта настройки API ключа:")
print()
print("ВАРИАНТ 1 (Рекомендуется):")
print("  1. Войдите в личный кабинет: https://developers.sber.ru/studio/workspaces")
print("  2. Выберите ваш проект")
print("  3. Скопируйте 'Authorization data' (это готовая base64 строка)")
print("  4. Вставьте её в .env файл как GIGACHAT_API_KEY")
print()
print("ВАРИАНТ 2 (Если у вас только Client ID и Secret):")
print("  Введите их ниже, и скрипт создаст base64 строку")
print()

choice = input("Выберите вариант (1 или 2): ").strip()

if choice == "1":
    print()
    auth_data = input("Вставьте Authorization data из личного кабинета: ").strip()
    if auth_data:
        print()
        print("✅ Отлично! Добавьте эту строку в ваш .env файл:")
        print(f"GIGACHAT_API_KEY={auth_data}")
    else:
        print("❌ Ошибка: строка пустая")
        
elif choice == "2":
    print()
    print("Введите ваши учетные данные:")
    client_id = input("Client ID: ").strip()
    client_secret = input("Client Secret: ").strip()
    
    if client_id and client_secret:
        credentials = f"{client_id}:{client_secret}"
        encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        
        print()
        print("✅ Готово! Закодированные учетные данные:")
        print(f"GIGACHAT_API_KEY={encoded}")
        print()
        print("Скопируйте эту строку в ваш .env файл")
    else:
        print("❌ Ошибка: Client ID или Secret пустые")
else:
    print("❌ Неверный выбор")

print()
print("=" * 80)
