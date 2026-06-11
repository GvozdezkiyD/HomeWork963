# -*- coding: utf-8 -*-
"""
Кластеризация приказов с использованием HDBSCAN и KMeans
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import hdbscan
import umap
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import pickle
import os
import config
from typing import Tuple, Dict, List


class OrdersClustering:
    """
    Класс для кластеризации приказов
    """
    
    def __init__(self, embeddings: np.ndarray):
        """
        Инициализация
        
        Args:
            embeddings: массив эмбеддингов
        """
        self.embeddings = embeddings
        self.reduced_embeddings = None
        self.hdbscan_labels = None
        self.kmeans_labels = None
        self.final_labels = None
        
    def reduce_dimensions(self, n_components: int = None,
                         n_neighbors: int = None,
                         min_dist: float = None):
        """
        Снижение размерности с помощью UMAP
        
        Args:
            n_components: количество компонент
            n_neighbors: количество соседей
            min_dist: минимальное расстояние
        """
        n_components = n_components or config.UMAP_N_COMPONENTS
        n_neighbors = n_neighbors or config.UMAP_N_NEIGHBORS
        min_dist = min_dist or config.UMAP_MIN_DIST
        
        print(f"Снижение размерности до {n_components} компонент...")
        
        reducer = umap.UMAP(
            n_components=n_components,
            n_neighbors=n_neighbors,
            min_dist=min_dist,
            metric='cosine',
            random_state=config.RANDOM_STATE
        )
        
        self.reduced_embeddings = reducer.fit_transform(self.embeddings)
        print(f"Размерность снижена: {self.reduced_embeddings.shape}")
        
        return self.reduced_embeddings
    
    def cluster_hdbscan(self, min_cluster_size: int = None,
                       min_samples: int = None) -> np.ndarray:
        """
        Кластеризация с помощью HDBSCAN
        
        Args:
            min_cluster_size: минимальный размер кластера
            min_samples: минимальное количество сэмплов
            
        Returns:
            массив меток кластеров
        """
        min_cluster_size = min_cluster_size or config.HDBSCAN_MIN_CLUSTER_SIZE
        min_samples = min_samples or config.HDBSCAN_MIN_SAMPLES
        
        print("Кластеризация HDBSCAN...")
        
        # Используем уменьшенные эмбеддинги если есть, иначе оригинальные
        data = self.reduced_embeddings if self.reduced_embeddings is not None else self.embeddings
        
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            metric='euclidean',
            cluster_selection_method='eom'
        )
        
        self.hdbscan_labels = clusterer.fit_predict(data)
        
        # Статистика
        n_clusters = len(set(self.hdbscan_labels)) - (1 if -1 in self.hdbscan_labels else 0)
        n_noise = list(self.hdbscan_labels).count(-1)
        
        print(f"HDBSCAN: найдено {n_clusters} кластеров, {n_noise} шумовых точек")
        
        return self.hdbscan_labels
    
    def cluster_kmeans(self, n_clusters: int = None) -> np.ndarray:
        """
        Кластеризация с помощью KMeans
        
        Args:
            n_clusters: количество кластеров
            
        Returns:
            массив меток кластеров
        """
        n_clusters = n_clusters or config.KMEANS_N_CLUSTERS
        
        print(f"Кластеризация KMeans на {n_clusters} кластеров...")
        
        # Используем уменьшенные эмбеддинги если есть
        data = self.reduced_embeddings if self.reduced_embeddings is not None else self.embeddings
        
        kmeans = KMeans(
            n_clusters=n_clusters,
            random_state=config.RANDOM_STATE,
            n_init=10,
            max_iter=300
        )
        
        self.kmeans_labels = kmeans.fit_predict(data)
        
        # Статистика
        cluster_counts = Counter(self.kmeans_labels)
        print(f"KMeans: создано {n_clusters} кластеров")
        print(f"Распределение по кластерам: {dict(sorted(cluster_counts.items()))}")
        
        return self.kmeans_labels
    
    def combine_clustering(self) -> np.ndarray:
        """
        Комбинирует результаты HDBSCAN и KMeans
        
        Returns:
            финальные метки кластеров
        """
        print("Комбинирование результатов кластеризации...")
        
        if self.hdbscan_labels is None or self.kmeans_labels is None:
            raise ValueError("Сначала выполните оба метода кластеризации")
        
        # Стратегия: используем HDBSCAN для основных кластеров,
        # KMeans для шумовых точек
        self.final_labels = self.hdbscan_labels.copy()
        
        # Для шумовых точек HDBSCAN (-1) используем метки KMeans
        noise_mask = self.hdbscan_labels == -1
        
        if noise_mask.sum() > 0:
            # Сдвигаем метки KMeans чтобы не пересекались с HDBSCAN
            max_hdbscan_label = self.hdbscan_labels.max()
            self.final_labels[noise_mask] = self.kmeans_labels[noise_mask] + max_hdbscan_label + 1
        
        n_final_clusters = len(set(self.final_labels))
        print(f"Финальное количество кластеров: {n_final_clusters}")
        
        return self.final_labels
    
    def visualize_clusters(self, labels: np.ndarray, title: str = "Кластеры",
                          save_path: str = None):
        """
        Визуализация кластеров
        
        Args:
            labels: метки кластеров
            title: заголовок графика
            save_path: путь для сохранения
        """
        # Снижаем до 2D для визуализации если еще не сделали
        if self.reduced_embeddings is None or self.reduced_embeddings.shape[1] != 2:
            print("Снижение размерности до 2D для визуализации...")
            reducer = umap.UMAP(
                n_components=2,
                n_neighbors=15,
                min_dist=0.1,
                metric='cosine',
                random_state=config.RANDOM_STATE
            )
            embeddings_2d = reducer.fit_transform(self.embeddings)
        else:
            embeddings_2d = self.reduced_embeddings
        
        # График
        plt.figure(figsize=(12, 8))
        
        # Разные цвета для разных кластеров
        unique_labels = set(labels)
        colors = plt.cm.Spectral(np.linspace(0, 1, len(unique_labels)))
        
        for label, color in zip(unique_labels, colors):
            mask = labels == label
            plt.scatter(
                embeddings_2d[mask, 0],
                embeddings_2d[mask, 1],
                c=[color],
                label=f'Кластер {label}' if label != -1 else 'Шум',
                alpha=0.6,
                s=50
            )
        
        plt.title(title, fontsize=14)
        plt.xlabel('UMAP 1')
        plt.ylabel('UMAP 2')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"График сохранен в {save_path}")
        
        plt.close()
    
    def save_clustering_results(self, df: pd.DataFrame, 
                                labels: np.ndarray,
                                filename: str):
        """
        Сохраняет результаты кластеризации
        
        Args:
            df: исходный DataFrame
            labels: метки кластеров
            filename: имя файла для сохранения
        """
        df_with_clusters = df.copy()
        df_with_clusters['cluster'] = labels
        
        output_path = os.path.join(config.CLUSTERS_DIR, filename)
        df_with_clusters.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"Результаты кластеризации сохранены в {output_path}")
        
        return df_with_clusters


def perform_clustering(embeddings: np.ndarray, 
                      df: pd.DataFrame,
                      use_cache: bool = True) -> Tuple[np.ndarray, pd.DataFrame]:
    """
    Выполняет полный процесс кластеризации
    
    Args:
        embeddings: эмбеддинги документов
        df: DataFrame с данными
        use_cache: использовать кэш
        
    Returns:
        метки кластеров и DataFrame с результатами
    """
    cache_file = os.path.join(config.CLUSTERS_DIR, "clustered_orders.csv")
    
    # Проверяем кэш
    if use_cache and os.path.exists(cache_file):
        print("Загрузка результатов кластеризации из кэша...")
        df_clustered = pd.read_csv(cache_file)
        return df_clustered['cluster'].values, df_clustered
    
    # Выполняем кластеризацию
    print("Выполнение кластеризации...")
    clusterer = OrdersClustering(embeddings)
    
    # 1. Снижение размерности
    clusterer.reduce_dimensions()
    
    # 2. HDBSCAN
    hdbscan_labels = clusterer.cluster_hdbscan()
    
    # 3. KMeans
    kmeans_labels = clusterer.cluster_kmeans()
    
    # 4. Комбинирование
    final_labels = clusterer.combine_clustering()
    
    # 5. Визуализация
    print("Создание визуализаций...")
    
    # Визуализация HDBSCAN
    clusterer.visualize_clusters(
        hdbscan_labels,
        "HDBSCAN Кластеризация",
        os.path.join(config.CLUSTERS_DIR, "hdbscan_clusters.png")
    )
    
    # Визуализация KMeans
    clusterer.visualize_clusters(
        kmeans_labels,
        "KMeans Кластеризация",
        os.path.join(config.CLUSTERS_DIR, "kmeans_clusters.png")
    )
    
    # Визуализация финальных кластеров
    clusterer.visualize_clusters(
        final_labels,
        "Финальная Кластеризация (HDBSCAN + KMeans)",
        os.path.join(config.CLUSTERS_DIR, "final_clusters.png")
    )
    
    # 6. Сохранение результатов
    df_clustered = clusterer.save_clustering_results(
        df,
        final_labels,
        "clustered_orders.csv"
    )
    
    return final_labels, df_clustered


if __name__ == "__main__":
    # Тестирование
    print("=== Тестирование кластеризации ===")
    
    # Загружаем данные и эмбеддинги
    data_path = os.path.join(config.OUTPUT_DIR, "processed_orders.csv")
    embeddings_path = os.path.join(config.EMBEDDINGS_DIR, "orders_embeddings.pkl")
    
    if os.path.exists(data_path) and os.path.exists(embeddings_path):
        df = pd.read_csv(data_path)
        
        with open(embeddings_path, 'rb') as f:
            embeddings = pickle.load(f)
        
        print(f"Загружено {len(df)} приказов и {embeddings.shape} эмбеддингов")
        
        # Выполняем кластеризацию
        labels, df_clustered = perform_clustering(embeddings, df, use_cache=False)
        
        print("\nСтатистика по кластерам:")
        print(df_clustered['cluster'].value_counts().sort_index())
    else:
        print("Необходимые файлы не найдены. Запустите сначала data_loader.py и embeddings_generator.py")
