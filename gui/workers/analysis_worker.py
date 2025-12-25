"""
Analysis Worker - выполняет анализ посещаемости в отдельном потоке
"""

from pathlib import Path
from PySide6.QtCore import QThread, Signal

from services.data_loader import DataLoader
from services.attendance_service import AttendanceService
from services.person_mapper import PersonMapper


class AnalysisWorker(QThread):
    """Рабочий поток для анализа посещаемости"""
    
    finished = Signal(list)  # Сигнал завершения с результатами
    error = Signal(str)      # Сигнал ошибки
    progress = Signal(str)   # Сигнал прогресса
    
    def __init__(
        self, files, prefs, prefs_file=None,
        data_source_type='files', device_mapping=None, **kwargs
    ):
        """
        Инициализация worker
        
        Args:
            files: Список путей к файлам логов (или путь к БД)
            prefs: Словарь настроек сотрудников
            prefs_file: Путь к файлу с настройками (для PersonMapper)
            data_source_type: Тип источника ('files' или 'sqlite')
            device_mapping: Опциональный маппинг камер для прихода/ухода
            **kwargs: Дополнительные параметры (для SQLite)
        """
        super().__init__()
        self.files = files
        self.prefs = prefs
        self.prefs_file = prefs_file
        self.data_source_type = data_source_type
        self.device_mapping = device_mapping
        self.kwargs = kwargs
    
    def run(self):
        """Выполнить анализ в фоновом потоке"""
        try:
            # Создаём PersonMapper если есть файл с алиасами
            person_mapper = None
            if self.prefs_file and Path(self.prefs_file).exists():
                self.progress.emit("Инициализация маппера сотрудников...")
                person_mapper = PersonMapper(str(self.prefs_file))
            
            # Загрузка данных с учётом источника
            if self.data_source_type == 'sqlite':
                self.progress.emit("Загрузка данных из SQLite...")
                # files содержит путь к БД
                db_path = (
                    self.files if isinstance(self.files, str)
                    else self.files[0]
                )
                df = DataLoader.load_logs(
                    db_path,
                    file_type='sqlite',
                    person_mapper=person_mapper,
                    **self.kwargs
                )
            else:
                self.progress.emit("Загрузка файлов...")
                df = DataLoader.load_logs(
                    self.files,
                    person_mapper=person_mapper
                )
            
            # Анализ посещаемости с callback для прогресса
            self.progress.emit("Анализ посещаемости...")
            service = AttendanceService(
                df, self.prefs, device_mapping=self.device_mapping
            )
            results = service.analyze_all(progress_callback=self._on_progress)
            
            self.progress.emit("Готово!")
            self.finished.emit(results)
            
        except Exception as e:
            import traceback
            error_details = f"{str(e)}\n{traceback.format_exc()}"
            print(f"ОШИБКА АНАЛИЗА:\n{error_details}")
            self.error.emit(str(e))
    
    def _on_progress(self, current: int, total: int, user_name: str):
        """Обработка прогресса анализа"""
        percent = int((current / total) * 100)
        msg = f"Анализ: {current}/{total} ({percent}%) - {user_name}"
        self.progress.emit(msg)
