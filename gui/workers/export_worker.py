"""
Export Worker - выполняет экспорт в Excel в отдельном потоке
"""

from PySide6.QtCore import QThread, Signal

from analyzer.reporters import ExcelReporter


class ExportWorker(QThread):
    """Рабочий поток для экспорта в Excel"""
    
    finished = Signal(str)  # Сигнал завершения с путём к файлу
    error = Signal(str)     # Сигнал ошибки
    progress = Signal(str)  # Сигнал прогресса
    
    def __init__(self, results, file_path):
        """
        Инициализация worker
        
        Args:
            results: Список AttendanceRecord для экспорта
            file_path: Путь к файлу Excel
        """
        super().__init__()
        self.results = results
        self.file_path = file_path
    
    def run(self):
        """Выполнить экспорт в фоновом потоке"""
        try:
            self.progress.emit("Подготовка данных...")
            
            # Создаём репортер и генерируем отчёт
            reporter = ExcelReporter(self.results)
            
            self.progress.emit("Формирование Excel файла...")
            reporter.generate_report(self.file_path)
            
            self.progress.emit("Готово!")
            self.finished.emit(self.file_path)
            
        except PermissionError:
            self.error.emit(
                "Файл занят. Закройте Excel и попробуйте снова."
            )
        except Exception as e:
            import traceback
            error_details = f"{str(e)}\n{traceback.format_exc()}"
            print(f"ОШИБКА ЭКСПОРТА:\n{error_details}")
            self.error.emit(str(e))
