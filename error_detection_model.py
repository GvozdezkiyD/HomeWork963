# -*- coding: utf-8 -*-
"""
Модель для выявления типовых ошибок в приказах
"""

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModel, get_linear_schedule_with_warmup
from torch.optim import AdamW
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, f1_score, precision_recall_fscore_support
from tqdm import tqdm
import re
import os
import pickle
import config
from typing import List, Dict, Tuple


class ErrorDetectionDataset(Dataset):
    """
    Dataset для обучения модели выявления ошибок
    """
    
    def __init__(self, texts: List[str], labels: List[int], 
                 tokenizer, max_length: int = 512):
        """
        Инициализация
        
        Args:
            texts: список текстов
            labels: метки (1 - есть ошибка, 0 - нет ошибки)
            tokenizer: токенизатор
            max_length: максимальная длина последовательности
        """
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]
        
        # Токенизация
        encoding = self.tokenizer(
            text,
            add_special_tokens=True,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }


class ErrorDetectionModel(nn.Module):
    """
    Модель для классификации: есть ошибка / нет ошибки
    """
    
    def __init__(self, model_name: str, n_classes: int = 2, dropout: float = 0.3):
        """
        Инициализация
        
        Args:
            model_name: название предобученной модели
            n_classes: количество классов (2 для бинарной классификации)
            dropout: вероятность dropout
        """
        super(ErrorDetectionModel, self).__init__()
        
        self.bert = AutoModel.from_pretrained(model_name)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(self.bert.config.hidden_size, n_classes)
    
    def forward(self, input_ids, attention_mask):
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        
        # Используем [CLS] токен
        pooled_output = outputs.pooler_output
        pooled_output = self.dropout(pooled_output)
        logits = self.classifier(pooled_output)
        
        return logits


class ErrorPatternMatcher:
    """
    Класс для проверки текстов на основе правил и шаблонов
    """
    
    def __init__(self, error_patterns: Dict):
        """
        Инициализация
        
        Args:
            error_patterns: словарь с шаблонами ошибок
        """
        self.error_patterns = error_patterns
    
    def check_text(self, text: str) -> Dict:
        """
        Проверяет текст на наличие ошибок по шаблонам
        
        Args:
            text: текст для проверки
            
        Returns:
            словарь с найденными ошибками
        """
        found_errors = {}
        
        for category, patterns in self.error_patterns.items():
            category_errors = []
            
            for pattern_info in patterns:
                # Проверяем regex паттерны
                if 'patterns' in pattern_info:
                    for pattern in pattern_info['patterns']:
                        if isinstance(pattern, str):
                            matches = re.findall(pattern, text, re.IGNORECASE)
                            if matches:
                                category_errors.append({
                                    'description': pattern_info.get('description', ''),
                                    'matches': matches[:5]  # Первые 5 совпадений
                                })
            
            if category_errors:
                found_errors[category] = category_errors
        
        return found_errors
    
    def has_errors(self, text: str) -> bool:
        """
        Проверяет, есть ли ошибки в тексте
        
        Args:
            text: текст
            
        Returns:
            True если найдены ошибки
        """
        errors = self.check_text(text)
        return len(errors) > 0


class ErrorDetectionTrainer:
    """
    Класс для обучения модели выявления ошибок
    """
    
    def __init__(self, model_name: str = None):
        """
        Инициализация
        
        Args:
            model_name: название модели
        """
        self.model_name = model_name or config.SBERT_MODEL
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Используется устройство: {self.device}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = None
        self.pattern_matcher = None
    
    def prepare_data(self, df: pd.DataFrame, 
                    error_patterns: Dict,
                    structure_validator=None) -> Tuple[DataLoader, DataLoader, DataLoader]:
        """
        Подготовка данных для обучения
        
        Args:
            df: DataFrame с приказами
            error_patterns: шаблоны ошибок
            structure_validator: валидатор структуры (опционально)
            
        Returns:
            train, val, test dataloaders
        """
        print("Подготовка данных для обучения...")
        
        # Создаем Pattern Matcher
        self.pattern_matcher = ErrorPatternMatcher(error_patterns)
        
        # Генерируем метки на основе шаблонов и структуры
        labels = []
        print("Генерация меток на основе шаблонов и структуры...")
        for text in tqdm(df['full_text'], desc="Генерация меток"):
            has_pattern_error = self.pattern_matcher.has_errors(str(text))
            
            # Если есть валидатор структуры, используем его тоже
            has_structure_error = False
            if structure_validator:
                result = structure_validator.validate(str(text))
                has_structure_error = not result['is_valid']
            
            # Документ имеет ошибку, если найдена ошибка по шаблону ИЛИ по структуре
            has_error = has_pattern_error or has_structure_error
            labels.append(1 if has_error else 0)
        
        df['has_error'] = labels
        
        # Статистика
        error_count = sum(labels)
        print(f"Документов с ошибками: {error_count} ({error_count/len(labels)*100:.1f}%)")
        print(f"Документов без ошибок: {len(labels) - error_count}")
        
        # Если нет ошибок вообще - возвращаем None (пропустим обучение)
        if error_count == 0:
            print("ВНИМАНИЕ: Не найдено ошибок. Обучение модели будет пропущено.")
            return None, None, None
        
        # Балансировка данных (опционально)
        # Берем все документы с ошибками и случайную выборку без ошибок
        df_errors = df[df['has_error'] == 1]
        df_no_errors = df[df['has_error'] == 0]
        
        if len(df_no_errors) > 0:
            df_no_errors = df_no_errors.sample(
                n=min(len(df_errors) * 2, len(df_no_errors)),
                random_state=config.RANDOM_STATE
            )
        
        df_balanced = pd.concat([df_errors, df_no_errors]).sample(
            frac=1, random_state=config.RANDOM_STATE
        )
        
        print(f"Балансированный датасет: {len(df_balanced)} документов")
        
        # Разделение на train/val/test
        train_df, temp_df = train_test_split(
            df_balanced, 
            test_size=(config.VAL_SIZE + config.TEST_SIZE),
            random_state=config.RANDOM_STATE,
            stratify=df_balanced['has_error']
        )
        
        val_df, test_df = train_test_split(
            temp_df,
            test_size=config.TEST_SIZE / (config.VAL_SIZE + config.TEST_SIZE),
            random_state=config.RANDOM_STATE,
            stratify=temp_df['has_error']
        )
        
        print(f"Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
        
        # Создание datasets
        train_dataset = ErrorDetectionDataset(
            train_df['text_for_embedding'].tolist(),
            train_df['has_error'].tolist(),
            self.tokenizer
        )
        
        val_dataset = ErrorDetectionDataset(
            val_df['text_for_embedding'].tolist(),
            val_df['has_error'].tolist(),
            self.tokenizer
        )
        
        test_dataset = ErrorDetectionDataset(
            test_df['text_for_embedding'].tolist(),
            test_df['has_error'].tolist(),
            self.tokenizer
        )
        
        # Создание dataloaders
        train_loader = DataLoader(
            train_dataset,
            batch_size=config.ERROR_DETECTION_BATCH_SIZE,
            shuffle=True
        )
        
        val_loader = DataLoader(
            val_dataset,
            batch_size=config.ERROR_DETECTION_BATCH_SIZE,
            shuffle=False
        )
        
        test_loader = DataLoader(
            test_dataset,
            batch_size=config.ERROR_DETECTION_BATCH_SIZE,
            shuffle=False
        )
        
        return train_loader, val_loader, test_loader
    
    def train(self, train_loader, val_loader, epochs: int = None):
        """
        Обучение модели
        
        Args:
            train_loader: DataLoader для обучения
            val_loader: DataLoader для валидации
            epochs: количество эпох
        """
        epochs = epochs or config.ERROR_DETECTION_EPOCHS
        
        print(f"Начало обучения на {epochs} эпох...")
        
        # Создание модели
        self.model = ErrorDetectionModel(self.model_name)
        self.model.to(self.device)
        
        # Оптимизатор и scheduler
        optimizer = AdamW(self.model.parameters(), lr=config.ERROR_DETECTION_LR)
        
        total_steps = len(train_loader) * epochs
        scheduler = get_linear_schedule_with_warmup(
            optimizer,
            num_warmup_steps=0,
            num_training_steps=total_steps
        )
        
        # Loss function
        criterion = nn.CrossEntropyLoss()
        
        # История обучения
        history = {
            'train_loss': [],
            'val_loss': [],
            'val_f1': []
        }
        
        best_val_f1 = 0
        
        for epoch in range(epochs):
            print(f"\nЭпоха {epoch + 1}/{epochs}")
            
            # Обучение
            self.model.train()
            train_loss = 0
            
            for batch in tqdm(train_loader, desc="Обучение"):
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)
                
                optimizer.zero_grad()
                
                outputs = self.model(input_ids, attention_mask)
                loss = criterion(outputs, labels)
                
                loss.backward()
                optimizer.step()
                scheduler.step()
                
                train_loss += loss.item()
            
            avg_train_loss = train_loss / len(train_loader)
            history['train_loss'].append(avg_train_loss)
            
            # Валидация
            val_loss, val_f1 = self.evaluate(val_loader, criterion)
            history['val_loss'].append(val_loss)
            history['val_f1'].append(val_f1)
            
            print(f"Train Loss: {avg_train_loss:.4f}")
            print(f"Val Loss: {val_loss:.4f}, Val F1: {val_f1:.4f}")
            
            # Сохранение лучшей модели
            if val_f1 > best_val_f1:
                best_val_f1 = val_f1
                self.save_model("best_error_detection_model.pt")
                print(f"Сохранена лучшая модель (F1: {best_val_f1:.4f})")
        
        return history
    
    def evaluate(self, data_loader, criterion=None):
        """
        Оценка модели
        
        Args:
            data_loader: DataLoader
            criterion: функция потерь
            
        Returns:
            loss и F1 score
        """
        self.model.eval()
        
        total_loss = 0
        all_predictions = []
        all_labels = []
        
        if criterion is None:
            criterion = nn.CrossEntropyLoss()
        
        with torch.no_grad():
            for batch in data_loader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)
                
                outputs = self.model(input_ids, attention_mask)
                loss = criterion(outputs, labels)
                
                total_loss += loss.item()
                
                predictions = torch.argmax(outputs, dim=1)
                all_predictions.extend(predictions.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
        
        avg_loss = total_loss / len(data_loader)
        f1 = f1_score(all_labels, all_predictions, average='weighted')
        
        return avg_loss, f1
    
    def test(self, test_loader):
        """
        Тестирование модели
        
        Args:
            test_loader: DataLoader для тестирования
        """
        print("\nТестирование модели...")
        
        self.model.eval()
        
        all_predictions = []
        all_labels = []
        
        with torch.no_grad():
            for batch in tqdm(test_loader, desc="Тестирование"):
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)
                
                outputs = self.model(input_ids, attention_mask)
                predictions = torch.argmax(outputs, dim=1)
                
                all_predictions.extend(predictions.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
        
        # Метрики
        print("\nРезультаты тестирования:")
        
        # Определяем, какие классы присутствуют
        unique_labels = sorted(set(all_labels))
        unique_predictions = sorted(set(all_predictions))
        all_classes = sorted(set(unique_labels) | set(unique_predictions))
        
        # Формируем имена классов только для присутствующих классов
        class_names = []
        for cls in all_classes:
            if cls == 0:
                class_names.append('Нет ошибок')
            else:
                class_names.append('Есть ошибки')
        
        # Если есть только один класс, добавляем labels параметр
        if len(all_classes) == 1:
            print(f"ВНИМАНИЕ: В тестовой выборке только класс '{class_names[0]}'")
            print(classification_report(
                all_labels, 
                all_predictions,
                labels=all_classes,
                target_names=class_names,
                zero_division=0
            ))
        else:
            print(classification_report(
                all_labels, 
                all_predictions,
                target_names=class_names,
                zero_division=0
            ))
        
        precision, recall, f1, _ = precision_recall_fscore_support(
            all_labels, all_predictions, average='weighted', zero_division=0
        )
        
        return {
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'predictions': all_predictions,
            'labels': all_labels
        }
    
    def predict(self, text: str) -> Dict:
        """
        Предсказание для одного текста
        
        Args:
            text: текст приказа
            
        Returns:
            словарь с результатами
        """
        self.model.eval()
        
        # Проверка по шаблонам
        pattern_errors = self.pattern_matcher.check_text(text) if self.pattern_matcher else {}
        
        # Предсказание модели
        encoding = self.tokenizer(
            text,
            add_special_tokens=True,
            max_length=512,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)
        
        with torch.no_grad():
            outputs = self.model(input_ids, attention_mask)
            probabilities = torch.softmax(outputs, dim=1)
            prediction = torch.argmax(outputs, dim=1).item()
        
        return {
            'has_errors': prediction == 1,
            'confidence': probabilities[0][prediction].item(),
            'probabilities': {
                'no_errors': probabilities[0][0].item(),
                'has_errors': probabilities[0][1].item()
            },
            'pattern_errors': pattern_errors
        }
    
    def save_model(self, filename: str):
        """Сохранение модели"""
        model_path = os.path.join(config.MODELS_DIR, filename)
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'model_name': self.model_name
        }, model_path)
        print(f"Модель сохранена в {model_path}")
    
    def load_model(self, filename: str):
        """Загрузка модели"""
        model_path = os.path.join(config.MODELS_DIR, filename)
        checkpoint = torch.load(model_path, map_location=self.device, weights_only=False)
        
        self.model = ErrorDetectionModel(checkpoint['model_name'])
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.to(self.device)
        self.model.eval()
        
        print(f"Модель загружена из {model_path}")


if __name__ == "__main__":
    print("=== Тестирование модели выявления ошибок ===")
    
    # Загружаем данные
    from data_loader import load_all_orders, load_error_patterns
    
    df = load_all_orders()
    error_patterns = load_error_patterns()
    
    # Создаем тренер
    trainer = ErrorDetectionTrainer()
    
    # Подготовка данных
    train_loader, val_loader, test_loader = trainer.prepare_data(df, error_patterns)
    
    # Обучение
    history = trainer.train(train_loader, val_loader, epochs=3)
    
    # Тестирование
    test_results = trainer.test(test_loader)
    
    print(f"\nФинальные результаты:")
    print(f"Precision: {test_results['precision']:.4f}")
    print(f"Recall: {test_results['recall']:.4f}")
    print(f"F1 Score: {test_results['f1']:.4f}")
