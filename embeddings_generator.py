# -*- coding: utf-8 -*-
"""
Генерация эмбеддингов для приказов используя ruBERT и Sentence-BERT
"""

import torch
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel
from tqdm import tqdm
import pickle
import os
import config


class EmbeddingsGenerator:
    """
    Класс для генерации эмбеддингов текстов приказов
    """
    
    def __init__(self, use_sbert=True, use_rubert=True):
        """
        Инициализация моделей
        
        Args:
            use_sbert: использовать Sentence-BERT
            use_rubert: использовать ruBERT
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Используется устройство: {self.device}")
        
        self.use_sbert = use_sbert
        self.use_rubert = use_rubert
        
        # Инициализация Sentence-BERT (более легковесная модель)
        if self.use_sbert:
            print("Загрузка Sentence-BERT модели...")
            self.sbert_model = SentenceTransformer(config.SBERT_MODEL)
            self.sbert_model.to(self.device)
            print("Sentence-BERT загружен")
        
        # Инициализация ruBERT (более мощная, но тяжелая модель)
        if self.use_rubert:
            print("Загрузка ruBERT модели...")
            self.rubert_tokenizer = AutoTokenizer.from_pretrained(config.RUBERT_MODEL)
            self.rubert_model = AutoModel.from_pretrained(config.RUBERT_MODEL)
            self.rubert_model.to(self.device)
            self.rubert_model.eval()
            print("ruBERT загружен")
    
    def get_sbert_embeddings(self, texts: list, batch_size: int = 32) -> np.ndarray:
        """
        Получение эмбеддингов через Sentence-BERT
        
        Args:
            texts: список текстов
            batch_size: размер батча
            
        Returns:
            numpy array с эмбеддингами
        """
        if not self.use_sbert:
            return None
        
        print("Генерация Sentence-BERT эмбеддингов...")
        embeddings = self.sbert_model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            device=self.device
        )
        
        return embeddings
    
    def get_rubert_embeddings(self, texts: list, batch_size: int = 8) -> np.ndarray:
        """
        Получение эмбеддингов через ruBERT
        
        Args:
            texts: список текстов
            batch_size: размер батча
            
        Returns:
            numpy array с эмбеддингами
        """
        if not self.use_rubert:
            return None
        
        print("Генерация ruBERT эмбеддингов...")
        embeddings = []
        
        with torch.no_grad():
            for i in tqdm(range(0, len(texts), batch_size)):
                batch_texts = texts[i:i + batch_size]
                
                # Токенизация
                encoded = self.rubert_tokenizer(
                    batch_texts,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors='pt'
                )
                
                # Перемещаем на устройство
                encoded = {k: v.to(self.device) for k, v in encoded.items()}
                
                # Получаем эмбеддинги
                outputs = self.rubert_model(**encoded)
                
                # Используем [CLS] токен или среднее по всем токенам
                # Вариант 1: [CLS] токен
                cls_embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
                
                # Вариант 2: Mean pooling (закомментирован)
                # attention_mask = encoded['attention_mask']
                # token_embeddings = outputs.last_hidden_state
                # input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
                # sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
                # sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
                # mean_embeddings = (sum_embeddings / sum_mask).cpu().numpy()
                
                embeddings.extend(cls_embeddings)
        
        return np.array(embeddings)
    
    def generate_combined_embeddings(self, texts: list, 
                                     sbert_weight: float = 0.5,
                                     rubert_weight: float = 0.5) -> np.ndarray:
        """
        Генерирует комбинированные эмбеддинги из обеих моделей
        
        Args:
            texts: список текстов
            sbert_weight: вес для Sentence-BERT эмбеддингов
            rubert_weight: вес для ruBERT эмбеддингов
            
        Returns:
            numpy array с комбинированными эмбеддингами
        """
        embeddings_list = []
        
        # Получаем эмбеддинги от обеих моделей
        if self.use_sbert:
            sbert_emb = self.get_sbert_embeddings(texts)
            if sbert_emb is not None:
                # Нормализуем
                sbert_emb = sbert_emb / np.linalg.norm(sbert_emb, axis=1, keepdims=True)
                embeddings_list.append(sbert_emb * sbert_weight)
        
        if self.use_rubert:
            rubert_emb = self.get_rubert_embeddings(texts)
            if rubert_emb is not None:
                # Нормализуем
                rubert_emb = rubert_emb / np.linalg.norm(rubert_emb, axis=1, keepdims=True)
                embeddings_list.append(rubert_emb * rubert_weight)
        
        # Объединяем эмбеддинги
        if len(embeddings_list) == 2:
            print("Комбинирование эмбеддингов...")
            # Конкатенация
            combined = np.concatenate(embeddings_list, axis=1)
        elif len(embeddings_list) == 1:
            combined = embeddings_list[0]
        else:
            raise ValueError("Необходимо активировать хотя бы одну модель")
        
        return combined
    
    def save_embeddings(self, embeddings: np.ndarray, filename: str):
        """Сохранение эмбеддингов"""
        filepath = os.path.join(config.EMBEDDINGS_DIR, filename)
        with open(filepath, 'wb') as f:
            pickle.dump(embeddings, f)
        print(f"Эмбеддинги сохранены в {filepath}")
    
    def load_embeddings(self, filename: str) -> np.ndarray:
        """Загрузка эмбеддингов"""
        filepath = os.path.join(config.EMBEDDINGS_DIR, filename)
        with open(filepath, 'rb') as f:
            embeddings = pickle.load(f)
        print(f"Эмбеддинги загружены из {filepath}")
        return embeddings


def generate_and_save_embeddings(df: pd.DataFrame, 
                                  use_cache: bool = True) -> np.ndarray:
    """
    Генерирует и сохраняет эмбеддинги для всех приказов
    
    Args:
        df: DataFrame с приказами
        use_cache: использовать кэш если есть
        
    Returns:
        numpy array с эмбеддингами
    """
    embeddings_file = "orders_embeddings.pkl"
    embeddings_path = os.path.join(config.EMBEDDINGS_DIR, embeddings_file)
    
    # Проверяем кэш
    if use_cache and os.path.exists(embeddings_path):
        print("Загрузка эмбеддингов из кэша...")
        generator = EmbeddingsGenerator(use_sbert=True, use_rubert=False)
        return generator.load_embeddings(embeddings_file)
    
    # Генерируем новые эмбеддинги
    print("Генерация новых эмбеддингов...")
    generator = EmbeddingsGenerator(use_sbert=True, use_rubert=True)
    
    texts = df['text_for_embedding'].tolist()
    
    # Генерируем комбинированные эмбеддинги
    embeddings = generator.generate_combined_embeddings(
        texts,
        sbert_weight=0.6,  # Больше веса для Sentence-BERT (быстрее и эффективнее)
        rubert_weight=0.4
    )
    
    # Сохраняем
    generator.save_embeddings(embeddings, embeddings_file)
    
    print(f"Форма эмбеддингов: {embeddings.shape}")
    
    return embeddings


if __name__ == "__main__":
    # Тестирование
    print("=== Тестирование генерации эмбеддингов ===")
    
    # Загружаем данные
    data_path = os.path.join(config.OUTPUT_DIR, "processed_orders.csv")
    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
        print(f"Загружено {len(df)} приказов")
        
        # Генерируем эмбеддинги
        embeddings = generate_and_save_embeddings(df, use_cache=False)
        print(f"Размерность эмбеддингов: {embeddings.shape}")
    else:
        print(f"Файл {data_path} не найден. Сначала запустите data_loader.py")
