# -*- coding: utf-8 -*-
"""
Автоматическое определение тем кластеров
"""

import pandas as pd
import numpy as np
from collections import Counter
import re
from typing import List, Dict
import config
import os

# Для извлечения ключевых слов
try:
    import pymorphy2
    morph = pymorphy2.MorphAnalyzer()
except:
    morph = None
    print("pymorphy2 не установлен. Лемматизация будет упрощенной.")


class TopicExtractor:
    """
    Класс для извлечения тем из кластеров
    """
    
    def __init__(self):
        """Инициализация"""
        # Стоп-слова для русского языка
        self.stop_words = self._load_stop_words()
        
        # Ключевые слова для тематик приказов
        self.theme_keywords = {
            'кадры': ['назначение', 'освобождение', 'должность', 'руководитель', 
                     'директор', 'заместитель', 'кадр', 'увольнение', 'прием'],
            'финансы': ['бюджет', 'финансирование', 'средства', 'расходы', 
                       'выплата', 'субсидия', 'грант', 'оплата'],
            'регламент': ['порядок', 'процедура', 'правила', 'требования', 
                         'регламент', 'инструкция', 'методика'],
            'структура': ['структура', 'состав', 'организация', 'подразделение', 
                         'департамент', 'управление', 'отдел'],
            'программы': ['программа', 'проект', 'мероприятие', 'план', 
                         'разработка', 'реализация'],
            'контроль': ['контроль', 'надзор', 'проверка', 'аудит', 'мониторинг', 
                        'инспекция'],
            'документы': ['утверждение', 'изменение', 'форма', 'образец', 
                         'документ', 'положение', 'устав'],
            'отмена': ['признание', 'утративший', 'отмена', 'прекращение', 'силу'],
            'территории': ['регион', 'область', 'территория', 'федеральный', 
                          'округ', 'субъект'],
            'лицензирование': ['лицензия', 'аккредитация', 'сертификация', 
                              'разрешение', 'допуск']
        }
    
    def _load_stop_words(self) -> set:
        """Загружает стоп-слова"""
        stop_words = {
            'в', 'и', 'на', 'с', 'по', 'для', 'от', 'до', 'к', 'о', 'об', 
            'при', 'за', 'у', 'из', 'со', 'не', 'что', 'как', 'это', 'а', 
            'но', 'бы', 'же', 'ли', 'или', 'да', 'нет', 'г', 'года', 'году',
            'приказ', 'министерство', 'российский', 'федерация', 'российской',
            'федерации', 'россии', 'минэкономразвития', 'минюст', 'пункт',
            'статья', 'абзац', 'часть', 'номер', 'зарегистрирован', 'утверждение',
            'соответствие', 'основание', 'внесение', 'согласно', 'следующий',
            'данный', 'который', 'являться', 'быть', 'мочь', 'свой', 'весь'
        }
        return stop_words
    
    def _lemmatize(self, word: str) -> str:
        """Лемматизация слова"""
        if morph:
            parsed = morph.parse(word)[0]
            return parsed.normal_form
        else:
            # Упрощенная версия - просто lowercase
            return word.lower()
    
    def extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """
        Извлекает ключевые слова из текста
        
        Args:
            text: текст
            top_n: количество топ слов
            
        Returns:
            список ключевых слов
        """
        if not text or pd.isna(text):
            return []
        
        # Приводим к нижнему регистру и разбиваем на слова
        words = re.findall(r'\b[а-яё]+\b', text.lower())
        
        # Фильтруем стоп-слова и короткие слова
        filtered_words = []
        for word in words:
            if word not in self.stop_words and len(word) > 3:
                lemma = self._lemmatize(word)
                if lemma not in self.stop_words:
                    filtered_words.append(lemma)
        
        # Подсчитываем частоту
        word_freq = Counter(filtered_words)
        
        # Возвращаем топ слова
        return [word for word, _ in word_freq.most_common(top_n)]
    
    def get_cluster_keywords(self, texts: List[str], top_n: int = None) -> List[str]:
        """
        Извлекает ключевые слова для кластера
        
        Args:
            texts: список текстов в кластере
            top_n: количество топ слов
            
        Returns:
            список ключевых слов
        """
        top_n = top_n or config.TOP_KEYWORDS
        
        # Объединяем все тексты
        combined_text = ' '.join([str(t) for t in texts if t and not pd.isna(t)])
        
        # Извлекаем ключевые слова
        return self.extract_keywords(combined_text, top_n)
    
    def identify_theme(self, keywords: List[str]) -> str:
        """
        Определяет тему на основе ключевых слов
        
        Args:
            keywords: список ключевых слов
            
        Returns:
            название темы
        """
        # Подсчитываем совпадения с предопределенными темами
        theme_scores = {}
        
        for theme, theme_words in self.theme_keywords.items():
            score = sum(1 for kw in keywords if kw in theme_words)
            if score > 0:
                theme_scores[theme] = score
        
        # Возвращаем тему с наибольшим скором
        if theme_scores:
            best_theme = max(theme_scores, key=theme_scores.get)
            return best_theme
        else:
            # Если не нашли совпадений, используем топ ключевые слова
            return '_'.join(keywords[:3])
    
    def generate_cluster_names(self, df: pd.DataFrame) -> Dict[int, Dict]:
        """
        Генерирует названия для всех кластеров
        
        Args:
            df: DataFrame с кластеризованными данными
            
        Returns:
            словарь с информацией о кластерах
        """
        cluster_info = {}
        
        clusters = sorted(df['cluster'].unique())
        
        print(f"Генерация названий для {len(clusters)} кластеров...")
        
        for cluster_id in clusters:
            # Получаем тексты кластера
            cluster_texts = df[df['cluster'] == cluster_id]['text_for_embedding'].tolist()
            
            # Извлекаем ключевые слова
            keywords = self.get_cluster_keywords(cluster_texts)
            
            # Определяем тему
            theme = self.identify_theme(keywords)
            
            # Количество документов
            n_docs = len(cluster_texts)
            
            # Примеры документов (первые 3)
            sample_docs = df[df['cluster'] == cluster_id]['file_name'].head(3).tolist()
            
            cluster_info[cluster_id] = {
                'theme': theme,
                'keywords': keywords,
                'n_documents': n_docs,
                'sample_documents': sample_docs
            }
        
        return cluster_info
    
    def save_cluster_info(self, cluster_info: Dict, filename: str = "cluster_themes.txt"):
        """
        Сохраняет информацию о кластерах в файл
        
        Args:
            cluster_info: информация о кластерах
            filename: имя файла
        """
        output_path = os.path.join(config.CLUSTERS_DIR, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("АВТОМАТИЧЕСКИ ОПРЕДЕЛЕННЫЕ ТЕМЫ КЛАСТЕРОВ\n")
            f.write("=" * 80 + "\n\n")
            
            for cluster_id, info in sorted(cluster_info.items()):
                f.write(f"Кластер {cluster_id}: {info['theme']}\n")
                f.write(f"Количество документов: {info['n_documents']}\n")
                f.write(f"Ключевые слова: {', '.join(info['keywords'])}\n")
                f.write(f"Примеры документов:\n")
                for doc in info['sample_documents']:
                    f.write(f"  - {doc}\n")
                f.write("\n" + "-" * 80 + "\n\n")
        
        print(f"Информация о кластерах сохранена в {output_path}")


def generate_topics(df: pd.DataFrame) -> Dict[int, Dict]:
    """
    Генерирует темы для всех кластеров
    
    Args:
        df: DataFrame с кластеризованными данными
        
    Returns:
        словарь с информацией о кластерах
    """
    extractor = TopicExtractor()
    cluster_info = extractor.generate_cluster_names(df)
    extractor.save_cluster_info(cluster_info)
    
    return cluster_info


if __name__ == "__main__":
    # Тестирование
    print("=== Тестирование извлечения тем ===")
    
    clustered_path = os.path.join(config.CLUSTERS_DIR, "clustered_orders.csv")
    
    if os.path.exists(clustered_path):
        df = pd.read_csv(clustered_path)
        print(f"Загружено {len(df)} документов в {df['cluster'].nunique()} кластерах")
        
        # Генерируем темы
        cluster_info = generate_topics(df)
        
        # Выводим краткую информацию
        print("\nОбзор тем:")
        for cluster_id, info in sorted(cluster_info.items())[:10]:
            print(f"Кластер {cluster_id} ({info['n_documents']} док.): {info['theme']}")
            print(f"  Ключевые слова: {', '.join(info['keywords'][:5])}")
    else:
        print("Файл с кластеризованными данными не найден. Запустите сначала clustering.py")
