"""
Модуль для работы с хранилищем событий
Поддерживает одновременную запись в NDJSON и SQLite
"""
import json
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from threading import Lock


class EventStorage:
    """Двойное хранилище: NDJSON + SQLite"""
    
    def __init__(self, ndjson_path: str, sqlite_path: Optional[str] = None):
        """
        Args:
            ndjson_path: Путь к NDJSON файлу
            sqlite_path: Путь к SQLite БД (опционально,
                по умолчанию рядом с NDJSON)
        """
        self.ndjson_path = ndjson_path
        
        # SQLite файл рядом с NDJSON, если не указан
        if sqlite_path is None:
            base = os.path.splitext(ndjson_path)[0]
            sqlite_path = f"{base}.db"
        
        self.sqlite_path = sqlite_path
        self._lock = Lock()
        
        # Создаём директории для файлов
        for path in [ndjson_path, sqlite_path]:
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)
        
        self._init_sqlite()
    
    def _init_sqlite(self) -> None:
        """Инициализация SQLite БД"""
        conn = sqlite3.connect(self.sqlite_path, timeout=30.0)
        
        # Таблица событий
        conn.execute('''
            CREATE TABLE IF NOT EXISTS events (
                device TEXT NOT NULL,
                serialNo INTEGER NOT NULL,
                time TEXT NOT NULL,
                employeeNoString TEXT,
                name TEXT,
                event_data TEXT NOT NULL,
                collected_at TEXT NOT NULL,
                PRIMARY KEY (device, serialNo)
            )
        ''')
        
        # Таблица состояния коллектора
        conn.execute('''
            CREATE TABLE IF NOT EXISTS collector_state (
                device TEXT PRIMARY KEY,
                last_serial INTEGER NOT NULL,
                last_collect TEXT,
                updated_at TEXT NOT NULL
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS attendance_manual_overrides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                date TEXT NOT NULL,
                patch_data TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'eusrr',
                note TEXT,
                updated_at TEXT NOT NULL,
                UNIQUE(employee_id, date)
            )
        ''')
        
        # Индексы для быстрого поиска
        conn.execute(
            'CREATE INDEX IF NOT EXISTS idx_device_serial '
            'ON events(device, serialNo DESC)'
        )
        conn.execute(
            'CREATE INDEX IF NOT EXISTS idx_time '
            'ON events(time)'
        )

        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        
        conn.commit()
        conn.close()
    
    def write_events(self, events: List[Dict[str, Any]]) -> None:
        """
        Запись событий в оба хранилища
        
        Args:
            events: Список событий для записи
        """
        if not events:
            return
        
        with self._lock:
            # 1. Запись в NDJSON
            with open(self.ndjson_path, 'a', encoding='utf-8') as f:
                for event in events:
                    f.write(json.dumps(event, ensure_ascii=False) + '\n')

            # 2. Запись в SQLite (батчем)
            self._write_sqlite_events(events)

    def _write_sqlite_events(self, events: List[Dict[str, Any]]) -> None:
        """Запись событий только в SQLite."""
        conn = sqlite3.connect(self.sqlite_path, timeout=30.0)
        try:
            rows = []
            for event in events:
                rows.append((
                    event.get('_device', ''),
                    event.get('serialNo', 0),
                    event.get('time', ''),
                    event.get('employeeNoString', ''),
                    event.get('name', ''),
                    json.dumps(event, ensure_ascii=False),
                    event.get('_collected', '')
                ))

            conn.executemany(
                'INSERT OR REPLACE INTO events '
                '(device, serialNo, time, employeeNoString, name, '
                'event_data, collected_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?)',
                rows
            )
            conn.commit()
        finally:
            conn.close()
    
    def update_collector_state(
        self, device: str, last_serial: int, last_collect: Optional[str] = None
    ) -> None:
        """
        Обновить состояние коллектора для устройства
        
        Args:
            device: IP или идентификатор устройства
            last_serial: Последний успешно собранный serialNo
            last_collect: Время последнего сбора (ISO format)
        """
        conn = sqlite3.connect(self.sqlite_path, timeout=30.0)
        try:
            now = datetime.now().isoformat()
            conn.execute(
                'INSERT OR REPLACE INTO collector_state '
                '(device, last_serial, last_collect, updated_at) '
                'VALUES (?, ?, ?, ?)',
                (device, last_serial, last_collect, now)
            )
            conn.commit()
        finally:
            conn.close()
    
    def get_collector_state(self, device: str) -> Optional[Dict[str, Any]]:
        """
        Получить состояние коллектора для устройства
        
        Args:
            device: IP или идентификатор устройства
            
        Returns:
            Словарь с полями last_serial, last_collect, updated_at
            или None если состояния нет
        """
        conn = sqlite3.connect(self.sqlite_path, timeout=30.0)
        try:
            cursor = conn.execute(
                'SELECT last_serial, last_collect, updated_at '
                'FROM collector_state WHERE device = ?',
                (device,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    'last_serial': row[0],
                    'last_collect': row[1],
                    'updated_at': row[2]
                }
            return None
        finally:
            conn.close()
    
    def get_last_serial(self, device: str) -> int:
        """
        Получить последний serialNo для устройства из SQLite
        
        Args:
            device: IP или идентификатор устройства
            
        Returns:
            Последний serialNo или 1 если событий нет
        """
        conn = sqlite3.connect(self.sqlite_path, timeout=30.0)
        try:
            cursor = conn.execute(
                'SELECT MAX(serialNo) FROM events WHERE device = ?',
                (device,)
            )
            result = cursor.fetchone()[0]
            return result if result is not None else 1
        finally:
            conn.close()
    
    def get_last_serials_all_devices(self) -> Dict[str, int]:
        """
        Получить последние serialNo для всех устройств
        
        Returns:
            Словарь {device: last_serialNo}
        """
        conn = sqlite3.connect(self.sqlite_path, timeout=30.0)
        try:
            cursor = conn.execute(
                'SELECT device, MAX(serialNo) '
                'FROM events '
                'GROUP BY device'
            )
            return dict(cursor.fetchall())
        finally:
            conn.close()
    
    def get_event_count(self, device: Optional[str] = None) -> int:
        """
        Получить количество событий
        
        Args:
            device: Устройство (если None - все устройства)
            
        Returns:
            Количество событий
        """
        conn = sqlite3.connect(self.sqlite_path, timeout=30.0)
        try:
            if device:
                cursor = conn.execute(
                    'SELECT COUNT(*) FROM events WHERE device = ?',
                    (device,)
                )
            else:
                cursor = conn.execute('SELECT COUNT(*) FROM events')
            
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def iter_events_without_images(
        self,
        device: Optional[str] = None,
        limit: Optional[int] = None,
    ):
        """
        Итерация по событиям без сохранённого пути к изображению.

        Args:
            device: Устройство (если None - все устройства)
            limit: Максимальное количество событий

        Yields:
            Сырые события из event_data
        """
        conn = sqlite3.connect(self.sqlite_path, timeout=30.0)
        try:
            query = (
                "SELECT event_data FROM events "
                "WHERE event_data NOT LIKE ?"
            )
            params = ['%"_imagePath"%']
            if device:
                query += " AND device = ?"
                params.append(device)
            query += " ORDER BY device, time, serialNo"
            if limit is not None:
                query += " LIMIT ?"
                params.append(int(limit))

            cursor = conn.execute(query, params)
            for (event_data,) in cursor:
                try:
                    yield json.loads(event_data)
                except json.JSONDecodeError:
                    continue
        finally:
            conn.close()

    def update_event(self, event: Dict[str, Any]) -> None:
        """
        Обновить существующее событие в SQLite.

        NDJSON не переписывается: это append-only журнал сырых событий.
        """
        conn = sqlite3.connect(self.sqlite_path, timeout=30.0)
        try:
            conn.execute(
                'UPDATE events '
                'SET time = ?, employeeNoString = ?, name = ?, '
                'event_data = ?, collected_at = ? '
                'WHERE device = ? AND serialNo = ?',
                (
                    event.get('time', ''),
                    event.get('employeeNoString', ''),
                    event.get('name', ''),
                    json.dumps(event, ensure_ascii=False),
                    event.get('_collected', ''),
                    event.get('_device', ''),
                    event.get('serialNo', 0),
                )
            )
            conn.commit()
        finally:
            conn.close()

    def update_event_image(
        self,
        device: str,
        serial_no: int,
        image_path: str,
    ) -> bool:
        """
        Обновить только путь к изображению в event_data существующего события.

        Возвращает True, если событие найдено и обновлено.
        """
        conn = sqlite3.connect(self.sqlite_path, timeout=30.0)
        try:
            cursor = conn.execute(
                'SELECT event_data FROM events WHERE device = ? AND serialNo = ?',
                (device, serial_no),
            )
            row = cursor.fetchone()
            if row is None:
                return False

            try:
                event = json.loads(row[0])
            except json.JSONDecodeError:
                return False

            event['_imagePath'] = image_path

            conn.execute(
                'UPDATE events SET event_data = ? WHERE device = ? AND serialNo = ?',
                (
                    json.dumps(event, ensure_ascii=False),
                    device,
                    serial_no,
                )
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def rebuild_sqlite_from_ndjson(self, progress_callback=None) -> int:
        """
        Восстановить SQLite БД из NDJSON файла
        
        Args:
            progress_callback: Функция для отчёта о прогрессе
            
        Returns:
            Количество импортированных событий
        """
        if not os.path.exists(self.ndjson_path):
            return 0
        
        # Пересоздаём БД
        if os.path.exists(self.sqlite_path):
            os.remove(self.sqlite_path)
        self._init_sqlite()
        
        count = 0
        batch = []
        batch_size = 1000
        
        with open(self.ndjson_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    batch.append(event)
                    count += 1
                    
                    if len(batch) >= batch_size:
                        self._write_sqlite_events(batch)
                        batch = []
                        
                        if progress_callback:
                            progress_callback(count)
                
                except json.JSONDecodeError:
                    continue
        
        # Запись остатка
        if batch:
            self._write_sqlite_events(batch)
        
        return count
