#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LogStorm - Refactored"""

from analyzer import AttendanceService, DataLoader
from analyzer.reporters import ExcelReporter, SummaryReporter
from config import LOGS_FILE, PERSON_MAPPING_FILE, OUTPUT_EXCEL_FILE

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class LogStormApp:
    def __init__(self):
        self.records = []
    
    def run(self):
        print("="*80)
        print("LogStorm - Refactored Version")
        print("="*80)
        
        print("\n[1/4] Загрузка...")
        df = DataLoader.load_logs(LOGS_FILE)
        
        # Профили теперь опциональны
        import os
        if PERSON_MAPPING_FILE and os.path.exists(PERSON_MAPPING_FILE):
            from analyzer import PersonMapper
            mapper = PersonMapper(PERSON_MAPPING_FILE)
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
        excel_reporter = ExcelReporter(self.records)
        excel_reporter.generate_report(OUTPUT_EXCEL_FILE)
        
        print("\n[OK] Анализ завершен!")
        print(f"Отчёт сохранён: {OUTPUT_EXCEL_FILE}")


def main():
    app = LogStormApp()
    app.run()


if __name__ == '__main__':
    main()
