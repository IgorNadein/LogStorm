"""
Log Download Worker - загружает логи с устройства Hikvision в отдельном потоке
"""

import json
from PySide6.QtCore import QThread, Signal


class LogDownloadWorker(QThread):
    """Worker для загрузки логов с устройства Hikvision"""
    
    progress = Signal(str)  # Сообщение о прогрессе
    finished = Signal(str)  # Путь к сохранённому файлу
    error = Signal(str)     # Сообщение об ошибке
    
    def __init__(self, host, user, password, start_date, end_date,
                 output_file, major=5, minor=75, pic_enable=False):
        """
        Инициализация worker
        
        Args:
            host: IP адрес устройства
            user: Имя пользователя
            password: Пароль
            start_date: Начальная дата (формат ISO)
            end_date: Конечная дата (формат ISO)
            output_file: Путь для сохранения файла
            major: Major тип события (по умолчанию 5 - ACS)
            minor: Minor тип события (по умолчанию 75 - вход/выход)
            pic_enable: Загружать ли фотографии
        """
        super().__init__()
        self.host = host
        self.user = user
        self.password = password
        self.start_date = start_date
        self.end_date = end_date
        self.output_file = output_file
        self.major = major
        self.minor = minor
        self.pic_enable = pic_enable
    
    def run(self):
        """Выполнение загрузки в фоновом потоке"""
        try:
            import requests
            from requests.auth import HTTPDigestAuth
            
            self.progress.emit("🔌 Подключение к устройству...")
            
            base_url = f"http://{self.host}"
            auth = HTTPDigestAuth(self.user, self.password)
            session = requests.Session()
            
            # Подготовка условий запроса
            cond = {
                "searchID": "1",
                "searchResultPosition": 0,
                "maxResults": 30,
                "major": self.major,
                "minor": self.minor,
                "startTime": self.start_date,
                "endTime": self.end_date,
            }
            
            if self.pic_enable:
                cond["picEnable"] = True
            
            url = f"{base_url}/ISAPI/AccessControl/AcsEvent?format=json"
            timeout = (5, 30)
            
            all_events = []
            page = 1
            
            while True:
                self.progress.emit(f"📥 Страница {page}...")
                
                try:
                    resp = session.post(
                        url, auth=auth,
                        json={"AcsEventCond": cond},
                        timeout=timeout
                    )
                    
                    if resp.status_code == 401:
                        raise RuntimeError("Ошибка авторизации (401)")
                    if resp.status_code >= 400:
                        raise RuntimeError(f"HTTP {resp.status_code}")
                    
                    # Парсим ответ
                    payload = resp.json()
                    
                    # Извлекаем события
                    acs = payload.get("AcsEvent", {})
                    info_list = acs.get("InfoList", [])
                    
                    if not info_list:
                        break
                    
                    all_events.extend(info_list)
                    self.progress.emit(f"✓ Получено событий: {len(all_events)}")
                    
                    # Проверяем, есть ли еще страницы
                    total = acs.get("totalMatches", 0)
                    if len(all_events) >= total or len(info_list) < 30:
                        break
                    
                    # Следующая страница
                    cond["searchResultPosition"] = len(all_events)
                    page += 1
                    
                except Exception as e:
                    self.error.emit(f"Ошибка запроса: {str(e)}")
                    return
            
            # Сохраняем в NDJSON
            self.progress.emit(f"💾 Сохранение в {self.output_file.name}...")
            
            with open(self.output_file, 'w', encoding='utf-8') as f:
                for event in all_events:
                    f.write(json.dumps(event, ensure_ascii=False) + '\n')
            
            self.progress.emit(f"✅ Готово! Сохранено {len(all_events)} событий")
            self.finished.emit(str(self.output_file))
            
        except Exception as e:
            self.error.emit(f"❌ Ошибка: {str(e)}")
