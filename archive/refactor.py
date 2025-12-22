#!/usr/bin/env python3
"""
Скрипт автоматического рефакторинга проекта LogStorm
Выполняет пошаговую очистку с подтверждением
"""

import os
import shutil
from pathlib import Path

# Корневая директория проекта
ROOT_DIR = Path(__file__).parent

# Списки файлов для удаления
FILES_TO_DELETE = {
    "Устаревшие исполняемые": [
        "main_old.py",
        "main_test.py",
        "encode_credentials.py",
        "update_mapping_from_prefs.py",
        "examples_person_mapper.py",
    ],
    "Устаревшие тесты": [
        "test_gui_ndjson.py",
        "test_event_merging.py",
        "test_models.py",
        "test_multiple_files.py",
        "test_ndjson_loader.py",
        "test_without_prefs.py",
    ],
    "Устаревшая документация": [
        "CHANGELOG_GUI.md",
        "CHANGELOG_v2.7.md",
        "CHANGELOG_v2.8.md",
        "CLASSIFICATION_GUIDE.md",
        "GIGACHAT_SETUP.md",
        "GUI_GUIDE.md",
        "GUI_NDJSON_CHECKLIST.md",
        "GUI_NDJSON_FIX.md",
        "GUI_NDJSON_GUIDE.md",
        "IMPLEMENTATION_SUMMARY.md",
        "MULTIPLE_FILES_GUIDE.md",
        "NDJSON_MAPPING_GUIDE.md",
        "OPTIONAL_PREFS_GUIDE.md",
        "QUICKSTART_NDJSON.md",
        "REFACTORING.md",
        "REFACTORING_PLAN.md",
        "TESTING_PERSON_MAPPER.md",
        "ai_summary.txt",
    ],
    "Дубликаты конфигурации": [
        "person_prefs.json",
    ]
}

# Файлы для перемещения
FILES_TO_MOVE = {
    "tests/": [
        "test_mapping_optional.py",
        "test_melanya_mapping.py",
        "test_ndjson_with_mapper.py",
    ]
}


def create_backup():
    """Создать папку для резервного копирования"""
    backup_dir = ROOT_DIR / "refactoring_backup"
    backup_dir.mkdir(exist_ok=True)
    return backup_dir


def delete_files_interactive():
    """Интерактивное удаление файлов с подтверждением"""
    backup_dir = create_backup()
    
    print("=" * 70)
    print("РЕФАКТОРИНГ LOGSTORM - УДАЛЕНИЕ УСТАРЕВШИХ ФАЙЛОВ")
    print("=" * 70)
    
    for category, files in FILES_TO_DELETE.items():
        print(f"\n📦 {category}:")
        existing_files = []
        
        for filename in files:
            filepath = ROOT_DIR / filename
            if filepath.exists():
                size = filepath.stat().st_size / 1024  # KB
                print(f"   ✓ {filename} ({size:.1f} KB)")
                existing_files.append(filepath)
            else:
                print(f"   - {filename} (не найден)")
        
        if not existing_files:
            print(f"   → Нет файлов для удаления")
            continue
        
        response = input(f"\n🗑️  Удалить {len(existing_files)} файлов? [y/N]: ")
        
        if response.lower() == 'y':
            for filepath in existing_files:
                # Создаем backup
                backup_path = backup_dir / filepath.name
                shutil.copy2(filepath, backup_path)
                # Удаляем
                filepath.unlink()
                print(f"   ✅ Удален: {filepath.name}")
            print(f"   💾 Backup создан в: {backup_dir}")
        else:
            print(f"   ⏭️  Пропущено")


def move_files_interactive():
    """Интерактивное перемещение файлов"""
    print("\n" + "=" * 70)
    print("ПЕРЕМЕЩЕНИЕ ФАЙЛОВ")
    print("=" * 70)
    
    for target_dir, files in FILES_TO_MOVE.items():
        target_path = ROOT_DIR / target_dir
        print(f"\n📁 Перемещение в {target_dir}:")
        
        existing_files = []
        for filename in files:
            filepath = ROOT_DIR / filename
            if filepath.exists():
                print(f"   ✓ {filename}")
                existing_files.append(filepath)
            else:
                print(f"   - {filename} (не найден)")
        
        if not existing_files:
            print(f"   → Нет файлов для перемещения")
            continue
        
        response = input(f"\n📦 Переместить {len(existing_files)} файлов? [y/N]: ")
        
        if response.lower() == 'y':
            target_path.mkdir(exist_ok=True)
            for filepath in existing_files:
                new_path = target_path / filepath.name
                shutil.move(str(filepath), str(new_path))
                print(f"   ✅ Перемещен: {filepath.name} → {target_dir}")
        else:
            print(f"   ⏭️  Пропущено")


def check_directory_structure():
    """Проверить структуру директорий после рефакторинга"""
    print("\n" + "=" * 70)
    print("ПРОВЕРКА СТРУКТУРЫ ПРОЕКТА")
    print("=" * 70)
    
    required_dirs = ['analyzers', 'models', 'reporters', 'services', 'utils', 'validators']
    
    for dirname in required_dirs:
        dirpath = ROOT_DIR / dirname
        if dirpath.exists() and dirpath.is_dir():
            files = list(dirpath.glob('*.py'))
            print(f"   ✅ {dirname}/ ({len(files)} файлов)")
        else:
            print(f"   ❌ {dirname}/ (не найдена)")


def main():
    print("\n🚀 LogStorm Refactoring Tool\n")
    print("Этот скрипт выполнит:")
    print("  1. Удаление устаревших файлов (с backup)")
    print("  2. Перемещение актуальных тестов в tests/")
    print("  3. Проверку структуры проекта")
    
    input("\nНажмите Enter для продолжения или Ctrl+C для отмены...")
    
    delete_files_interactive()
    move_files_interactive()
    check_directory_structure()
    
    print("\n" + "=" * 70)
    print("✅ РЕФАКТОРИНГ ЗАВЕРШЕН")
    print("=" * 70)
    print(f"\n💾 Backup файлов: {ROOT_DIR / 'refactoring_backup'}")
    print("\nСледующие шаги:")
    print("  1. Проверьте работу приложения: python run_gui.py")
    print("  2. Запустите тесты: python -m pytest tests/")
    print("  3. Если всё работает - удалите refactoring_backup/")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Рефакторинг отменен пользователем")
    except Exception as e:
        print(f"\n\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
