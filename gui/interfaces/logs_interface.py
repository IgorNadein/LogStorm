"""
Logs Interface - интерфейс управления логами
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
    QDialog, QTextEdit
)
from PySide6.QtCore import QDate
from qfluentwidgets import (
    CardWidget, PrimaryPushButton, PushButton, LineEdit, CheckBox,
    StrongBodyLabel, BodyLabel, InfoBar, DatePicker
)

from gui.workers import LogDownloadWorker


class LogsInterface(QWidget):
    """Интерфейс управления логами и импорта сотрудников"""
    
    def __init__(self, parent=None):
        """
        Инициализация интерфейса
        
        Args:
            parent: Родительский виджет
        """
        super().__init__(parent=parent)
        self.setObjectName("logsInterface")
        self.download_worker = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        title = StrongBodyLabel("Управление логами", self)
        layout.addWidget(title)
        
        # Карточка: Получение логов с устройства
        fetch_card = CardWidget(self)
        fetch_layout = QVBoxLayout(fetch_card)
        fetch_layout.setSpacing(12)
        
        fetch_label = StrongBodyLabel("Получение логов с устройства")
        fetch_layout.addWidget(fetch_label)
        
        info_label = BodyLabel(
            "Подключение к устройству HIKVISION для получения событий"
        )
        fetch_layout.addWidget(info_label)
        
        # Настройки устройства
        device_form = QHBoxLayout()
        device_form.setSpacing(8)
        
        self.host_edit = LineEdit(self)
        self.host_edit.setPlaceholderText("192.168.1.101")
        self.host_edit.setText("192.168.1.101")
        
        self.user_edit = LineEdit(self)
        self.user_edit.setPlaceholderText("admin")
        self.user_edit.setText("admin")
        
        self.password_edit = LineEdit(self)
        self.password_edit.setPlaceholderText("пароль")
        self.password_edit.setEchoMode(LineEdit.EchoMode.Password)
        
        device_form.addWidget(BodyLabel("IP:"))
        device_form.addWidget(self.host_edit)
        device_form.addWidget(BodyLabel("Логин:"))
        device_form.addWidget(self.user_edit)
        device_form.addWidget(BodyLabel("Пароль:"))
        device_form.addWidget(self.password_edit)
        
        fetch_layout.addLayout(device_form)
        
        # Диапазон дат
        dates_form = QHBoxLayout()
        dates_form.setSpacing(8)
        
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        
        # DatePicker - легкий виджет с диалогом
        self.start_date_picker = DatePicker(self)
        self.start_date_picker.setDate(
            QDate(week_ago.year, week_ago.month, week_ago.day)
        )
        
        self.end_date_picker = DatePicker(self)
        self.end_date_picker.setDate(
            QDate(today.year, today.month, today.day)
        )
        
        dates_form.addWidget(BodyLabel("От:"))
        dates_form.addWidget(self.start_date_picker)
        dates_form.addWidget(BodyLabel("До:"))
        dates_form.addWidget(self.end_date_picker)
        
        fetch_layout.addLayout(dates_form)
        
        # Дополнительные параметры
        params_form = QHBoxLayout()
        params_form.setSpacing(8)
        
        self.major_edit = LineEdit(self)
        self.major_edit.setText("5")
        self.major_edit.setFixedWidth(60)
        
        self.minor_edit = LineEdit(self)
        self.minor_edit.setText("75")
        self.minor_edit.setFixedWidth(60)
        
        self.pic_check = CheckBox("Загружать фото", self)
        
        params_form.addWidget(BodyLabel("Major:"))
        params_form.addWidget(self.major_edit)
        params_form.addWidget(BodyLabel("Minor:"))
        params_form.addWidget(self.minor_edit)
        params_form.addWidget(self.pic_check)
        params_form.addStretch()
        
        fetch_layout.addLayout(params_form)
        
        # Область прогресса
        self.progress_text = QTextEdit(self)
        self.progress_text.setReadOnly(True)
        self.progress_text.setMaximumHeight(100)
        self.progress_text.setPlaceholderText(
            "Здесь будет отображаться прогресс..."
        )
        fetch_layout.addWidget(self.progress_text)
        
        # Кнопка получения логов
        self.fetch_btn = PrimaryPushButton("Получить логи", self)
        self.fetch_btn.setMinimumHeight(36)
        fetch_layout.addWidget(self.fetch_btn)
        
        layout.addWidget(fetch_card)
        
        # Карточка: Импорт новых сотрудников
        import_card = CardWidget(self)
        import_layout = QVBoxLayout(import_card)
        import_layout.setSpacing(12)
        
        import_label = StrongBodyLabel(
            "Импорт новых сотрудников из логов"
        )
        import_layout.addWidget(import_label)
        
        import_info = BodyLabel(
            "Найти новых сотрудников в NDJSON файлах "
            "и добавить в конфигурацию"
        )
        import_layout.addWidget(import_info)
        
        # Выбор файла
        file_layout = QHBoxLayout()
        file_layout.setSpacing(8)
        
        self.ndjson_edit = LineEdit(self)
        self.ndjson_edit.setPlaceholderText("logs/events.ndjson")
        
        self.browse_ndjson_btn = PushButton("Обзор", self)
        
        file_layout.addWidget(BodyLabel("NDJSON файл:"))
        file_layout.addWidget(self.ndjson_edit)
        file_layout.addWidget(self.browse_ndjson_btn)
        
        import_layout.addLayout(file_layout)
        
        # Кнопка импорта
        self.import_btn = PrimaryPushButton("Импортировать новых", self)
        self.import_btn.setMinimumHeight(36)
        import_layout.addWidget(self.import_btn)
        
        layout.addWidget(import_card)
        
        layout.addStretch()
        
        # Подключаем обработчики
        self.browse_ndjson_btn.clicked.connect(self._on_browse_ndjson)
        self.fetch_btn.clicked.connect(self._on_fetch_logs)
        self.import_btn.clicked.connect(self._on_import_employees)
    
    def _on_browse_ndjson(self):
        """Выбор NDJSON файла для импорта"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите NDJSON файл",
            str(Path.cwd() / "logs"),
            "NDJSON файлы (*.ndjson);;Все файлы (*.*)"
        )
        
        if file_path:
            self.ndjson_edit.setText(file_path)
    
    def _on_fetch_logs(self):
        """Получить логи с устройства"""
        # Проверка, не запущен ли уже процесс
        if self.download_worker and self.download_worker.isRunning():
            InfoBar.warning(
                title="Внимание",
                content="Загрузка уже выполняется",
                parent=self
            )
            return
        
        host = self.host_edit.text().strip()
        user = self.user_edit.text().strip()
        password = self.password_edit.text().strip()
        
        # Получаем даты из DatePicker (getDate возвращает QDate)
        start_qdate = self.start_date_picker.getDate()
        end_qdate = self.end_date_picker.getDate()
        
        # Форматируем в ISO формат
        start_date = start_qdate.toString("yyyy-MM-dd") + "T00:00:00"
        end_date = end_qdate.toString("yyyy-MM-dd") + "T23:59:59"
        
        if not all([host, user, password]):
            InfoBar.warning(
                title="Ошибка",
                content="Заполните все поля подключения",
                parent=self
            )
            return
        
        # Получаем параметры
        try:
            major = int(self.major_edit.text())
            minor = int(self.minor_edit.text())
        except ValueError:
            InfoBar.warning(
                title="Ошибка",
                content="Major и Minor должны быть числами",
                parent=self
            )
            return
        
        pic_enable = self.pic_check.isChecked()
        
        # Создаем имя файла с текущей датой
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = Path.cwd() / "logs" / f"events_{timestamp}.ndjson"
        output_file.parent.mkdir(exist_ok=True)
        
        # Очищаем прогресс
        self.progress_text.clear()
        self.progress_text.append(f"🚀 Начинаем загрузку с {host}...")
        
        # Отключаем кнопку
        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setText("Загрузка...")
        
        # Создаем и запускаем worker
        self.download_worker = LogDownloadWorker(
            host, user, password, start_date, end_date,
            output_file, major, minor, pic_enable
        )
        
        # Подключаем сигналы
        self.download_worker.progress.connect(self._on_download_progress)
        self.download_worker.finished.connect(self._on_download_finished)
        self.download_worker.error.connect(self._on_download_error)
        
        # Запускаем
        self.download_worker.start()
    
    def _on_download_progress(self, message):
        """Обновление прогресса"""
        self.progress_text.append(message)
        # Прокручиваем вниз
        cursor = self.progress_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.progress_text.setTextCursor(cursor)
    
    def _on_download_finished(self, file_path):
        """Загрузка завершена"""
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("Получить логи")
        
        InfoBar.success(
            title="Успешно",
            content=f"Логи сохранены в:\n{file_path}",
            parent=self
        )
        
        # Добавляем файл в список для импорта
        self.ndjson_edit.setText(file_path)
    
    def _on_download_error(self, error_message):
        """Ошибка загрузки"""
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("Получить логи")
        
        self.progress_text.append(error_message)
        
        InfoBar.error(
            title="Ошибка",
            content=error_message,
            parent=self
        )
    
    def _on_import_employees(self):
        """Импортировать новых сотрудников из NDJSON"""
        ndjson_path = self.ndjson_edit.text().strip()
        
        if not ndjson_path:
            InfoBar.warning(
                title="Ошибка",
                content="Укажите путь к NDJSON файлу",
                parent=self
            )
            return
        
        ndjson_file = Path(ndjson_path)
        if not ndjson_file.exists():
            InfoBar.error(
                title="Ошибка",
                content=f"Файл не найден:\n{ndjson_path}",
                parent=self
            )
            return
        
        # Получаем родительское окно с состоянием
        main_window = self.window()
        if not hasattr(main_window, 'state'):
            InfoBar.error(
                title="Ошибка",
                content="Не удалось получить доступ к настройкам",
                parent=self
            )
            return
        
        # Загружаем ПОЛНЫЙ список существующих ID из файла
        existing_ids = set()
        try:
            prefs_file = Path(main_window.state.prefs_file)
            if prefs_file.exists():
                with open(prefs_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Собираем все ID из person_mappings
                person_mappings = data.get('person_mappings', {})
                existing_ids.update(person_mappings.keys())
                
                # Добавляем все алиасы
                aliases_data = data.get('aliases', {})
                for main_id, alias_list in aliases_data.items():
                    if main_id != 'NOTE' and isinstance(alias_list, list):
                        existing_ids.update(alias_list)
                
                print(f"✓ Загружено {len(existing_ids)} ID "
                      f"({len(person_mappings)} основных + алиасы)")
            else:
                print(f"⚠️  Файл не найден: {prefs_file}")
        except Exception as e:
            print(f"❌ Ошибка чтения файла сотрудников: {e}")
            InfoBar.error(
                title="Ошибка",
                content=f"Не удалось прочитать файл сотрудников:\n{e}",
                parent=self
            )
            return
        
        # Сканируем NDJSON на новых сотрудников
        new_employees = {}
        try:
            with open(ndjson_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                        emp_id = event.get('employeeNoString')
                        emp_name = event.get('name', '')
                        
                        if (emp_id and emp_id not in existing_ids and
                                emp_id not in new_employees):
                            new_employees[emp_id] = emp_name or emp_id
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            InfoBar.error(
                title="Ошибка чтения файла",
                content=str(e),
                parent=self
            )
            return
        
        if not new_employees:
            InfoBar.success(
                title="Импорт завершен",
                content="Новых сотрудников не найдено",
                parent=self
            )
            return
        
        # Показываем диалог с новыми сотрудниками
        dialog = QDialog(self)
        dialog.setWindowTitle("Новые сотрудники")
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(400)
        
        layout = QVBoxLayout(dialog)
        
        # Информация о файле
        prefs_info = BodyLabel(
            f"Файл сотрудников: {main_window.state.prefs_file}"
        )
        layout.addWidget(prefs_info)
        
        info = BodyLabel(
            f"Найдено новых сотрудников: {len(new_employees)}"
        )
        layout.addWidget(info)
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        employees_text = "\n".join([
            f"{emp_id}: {name}" for emp_id, name in new_employees.items()
        ])
        text_edit.setPlainText(employees_text)
        layout.addWidget(text_edit)
        
        btn_layout = QHBoxLayout()
        add_btn = PrimaryPushButton("Добавить всех")
        cancel_btn = PushButton("Отмена")
        
        def add_employees():
            # Добавляем новых сотрудников в конфигурацию
            for emp_id, emp_name in new_employees.items():
                main_window.state.prefs[emp_id] = {
                    "display_name": emp_name,
                    "original_names": [emp_name],
                    "workdays": [
                        "Monday", "Tuesday", "Wednesday",
                        "Thursday", "Friday"
                    ],
                    "start_time": "09:00",
                    "end_time": "18:00",
                    "work_hours": 9
                }
            
            # Сохраняем конфигурацию
            main_window.state.save_prefs()
            
            # Обновляем таблицу сотрудников
            if hasattr(main_window, 'personsInterface'):
                main_window.personsInterface.refresh_persons_table(
                    main_window.state.prefs,
                    main_window.state.aliases
                )
            
            InfoBar.success(
                title="Успешно",
                content=f"Добавлено сотрудников: {len(new_employees)}",
                parent=self
            )
            dialog.accept()
        
        add_btn.clicked.connect(add_employees)
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        dialog.exec()
    
    def set_default_ndjson_from_settings(self, files):
        """
        Установить путь к NDJSON файлу из настроек
        
        Args:
            files: Список файлов из настроек
        """
        if not files:
            return
        
        # Берем первый NDJSON файл из списка
        for file_path in files:
            # Нормализуем путь
            if isinstance(file_path, str):
                normalized_path = Path(file_path)
            else:
                normalized_path = file_path
            
            file_str = str(normalized_path)
            
            # Проверяем расширение
            if file_str.lower().endswith('.ndjson'):
                self.ndjson_edit.setText(file_str)
                print(f"✓ NDJSON файл установлен: {file_str}")
                return
        
        # Если NDJSON файлов нет, берем первый файл
        if files:
            first_file = str(files[0])
            self.ndjson_edit.setText(first_file)
            print(f"✓ Установлен первый файл: {first_file}")
