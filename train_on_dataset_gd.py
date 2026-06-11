# -*- coding: utf-8 -*-
"""
Обучение модели выявления ошибок на датасете dataset_gd.
Данные: только записи с источником 'prikaz' и непустым текстом.
Запуск: python train_on_dataset_gd.py
"""

import io
import json
import os
import sys

# UTF-8 вывод в Windows-консоли
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from collections import Counter

import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from transformers import AutoTokenizer, AutoModel, get_linear_schedule_with_warmup
from sklearn.metrics import classification_report, f1_score
from tqdm import tqdm

import config

# ─── константы ────────────────────────────────────────────────────────────────
DATASET_DIR = Path("dataset_gd")
TRAIN_FILE  = DATASET_DIR / "train.jsonl"
VAL_FILE    = DATASET_DIR / "val.jsonl"
TEST_FILE   = DATASET_DIR / "test.jsonl"

MODEL_NAME  = config.SBERT_MODEL          # cointegrated/rubert-tiny2
SAVE_NAME   = "best_error_detection_model.pt"
BATCH_SIZE  = config.ERROR_DETECTION_BATCH_SIZE   # 8
EPOCHS      = config.ERROR_DETECTION_EPOCHS        # 5
LR          = config.ERROR_DETECTION_LR            # 2e-5
MAX_LEN     = 512
MIN_TEXT    = 100


# ─── загрузка данных ──────────────────────────────────────────────────────────
def load_jsonl(path: Path):
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def filter_records(records):
    """Оставляем только приказы с реальным текстом."""
    return [
        r for r in records
        if r.get("source") == "prikaz" and len(r.get("text", "").strip()) >= MIN_TEXT
    ]


def get_label(record: dict) -> int:
    """1 — есть ошибки, 0 — документ корректный."""
    return 1 if record.get("has_critical_errors") else 0


def get_text(record: dict) -> str:
    return record.get("text", "").strip()[:2000]


# ─── Dataset ──────────────────────────────────────────────────────────────────
class OrderDataset(Dataset):
    def __init__(self, records, tokenizer, max_len=MAX_LEN):
        self.tokenizer = tokenizer
        self.max_len   = max_len
        self.texts  = [get_text(r)  for r in records]
        self.labels = [get_label(r) for r in records]

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        enc = self.tokenizer(
            self.texts[idx],
            add_special_tokens=True,
            max_length=self.max_len,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        return {
            "input_ids":      enc["input_ids"].flatten(),
            "attention_mask": enc["attention_mask"].flatten(),
            "labels":         torch.tensor(self.labels[idx], dtype=torch.long),
        }


# ─── Модель ───────────────────────────────────────────────────────────────────
class BertClassifier(nn.Module):
    def __init__(self, model_name: str, n_classes: int = 2, dropout: float = 0.3):
        super().__init__()
        self.bert       = AutoModel.from_pretrained(model_name)
        self.dropout    = nn.Dropout(dropout)
        self.classifier = nn.Linear(self.bert.config.hidden_size, n_classes)

    def forward(self, input_ids, attention_mask):
        out    = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled = self.dropout(out.pooler_output)
        return self.classifier(pooled)


# ─── обучение одной эпохи ─────────────────────────────────────────────────────
def train_epoch(model, loader, optimizer, scheduler, criterion, device):
    model.train()
    total_loss = 0.0
    for batch in tqdm(loader, desc="  train", leave=False):
        ids   = batch["input_ids"].to(device)
        mask  = batch["attention_mask"].to(device)
        lbls  = batch["labels"].to(device)
        optimizer.zero_grad()
        loss = criterion(model(ids, mask), lbls)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()
        total_loss += loss.item()
    return total_loss / len(loader)


# ─── оценка ───────────────────────────────────────────────────────────────────
def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss, preds_all, labels_all = 0.0, [], []
    with torch.no_grad():
        for batch in loader:
            ids   = batch["input_ids"].to(device)
            mask  = batch["attention_mask"].to(device)
            lbls  = batch["labels"].to(device)
            logits = model(ids, mask)
            total_loss += criterion(logits, lbls).item()
            preds_all.extend(torch.argmax(logits, dim=1).cpu().tolist())
            labels_all.extend(lbls.cpu().tolist())
    avg_loss = total_loss / len(loader)
    f1 = f1_score(labels_all, preds_all, average="weighted", zero_division=0)
    return avg_loss, f1, preds_all, labels_all


# ─── main ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("  Обучение модели выявления ошибок (dataset_gd / prikaz)")
    print("=" * 65)

    for fp in (TRAIN_FILE, VAL_FILE, TEST_FILE):
        if not fp.exists():
            print(f"[ОШИБКА] Файл не найден: {fp}")
            sys.exit(1)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Устройство: {device}")

    # ── загрузка и фильтрация ──────────────────────────────────────────────
    print("\nЗагрузка данных...")
    train_recs = filter_records(load_jsonl(TRAIN_FILE))
    val_recs   = filter_records(load_jsonl(VAL_FILE))
    test_recs  = filter_records(load_jsonl(TEST_FILE))

    print(f"  train: {len(train_recs)}  val: {len(val_recs)}  test: {len(test_recs)}")

    train_labels = [get_label(r) for r in train_recs]
    cnt = Counter(train_labels)
    print(f"  train labels -> ошибки: {cnt[1]}  корректные: {cnt[0]}")

    # ── токенизатор ────────────────────────────────────────────────────────
    print(f"\nЗагрузка токенизатора: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    # ── датасеты ───────────────────────────────────────────────────────────
    train_ds = OrderDataset(train_recs, tokenizer)
    val_ds   = OrderDataset(val_recs,   tokenizer)
    test_ds  = OrderDataset(test_recs,  tokenizer)

    # балансировка через WeightedRandomSampler
    class_counts = [cnt[0], cnt[1]]
    weights = [1.0 / class_counts[l] for l in train_labels]
    sampler = WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, sampler=sampler,  num_workers=0)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False,    num_workers=0)
    test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE, shuffle=False,    num_workers=0)

    # ── модель ─────────────────────────────────────────────────────────────
    print(f"\nСоздание модели: {MODEL_NAME}")
    model = BertClassifier(MODEL_NAME).to(device)

    total_steps = len(train_loader) * EPOCHS
    optimizer  = AdamW(model.parameters(), lr=LR, weight_decay=0.01)
    scheduler  = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=max(1, total_steps // 10),
        num_training_steps=total_steps,
    )

    # взвешенная функция потерь — усиливаем редкий класс (clean)
    w0 = len(train_labels) / (2 * cnt[0])
    w1 = len(train_labels) / (2 * cnt[1])
    class_weights = torch.tensor([w0, w1], dtype=torch.float).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    model_save_path = os.path.join(config.MODELS_DIR, SAVE_NAME)
    best_val_f1     = 0.0
    patience        = 2
    no_improve      = 0

    print(f"\nНачало обучения: {EPOCHS} эпох | batch={BATCH_SIZE} | lr={LR}")
    print(f"Веса классов: clean={w0:.3f}  errors={w1:.3f}")
    print("-" * 65)

    for epoch in range(1, EPOCHS + 1):
        print(f"\nЭпоха {epoch}/{EPOCHS}")
        train_loss = train_epoch(model, train_loader, optimizer, scheduler, criterion, device)
        val_loss, val_f1, _, _ = evaluate(model, val_loader, criterion, device)

        print(f"  Train Loss: {train_loss:.4f}  |  Val Loss: {val_loss:.4f}  |  Val F1: {val_f1:.4f}")

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            no_improve  = 0
            torch.save(
                {"model_state_dict": model.state_dict(), "model_name": MODEL_NAME},
                model_save_path,
            )
            print(f"  OK Сохранена лучшая модель  F1={best_val_f1:.4f}  -> {model_save_path}")
        else:
            no_improve += 1
            print(f"  Улучшений нет ({no_improve}/{patience})")
            if no_improve >= patience:
                print("  Ранняя остановка.")
                break

    # ── тест ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("Тестирование лучшей модели на test-выборке...")
    ckpt = torch.load(model_save_path, map_location=device)
    model.load_state_dict(ckpt["model_state_dict"])

    _, test_f1, test_preds, test_labels_list = evaluate(model, test_loader, criterion, device)
    all_cls = sorted(set(test_labels_list) | set(test_preds))
    names   = {0: "Корректный", 1: "Есть ошибки"}

    print(classification_report(
        test_labels_list, test_preds,
        labels=all_cls,
        target_names=[names[c] for c in all_cls],
        zero_division=0,
    ))
    print(f"Test F1 (weighted): {test_f1:.4f}")
    print("=" * 65)
    print(f"\nГотово! Модель сохранена: {model_save_path}")
    print("Запустите gui_app.py — модель загрузится автоматически.")


if __name__ == "__main__":
    main()
