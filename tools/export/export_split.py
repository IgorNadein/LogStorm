#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Экспорт событий СКУД с разделением на периоды

Позволяет экспортировать большой период частями для ускорения
и возможности параллельного запуска.

Функции:
  - Разбиение большого периода на части
  - Объединение результатов с дедупликацией
  - Защита от перезаписи существующих файлов
  - Возможность продолжения прерванного экспорта
"""

import argparse
import subprocess
import sys
import os
from datetime import datetime, timedelta
import time
from typing import List, Tuple

from export_utils import (
    get_safe_output_path,
    backup_existing_file,
    merge_ndjson_files,
    ensure_dir,
    count_events_in_file,
)


class ChunkExporter:
    """Экспортер с разбиением на периоды"""
    
    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        start_date: datetime,
        end_date: datetime,
        chunk_days: int = 30,
        page_size: int = 30,
        pic_enabled: bool = False,
        verbose: bool = False,
        output_file: str = "events_merged.ndjson",
        chunks_dir: str = "chunks",
        keep_chunks: bool = False,
        force: bool = False,
        deduplicate: bool = True,
    ):
        self.host = host
        self.user = user
        self.password = password
        self.start_date = start_date
        self.end_date = end_date
        self.chunk_days = chunk_days
        self.page_size = page_size
        self.pic_enabled = pic_enabled
        self.verbose = verbose
        self.output_file = output_file
        self.chunks_dir = chunks_dir
        self.keep_chunks = keep_chunks
        self.force = force
        self.deduplicate = deduplicate
        
        # Статистика
        self.chunk_files: List[str] = []
        self.total_events = 0
        self.total_time = 0.0
        self.successful_chunks = 0
        self.failed_chunks = 0
        self.skipped_chunks = 0
    
    def calculate_chunks(self) -> List[Tuple[datetime, datetime]]:
        """Расчёт периодов для экспорта"""
        chunks = []
        current = self.start_date
        
        while current < self.end_date:
            chunk_end = min(
                current + timedelta(days=self.chunk_days),
                self.end_date
            )
            chunks.append((current, chunk_end))
            current = chunk_end
        
        return chunks
    
    def get_chunk_filename(
        self,
        index: int,
        start: datetime,
        end: datetime
    ) -> str:
        """Генерация имени файла для чанка"""
        start_str = start.strftime('%Y%m%d')
        end_str = end.strftime('%Y%m%d')
        
        if self.keep_chunks:
            ensure_dir(self.chunks_dir)
            return os.path.join(
                self.chunks_dir,
                f"chunk_{index:03d}_{start_str}_{end_str}.ndjson"
            )
        else:
            return f"temp_chunk_{index:03d}.ndjson"
    
    def chunk_exists_with_data(self, filepath: str) -> bool:
        """Проверка, существует ли чанк с данными"""
        if not os.path.exists(filepath):
            return False
        
        count = count_events_in_file(filepath)
        return count > 0
    
    def export_chunk(
        self,
        start: datetime,
        end: datetime,
        output_file: str
    ) -> Tuple[bool, int, float]:
        """
        Экспорт одного периода
        
        Returns:
            Tuple (success, event_count, elapsed_time)
        """
        # Проверка существующего файла (для возможности продолжения)
        if not self.force and self.chunk_exists_with_data(output_file):
            existing_count = count_events_in_file(output_file)
            print(f"   ⏭️  Пропуск: файл существует "
                  f"({existing_count} событий)")
            return True, existing_count, 0.0
        
        cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "export_acs_events.py"),
            "--host", self.host,
            "--user", self.user,
            "--password", self.password,
            "--start", start.strftime("%Y-%m-%dT00:00:00"),
            "--end", end.strftime("%Y-%m-%dT23:59:59"),
            "--out", output_file,
            "--page", str(self.page_size),
            "--force",  # Разрешаем перезапись для temp файлов
            "--deduplicate",  # Всегда дедупликация
        ]
        
        if self.pic_enabled:
            cmd.append("--pic")
        
        if self.verbose:
            cmd.append("--verbose")
        
        print(f"📅 Экспорт: {start.date()} → {end.date()}")
        print(f"   Файл: {output_file}")
        
        start_time = time.perf_counter()
        
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            elapsed = time.perf_counter() - start_time
            
            # Подсчитать события
            event_count = count_events_in_file(output_file)
            
            print(f"   ✅ Готово: {event_count} событий за {elapsed:.1f}с")
            return True, event_count, elapsed
            
        except subprocess.CalledProcessError as e:
            elapsed = time.perf_counter() - start_time
            print(f"   ❌ Ошибка: {e}")
            if e.stderr:
                print(f"   Детали: {e.stderr[:200]}")
            return False, 0, elapsed
    
    def run(self) -> Tuple[int, str]:
        """
        Запуск экспорта
        
        Returns:
            Tuple (total_events, output_path)
        """
        chunks = self.calculate_chunks()
        total_chunks = len(chunks)
        total_days = (self.end_date - self.start_date).days
        
        # Определение выходного файла
        output_path = get_safe_output_path(
            self.output_file,
            force=self.force
        )
        
        self._print_header(total_days, total_chunks)
        
        overall_start = time.perf_counter()
        
        try:
            for i, (chunk_start, chunk_end) in enumerate(chunks, 1):
                print(f"\n[{i}/{total_chunks}]", end=" ")
                
                chunk_file = self.get_chunk_filename(i, chunk_start, chunk_end)
                self.chunk_files.append(chunk_file)
                
                success, events, elapsed = self.export_chunk(
                    chunk_start,
                    chunk_end,
                    chunk_file
                )
                
                if success:
                    if elapsed > 0:
                        self.successful_chunks += 1
                    else:
                        self.skipped_chunks += 1
                    self.total_events += events
                    self.total_time += elapsed
                else:
                    self.failed_chunks += 1
        
        except KeyboardInterrupt:
            print("\n\n⚠️ Экспорт прерван пользователем")
            print(f"   Успешно: {self.successful_chunks}/{i} периодов")
        
        overall_elapsed = time.perf_counter() - overall_start
        
        # Объединение файлов
        existing_files = [f for f in self.chunk_files if os.path.exists(f)]
        
        if existing_files:
            total_merged, duplicates = merge_ndjson_files(
                existing_files,
                output_path,
                deduplicate=self.deduplicate,
                force=True  # Мы уже проверили путь выше
            )
            
            # Удалить временные файлы
            if not self.keep_chunks:
                self._cleanup_temp_files()
        else:
            total_merged = 0
            duplicates = 0
        
        self._print_summary(overall_elapsed, total_chunks, output_path, duplicates)
        
        return total_merged, output_path
    
    def _cleanup_temp_files(self) -> None:
        """Удаление временных файлов"""
        print("\n🗑️  Удаление временных файлов...")
        
        for filepath in self.chunk_files:
            if not filepath.startswith("temp_"):
                continue
            
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    print(f"   Удалён: {filepath}")
            except Exception as e:
                print(f"   ⚠️ Не удалось удалить {filepath}: {e}")
    
    def _print_header(self, total_days: int, total_chunks: int) -> None:
        """Вывод заголовка"""
        print("=" * 70)
        print("📊 ЭКСПОРТ СОБЫТИЙ СКУД С РАЗДЕЛЕНИЕМ НА ПЕРИОДЫ")
        print("=" * 70)
        print(f"Период:           {self.start_date.date()} → {self.end_date.date()}")
        print(f"Всего дней:       {total_days}")
        print(f"Размер периода:   {self.chunk_days} дней")
        print(f"Количество частей: {total_chunks}")
        print(f"Изображения:      {'Да' if self.pic_enabled else 'Нет'}")
        print(f"Размер страницы:  {self.page_size}")
        print(f"Дедупликация:     {'Да' if self.deduplicate else 'Нет'}")
        print(f"Сохранять части:  {'Да' if self.keep_chunks else 'Нет'}")
        print("=" * 70)
    
    def _print_summary(
        self,
        elapsed: float,
        total_chunks: int,
        output_path: str,
        duplicates: int
    ) -> None:
        """Вывод итогов"""
        print("\n" + "=" * 70)
        print("📈 ИТОГИ")
        print("=" * 70)
        
        print(f"Успешных периодов:  {self.successful_chunks}/{total_chunks}")
        
        if self.skipped_chunks > 0:
            print(f"Пропущено (существуют): {self.skipped_chunks}")
        
        if self.failed_chunks > 0:
            print(f"Неудачных периодов: {self.failed_chunks}")
        
        print(f"Всего событий:      {self.total_events}")
        
        if duplicates > 0:
            print(f"Удалено дубликатов: {duplicates}")
        
        print(f"Общее время:        {elapsed:.1f}с ({elapsed/60:.1f} мин)")
        
        if self.total_events > 0 and elapsed > 0:
            print(f"Скорость:           {self.total_events/elapsed:.1f} событий/сек")
        
        if self.successful_chunks > 0 and self.total_time > 0:
            avg_time = self.total_time / self.successful_chunks
            print(f"Среднее на период:  {avg_time:.1f}с")
        
        print(f"\n✅ Результат: {output_path}")
        print("=" * 70)


def create_argument_parser() -> argparse.ArgumentParser:
    """Создание парсера аргументов"""
    parser = argparse.ArgumentParser(
        description="Экспорт событий СКУД с разделением на периоды",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Базовый экспорт за год
  python export_split.py --password CHANGE_ME --start 2024-01-01 --end 2024-12-31

  # С сохранением промежуточных файлов
  python export_split.py --password CHANGE_ME --start 2024-01-01 --end 2024-12-31 --keep-chunks

  # Продолжение прерванного экспорта (пропускает существующие файлы)
  python export_split.py --password CHANGE_ME --start 2024-01-01 --end 2024-12-31 --keep-chunks

  # Принудительный перезапуск
  python export_split.py --password CHANGE_ME --start 2024-01-01 --end 2024-12-31 --force
        """
    )
    
    # Подключение
    conn = parser.add_argument_group('Подключение')
    conn.add_argument("--host", default="192.168.1.101",
                      help="IP-адрес устройства")
    conn.add_argument("--user", default="admin",
                      help="Имя пользователя")
    conn.add_argument("--password", required=True,
                      help="Пароль")
    
    # Период
    period = parser.add_argument_group('Период')
    period.add_argument("--start", required=True,
                        help="Начальная дата (YYYY-MM-DD)")
    period.add_argument("--end", required=True,
                        help="Конечная дата (YYYY-MM-DD)")
    period.add_argument("--chunk-days", type=int, default=30,
                        help="Размер периода в днях (по умолчанию 30)")
    
    # Параметры экспорта
    export = parser.add_argument_group('Параметры экспорта')
    export.add_argument("--pic", action="store_true",
                        help="Включить экспорт изображений")
    export.add_argument("--page", type=int, default=30,
                        help="Размер страницы (maxResults)")
    export.add_argument("--verbose", action="store_true",
                        help="Подробный вывод")
    
    # Выходные файлы
    output = parser.add_argument_group('Выходные файлы')
    output.add_argument("--out", default="events_merged.ndjson",
                        help="Итоговый объединённый файл")
    output.add_argument("--chunks-dir", default="chunks",
                        help="Директория для промежуточных файлов")
    output.add_argument("--keep-chunks", action="store_true",
                        help="Сохранить промежуточные файлы")
    
    # Режим работы
    mode = parser.add_argument_group('Режим работы')
    mode.add_argument("--force", action="store_true",
                      help="Перезаписать существующие файлы")
    mode.add_argument("--no-deduplicate", action="store_true",
                      help="Отключить дедупликацию при объединении")
    mode.add_argument("--backup", action="store_true",
                      help="Создать резервную копию перед перезаписью")
    
    return parser


def parse_date(date_str: str, name: str) -> datetime:
    """Парсинг даты из строки"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print(f"❌ Ошибка формата даты {name}: {date_str}")
        print("   Используйте формат: YYYY-MM-DD")
        sys.exit(1)


def main() -> None:
    """Главная функция"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Парсинг дат
    start_date = parse_date(args.start, "начальной")
    end_date = parse_date(args.end, "конечной")
    
    if start_date >= end_date:
        print("❌ Начальная дата должна быть раньше конечной")
        sys.exit(1)
    
    # Резервная копия
    if args.backup and os.path.exists(args.out):
        backup_existing_file(args.out)
    
    # Создание экспортера
    exporter = ChunkExporter(
        host=args.host,
        user=args.user,
        password=args.password,
        start_date=start_date,
        end_date=end_date,
        chunk_days=args.chunk_days,
        page_size=args.page,
        pic_enabled=args.pic,
        verbose=args.verbose,
        output_file=args.out,
        chunks_dir=args.chunks_dir,
        keep_chunks=args.keep_chunks,
        force=args.force,
        deduplicate=not args.no_deduplicate,
    )
    
    # Запуск
    script_start = time.perf_counter()
    
    try:
        total_events, output_path = exporter.run()
    except KeyboardInterrupt:
        print("\n⚠️ Прервано пользователем")
        sys.exit(1)
    finally:
        script_elapsed = time.perf_counter() - script_start
        print(f"\n⏱️  Общее время скрипта: {script_elapsed:.2f} сек")


if __name__ == "__main__":
    main()
