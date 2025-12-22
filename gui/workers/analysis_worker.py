"""
Analysis Worker - выполняет анализ посещаемости в отдельном потоке
"""

from pathlib import Path
from PySide6.QtCore import QThread, Signal

from services.data_loader import DataLoader
from services.attendance_service import AttendanceService
from services.ai_service import AIService
from services.person_mapper import PersonMapper


class AnalysisWorker(QThread):
    """Рабочий поток для анализа посещаемости"""
    
    finished = Signal(list)  # Сигнал завершения с результатами
    error = Signal(str)      # Сигнал ошибки
    progress = Signal(str)   # Сигнал прогресса
    
    def __init__(self, files, prefs, use_ai=False, prefs_file=None):
        """
        Инициализация worker
        
        Args:
            files: Список путей к файлам логов
            prefs: Словарь настроек сотрудников
            use_ai: Использовать ли AI анализ
            prefs_file: Путь к файлу с настройками (для PersonMapper)
        """
        super().__init__()
        self.files = files
        self.prefs = prefs
        self.use_ai = use_ai
        self.prefs_file = prefs_file
    
    def run(self):
        """Выполнить анализ в фоновом потоке"""
        try:
            # Создаём PersonMapper если есть файл с алиасами
            person_mapper = None
            if self.prefs_file and Path(self.prefs_file).exists():
                self.progress.emit("Инициализация маппера сотрудников...")
                person_mapper = PersonMapper(str(self.prefs_file))
            
            # Загрузка данных с учётом алиасов
            self.progress.emit("Загрузка файлов...")
            df = DataLoader.load_logs(self.files, person_mapper=person_mapper)
            
            # Анализ посещаемости
            self.progress.emit("Анализ посещаемости...")
            service = AttendanceService(df, self.prefs)
            results = service.analyze_all()
            
            # AI обработка если включена
            if self.use_ai:
                self.progress.emit("AI анализ отсутствий...")
                try:
                    ai_service = AIService()
                    results = ai_service.enhance_results(results)
                except Exception as e:
                    print(f"AI анализ недоступен: {e}")
            
            self.progress.emit("Готово!")
            self.finished.emit(results)
            
        except Exception as e:
            import traceback
            error_details = f"{str(e)}\n{traceback.format_exc()}"
            print(f"ОШИБКА АНАЛИЗА:\n{error_details}")
            self.error.emit(str(e))
