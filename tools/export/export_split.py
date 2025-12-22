#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Экспорт событий СКУД с разделением на периоды
Позволяет экспортировать большой период частями для ускорения
и возможности параллельного запуска
"""

import argparse
import subprocess
import sys
import os
from datetime import datetime, timedelta
import time


def export_period(host, user, password, start_date, end_date, output_file, 
                  pic=False, page=30, verbose=False):
    """Экспорт одного периода"""
    
    cmd = [
        sys.executable,
        "export_acs_events.py",
        "--host", host,
        "--user", user,
        "--password", password,
        "--start", start_date.strftime("%Y-%m-%dT00:00:00"),
        "--end", end_date.strftime("%Y-%m-%dT23:59:59"),
        "--out", output_file,
        "--page", str(page),
    ]
    
    if pic:
        cmd.append("--pic")
    
    if verbose:
        cmd.append("--verbose")
    
    print(f"📅 Экспорт: {start_date.date()} → {end_date.date()}")
    print(f"   Файл: {output_file}")
    
    start_time = time.perf_counter()
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        elapsed = time.perf_counter() - start_time
        
        # Подсчитать события
        event_count = 0
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                event_count = sum(1 for _ in f)
        
        print(f"   ✅ Готово: {event_count} событий за {elapsed:.1f}с")
        return True, event_count, elapsed
        
    except subprocess.CalledProcessError as e:
        elapsed = time.perf_counter() - start_time
        print(f"   ❌ Ошибка: {e}")
        return False, 0, elapsed
    except KeyboardInterrupt:
        print("\n   ⚠️ Прервано пользователем")
        raise


def merge_files(files, output_file):
    """Объединение NDJSON файлов"""
    print(f"\n📦 Объединение {len(files)} файлов...")
    
    total_lines = 0
    
    with open(output_file, 'w', encoding='utf-8') as out:
        for i, f in enumerate(files, 1):
            if not os.path.exists(f):
                print(f"   ⚠️ Файл {f} не найден, пропускаем")
                continue
            
            lines = 0
            with open(f, 'r', encoding='utf-8') as inp:
                for line in inp:
                    out.write(line)
                    lines += 1
            
            total_lines += lines
            print(f"   [{i}/{len(files)}] {f}: {lines} событий")
    
    print(f"✅ Объединено: {total_lines} событий → {output_file}")
    return total_lines


def main():
    parser = argparse.ArgumentParser(
        description="Экспорт событий СКУД с разделением на периоды"
    )
    
    # Параметры устройства
    parser.add_argument("--host", default="192.168.1.101")
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", required=True)
    
    # Период
    parser.add_argument("--start", required=True, 
                       help="Начальная дата (YYYY-MM-DD)")
    parser.add_argument("--end", required=True,
                       help="Конечная дата (YYYY-MM-DD)")
    
    # Разделение на периоды
    parser.add_argument("--chunk-days", type=int, default=30,
                       help="Размер периода в днях (по умолчанию 30)")
    
    # Параметры экспорта
    parser.add_argument("--pic", action="store_true",
                       help="Включить экспорт изображений")
    parser.add_argument("--page", type=int, default=30,
                       help="Размер страницы (maxResults)")
    parser.add_argument("--verbose", action="store_true",
                       help="Подробный вывод")
    
    # Выходные файлы
    parser.add_argument("--out", default="events_merged.ndjson",
                       help="Итоговый объединённый файл")
    parser.add_argument("--keep-chunks", action="store_true",
                       help="Сохранить промежуточные файлы")
    parser.add_argument("--chunks-dir", default="chunks",
                       help="Директория для промежуточных файлов")
    
    args = parser.parse_args()
    
    # Парсинг дат
    try:
        start_date = datetime.strptime(args.start, "%Y-%m-%d")
        end_date = datetime.strptime(args.end, "%Y-%m-%d")
    except ValueError as e:
        print(f"❌ Ошибка формата даты: {e}")
        print("   Используйте формат: YYYY-MM-DD")
        sys.exit(1)
    
    if start_date >= end_date:
        print("❌ Начальная дата должна быть раньше конечной")
        sys.exit(1)
    
    # Создать директорию для промежуточных файлов
    if args.keep_chunks:
        os.makedirs(args.chunks_dir, exist_ok=True)
    
    # Расчёт периодов
    total_days = (end_date - start_date).days
    num_chunks = (total_days + args.chunk_days - 1) // args.chunk_days
    
    print("=" * 70)
    print("📊 ЭКСПОРТ СОБЫТИЙ СКУД С РАЗДЕЛЕНИЕМ НА ПЕРИОДЫ")
    print("=" * 70)
    print(f"Период:        {start_date.date()} → {end_date.date()}")
    print(f"Всего дней:    {total_days}")
    print(f"Размер периода: {args.chunk_days} дней")
    print(f"Количество периодов: {num_chunks}")
    print(f"Изображения:   {'Да' if args.pic else 'Нет'}")
    print(f"Размер страницы: {args.page}")
    print("=" * 70)
    print()
    
    # Экспорт по периодам
    current = start_date
    chunk_files = []
    total_events = 0
    total_time = 0
    successful = 0
    
    overall_start = time.perf_counter()
    
    try:
        for i in range(num_chunks):
            chunk_end = min(current + timedelta(days=args.chunk_days), end_date)
            
            # Имя файла для периода
            if args.keep_chunks:
                chunk_file = os.path.join(
                    args.chunks_dir,
                    f"chunk_{i+1:03d}_{current.strftime('%Y%m%d')}_{chunk_end.strftime('%Y%m%d')}.ndjson"
                )
            else:
                chunk_file = f"temp_chunk_{i+1:03d}.ndjson"
            
            chunk_files.append(chunk_file)
            
            # Экспорт
            success, events, elapsed = export_period(
                host=args.host,
                user=args.user,
                password=args.password,
                start_date=current,
                end_date=chunk_end,
                output_file=chunk_file,
                pic=args.pic,
                page=args.page,
                verbose=args.verbose
            )
            
            if success:
                successful += 1
                total_events += events
                total_time += elapsed
            
            current = chunk_end
            print()
    
    except KeyboardInterrupt:
        print("\n⚠️ Экспорт прерван пользователем")
        print(f"Успешно экспортировано: {successful}/{i+1} периодов")
    
    overall_elapsed = time.perf_counter() - overall_start
    
    # Объединение файлов
    if chunk_files:
        print()
        merged_events = merge_files(chunk_files, args.out)
        
        # Удалить временные файлы
        if not args.keep_chunks:
            print("\n🗑️  Удаление временных файлов...")
            for f in chunk_files:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                        print(f"   Удалён: {f}")
                except Exception as e:
                    print(f"   ⚠️ Не удалось удалить {f}: {e}")
    
    # Итоговая статистика
    print("\n" + "=" * 70)
    print("📈 ИТОГИ")
    print("=" * 70)
    print(f"Успешных периодов: {successful}/{num_chunks}")
    print(f"Всего событий:     {total_events}")
    print(f"Общее время:       {overall_elapsed:.1f}с ({overall_elapsed/60:.1f} мин)")
    
    if total_events > 0:
        print(f"Скорость:          {total_events/overall_elapsed:.1f} событий/сек")
    
    if successful > 0:
        avg_time = total_time / successful
        print(f"Среднее время на период: {avg_time:.1f}с")
    
    print(f"\n✅ Результат сохранён в: {args.out}")
    print("=" * 70)


if __name__ == "__main__":
    main()
