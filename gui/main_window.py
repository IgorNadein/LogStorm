"""
Main Window - главное окно приложения LogStorm
"""

import sys
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog
from PySide6.QtGui import QColor
from qfluentwidgets import (
    FluentWindow, FluentIcon, NavigationItemPosition,
    InfoBar, InfoBarPosition, MessageBox, setTheme, Theme, setThemeColor
)

from gui.state import AppState
from gui.interfaces import (
    SettingsInterface, PersonsInterface, LogsInterface,
    AnalysisInterface, AboutInterface
)
from gui.dialogs import PersonDialog
from gui.workers import AnalysisWorker, ExportWorker


class LogStormWindow(FluentWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("LogStorm - Анализ логов посещений")
        self.resize(1100, 750)
        
        # Состояние приложения
        self.state = AppState()
        
        # Создаём интерфейсы
        self.settingsInterface = SettingsInterface(self)
        self.personsInterface = PersonsInterface(self)
        self.logsInterface = LogsInterface(self)
        self.analysisInterface = AnalysisInterface(self)
        self.aboutInterface = AboutInterface(self)
        
        self._init_navigation()
        self._connect_signals()
        self._load_initial_data()
        
        # Применяем тему системы
        self._apply_system_theme()
    
    def _load_initial_data(self):
        """Загрузить начальные данные"""
        # Загружаем конфигурацию
        if self.state.load_config():
            # Блокируем сигналы при загрузке
            self.settingsInterface.sqlite_radio.blockSignals(True)
            self.settingsInterface.files_radio.blockSignals(True)
            
            # Обновляем UI источника данных
            if self.state.data_source_type == 'sqlite':
                self.settingsInterface.sqlite_radio.setChecked(True)
                self.settingsInterface.sqlite_edit.setText(
                    self.state.sqlite_path
                )
            else:
                self.settingsInterface.files_radio.setChecked(True)
            
            # Обновляем видимость карточек
            self.settingsInterface._on_source_changed()
            
            # Разблокируем сигналы
            self.settingsInterface.sqlite_radio.blockSignals(False)
            self.settingsInterface.files_radio.blockSignals(False)
            
            # Загружаем цветовую схему в GUI
            self.settingsInterface.set_color_scheme(self.state.color_scheme)
            
            # Обновляем UI настроек
            self.settingsInterface.prefs_edit.setText(
                str(self.state.prefs_file)
            )
            self.settingsInterface.export_edit.setText(
                str(self.state.export_dir)
            )
            self.settingsInterface.verbose_check.setChecked(
                self.state.verbose
            )
            
            # Загружаем файлы в список
            for file_path in self.state.files:
                self.settingsInterface.files_list.addItem(file_path)
        
        # Загружаем настройки сотрудников
        if self.state.load_prefs():
            self.personsInterface.refresh_persons_table(
                self.state.prefs, self.state.aliases
            )
            InfoBar.success(
                title="Загружено",
                content=f"Найдено сотрудников: {len(self.state.prefs)}",
                parent=self,
                position=InfoBarPosition.TOP
            )
        else:
            InfoBar.warning(
                title="Внимание",
                content="Файл person_prefs.json не найден",
                parent=self,
                position=InfoBarPosition.TOP
            )
        
        # Устанавливаем путь к NDJSON из настроек
        self.logsInterface.set_default_ndjson_from_settings(
            self.state.files
        )
    
    def _connect_signals(self):
        """Подключить сигналы"""
        # Настройки
        self.settingsInterface.apply_btn.clicked.connect(
            self._on_apply_settings
        )
        self.settingsInterface.save_config_btn.clicked.connect(
            self._on_save_config
        )
        self.settingsInterface.data_source_changed.connect(
            self._on_data_source_changed
        )
        
        # Сотрудники
        self.personsInterface.refresh_btn.clicked.connect(
            self._on_refresh_persons
        )
        self.personsInterface.add_person_btn.clicked.connect(
            self._on_add_person
        )
        self.personsInterface.edit_person_btn.clicked.connect(
            self._on_edit_person
        )
        self.personsInterface.delete_person_btn.clicked.connect(
            self._on_delete_person
        )
        
        # Анализ
        self.analysisInterface.run_btn.clicked.connect(
            self._on_run_analysis
        )
        
        # Экспорт (кнопка на вкладке анализа)
        self.analysisInterface.export_btn.clicked.connect(
            self._on_export
        )
    
    def _on_refresh_persons(self):
        """Обновить список сотрудников"""
        if self.state.load_prefs():
            self.personsInterface.refresh_persons_table(
                self.state.prefs, self.state.aliases
            )
            InfoBar.success(
                title="Обновлено",
                content=f"Загружено сотрудников: {len(self.state.prefs)}",
                parent=self,
                position=InfoBarPosition.TOP
            )
    
    def _on_add_person(self):
        """Добавить сотрудника"""
        dialog = PersonDialog(parent=self)
        if dialog.exec():
            person_id, person_data = dialog.get_person_data()
            
            if not person_id or not person_data.get('display_name'):
                InfoBar.error(
                    title="Ошибка",
                    content="Заполните обязательные поля: ID и Имя",
                    parent=self,
                    position=InfoBarPosition.TOP
                )
                return
            
            if person_id in self.state.prefs:
                InfoBar.warning(
                    title="Предупреждение",
                    content=f"Сотрудник {person_id} уже существует",
                    parent=self,
                    position=InfoBarPosition.TOP
                )
                return
            
            # Извлекаем алиасы из данных (если есть)
            aliases = person_data.pop('_aliases', [])
            
            # Сохраняем основные данные
            self.state.prefs[person_id] = person_data
            
            # Сохраняем алиасы
            if aliases:
                self.state.aliases[person_id] = aliases
                for alias_id in aliases:
                    if alias_id in self.state.prefs:
                        del self.state.prefs[alias_id]
            elif person_id in self.state.aliases:
                del self.state.aliases[person_id]
            
            if self.state.save_prefs():
                self.personsInterface.refresh_persons_table(
                    self.state.prefs, self.state.aliases
                )
                InfoBar.success(
                    title="Успешно",
                    content=f"Сотрудник {person_data['display_name']} добавлен",  # noqa: E501
                    parent=self,
                    position=InfoBarPosition.TOP
                )
    
    def _on_edit_person(self):
        """Редактировать сотрудника"""
        person_id = self.personsInterface.get_selected_person_id()
        if not person_id:
            InfoBar.warning(
                title="Выберите сотрудника",
                content="Выберите сотрудника из таблицы для редактирования",
                parent=self,
                position=InfoBarPosition.TOP
            )
            return
        
        # Подготавливаем данные для редактирования (включая алиасы)
        person_data = self.state.prefs.get(person_id, {}).copy()
        person_data['_aliases'] = self.state.aliases.get(person_id, [])
        
        dialog = PersonDialog(
            person_id=person_id,
            person_data=person_data,
            parent=self
        )
        
        if dialog.exec():
            _, updated_data = dialog.get_person_data()
            
            # Извлекаем алиасы из обновлённых данных
            aliases = updated_data.pop('_aliases', [])
            
            # Сохраняем основные данные
            self.state.prefs[person_id] = updated_data
            
            # Сохраняем алиасы
            if aliases:
                self.state.aliases[person_id] = aliases
                for alias_id in aliases:
                    if alias_id in self.state.prefs:
                        del self.state.prefs[alias_id]
            elif person_id in self.state.aliases:
                del self.state.aliases[person_id]
            
            if self.state.save_prefs():
                self.personsInterface.refresh_persons_table(
                    self.state.prefs, self.state.aliases
                )
                InfoBar.success(
                    title="Успешно",
                    content="Данные сотрудника обновлены",
                    parent=self,
                    position=InfoBarPosition.TOP
                )
    
    def _on_delete_person(self):
        """Удалить сотрудника"""
        person_id = self.personsInterface.get_selected_person_id()
        if not person_id:
            InfoBar.warning(
                title="Выберите сотрудника",
                content="Выберите сотрудника из таблицы для удаления",
                parent=self,
                position=InfoBarPosition.TOP
            )
            return
        
        person_name = self.state.prefs.get(person_id, {}).get(
            'display_name', person_id
        )
        
        # Подтверждение удаления
        w = MessageBox(
            f"Удалить {person_name}?",
            f"Вы уверены что хотите удалить сотрудника {person_name}?",
            self
        )
        
        if w.exec():
            del self.state.prefs[person_id]
            
            if person_id in self.state.aliases:
                del self.state.aliases[person_id]
            
            if self.state.save_prefs():
                self.personsInterface.refresh_persons_table(
                    self.state.prefs, self.state.aliases
                )
                InfoBar.success(
                    title="Успешно",
                    content=f"Сотрудник {person_name} удалён",
                    parent=self,
                    position=InfoBarPosition.TOP
                )
    
    def _on_save_config(self):
        """Сохранить конфигурацию в файл"""
        self._on_apply_settings()
        
        if self.state.save_config():
            InfoBar.success(
                title="Успешно",
                content="Конфигурация сохранена в config.json",
                parent=self,
                position=InfoBarPosition.TOP
            )
        else:
            InfoBar.error(
                title="Ошибка",
                content="Не удалось сохранить конфигурацию",
                parent=self,
                position=InfoBarPosition.TOP
            )
    
    def _on_data_source_changed(self, source_type: str, path: str):
        """Обработка изменения источника данных"""
        self.state.data_source_type = source_type
        if source_type == 'sqlite':
            self.state.sqlite_path = path
            print(f"Источник данных изменён: SQLite ({path})")
        else:
            print("Источник данных изменён: NDJSON/CSV файлы")
    
    def _on_apply_settings(self):
        """Применить настройки"""
        from config.colors import ColorScheme, ColorThresholds
        
        # Сохраняем источник данных
        if self.settingsInterface.sqlite_radio.isChecked():
            self.state.data_source_type = 'sqlite'
            self.state.sqlite_path = self.settingsInterface.sqlite_edit.text()
        else:
            self.state.data_source_type = 'files'
        
        # Сохраняем файлы
        self.state.files = [
            self.settingsInterface.files_list.item(i).text()
            for i in range(self.settingsInterface.files_list.count())
        ]
        
        # Сохраняем опции
        self.state.verbose = self.settingsInterface.verbose_check.isChecked()
        
        # Сохраняем пути
        self.state.prefs_file = Path(
            self.settingsInterface.prefs_edit.text()
        )
        self.state.export_dir = Path(
            self.settingsInterface.export_edit.text()
        )
        
        # Сохраняем цветовую схему
        colors_dict = self.settingsInterface.get_color_scheme_dict()
        self.state.color_scheme = ColorScheme(
            neutral=colors_dict['neutral'],
            warning=colors_dict['warning'],
            error=colors_dict['error'],
            success=colors_dict['success'],
            info=colors_dict['info'],
            thresholds=ColorThresholds()
        )
        
        # Перезагружаем prefs если путь изменился
        if self.state.load_prefs():
            self.personsInterface.refresh_persons_table(
                self.state.prefs, self.state.aliases
            )
        
        if self.state.files:
            InfoBar.success(
                title="Успешно",
                content=f"Настройки применены. Файлов: {len(self.state.files)}",  # noqa: E501
                parent=self,
                position=InfoBarPosition.TOP
            )
        else:
            InfoBar.warning(
                title="Предупреждение",
                content="Не выбрано ни одного файла",
                parent=self,
                position=InfoBarPosition.TOP
            )
    
    def _on_run_analysis(self):
        """Запустить анализ"""
        # Проверка наличия источника данных
        if self.state.data_source_type == 'sqlite':
            if not self.state.sqlite_path:
                InfoBar.error(
                    title="Ошибка",
                    content="Укажите путь к SQLite базе в настройках",
                    parent=self,
                    position=InfoBarPosition.TOP
                )
                return
            data_source = self.state.sqlite_path
        else:
            if not self.state.files:
                InfoBar.error(
                    title="Ошибка",
                    content="Сначала добавьте файлы в настройках",
                    parent=self,
                    position=InfoBarPosition.TOP
                )
                return
            data_source = self.state.files
        
        # Создаём рабочий поток
        self.analysis_worker = AnalysisWorker(
            data_source,
            self.state.prefs,
            str(self.state.prefs_file),
            data_source_type=self.state.data_source_type,
            start_date=self.state.filter_start_date,
            end_date=self.state.filter_end_date,
            devices=self.state.filter_devices
        )
        
        # Подключаем сигналы
        self.analysis_worker.progress.connect(self._on_analysis_progress)
        self.analysis_worker.finished.connect(self._on_analysis_finished)
        self.analysis_worker.error.connect(self._on_analysis_error)
        
        # Запускаем
        self.analysisInterface.set_analyzing(True)
        self.analysis_worker.start()
    
    def _on_analysis_progress(self, message: str):
        """Обновить прогресс анализа"""
        # Парсим сообщение для извлечения прогресса
        if "Анализ:" in message and "/" in message and "%" in message:
            # Формат: "Анализ: 5/78 (6%) - Имя"
            try:
                parts = message.split(":")
                if len(parts) >= 2:
                    progress_part = parts[1].split("(")[0].strip()
                    current, total = progress_part.split("/")
                    current = int(current)
                    total = int(total)
                    
                    # Извлекаем имя пользователя если есть
                    user_name = ""
                    if " - " in message:
                        user_name = message.split(" - ")[-1]
                    
                    self.analysisInterface.set_progress(
                        current, total, f"Анализ: {user_name}"
                    )
                    return
            except Exception:
                pass  # Если не удалось распарсить, показываем как текст
        
        # Обычное текстовое сообщение
        self.analysisInterface.status_label.setText(message)
    
    def _on_analysis_finished(self, results):
        """Анализ завершён"""
        self.state.results = results
        self.analysisInterface.set_analyzing(False)
        
        # Показываем результаты в таблице с фильтрами
        self.analysisInterface.set_results(results)
        
        InfoBar.success(
            title="Успешно",
            content=f"Анализ завершён: {len(results)} записей",
            parent=self,
            position=InfoBarPosition.TOP
        )
    
    def _on_analysis_error(self, error_msg: str):
        """Ошибка анализа"""
        self.analysisInterface.set_analyzing(False)
        self.analysisInterface.status_label.setText("Ошибка анализа")
        InfoBar.error(
            title="Ошибка",
            content=f"Ошибка при анализе: {error_msg}",
            parent=self,
            position=InfoBarPosition.TOP
        )
    
    def _on_export(self):
        """Экспорт результатов"""
        if not self.state.results:
            InfoBar.error(
                title="Ошибка",
                content="Сначала выполните анализ",
                parent=self,
                position=InfoBarPosition.TOP
            )
            return
        
        try:
            # Создаём директорию для экспорта
            self.state.export_dir.mkdir(parents=True, exist_ok=True)
            
            # Формируем имя файла
            from datetime import datetime
            default_name = (
                f"attendance_report_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
            default_path = str(self.state.export_dir / default_name)
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить отчёт",
                default_path,
                "Excel Files (*.xlsx);;CSV Files (*.csv)"
            )
            
            if file_path:
                # Создаём рабочий поток для экспорта
                self.export_worker = ExportWorker(
                    self.state.results,
                    file_path,
                    self.state.color_scheme  # Передаем цветовую схему
                )
                
                # Подключаем сигналы
                self.export_worker.progress.connect(self._on_export_progress)
                self.export_worker.finished.connect(self._on_export_finished)
                self.export_worker.error.connect(self._on_export_error)
                
                # Показываем индикатор прогресса
                self.analysisInterface.export_btn.setEnabled(False)
                self.analysisInterface.status_label.setText(
                    "Экспорт в Excel..."
                )
                
                # Запускаем
                self.export_worker.start()
                
        except Exception as e:
            import traceback
            error_details = f"{str(e)}\n{traceback.format_exc()}"
            print(f"ОШИБКА ЭКСПОРТА:\n{error_details}")
            InfoBar.error(
                title="Ошибка",
                content=f"Ошибка экспорта: {str(e)}",
                parent=self,
                position=InfoBarPosition.TOP
            )
    
    def _on_export_progress(self, message: str):
        """Обновить прогресс экспорта"""
        self.analysisInterface.status_label.setText(message)
    
    def _on_export_finished(self, file_path: str):
        """Экспорт завершён"""
        self.analysisInterface.export_btn.setEnabled(True)
        self.analysisInterface.status_label.setText("Экспорт завершён")
        
        InfoBar.success(
            title="Успешно",
            content=f"Отчёт сохранён: {file_path}",
            parent=self,
            position=InfoBarPosition.TOP
        )
    
    def _on_export_error(self, error_msg: str):
        """Ошибка экспорта"""
        self.analysisInterface.export_btn.setEnabled(True)
        self.analysisInterface.status_label.setText("Ошибка экспорта")
        
        InfoBar.error(
            title="Ошибка",
            content=f"Ошибка экспорта: {error_msg}",
            parent=self,
            position=InfoBarPosition.TOP
        )
    
    def _init_navigation(self):
        """Инициализация навигации"""
        
        # Добавляем основные вкладки
        self.addSubInterface(
            self.settingsInterface,
            FluentIcon.SETTING,
            'Настройки',
            NavigationItemPosition.TOP
        )
        
        self.addSubInterface(
            self.personsInterface,
            FluentIcon.PEOPLE,
            'Сотрудники',
            NavigationItemPosition.TOP
        )
        
        self.addSubInterface(
            self.logsInterface,
            FluentIcon.CLOUD_DOWNLOAD,
            'Логи',
            NavigationItemPosition.TOP
        )
        
        self.addSubInterface(
            self.analysisInterface,
            FluentIcon.MARKET,
            'Анализ',
            NavigationItemPosition.TOP
        )
        
        # О программе внизу
        self.addSubInterface(
            self.aboutInterface,
            FluentIcon.INFO,
            'О программе',
            NavigationItemPosition.BOTTOM
        )
    
    def _apply_system_theme(self):
        """Применить системную тему и цвета из Windows"""
        try:
            import darkdetect
            if darkdetect.isDark():
                setTheme(Theme.DARK)
            else:
                setTheme(Theme.LIGHT)
        except Exception:
            setTheme(Theme.LIGHT)
        
        # Применяем системный акцентный цвет Windows
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\DWM"
            )
            accent_color, _ = winreg.QueryValueEx(key, "AccentColor")
            winreg.CloseKey(key)
            
            # Windows хранит цвет в формате AABBGGRR
            b = (accent_color >> 16) & 0xFF
            g = (accent_color >> 8) & 0xFF
            r = accent_color & 0xFF
            
            color = QColor(r, g, b)
            setThemeColor(color)
        except Exception:
            pass


def main():
    """Запуск приложения"""
    # Включаем DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    app = QApplication(sys.argv)
    
    window = LogStormWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
