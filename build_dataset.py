#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка датасета из двух источников:
  1. Законодательные акты ГД РФ (.doc/.rtf)
     C:\...\Modeldataish\<bill_id>\<doc_type>\<file>
  2. Приказы pravo.gov.ru (.txt)
     C:\...\Modeldataish\PravoGov\Приказы\<file>.txt
     + (опционально) мета-CSV: PravoGovПриказы.csv рядом с папкой

Запуск (скрипт лежит в папке 7125455):
  python build_dataset.py

С явными путями:
  python build_dataset.py --src "C:/..." --out "C:/..." --target 10000
"""

import os
import re
import sys
import csv
import json
import copy
import random
import argparse
import logging
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

# ================================================================
# ЧАСТЬ 1 — константы для ГД-актов
# ================================================================
KNOWN_DOC_TYPES = {
    "заключение_комитета", "перечень_нпа", "письмо_в_сгд",
    "пояснительная_записка", "протокол_совета_гд", "прочее",
    "сопроводительное_письмо", "текст_внесённый", "фзо", "фэо",
    "решение_комитета", "проект_постановления", "отзыв_правительства",
    "поправки", "таблица_поправок", "заключение_правового_управления",
    "заключение_счётной_палаты", "особое_мнение", "стенограмма",
    "пояснение", "сведения_об_авторах",
}
REQUIRED_DOC_TYPES   = {"пояснительная_записка", "текст_внесённый"}
RECOMMENDED_DOC_TYPES = {"перечень_нпа", "сопроводительное_письмо"}

# ================================================================
# ЧАСТЬ 2 — парсер приказов pravo.gov.ru (.txt)
# ================================================================

# Паттерны для извлечения структурных полей приказа
_PATTERNS = {
    "registration": re.compile(
        r"Зарегистрировано в Минюсте России\s+(.+?)\s+N\s+(\d+)", re.I
    ),
    "ministry": re.compile(
        r"(МИНИСТЕРСТВО|ФЕДЕРАЛЬНАЯ СЛУЖБА|ФЕДЕРАЛЬНОЕ АГЕНТСТВО|"
        r"РОССТАТ|РОСКОМНАДЗОР|БАНК РОССИИ)[^\n]{0,120}", re.I
    ),
    "order_date": re.compile(
        r"ПРИКАЗ\s*от\s+(\d{1,2}\s+\w+\s+\d{4}\s+г\.)\s+N\s+([\w\-]+)", re.I
    ),
    "order_title": re.compile(
        r"ОБ УТВЕРЖДЕНИИ\s+(.{10,300}?)(?=В соответствии|В целях|Приказываю|$)",
        re.I | re.S
    ),
    "basis": re.compile(
        r"В соответствии с\s+(.{20,400}?)\s*приказываю:", re.I | re.S
    ),
    "approved_doc": re.compile(
        r"Утвердить\s+(.{10,300}?)\s*(?:согласно приложению|к настоящему приказу|\.\s)",
        re.I | re.S
    ),
    "signatory": re.compile(
        r"(?:Министр|Директор|Руководитель|Председатель)[^\n]{0,60}\n\s*([А-ЯЁ]\.[А-ЯЁ]\.[А-ЯЁ][а-яё]+)",
        re.M
    ),
}

# Обязательные поля приказа для проверки структуры
REQUIRED_ORDER_FIELDS = {
    "ministry":      "Наименование органа власти",
    "order_date":    "Дата и номер приказа",
    "order_title":   "Предмет приказа (ОБ УТВЕРЖДЕНИИ...)",
    "approved_doc":  "Утверждаемый документ",
}
RECOMMENDED_ORDER_FIELDS = {
    "registration":  "Регистрация в Минюсте",
    "basis":         "Правовое основание (В соответствии с...)",
    "signatory":     "Подпись (Министр / Руководитель)",
}


def parse_order_txt(filepath: Path) -> dict:
    """
    Читает .txt приказа и извлекает структурные поля.
    Возвращает dict с полями и списком errors.
    """
    try:
        raw = filepath.read_bytes()
    except Exception as e:
        return {"error": f"read_error: {e}", "fields": {}, "errors": [], "text": ""}

    # Определяем кодировку
    for enc in ("utf-8", "cp1251", "utf-16", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")

    # Нормализуем пробелы для regex (файл может быть однострочным)
    text_norm = re.sub(r"  +", " ", text)

    fields = {}
    for key, pat in _PATTERNS.items():
        m = pat.search(text_norm)
        if m:
            fields[key] = " ".join(m.group(0).split())[:300]

    # Структурные ошибки
    errors = []
    for field, label in REQUIRED_ORDER_FIELDS.items():
        if field not in fields:
            errors.append({
                "type": "missing_required_field",
                "severity": "error",
                "detail": f"Не найдено обязательное поле: '{label}'"
            })
    for field, label in RECOMMENDED_ORDER_FIELDS.items():
        if field not in fields:
            errors.append({
                "type": "missing_recommended_field",
                "severity": "warning",
                "detail": f"Не найдено рекомендуемое поле: '{label}'"
            })

    # Краткое резюме текста (первые 3000 символов)
    summary = text_norm.strip()[:3000]

    return {
        "fields": fields,
        "errors": errors,
        "text": summary,
    }


def make_order_record(filepath: Path, source_id: str) -> Optional[dict]:
    """Создаёт запись датасета для одного приказа (.txt)."""
    parsed = parse_order_txt(filepath)
    if "error" in parsed:
        log.warning(f"Пропускаем {filepath.name}: {parsed['error']}")
        return None

    errors = parsed["errors"]
    critical = [e for e in errors if e["severity"] == "error"]
    fields   = parsed["fields"]

    # Формируем текст input для модели
    fields_text = "\n".join(
        f"  {k}: {v}" for k, v in fields.items()
    ) if fields else "  (структурные поля не обнаружены)"

    input_text = (
        f"=== ПРИКАЗ: {filepath.stem} ===\n"
        f"Извлечённые поля:\n{fields_text}\n\n"
        f"Текст документа (фрагмент):\n{parsed['text'][:2000]}"
    )

    if not errors:
        response = "Структурных ошибок не обнаружено. Приказ оформлен корректно."
    else:
        lines = []
        crit = [e for e in errors if e["severity"] == "error"]
        warn = [e for e in errors if e["severity"] == "warning"]
        if crit:
            lines.append("КРИТИЧЕСКИЕ ОШИБКИ:")
            lines.extend(f"  - {e['detail']}" for e in crit)
        if warn:
            lines.append("ПРЕДУПРЕЖДЕНИЯ:")
            lines.extend(f"  - {e['detail']}" for e in warn)
        response = "\n".join(lines)

    return {
        "source":             "prikaz",
        "bill_id":            source_id,
        "filename":           filepath.name,
        "fields_found":       sorted(fields.keys()),
        "text":               input_text[:6000],
        "errors":             errors,
        "has_critical_errors": len(critical) > 0,
        "has_any_issues":     len(errors) > 0,
        "instruction": (
            "Проверь структуру нормативного приказа федерального органа исполнительной власти. "
            "Укажи критические ошибки (отсутствующие обязательные реквизиты: наименование органа, "
            "дата/номер приказа, предмет приказа, утверждаемый документ) "
            "и предупреждения (отсутствует регистрация в Минюсте, правовое основание, подпись)."
        ),
        "response": response,
    }


# ================================================================
# ЧАСТЬ 3 — конвертер doc/rtf (как раньше)
# ================================================================

def read_file_bytes(filepath: Path) -> Optional[bytes]:
    try:
        with open(filepath, "rb") as f:
            return f.read()
    except Exception as e:
        log.warning(f"Не удалось прочитать {filepath.name}: {e}")
        return None


def convert_to_text(filepath: Path, tmp_dir: Path) -> Optional[str]:
    suffix = filepath.suffix.lower()
    if suffix not in (".doc", ".rtf", ".docx"):
        return None

    raw_bytes = read_file_bytes(filepath)
    if raw_bytes is None:
        return None

    safe_input = tmp_dir / f"src{suffix}"
    try:
        with open(safe_input, "wb") as f:
            f.write(raw_bytes)
    except Exception as e:
        log.warning(f"Не удалось записать tmp для {filepath.name}: {e}")
        return None

    text_bytes = None
    try:
        if suffix in (".doc", ".rtf"):
            safe_docx = tmp_dir / "src.docx"
            if safe_docx.exists():
                safe_docx.unlink()
            subprocess.run(
                ["soffice", "--headless", "--convert-to", "docx",
                 "--outdir", str(tmp_dir), str(safe_input)],
                capture_output=True, timeout=60,
            )
            if safe_docx.exists():
                r = subprocess.run(
                    ["pandoc", str(safe_docx), "-t", "plain"],
                    capture_output=True, timeout=30,
                )
                text_bytes = r.stdout
                safe_docx.unlink(missing_ok=True)
            else:
                r = subprocess.run(
                    ["pandoc", str(safe_input), "-t", "plain"],
                    capture_output=True, timeout=30,
                )
                text_bytes = r.stdout
        elif suffix == ".docx":
            r = subprocess.run(
                ["pandoc", str(safe_input), "-t", "plain"],
                capture_output=True, timeout=30,
            )
            text_bytes = r.stdout
    except subprocess.TimeoutExpired:
        log.debug(f"Timeout: {filepath.name}")
        return None
    except Exception as e:
        log.debug(f"Конвертация {filepath.name}: {e}")
        return None
    finally:
        safe_input.unlink(missing_ok=True)

    if not text_bytes:
        return None

    for enc in ("utf-8", "cp1251", "latin-1"):
        try:
            decoded = text_bytes.decode(enc) if isinstance(text_bytes, bytes) else text_bytes
            clean = decoded.strip()
            if clean:
                return clean[:4000]
        except (UnicodeDecodeError, AttributeError):
            continue
    return None


# ================================================================
# ЧАСТЬ 4 — обработка ГД-актов (папки bill_id)
# ================================================================

def detect_gd_errors(found_types: set) -> list:
    errors = []
    for req in REQUIRED_DOC_TYPES:
        if req not in found_types:
            errors.append({
                "type": "missing_required_section",
                "severity": "error",
                "detail": f"Отсутствует обязательный раздел: '{req}'"
            })
    for rec in RECOMMENDED_DOC_TYPES:
        if rec not in found_types:
            errors.append({
                "type": "missing_recommended_section",
                "severity": "warning",
                "detail": f"Отсутствует рекомендуемый раздел: '{rec}'"
            })
    for u in sorted(found_types - KNOWN_DOC_TYPES):
        errors.append({
            "type": "unknown_section",
            "severity": "warning",
            "detail": f"Неизвестный тип раздела: '{u}'"
        })
    return errors


def process_gd_bill(bill_dir: Path, tmp_dir: Path) -> Optional[dict]:
    bill_id = bill_dir.name
    subdirs = [d for d in bill_dir.iterdir() if d.is_dir()]
    if not subdirs:
        return None

    found_types = {d.name.lower() for d in subdirs}
    sections = {}
    for subdir in subdirs:
        doc_type = subdir.name.lower()
        files = (
            list(subdir.glob("*.doc")) +
            list(subdir.glob("*.rtf")) +
            list(subdir.glob("*.docx"))
        )
        sections[doc_type] = convert_to_text(files[0], tmp_dir) if files else ""

    errors  = detect_gd_errors(found_types)
    critical = [e for e in errors if e["severity"] == "error"]

    parts = [
        f"=== {dt.upper()} ===\n{sections[dt][:800]}"
        for dt in sorted(sections) if sections[dt]
    ]

    if not errors:
        response = "Структурных ошибок не обнаружено. Пакет документов сформирован корректно."
    else:
        lines = []
        crit = [e for e in errors if e["severity"] == "error"]
        warn = [e for e in errors if e["severity"] == "warning"]
        if crit:
            lines.append("КРИТИЧЕСКИЕ ОШИБКИ:")
            lines.extend(f"  - {e['detail']}" for e in crit)
        if warn:
            lines.append("ПРЕДУПРЕЖДЕНИЯ:")
            lines.extend(f"  - {e['detail']}" for e in warn)
        response = "\n".join(lines)

    return {
        "source":             "gd_bill",
        "bill_id":            bill_id,
        "sections_found":     sorted(found_types),
        "text":               "\n\n".join(parts)[:6000],
        "errors":             errors,
        "has_critical_errors": len(critical) > 0,
        "has_any_issues":     len(errors) > 0,
        "instruction": (
            "Проверь структуру пакета документов законодательного акта ГД РФ. "
            "Укажи критические ошибки (отсутствующие обязательные разделы: "
            "пояснительная_записка, текст_внесённый) и предупреждения."
        ),
        "response": response,
    }


# ================================================================
# ЧАСТЬ 5 — аугментация до target
# ================================================================

def augment_to_target(records: list, target: int, seed: int) -> list:
    if len(records) >= target:
        return records[:target]

    rng   = random.Random(seed + 1)
    result = list(records)
    needed = target - len(records)
    log.info(f"Реальных записей: {len(records)}. Аугментируем до {target} (+{needed}).")

    fake_sections = [
        "справка_автора", "биография_автора", "медиаматериалы",
        "приложение", "экспертиза_нии", "дополнение",
    ]
    fake_fields = [
        "annex_1", "annex_2", "cover_note", "expert_review",
    ]

    ctr = 0
    aug_pool = [r for r in records if r.get("text")]
    if not aug_pool:
        log.warning("Нет данных для аугментации")
        return result

    while len(result) < target:
        base = copy.deepcopy(rng.choice(aug_pool))
        ctr += 1
        base["bill_id"] = f"AUG_{ctr:05d}_" + base["bill_id"]
        action = rng.random()

        if base["source"] == "gd_bill":
            found = set(base.get("sections_found", []))
            if action < 0.35 and found:
                found.discard(rng.choice(sorted(found)))
            elif action < 0.55:
                found.add(rng.choice(fake_sections))
            base["sections_found"] = sorted(found)
            new_errors = detect_gd_errors(found)

        else:  # prikaz
            found_f = set(base.get("fields_found", []))
            if action < 0.35 and found_f:
                found_f.discard(rng.choice(sorted(found_f)))
            elif action < 0.55:
                found_f.add(rng.choice(fake_fields))
            base["fields_found"] = sorted(found_f)

            new_errors = []
            for field, label in REQUIRED_ORDER_FIELDS.items():
                if field not in found_f:
                    new_errors.append({
                        "type": "missing_required_field",
                        "severity": "error",
                        "detail": f"Не найдено обязательное поле: '{label}'"
                    })
            for field, label in RECOMMENDED_ORDER_FIELDS.items():
                if field not in found_f:
                    new_errors.append({
                        "type": "missing_recommended_field",
                        "severity": "warning",
                        "detail": f"Не найдено рекомендуемое поле: '{label}'"
                    })

        base["errors"]             = new_errors
        base["has_critical_errors"] = any(e["severity"] == "error" for e in new_errors)
        base["has_any_issues"]      = len(new_errors) > 0

        if not new_errors:
            base["response"] = (
                "Структурных ошибок не обнаружено. Документ оформлен корректно."
            )
        else:
            lines = []
            crit = [e for e in new_errors if e["severity"] == "error"]
            warn = [e for e in new_errors if e["severity"] == "warning"]
            if crit:
                lines.append("КРИТИЧЕСКИЕ ОШИБКИ:")
                lines.extend(f"  - {e['detail']}" for e in crit)
            if warn:
                lines.append("ПРЕДУПРЕЖДЕНИЯ:")
                lines.extend(f"  - {e['detail']}" for e in warn)
            base["response"] = "\n".join(lines)

        result.append(base)

    log.info(f"Аугментация завершена. Итого: {len(result)} записей.")
    return result


# ================================================================
# ЧАСТЬ 6 — сборка и сохранение датасета
# ================================================================

def save_dataset(records: list, out_dir: Path):
    # Полный JSONL
    with open(out_dir / "dataset.jsonl", "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Fine-tune формат (messages)
    system_gd = (
        "Ты эксперт по проверке структуры пакетов документов "
        "законодательных актов Государственной Думы РФ. "
        "Обязательные разделы: пояснительная_записка, текст_внесённый."
    )
    system_prikaz = (
        "Ты эксперт по проверке структуры нормативных приказов "
        "федеральных органов исполнительной власти РФ. "
        "Обязательные реквизиты: наименование органа, дата/номер приказа, "
        "предмет приказа, утверждаемый документ."
    )
    with open(out_dir / "finetune_instruction.jsonl", "w", encoding="utf-8") as f:
        for rec in records:
            sys_msg = system_prikaz if rec["source"] == "prikaz" else system_gd
            ft_rec = {
                "messages": [
                    {"role": "system", "content": sys_msg},
                    {
                        "role": "user",
                        "content": (
                            f"{rec['instruction']}\n\n"
                            f"Документ ID: {rec['bill_id']}\n\n"
                            f"{rec['text']}"
                        )
                    },
                    {"role": "assistant", "content": rec["response"]}
                ]
            }
            f.write(json.dumps(ft_rec, ensure_ascii=False) + "\n")

    # Сплиты 80/10/10
    random.shuffle(records)
    n = len(records)
    splits = {
        "train": records[:int(n * 0.8)],
        "val":   records[int(n * 0.8):int(n * 0.9)],
        "test":  records[int(n * 0.9):]
    }
    for name, data in splits.items():
        with open(out_dir / f"{name}.jsonl", "w", encoding="utf-8") as f:
            for rec in data:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        log.info(f"  {name}: {len(data)} записей")

    # Статистика
    by_source: dict = {}
    error_types: dict = {}
    critical_total = sum(1 for r in records if r["has_critical_errors"])
    issues_total   = sum(1 for r in records if r["has_any_issues"])
    for rec in records:
        src = rec["source"]
        by_source[src] = by_source.get(src, 0) + 1
        for err in rec["errors"]:
            t = f"{err['severity']}:{err['type']}"
            error_types[t] = error_types.get(t, 0) + 1

    stats = {
        "total_records": len(records),
        "by_source": by_source,
        "records_with_critical_errors": critical_total,
        "records_with_any_issues": issues_total,
        "records_clean": len(records) - issues_total,
        "critical_error_rate_pct": round(critical_total / len(records) * 100, 1) if records else 0,
        "splits": {k: len(v) for k, v in splits.items()},
        "issue_type_counts": error_types,
    }
    with open(out_dir / "stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    return stats


def build_dataset(src_dir: Path, out_dir: Path, target: int, seed: int = 42):
    random.seed(seed)
    out_dir.mkdir(parents=True, exist_ok=True)

    records = []

    # ---- Источник 1: ГД-акты ----
    gd_dirs = []
    pravogov_dir = src_dir / "PravoGov"

    for d in src_dir.iterdir():
        if d.is_dir() and d.name != "PravoGov":
            gd_dirs.append(d)

    log.info(f"ГД-акты: найдено {len(gd_dirs)} папок")

    tmp_dir = Path(tempfile.mkdtemp(prefix="gd_"))
    log.info(f"Временная папка: {tmp_dir}")
    try:
        for i, bill_dir in enumerate(gd_dirs):
            if i % 200 == 0:
                log.info(f"  ГД прогресс: {i}/{len(gd_dirs)} (записей: {len(records)})")
            rec = process_gd_bill(bill_dir, tmp_dir)
            if rec:
                records.append(rec)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    log.info(f"ГД-актов обработано: {sum(1 for r in records if r['source']=='gd_bill')}")

    # ---- Источник 2: Приказы PravoGov (.txt) ----
    prikaz_dir = pravogov_dir / "Приказы" if pravogov_dir.exists() else None
    if prikaz_dir and prikaz_dir.exists():
        txt_files = list(prikaz_dir.glob("*.txt"))
        log.info(f"Приказы PravoGov: найдено {len(txt_files)} .txt файлов")
        for i, fp in enumerate(txt_files):
            if i % 200 == 0:
                log.info(f"  Приказы прогресс: {i}/{len(txt_files)}")
            rec = make_order_record(fp, fp.stem)
            if rec:
                records.append(rec)
        log.info(f"Приказов обработано: {sum(1 for r in records if r['source']=='prikaz')}")
    else:
        log.warning(f"Папка приказов не найдена: {prikaz_dir}")

    if not records:
        log.error("Нет ни одной записи! Проверьте пути.")
        sys.exit(1)

    log.info(f"Всего реальных записей: {len(records)}")

    # ---- Аугментация до target ----
    random.shuffle(records)
    records = augment_to_target(records, target, seed)

    # ---- Сохранение ----
    stats = save_dataset(records, out_dir)

    log.info(f"\n{'='*60}")
    log.info(f"Датасет готов           : {out_dir}")
    log.info(f"Всего записей           : {stats['total_records']}")
    log.info(f"По источникам           : {stats['by_source']}")
    log.info(f"С критическими ошибками : {stats['records_with_critical_errors']} "
             f"({stats['critical_error_rate_pct']}%)")
    log.info(f"Чистых записей          : {stats['records_clean']}")
    log.info(f"Файлы:")
    log.info(f"  dataset.jsonl              - полный датасет")
    log.info(f"  finetune_instruction.jsonl - формат messages для fine-tuning")
    log.info(f"  train / val / test .jsonl  - сплиты 80/10/10")
    log.info(f"  stats.json                 - статистика")
    log.info(f"{'='*60}")


# ================================================================
# ЧАСТЬ 7 — точка входа
# ================================================================
if __name__ == "__main__":
    _script_dir = Path(__file__).resolve().parent
    _default_src = _script_dir / "Modeldataish"
    _default_out = _script_dir / "dataset_gd"

    parser = argparse.ArgumentParser(
        description="Сборка датасета: ГД-акты + приказы PravoGov",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--src", default=str(_default_src),
        help=f"Папка Modeldataish\n(default: {_default_src})"
    )
    parser.add_argument(
        "--out", default=str(_default_out),
        help=f"Папка для датасета\n(default: {_default_out})"
    )
    parser.add_argument(
        "--target", type=int, default=10000,
        help="Целевой размер датасета (default: 10000)"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed (default: 42)"
    )

    args = parser.parse_args()
    log.info(f"Папка с данными : {args.src}")
    log.info(f"Папка датасета  : {args.out}")
    log.info(f"Целевой размер  : {args.target}")

    src = Path(args.src)
    if not src.exists():
        log.error(f"Папка не найдена: {src}")
        sys.exit(1)

    build_dataset(
        src_dir=src,
        out_dir=Path(args.out),
        target=args.target,
        seed=args.seed,
    )
