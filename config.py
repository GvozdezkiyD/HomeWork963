# -*- coding: utf-8 -*-
"""
Конфигурация для системы анализа приказов
"""

import os

# Пути к данным
DATA_DIR = "PravoGov"
ORDERS_DIR = os.path.join(DATA_DIR, "Приказы")
ERRORS_FILE = "tipovye_oshibki_v_prikazah_minekonomrazvitiya_rossii1 (2).txt"
CSV_FILE = os.path.join(DATA_DIR, "PravoGovПриказы.csv")

# Выходные директории
OUTPUT_DIR = "output"
EMBEDDINGS_DIR = os.path.join(OUTPUT_DIR, "embeddings")
CLUSTERS_DIR = os.path.join(OUTPUT_DIR, "clusters")
MODELS_DIR = os.path.join(OUTPUT_DIR, "models")
REPORTS_DIR = os.path.join(OUTPUT_DIR, "reports")

# Создание директорий
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
os.makedirs(CLUSTERS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Модели
RUBERT_MODEL = "DeepPavlov/rubert-base-cased"
SBERT_MODEL = "cointegrated/rubert-tiny2"  # Легковесная русская модель для sentence embeddings

# Параметры обработки
MAX_PARAGRAPHS = 5  # Количество абзацев для получения эмбеддингов
MIN_TEXT_LENGTH = 50  # Минимальная длина текста

# Параметры кластеризации
HDBSCAN_MIN_CLUSTER_SIZE = 5
HDBSCAN_MIN_SAMPLES = 3
KMEANS_N_CLUSTERS = 15  # Начальное количество кластеров
UMAP_N_COMPONENTS = 5
UMAP_N_NEIGHBORS = 15
UMAP_MIN_DIST = 0.1

# Параметры модели выявления ошибок
ERROR_DETECTION_BATCH_SIZE = 8
ERROR_DETECTION_EPOCHS = 5
ERROR_DETECTION_LR = 2e-5

# Топ слов для названия кластера
TOP_KEYWORDS = 10

# Разделение данных
TRAIN_SIZE = 0.8
VAL_SIZE = 0.1
TEST_SIZE = 0.1

# Случайное состояние
RANDOM_STATE = 42
