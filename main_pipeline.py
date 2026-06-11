# -*- coding: utf-8 -*-
"""
Главный пайплайн для обработки приказов:
1. Загрузка данных
2. Генерация эмбеддингов
3. Кластеризация
4. Определение тем
5. Обучение модели
6. Тестирование
"""

import os
import pandas as pd
import config

from data_loader import load_all_orders, load_error_patterns, save_processed_data
from embeddings_generator import generate_and_save_embeddings
from clustering import perform_clustering
from topic_modeling import generate_topics
from error_detection_model import ErrorDetectionTrainer
from order_structure_validator import OrderStructureValidator


def main():
    """
    Главная функция запуска всего пайплайна
    """
    print("=" * 80)
    print("СИСТЕМА АНАЛИЗА ПРИКАЗОВ И ВЫЯВЛЕНИЯ ТИПОВЫХ ОШИБОК")
    print("=" * 80)
    
    # ========== Этап 1: Загрузка данных ==========
    print("\n" + "=" * 80)
    print("ЭТАП 1: ЗАГРУЗКА И ПРЕДОБРАБОТКА ДАННЫХ")
    print("=" * 80)
    
    data_path = os.path.join(config.OUTPUT_DIR, "processed_orders.csv")
    
    if os.path.exists(data_path):
        print("Загрузка обработанных данных из кэша...")
        df = pd.read_csv(data_path)
    else:
        print("Загрузка приказов из файлов (TXT, DOCX, PDF)...")
        df = load_all_orders()
        if not df.empty:
            save_processed_data(df)
        else:
            print("ОШИБКА: Нет данных. Разместите приказы в PravoGov/Приказы/ или создайте processed_orders.csv")
            return
    
    print(f"\nЗагружено документов: {len(df)}")
    print(f"Средняя длина текста: {df['full_text'].str.len().mean():.0f} символов")
    
    # ========== Этап 2: Генерация эмбеддингов ==========
    print("\n" + "=" * 80)
    print("ЭТАП 2: ГЕНЕРАЦИЯ ЭМБЕДДИНГОВ")
    print("=" * 80)
    
    embeddings = generate_and_save_embeddings(df, use_cache=True)
    print(f"Размерность эмбеддингов: {embeddings.shape}")
    
    # ========== Этап 3: Кластеризация ==========
    print("\n" + "=" * 80)
    print("ЭТАП 3: КЛАСТЕРИЗАЦИЯ ПРИКАЗОВ")
    print("=" * 80)
    
    labels, df_clustered = perform_clustering(embeddings, df, use_cache=True)
    
    n_clusters = len(set(labels))
    print(f"\nОбщее количество кластеров: {n_clusters}")
    print(f"\nРаспределение документов по кластерам:")
    print(df_clustered['cluster'].value_counts().head(10))
    
    # ========== Этап 4: Определение тем ==========
    print("\n" + "=" * 80)
    print("ЭТАП 4: ОПРЕДЕЛЕНИЕ ТЕМ КЛАСТЕРОВ")
    print("=" * 80)
    
    cluster_info = generate_topics(df_clustered)
    
    print("\nПримеры определенных тем:")
    for cluster_id, info in sorted(cluster_info.items())[:10]:
        print(f"\nКластер {cluster_id}: {info['theme']}")
        print(f"  Документов: {info['n_documents']}")
        print(f"  Ключевые слова: {', '.join(info['keywords'][:5])}")
    
    # ========== Этап 5: Загрузка типовых ошибок ==========
    print("\n" + "=" * 80)
    print("ЭТАП 5: ЗАГРУЗКА ТИПОВЫХ ОШИБОК")
    print("=" * 80)
    
    error_patterns = load_error_patterns()
    print(f"Загружено категорий ошибок: {len(error_patterns)}")
    
    for category in list(error_patterns.keys())[:5]:
        print(f"  - {category}")
    
    # ========== Этап 6: Обучение модели ==========
    print("\n" + "=" * 80)
    print("ЭТАП 6: ОБУЧЕНИЕ МОДЕЛИ ВЫЯВЛЕНИЯ ОШИБОК")
    print("=" * 80)
    
    # Проверяем, есть ли уже обученная модель
    model_path = os.path.join(config.MODELS_DIR, "best_error_detection_model.pt")
    
    trainer = ErrorDetectionTrainer()
    
    # Создаём валидатор структуры для генерации меток
    from order_structure_validator import OrderStructureValidator
    structure_validator_for_labels = OrderStructureValidator()
    
    # Подготовка данных
    print("\nПодготовка данных...")
    train_loader, val_loader, test_loader = trainer.prepare_data(
        df_clustered, 
        error_patterns,
        structure_validator=structure_validator_for_labels
    )
    
    # Если данных нет (все None), пропускаем обучение
    model_available = False
    test_results = None
    
    if train_loader is None:
        print("\nДанные для обучения отсутствуют.")
        if os.path.exists(model_path):
            print("Загрузка ранее обученной модели...")
            trainer.load_model("best_error_detection_model.pt")
            model_available = True
        else:
            print("Обученная модель отсутствует. Будет использоваться только проверка структуры.")
    else:
        # Обучение или загрузка модели
        if not os.path.exists(model_path):
            print("\nОбучение новой модели...")
            history = trainer.train(train_loader, val_loader, epochs=config.ERROR_DETECTION_EPOCHS)
            model_available = True
        else:
            print("\nЗагрузка обученной модели...")
            trainer.load_model("best_error_detection_model.pt")
            model_available = True
        
        # ========== Этап 7: Тестирование ==========
        print("\n" + "=" * 80)
        print("ЭТАП 7: ТЕСТИРОВАНИЕ МОДЕЛИ")
        print("=" * 80)
        
        test_results = trainer.test(test_loader)
    
    # ========== Этап 8: Проверка структуры приказов ==========
    print("\n" + "=" * 80)
    print("ЭТАП 8: ПРОВЕРКА СТРУКТУРЫ ПРИКАЗОВ")
    print("=" * 80)
    
    # Создаем валидатор структуры
    structure_validator = OrderStructureValidator()
    
    # Проверяем все документы
    print("\nПроверка структуры всех документов...")
    structure_results = []
    
    for idx, row in df_clustered.iterrows():
        validation_result = structure_validator.validate(row['full_text'])
        structure_results.append({
            'file_name': row['file_name'],
            'is_valid': validation_result['is_valid'],
            'total_errors': validation_result['total_errors'],
            'total_warnings': validation_result['total_warnings'],
            'errors': validation_result['errors'],
            'warnings': validation_result['warnings']
        })
    
    # Статистика по структуре
    valid_count = sum(1 for r in structure_results if r['is_valid'])
    invalid_count = len(structure_results) - valid_count
    total_structure_errors = sum(r['total_errors'] for r in structure_results)
    total_structure_warnings = sum(r['total_warnings'] for r in structure_results)
    
    print(f"\nСтатистика проверки структуры:")
    print(f"  ✓ Документов с корректной структурой: {valid_count} ({valid_count/len(structure_results)*100:.1f}%)")
    print(f"  ✗ Документов с ошибками структуры: {invalid_count} ({invalid_count/len(structure_results)*100:.1f}%)")
    print(f"  Всего критических ошибок: {total_structure_errors}")
    print(f"  Всего предупреждений: {total_structure_warnings}")
    
    # Сохраняем результаты проверки структуры
    structure_df = pd.DataFrame(structure_results)
    structure_report_path = os.path.join(config.REPORTS_DIR, "structure_validation_results.csv")
    structure_df[['file_name', 'is_valid', 'total_errors', 'total_warnings']].to_csv(
        structure_report_path, index=False, encoding='utf-8-sig'
    )
    print(f"\nРезультаты проверки структуры сохранены в: {structure_report_path}")
    
    # Показываем примеры документов с ошибками
    print("\n" + "=" * 80)
    print("ПРИМЕРЫ ДОКУМЕНТОВ С ОШИБКАМИ СТРУКТУРЫ:")
    print("=" * 80)
    
    invalid_docs = [r for r in structure_results if not r['is_valid']][:3]  # Первые 3
    
    for i, doc_result in enumerate(invalid_docs, 1):
        print(f"\n{i}. Документ: {doc_result['file_name']}")
        print(f"   Критических ошибок: {doc_result['total_errors']}")
        print(f"   Предупреждений: {doc_result['total_warnings']}")
        print("\n   Ошибки:")
        for error in doc_result['errors'][:3]:  # Первые 3 ошибки
            print(f"     - [{error.section}] {error.error_type}")
            print(f"       {error.description}")
    
    # ========== Этап 9: Примеры предсказаний модели ==========
    print("\n" + "=" * 80)
    print("ЭТАП 9: ПРИМЕРЫ ПРЕДСКАЗАНИЙ МОДЕЛИ")
    print("=" * 80)
    
    # Тестируем на нескольких примерах
    sample_docs = df_clustered.sample(5, random_state=config.RANDOM_STATE)
    
    for idx, row in sample_docs.iterrows():
        print(f"\n--- Документ: {row['file_name']} ---")
        print(f"Кластер: {row['cluster']} ({cluster_info[row['cluster']]['theme']})")
        print(f"Текст (первые 200 символов): {row['text_for_embedding'][:200]}...")
        
        # Проверка структуры
        struct_result = structure_validator.validate(row['full_text'])
        print(f"\nПроверка структуры:")
        print(f"  Структура корректна: {'ДА' if struct_result['is_valid'] else 'НЕТ'}")
        if not struct_result['is_valid']:
            print(f"  Ошибок структуры: {struct_result['total_errors']}")
        
        # Предсказание модели (если доступна)
        if model_available:
            result = trainer.predict(row['full_text'])
            
            print(f"\nРезультаты проверки модели:")
            print(f"  Есть ошибки: {'ДА' if result['has_errors'] else 'НЕТ'}")
            print(f"  Уверенность: {result['confidence']:.2%}")
            
            if result['pattern_errors']:
                print(f"  Найдено ошибок по шаблонам:")
                for category, errors in result['pattern_errors'].items():
                    print(f"    - {category}: {len(errors)} ошибок")
        else:
            print(f"\nМодель недоступна. Используется только проверка структуры.")
    
    # ========== Финальный отчет ==========
    print("\n" + "=" * 80)
    print("ФИНАЛЬНЫЙ ОТЧЕТ")
    print("=" * 80)
    
    report = f"""
СИСТЕМА АНАЛИЗА ПРИКАЗОВ - ИТОГОВЫЙ ОТЧЕТ

1. ДАННЫЕ:
   - Всего документов: {len(df)}
   - Средняя длина: {df['full_text'].str.len().mean():.0f} символов
   
2. КЛАСТЕРИЗАЦИЯ:
   - Количество кластеров: {n_clusters}
   - Метод: HDBSCAN + KMeans
   - Размерность эмбеддингов: {embeddings.shape[1]}
   
3. ТЕМЫ:
   - Автоматически определено: {len(cluster_info)} тем
   - Топ-5 тем по количеству документов:
"""
    
    # Топ-5 тем
    top_themes = sorted(cluster_info.items(), 
                       key=lambda x: x[1]['n_documents'], 
                       reverse=True)[:5]
    
    for i, (cluster_id, info) in enumerate(top_themes, 1):
        report += f"     {i}. {info['theme']} ({info['n_documents']} док.)\n"
    
    report += f"""
4. ПРОВЕРКА СТРУКТУРЫ ПРИКАЗОВ:
   - Документов с корректной структурой: {valid_count} ({valid_count/len(structure_results)*100:.1f}%)
   - Документов с ошибками структуры: {invalid_count} ({invalid_count/len(structure_results)*100:.1f}%)
   - Всего критических ошибок: {total_structure_errors}
   - Всего предупреждений: {total_structure_warnings}
   
5. МОДЕЛЬ ВЫЯВЛЕНИЯ ОШИБОК:"""
    
    if test_results:
        report += f"""
   - Архитектура: ruBERT + Classification Head
   - Precision: {test_results['precision']:.4f}
   - Recall: {test_results['recall']:.4f}
   - F1 Score: {test_results['f1']:.4f}"""
    else:
        report += """
   - Модель не обучена (используется только проверка структуры)"""
    
    report += f"""
   
6. ТИПОВЫЕ ОШИБКИ:
   - Категорий ошибок: {len(error_patterns)}
   - Используются как правила и шаблоны
   
СИСТЕМА ГОТОВА К РАБОТЕ!
"""
    
    print(report)
    
    # Сохраняем отчет
    report_path = os.path.join(config.REPORTS_DIR, "final_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nОтчет сохранен в: {report_path}")
    
    print("\n" + "=" * 80)
    print("ПАЙПЛАЙН ЗАВЕРШЕН УСПЕШНО!")
    print("=" * 80)


if __name__ == "__main__":
    main()
