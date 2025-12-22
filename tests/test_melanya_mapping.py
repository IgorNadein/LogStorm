#!/usr/bin/env python3
"""
Тест маппинга для Employee Alpha Alias/Employee Alpha
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.person_mapper import PersonMapper

def test_melanya_mapping():
    print("=" * 60)
    print("Тест объединения ID 666 и ID 19")
    print("=" * 60)
    
    # Загружаем маппер
    mapper = PersonMapper('person_mapping.json')
    
    print(f"\n[INFO] Загружено:")
    print(f"   - Маппингов: {len(mapper.mappings)}")
    print(f"   - Aliases: {len(mapper.aliases)}")
    print(f"   - Reverse alias map: {len(mapper.index.reverse_alias_map)}")
    
    print(f"\n[INFO] Проверка aliases:")
    print(f"   aliases['19'] = {mapper.aliases.get('19')}")
    print(f"   reverse_alias_map['666'] = {mapper.index.reverse_alias_map.get('666')}")
    
    print(f"\n🧪 Тест resolve_person_id:")
    
    # Тест 1: ID 19 (главный)
    resolved_19 = mapper.resolve_person_id('19', 'Employee Alpha')
    display_19 = mapper.get_display_name(resolved_19)
    print(f"   ID '19' -> resolved='{resolved_19}', display='{display_19}'")
    
    # Тест 2: ID 666 (алиас)
    resolved_666 = mapper.resolve_person_id('666', 'Employee Alpha Alias')
    display_666 = mapper.get_display_name(resolved_666)
    print(f"   ID '666' -> resolved='{resolved_666}', display='{display_666}'")
    
    # Тест 3: Проверка с разными типами
    test_ids = ['19', '666', 19, 666]
    print(f"\n🔢 Тест разных типов ID:")
    for test_id in test_ids:
        test_id_str = str(test_id)
        resolved = mapper.resolve_person_id(test_id_str)
        display = mapper.get_display_name(resolved)
        print(f"   {type(test_id).__name__:8} {test_id:>3} -> '{resolved}' -> '{display}'")
    
    # Результат
    print(f"\n✅ Результат:")
    if resolved_19 == resolved_666 == '19':
        print(f"   ✅ ID 666 и 19 объединяются в ID '19'")
        print(f"   ✅ Отображаемое имя: '{display_19}'")
    else:
        print(f"   ❌ ПРОБЛЕМА: ID не объединяются!")
        print(f"      resolved_19 = '{resolved_19}'")
        print(f"      resolved_666 = '{resolved_666}'")

if __name__ == '__main__':
    test_melanya_mapping()
