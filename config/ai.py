"""
AI Configuration - настройки AI (GigaChat)
"""

from dataclasses import dataclass


@dataclass
class AIConfig:
    """Настройки AI анализа"""
    
    gigachat_scope: str = 'GIGACHAT_API_PERS'
    ai_prompt_sentences: int = 5


# Глобальный экземпляр
ai_config = AIConfig()
