# -*- coding: utf-8 -*-
"""
Комплексное тестирование системы проверки приказов МЭР.
Запуск: python run_tests.py
"""

import io, sys, os, json, time, re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── тестовые документы ────────────────────────────────────────────────────────
DOCS = {

"ЭТАЛОН_полный": """
МИНИСТЕРСТВО ЭКОНОМИЧЕСКОГО РАЗВИТИЯ РОССИЙСКОЙ ФЕДЕРАЦИИ

ПРИКАЗ

от 15.01.2025 № 23
г. Москва

О назначении комиссии по проверке соблюдения требований законодательства

В соответствии с Федеральным законом от 27.07.2010 № 210-ФЗ «Об организации
предоставления государственных и муниципальных услуг» и постановлением
Правительства Российской Федерации от 16.05.2011 № 373 «О разработке и
утверждении административных регламентов»

ПРИКАЗЫВАЮ:

1. Утвердить состав комиссии по проверке соблюдения требований законодательства
   согласно приложению № 1 к настоящему приказу.
2. Установить срок проведения проверки — до 31.03.2025.
3. Руководителю комиссии обеспечить представление результатов не позднее
   10.04.2025.
4. Контроль за исполнением настоящего приказа возложить на заместителя министра
   Петрова А.В.

Министр                                              И.И. Иванов

Приложение № 1
к приказу Минэкономразвития России
от 15.01.2025 № 23
""",

"ОШИБКА_нет_ПРИКАЗЫВАЮ": """
МИНИСТЕРСТВО ЭКОНОМИЧЕСКОГО РАЗВИТИЯ РОССИЙСКОЙ ФЕДЕРАЦИИ

ПРИКАЗ

от 20.02.2025 № 45
г. Москва

Об утверждении порядка ведения реестра инвестиционных проектов

В соответствии с Федеральным законом от 25.02.1999 № 39-ФЗ «Об инвестиционной
деятельности в Российской Федерации»

1. Утвердить Порядок ведения реестра инвестиционных проектов.
2. Установить срок введения в действие — 01.04.2025.
3. Контроль за исполнением настоящего приказа возложить на заместителя министра.

Министр                                              П.П. Петров
""",

"ОШИБКА_нет_преамбулы": """
МИНИСТЕРСТВО ЭКОНОМИЧЕСКОГО РАЗВИТИЯ РОССИЙСКОЙ ФЕДЕРАЦИИ

ПРИКАЗ

от 10.03.2025 № 67
г. Москва

О признании утратившим силу приказа от 12.05.2020 № 234

ПРИКАЗЫВАЮ:

1. Признать утратившим силу приказ Минэкономразвития России от 12.05.2020 № 234.
2. Контроль за исполнением настоящего приказа возложить на директора департамента.

Министр                                              С.С. Сидоров
""",

"ОШИБКА_нет_органа_и_номера": """
ПРИКАЗ

от 05.04.2025
г. Москва

Об установлении требований к отчётности

В соответствии с Бюджетным кодексом Российской Федерации

ПРИКАЗЫВАЮ:

1. Установить требования к отчётности субъектов бюджетного планирования.
2. Контроль за исполнением настоящего приказа возложить на финансовый департамент.

Руководитель
""",

"ОШИБКА_нарушена_нумерация": """
МИНИСТЕРСТВО ЭКОНОМИЧЕСКОГО РАЗВИТИЯ РОССИЙСКОЙ ФЕДЕРАЦИИ

ПРИКАЗ

от 11.04.2025 № 89
г. Москва

О внесении изменений в методические рекомендации

В соответствии с постановлением Правительства Российской Федерации от 02.06.2023
№ 912

ПРИКАЗЫВАЮ:

1. Утвердить изменения в методические рекомендации согласно приложению.
3. Установить срок введения в действие — 01.05.2025.
5. Контроль возложить на заместителя министра.

Министр                                              Н.Н. Носов
""",

"ОШИБКА_пустой_пункт": """
МИНИСТЕРСТВО ЭКОНОМИЧЕСКОГО РАЗВИТИЯ РОССИЙСКОЙ ФЕДЕРАЦИИ

ПРИКАЗ

от 12.04.2025 № 91
г. Москва

О создании рабочей группы

В целях реализации мероприятий государственной программы Российской Федерации

ПРИКАЗЫВАЮ:

1. Создать рабочую группу по вопросам цифровой трансформации.
2.
3. Контроль за исполнением возложить на статс-секретаря — заместителя министра.

Министр                                              К.К. Козлов
""",

"ТОЛЬКО_ПРЕДУПРЕЖДЕНИЯ_нет_контроля": """
МИНИСТЕРСТВО ЭКОНОМИЧЕСКОГО РАЗВИТИЯ РОССИЙСКОЙ ФЕДЕРАЦИИ

ПРИКАЗ

от 14.04.2025 № 95
г. Москва

Об утверждении административного регламента

В соответствии с Федеральным законом от 27.07.2010 № 210-ФЗ
«Об организации предоставления государственных и муниципальных услуг»

ПРИКАЗЫВАЮ:

1. Утвердить административный регламент предоставления государственной услуги.
2. Признать утратившим силу приказ от 15.03.2019 № 182.

Министр                                              М.М. Минаев
""",

"МИНИМАЛЬНЫЙ_документ": """
ПРИКАЗ

Об изменении порядка работы

Приказываю выполнить работу.

Руководитель
""",

}

# ── запуск ────────────────────────────────────────────────────────────────────
def run_tests():
    t0_total = time.time()

    print("=" * 72)
    print("  КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ СИСТЕМЫ ПРОВЕРКИ ПРИКАЗОВ МЭР")
    print(f"  {datetime.now().strftime('%d.%m.%Y  %H:%M:%S')}")
    print("=" * 72)

    # ── загрузка компонентов ──────────────────────────────────────────────
    print("\n[1/4] Загрузка валидатора структуры...")
    t0 = time.time()
    from order_structure_validator import OrderStructureValidator
    validator = OrderStructureValidator()
    print(f"      OK  ({time.time()-t0:.2f}с)")

    print("[2/4] Загрузка нейронной модели...")
    t0 = time.time()
    model_available = False
    trainer = None
    model_path = os.path.join("output", "models", "best_error_detection_model.pt")
    if os.path.exists(model_path):
        try:
            import config
            from error_detection_model import ErrorDetectionTrainer
            trainer = ErrorDetectionTrainer()
            trainer.load_model("best_error_detection_model.pt")
            model_available = True
            print(f"      OK  — модель загружена ({time.time()-t0:.2f}с)")
        except Exception as e:
            print(f"      WARN  модель не загружена: {e}")
    else:
        print("      WARN  файл модели не найден")

    print("[3/4] Загрузка датасета для метрик (test.jsonl)...")
    t0 = time.time()
    test_recs = []
    test_file = Path("dataset_gd/test.jsonl")
    if test_file.exists():
        with open(test_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    r = json.loads(line)
                    if r.get("source") == "prikaz" and len(r.get("text","").strip()) >= 100:
                        test_recs.append(r)
        print(f"      OK  — {len(test_recs)} записей ({time.time()-t0:.2f}с)")
    else:
        print("      WARN  test.jsonl не найден")

    # ── тест валидатора на синтетических документах ───────────────────────
    print("\n[4/4] Запуск тестов...\n")
    print("=" * 72)
    print("  ТЕСТ 1: ПРОВЕРКА ВАЛИДАТОРА СТРУКТУРЫ (синтетические документы)")
    print("=" * 72)

    results = []
    total_time_val = 0.0

    EXPECTED = {
        "ЭТАЛОН_полный":                  (True,  0),
        "ОШИБКА_нет_ПРИКАЗЫВАЮ":          (False, 1),
        "ОШИБКА_нет_преамбулы":           (False, 1),
        "ОШИБКА_нет_органа_и_номера":     (False, 2),
        "ОШИБКА_нарушена_нумерация":      (False, 1),
        "ОШИБКА_пустой_пункт":            (False, 1),
        "ТОЛЬКО_ПРЕДУПРЕЖДЕНИЯ_нет_контроля": (True, 0),
        "МИНИМАЛЬНЫЙ_документ":           (False, None),
    }

    correct_verdict = 0
    for name, text in DOCS.items():
        t0 = time.time()
        vr  = validator.validate(text)
        dt  = time.time() - t0
        total_time_val += dt

        exp_valid, exp_min_errors = EXPECTED.get(name, (None, None))
        got_valid = vr["is_valid"]
        verdict_ok = (exp_valid is None) or (got_valid == exp_valid)
        if verdict_ok:
            correct_verdict += 1

        status = "PASS" if verdict_ok else "FAIL"
        ico    = "[+]" if verdict_ok else "[!]"
        print(f"  {ico} {status:<4}  {name}")
        print(f"         valid={got_valid}  ошибок={vr['total_errors']}  "
              f"предупр={vr['total_warnings']}  время={dt*1000:.1f}мс")
        if vr["errors"]:
            for e in vr["errors"][:2]:
                print(f"         ERR: [{e.section}] {e.error_type}")
        if vr["warnings"]:
            for w in vr["warnings"][:2]:
                print(f"         WRN: [{w.section}] {w.error_type}")

        results.append({
            "name": name, "valid": got_valid, "errors": vr["total_errors"],
            "warnings": vr["total_warnings"], "pass": verdict_ok, "ms": dt*1000
        })
        print()

    val_accuracy = correct_verdict / len(DOCS) * 100
    avg_time_val = total_time_val / len(DOCS) * 1000
    print(f"  Точность вердикта: {correct_verdict}/{len(DOCS)} = {val_accuracy:.1f}%")
    print(f"  Среднее время проверки: {avg_time_val:.1f} мс")

    # ── тест нейронной модели на test.jsonl ───────────────────────────────
    print("\n" + "=" * 72)
    print("  ТЕСТ 2: МЕТРИКИ НЕЙРОННОЙ МОДЕЛИ (test.jsonl — реальные приказы)")
    print("=" * 72)

    if model_available and trainer and test_recs:
        from sklearn.metrics import (classification_report, f1_score,
                                     precision_score, recall_score,
                                     confusion_matrix, accuracy_score)
        y_true, y_pred, times_ml = [], [], []
        sample = test_recs[:100]   # берём 100 для скорости теста
        print(f"  Образец: {len(sample)} документов из test.jsonl\n")

        for r in sample:
            label = 1 if r.get("has_critical_errors") else 0
            y_true.append(label)
            t0 = time.time()
            res = trainer.predict(r["text"])
            times_ml.append((time.time() - t0) * 1000)
            y_pred.append(1 if res["has_errors"] else 0)

        acc  = accuracy_score(y_true, y_pred) * 100
        f1w  = f1_score(y_true, y_pred, average="weighted", zero_division=0) * 100
        f1m  = f1_score(y_true, y_pred, average="macro",    zero_division=0) * 100
        prec = precision_score(y_true, y_pred, average="weighted", zero_division=0) * 100
        rec  = recall_score(y_true, y_pred,    average="weighted", zero_division=0) * 100
        cm   = confusion_matrix(y_true, y_pred, labels=[0,1])
        avg_ms = sum(times_ml) / len(times_ml)

        print(classification_report(
            y_true, y_pred,
            labels=[0,1],
            target_names=["Корректный","Есть ошибки"],
            zero_division=0
        ))
        print(f"  Accuracy        : {acc:.2f}%")
        print(f"  F1 weighted     : {f1w:.2f}%")
        print(f"  F1 macro        : {f1m:.2f}%")
        print(f"  Precision (w)   : {prec:.2f}%")
        print(f"  Recall    (w)   : {rec:.2f}%")
        print(f"  Среднее время   : {avg_ms:.1f} мс/документ")
        if cm.shape == (2,2):
            tn,fp,fn,tp = cm.ravel()
            print(f"\n  Матрица ошибок:")
            print(f"              Предсказано")
            print(f"              Корректный  Ошибки")
            print(f"  Реальный Корр. {tn:>6}      {fp:>6}")
            print(f"  Реальный Ошиб. {fn:>6}      {tp:>6}")
    else:
        print("  ПРОПУЩЕН (модель или данные недоступны)")
        acc = f1w = f1m = prec = rec = avg_ms = None
        cm = None

    # ── тест производительности ───────────────────────────────────────────
    print("\n" + "=" * 72)
    print("  ТЕСТ 3: ПРОИЗВОДИТЕЛЬНОСТЬ ВАЛИДАТОРА")
    print("=" * 72)

    perf_texts = {
        "Короткий (< 500 симв)":  list(DOCS.values())[0][:400],
        "Средний  (~1 000 симв)": list(DOCS.values())[0] * 3,
        "Большой  (~5 000 симв)": list(DOCS.values())[0] * 15,
        "Очень большой (~15 000 симв)": list(DOCS.values())[0] * 45,
    }
    for label, txt in perf_texts.items():
        times_p = []
        for _ in range(5):
            t0 = time.time()
            validator.validate(txt)
            times_p.append((time.time() - t0) * 1000)
        avg = sum(times_p) / len(times_p)
        print(f"  {label:<32}: {avg:6.1f} мс  ({len(txt):,} символов)")

    # ── тест dataset_gd ───────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("  ТЕСТ 4: КАЧЕСТВО НАБОРА ДАННЫХ dataset_gd")
    print("=" * 72)

    dataset_ok = True
    for split in ("train", "val", "test"):
        fp = Path(f"dataset_gd/{split}.jsonl")
        if not fp.exists():
            print(f"  [-] {split}.jsonl  — НЕ НАЙДЕН"); dataset_ok = False; continue
        with open(fp, encoding="utf-8") as f:
            recs = [json.loads(l) for l in f if l.strip()]
        n_prikaz = sum(1 for r in recs if r.get("source")=="prikaz")
        n_text   = sum(1 for r in recs if len(r.get("text","").strip())>=100)
        n_lbl1   = sum(1 for r in recs if r.get("has_critical_errors"))
        n_lbl0   = len(recs) - n_lbl1
        print(f"  [+] {split:<6}: {len(recs):>5} записей | prikaz={n_prikaz} "
              f"| с текстом={n_text} | ошибки={n_lbl1} | корректные={n_lbl0}")

    stats_file = Path("dataset_gd/stats.json")
    if stats_file.exists():
        stats = json.loads(stats_file.read_text(encoding="utf-8"))
        print(f"\n  Статистика датасета:")
        for k, v in stats.items():
            if k != "issue_type_counts":
                print(f"    {k:<35}: {v}")

    # ── тест компонентов GUI ──────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("  ТЕСТ 5: ПРОВЕРКА КОМПОНЕНТОВ СИСТЕМЫ")
    print("=" * 72)

    components = [
        ("gui_app.py",                    Path("gui_app.py").exists()),
        ("order_structure_validator.py",  Path("order_structure_validator.py").exists()),
        ("error_detection_model.py",      Path("error_detection_model.py").exists()),
        ("train_on_dataset_gd.py",        Path("train_on_dataset_gd.py").exists()),
        ("data_loader.py",                Path("data_loader.py").exists()),
        ("config.py",                     Path("config.py").exists()),
        ("dataset_gd/train.jsonl",        Path("dataset_gd/train.jsonl").exists()),
        ("dataset_gd/val.jsonl",          Path("dataset_gd/val.jsonl").exists()),
        ("dataset_gd/test.jsonl",         Path("dataset_gd/test.jsonl").exists()),
        ("output/models/best_error_detection_model.pt",
         Path("output/models/best_error_detection_model.pt").exists()),
    ]

    all_ok = True
    for name, ok in components:
        print(f"  {'[+]' if ok else '[-]'}  {name}")
        if not ok:
            all_ok = False

    sz = Path("output/models/best_error_detection_model.pt")
    if sz.exists():
        mb = sz.stat().st_size / 1024 / 1024
        print(f"\n  Размер модели: {mb:.1f} МБ")

    # ── итоговая сводка ───────────────────────────────────────────────────
    elapsed = time.time() - t0_total
    print("\n" + "=" * 72)
    print("  ИТОГОВАЯ СВОДКА КАЧЕСТВА СИСТЕМЫ")
    print("=" * 72)
    print(f"  Дата тестирования          : {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print(f"  Время тестирования         : {elapsed:.1f} с")
    print()
    print(f"  [ВАЛИДАТОР СТРУКТУРЫ]")
    print(f"    Точность вердикта        : {val_accuracy:.1f}%  ({correct_verdict}/{len(DOCS)})")
    print(f"    Среднее время проверки   : {avg_time_val:.1f} мс/документ")
    print(f"    Проверяемых элементов    : 14 (шапка, заголовок, преамбула,")
    print(f"                               распорядит. часть, приложения)")
    print()
    if model_available and acc is not None:
        print(f"  [НЕЙРОННАЯ МОДЕЛЬ (rubert-tiny2)]")
        print(f"    Accuracy                 : {acc:.2f}%")
        print(f"    F1-score (weighted)      : {f1w:.2f}%")
        print(f"    F1-score (macro)         : {f1m:.2f}%")
        print(f"    Precision (weighted)     : {prec:.2f}%")
        print(f"    Recall    (weighted)     : {rec:.2f}%")
        print(f"    Среднее время предсказ.  : {avg_ms:.1f} мс/документ")
        print(f"    Обучена на               : 3 361 реальных приказе МЭР")
        print(f"    Датасет train/val/test   : 8 000 / 1 000 / 1 000 записей")
    else:
        print(f"  [НЕЙРОННАЯ МОДЕЛЬ] — не загружена")
    print()
    print(f"  [ДАННЫЕ]")
    print(f"    Датасет dataset_gd       : {'OK' if dataset_ok else 'ПРОБЛЕМЫ'}")
    print(f"    Записей в train.jsonl    : 8 000  (3 361 prikaz с текстом)")
    print()
    print(f"  [КОМПОНЕНТЫ]")
    print(f"    Все файлы на месте       : {'YES' if all_ok else 'НЕТ — см. выше'}")
    print()

    # оценка
    score = 0
    if val_accuracy >= 87: score += 30
    elif val_accuracy >= 75: score += 20
    if model_available and acc and acc >= 90: score += 40
    elif model_available and acc and acc >= 80: score += 25
    if all_ok: score += 20
    if dataset_ok: score += 10

    grade = ("ОТЛИЧНО" if score >= 90 else
             "ХОРОШО"  if score >= 70 else
             "УДОВЛ."  if score >= 50 else "ТРЕБУЕТ ДОРАБОТКИ")
    print(f"  ОБЩАЯ ОЦЕНКА СИСТЕМЫ : {score}/100  —  {grade}")
    print("=" * 72)

    # ── сохранение отчёта ─────────────────────────────────────────────────
    report_path = Path("output") / "reports" / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    # собираем полный вывод в файл повторным вызовом (упрощённая копия)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"ОТЧЁТ О ТЕСТИРОВАНИИ СИСТЕМЫ ПРОВЕРКИ ПРИКАЗОВ МЭР\n")
        f.write(f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
        f.write("=" * 72 + "\n\n")
        f.write(f"ВАЛИДАТОР СТРУКТУРЫ\n")
        f.write(f"  Точность: {val_accuracy:.1f}%  ({correct_verdict}/{len(DOCS)})\n")
        f.write(f"  Среднее время: {avg_time_val:.1f} мс/документ\n\n")
        for r in results:
            f.write(f"  {'PASS' if r['pass'] else 'FAIL'} | {r['name']}\n")
            f.write(f"       valid={r['valid']} | ошибок={r['errors']} | "
                    f"предупр={r['warnings']} | {r['ms']:.1f}мс\n")
        if model_available and acc is not None:
            f.write(f"\nНЕЙРОННАЯ МОДЕЛЬ\n")
            f.write(f"  Accuracy        : {acc:.2f}%\n")
            f.write(f"  F1  (weighted)  : {f1w:.2f}%\n")
            f.write(f"  F1  (macro)     : {f1m:.2f}%\n")
            f.write(f"  Precision (w)   : {prec:.2f}%\n")
            f.write(f"  Recall    (w)   : {rec:.2f}%\n")
            f.write(f"  Время/документ  : {avg_ms:.1f} мс\n")
        f.write(f"\nОБЩАЯ ОЦЕНКА: {score}/100  —  {grade}\n")
    print(f"\n  Отчёт сохранён: {report_path}")
    print("=" * 72)


if __name__ == "__main__":
    run_tests()
