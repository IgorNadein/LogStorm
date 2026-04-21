#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LogStorm - Refactored"""

from services import DataLoader, AttendanceService
from reporters import SummaryReporter, ExcelReporter
from core import LogStormCore


class LogStormApp:
    def __init__(self, core: LogStormCore | None = None):
        self.core = core or LogStormCore.from_sources()
        self.records = []
    
    def run(self):
        print("="*80)
        print("LogStorm - Refactored Version")
        print("="*80)
        
        print("\n[1/4] Загрузка...")
        import os
        cli_settings = self.core.settings.cli
        if not os.path.exists(cli_settings.logs_file):
            raise FileNotFoundError(
                f"Файл логов не найден: {cli_settings.logs_file}. "
                "Укажите существующий путь в config/paths.py."
            )
        df = DataLoader.load_logs(cli_settings.logs_file)
        
        # Профили теперь опциональны
        if (
            cli_settings.person_mapping_file
            and os.path.exists(cli_settings.person_mapping_file)
        ):
            from services import PersonMapper
            mapper = PersonMapper(cli_settings.person_mapping_file)
            prefs = mapper.convert_to_prefs_format()
        else:
            print("ℹ️ Маппинг не задан - используются дефолты")
            prefs = {}
        
        print(f"Загружено {len(df)} записей, {len(prefs)} профилей")
        df = DataLoader.filter_known_users(df, prefs)
        
        print("\n[2/4] Анализ...")
        service = AttendanceService(df, prefs)
        self.records = service.analyze_all()
        
        print("\n[3/4] Сводка...")
        summary = SummaryReporter(self.records)
        summary.print_summary()
        
        print("\n[4/4] Excel отчёт...")
        output_dir = os.path.dirname(cli_settings.output_excel_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        excel_reporter = ExcelReporter(self.records)
        excel_reporter.generate_report(cli_settings.output_excel_file)
        
        print("\n[OK] Анализ завершен!")
        print(f"Отчёт сохранён: {cli_settings.output_excel_file}")


def main():
    app = LogStormApp()
    app.run()


if __name__ == '__main__':
    main()
