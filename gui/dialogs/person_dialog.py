"""
Person Dialog - диалог добавления/редактирования сотрудника
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFormLayout
)
from qfluentwidgets import (
    CardWidget, LineEdit, PrimaryPushButton, PushButton
)


class PersonDialog(QDialog):
    """Диалог добавления/редактирования сотрудника"""
    
    def __init__(self, person_id=None, person_data=None, parent=None):
        """
        Инициализация диалога
        
        Args:
            person_id: ID сотрудника (для редактирования, None для нового)
            person_data: Данные сотрудника (словарь)
            parent: Родительский виджет
        """
        super().__init__(parent)
        self.person_id = person_id
        self.person_data = person_data or {}
        
        self.setWindowTitle(
            "Редактировать сотрудника" if person_id
            else "Добавить сотрудника"
        )
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Карточка с формой
        card = CardWidget(self)
        form_layout = QFormLayout(card)
        form_layout.setSpacing(12)
        
        # ID сотрудника
        self.id_edit = LineEdit(self)
        self.id_edit.setPlaceholderText("ivan_ivanov")
        if person_id:
            self.id_edit.setText(person_id)
            self.id_edit.setReadOnly(True)
        form_layout.addRow(QLabel("ID:"), self.id_edit)
        
        # Отображаемое имя
        self.name_edit = LineEdit(self)
        self.name_edit.setPlaceholderText("Employee Sample")
        self.name_edit.setText(
            self.person_data.get('display_name', '')
        )
        form_layout.addRow(QLabel("Имя:"), self.name_edit)
        
        # Время начала работы
        self.start_time_edit = LineEdit(self)
        self.start_time_edit.setPlaceholderText("09:00")
        self.start_time_edit.setText(
            self.person_data.get('start_time', '')
        )
        form_layout.addRow(QLabel("Начало работы:"), self.start_time_edit)
        
        # Рабочие часы
        self.work_hours_edit = LineEdit(self)
        self.work_hours_edit.setPlaceholderText("9")
        work_hours = self.person_data.get('work_hours')
        if work_hours:
            self.work_hours_edit.setText(str(work_hours))
        form_layout.addRow(QLabel("Рабочих часов:"), self.work_hours_edit)
        
        # Рабочие дни
        self.workdays_edit = LineEdit(self)
        self.workdays_edit.setPlaceholderText(
            "Monday, Tuesday, Wednesday, Thursday, Friday"
        )
        workdays = self.person_data.get('workdays', [])
        if workdays:
            self.workdays_edit.setText(", ".join(workdays))
        form_layout.addRow(QLabel("Рабочие дни:"), self.workdays_edit)
        
        # Оригинальные имена (из камеры)
        self.original_names_edit = LineEdit(self)
        self.original_names_edit.setPlaceholderText(
            "Employee Sample, Ivan Ivanov (через запятую)"
        )
        original_names = self.person_data.get('original_names', [])
        if original_names:
            self.original_names_edit.setText(", ".join(original_names))
        form_layout.addRow(
            QLabel("Имена из камеры:"), self.original_names_edit
        )
        
        # Алиасы (дополнительные ID)
        self.aliases_edit = LineEdit(self)
        self.aliases_edit.setPlaceholderText("123, 456, 789 (через запятую)")
        aliases = self.person_data.get('_aliases', [])
        if aliases:
            self.aliases_edit.setText(", ".join(str(a) for a in aliases))
        form_layout.addRow(QLabel("Алиасы (доп. ID):"), self.aliases_edit)
        
        layout.addWidget(card)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        self.save_btn = PrimaryPushButton("Сохранить", self)
        self.save_btn.clicked.connect(self.accept)
        
        self.cancel_btn = PushButton("Отмена", self)
        self.cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addWidget(self.save_btn)
        
        layout.addLayout(buttons_layout)
    
    def get_person_data(self):
        """
        Получить данные сотрудника из формы
        
        Returns:
            Tuple[str, dict]: (person_id, person_data)
        """
        data = {
            'display_name': self.name_edit.text().strip()
        }
        
        # Добавляем start_time если указан
        start_time = self.start_time_edit.text().strip()
        if start_time:
            data['start_time'] = start_time
        
        # Добавляем work_hours если указаны
        work_hours_text = self.work_hours_edit.text().strip()
        if work_hours_text:
            try:
                data['work_hours'] = int(work_hours_text)
            except ValueError:
                # Если не удалось преобразовать в int, пропускаем
                pass
        
        # Добавляем workdays если указаны
        workdays_text = self.workdays_edit.text().strip()
        if workdays_text:
            workdays = [day.strip() for day in workdays_text.split(',')]
            data['workdays'] = workdays
        
        # Добавляем original_names если указаны
        original_names_text = self.original_names_edit.text().strip()
        if original_names_text:
            original_names = [
                name.strip() for name in original_names_text.split(',')
                if name.strip()
            ]
            data['original_names'] = original_names
        
        # Добавляем алиасы если указаны
        aliases_text = self.aliases_edit.text().strip()
        if aliases_text:
            aliases = [
                aid.strip() for aid in aliases_text.split(',')
                if aid.strip()
            ]
            data['_aliases'] = aliases
        
        return self.id_edit.text().strip(), data
