# -*- coding: utf-8 -*-
"""
Система проверки приказов Министерства экономического развития России
Поддержка форматов: TXT, DOCX, PDF
"""

import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk
import os
import threading
import webbrowser
import csv
from datetime import datetime
from order_structure_validator import OrderStructureValidator
from data_loader import load_file_by_type
from error_detection_model import ErrorDetectionTrainer
import config


SECTIONS = [
    {
        "title": "Раздел 1",
        "full_title": "Проекты приказов МЭР и результаты общественного обсуждения",
        "url": "https://regulation.gov.ru/projects/?type=Grid#departments=6",
        "portal": "regulation.gov.ru",
        "columns": ("№", "Название проекта приказа", "Дата публикации", "Статус", "Комментариев"),
        "data": [
            ("1", "Об утверждении методических рекомендаций по оценке регулирующего воздействия", "15.03.2025", "На обсуждении", "12"),
            ("2", "О внесении изменений в приказ МЭР № 532 от 25.09.2024", "10.03.2025", "Обсуждение завершено", "8"),
            ("3", "Об установлении порядка ведения реестра инвестиционных проектов", "05.03.2025", "Обсуждение завершено", "15"),
            ("4", "Об утверждении формы заключения об ОРВ проектов нормативных актов", "28.02.2025", "Обсуждение завершено", "6"),
            ("5", "О внесении изменений в порядок проведения антикоррупционной экспертизы", "20.02.2025", "На доработке", "22"),
            ("6", "Об утверждении стандарта государственной услуги по регистрации юрлиц", "15.02.2025", "Обсуждение завершено", "9"),
            ("7", "О признании утратившими силу некоторых приказов МЭР", "10.02.2025", "Обсуждение завершено", "3"),
            ("8", "Об установлении критериев оценки эффективности деятельности органов власти", "05.02.2025", "На обсуждении", "17"),
        ],
    },
    {
        "title": "Раздел 2",
        "full_title": "Независимая антикоррупционная экспертиза проектов приказов",
        "url": "https://regulation.gov.ru/projects/?type=Grid#departments=6&categories=5",
        "portal": "regulation.gov.ru",
        "columns": ("№", "Проект нормативного акта", "Дата начала экспертизы", "Эксперт", "Результат"),
        "data": [
            ("1", "Проект приказа об утверждении порядка ведения реестра субъектов МСП", "20.03.2025", "Иванов А.В.", "Нарушений не выявлено"),
            ("2", "Проект приказа о внесении изменений в методику оценки ущерба", "18.03.2025", "Петрова Е.С.", "Выявлены коррупциогенные факторы"),
            ("3", "Проект приказа об установлении требований к раскрытию информации", "12.03.2025", "Сидоров К.М.", "Нарушений не выявлено"),
            ("4", "Проект приказа об утверждении административного регламента", "08.03.2025", "Козлова Н.И.", "Нарушений не выявлено"),
            ("5", "Проект приказа о порядке согласования инвестиционных программ", "02.03.2025", "Новиков Д.А.", "На рассмотрении"),
            ("6", "Проект приказа об утверждении перечня документов для господдержки МСП", "25.02.2025", "Орлов В.Г.", "Нарушений не выявлено"),
            ("7", "Проект приказа о признании утратившими силу ряда нормативных актов", "20.02.2025", "Федоров С.Р.", "Нарушений не выявлено"),
        ],
    },
    {
        "title": "Раздел 3",
        "full_title": "Участие в подготовке законодательных актов. Сводная таблица по субъектам ЗИ с итогами",
        "url": "https://sozd.duma.gov.ru/oz_info_spzi/spzi_list",
        "portal": "sozd.duma.gov.ru",
        "columns": ("№", "Субъект законодательной инициативы", "Законопроект", "Стадия", "Дата внесения"),
        "data": [
            ("1", "Правительство РФ", "О внесении изменений в ФЗ «О развитии малого и среднего предпринимательства»", "Второе чтение", "22.03.2025"),
            ("2", "МЭР России", "О внесении изменений в ФЗ «Об обществах с ограниченной ответственностью»", "Первое чтение", "15.03.2025"),
            ("3", "Депутаты ГД", "Об инновационной деятельности и государственной инновационной политике", "Внесен", "10.03.2025"),
            ("4", "Правительство РФ", "О внесении изменений в Федеральный закон «Об инвестиционной деятельности»", "Подписан", "05.03.2025"),
            ("5", "Совет Федерации", "О внесении изменений в ФЗ «О государственной регистрации юридических лиц»", "Третье чтение", "28.02.2025"),
            ("6", "МЭР России", "О внесении изменений в Налоговый кодекс РФ (в части налогообложения МСП)", "Первое чтение", "20.02.2025"),
            ("7", "Правительство РФ", "О внесении изменений в ФЗ «О несостоятельности (банкротстве)»", "На рассмотрении", "14.02.2025"),
            ("8", "Депутаты ГД", "Об особых экономических зонах в Российской Федерации (новая редакция)", "Внесен", "08.02.2025"),
        ],
    },
    {
        "title": "Раздел 4",
        "full_title": "Официально опубликованные нормативные акты МЭР",
        "url": "http://publication.pravo.gov.ru/search/federal_authorities?pageSize=30&index=1&SignatoryAuthorityId=59ad7c35-7d14-424e-b305-f964615734bd&&PublishDateSearchType=0&NumberSearchType=0&DocumentDateSearchType=0&JdRegSearchType=0&SortedBy=6&SortDestination=1",
        "portal": "publication.pravo.gov.ru",
        "columns": ("№", "Название нормативного акта", "Дата публикации", "Номер приказа", "Статус"),
        "data": [
            ("1", "Приказ МЭР об утверждении методики расчёта прогнозного плана приватизации", "25.03.2025", "№ 145", "Действующий"),
            ("2", "Приказ МЭР об утверждении методики оценки финансового состояния юрлиц", "20.03.2025", "№ 142", "Действующий"),
            ("3", "Приказ МЭР о внесении изменений в приказ № 112 от 14.01.2025", "15.03.2025", "№ 138", "Действующий"),
            ("4", "Приказ МЭР об утверждении административного регламента предоставления госуслуги", "10.03.2025", "№ 134", "Действующий"),
            ("5", "Приказ МЭР о порядке согласования государственных программ субъектов РФ", "05.03.2025", "№ 129", "Действующий"),
            ("6", "Приказ МЭР об установлении требований к структуре стратегий развития", "28.02.2025", "№ 125", "Действующий"),
            ("7", "Приказ МЭР о признании утратившим силу приказа № 98 от 22.11.2024", "20.02.2025", "№ 118", "Действующий"),
            ("8", "Приказ МЭР об утверждении перечня системообразующих организаций", "15.02.2025", "№ 114", "Действующий"),
            ("9", "Приказ МЭР о порядке ведения реестра контрактов по ГЧП", "10.02.2025", "№ 110", "Действующий"),
        ],
    },
]

# Справочник и шаблоны для антикоррупционного сканирования формулировок НПА
CORRUPTION_REFERENCE_TEXT = """
При проведении анализа нормативных правовых актов к коррупциогенным формулировкам
целесообразно относить следующие конструкции:

  «Орган может принять иные решения по своему усмотрению»
      (отсутствуют пределы усмотрения и критерии выбора решения)

  «Допускается отклонение от установленных требований»
      (не указаны условия и границы допустимого отклонения)

  «При необходимости заявитель предоставляет дополнительные документы»
      (не определено, в каких случаях возникает необходимость и какие документы требуются)

  «Компетентный орган вправе установить особый порядок»
      (не раскрыто содержание «особого порядка»)

  «Решение принимается в разумный срок»
      (оценочная категория без конкретных временных рамок)

  «В исключительных случаях допускается продление срока»
      (не определены критерии «исключительности»)

  «Иные основания, предусмотренные действующим законодательством»
      (слишком широкая отсылка без конкретизации)

  «При наличии обоснованных причин может быть отказано»
      (не раскрыт перечень или критерии «обоснованных причин»)

  «Орган вправе запросить дополнительные пояснения»
      (не указано, какие именно пояснения и в каком объёме)

  «Размер выплаты определяется индивидуально»
      (отсутствуют методика расчёта и объективные критерии)

  «Допускается применение иных мер воздействия»
      (не конкретизирован перечень мер)

  «Решение принимается с учетом специфики ситуации»
      (размытая формулировка без перечня факторов)

  «Уполномоченное лицо самостоятельно определяет порядок действий»
      (чрезмерная дискреция без регламентации)

  «В отдельных случаях требования могут не применяться»
      (не раскрыто, какие случаи считаются отдельными)

  «Орган может учитывать иные обстоятельства»
      (отсутствует исчерпывающий перечень обстоятельств)
""".strip()

# (краткое название, regex, пояснение риска) — гибкий поиск по тексту акта
CORRUPTION_SCAN_RULES = [
    (
        "Орган может принять иные решения по своему усмотрению",
        r"орган\w{0,24}\s+(?:может\s+)?(?:принять\s+)?иные\s+решени\w*\s+.{0,45}усмотрени\w*",
        "отсутствуют пределы усмотрения и критерии выбора решения",
    ),
    (
        "Допускается отклонение от установленных требований",
        r"допускается\s+отклонение.{0,55}установленн\w*\s+требовани\w*",
        "не указаны условия и границы допустимого отклонения",
    ),
    (
        "При необходимости заявитель предоставляет дополнительные документы",
        r"при\s+необходимости.{0,40}заявител\w*.{0,50}дополнительн\w*\s+документ",
        "не определено, в каких случаях возникает необходимость и какие документы требуются",
    ),
    (
        "Компетентный орган вправе установить особый порядок",
        r"компетентн\w*\s+орган\w*.{0,55}особ\w+\s+порядок",
        "не раскрыто содержание «особого порядка»",
    ),
    (
        "Решение принимается в разумный срок",
        r"решени\w*\s+.{0,18}принима\w*.{0,30}разумн\w*\s+срок",
        "оценочная категория без конкретных временных рамок",
    ),
    (
        "В исключительных случаях допускается продление срока",
        r"исключительн\w*\s+случа\w*.{0,45}продлени\w*\s+срок",
        "не определены критерии «исключительности»",
    ),
    (
        "Иные основания, предусмотренные действующим законодательством",
        r"иные\s+основани\w*.{0,65}законодательств",
        "слишком широкая отсылка без конкретизации",
    ),
    (
        "При наличии обоснованных причин может быть отказано",
        r"обоснованн\w*\s+причин.{0,45}(?:может\s+быть\s+)?отказан",
        "не раскрыт перечень или критерии «обоснованных причин»",
    ),
    (
        "Орган вправе запросить дополнительные пояснения",
        r"орган\w{0,20}\s+вправе\s+запросить.{0,30}дополнительн\w*\s+пояснени",
        "не указано, какие именно пояснения и в каком объёме",
    ),
    (
        "Размер выплаты определяется индивидуально",
        r"размер\s+выплат\w*.{0,35}индивидуально",
        "отсутствуют методика расчёта и объективные критерии",
    ),
    (
        "Допускается применение иных мер воздействия",
        r"допускается\s+применени\w*.{0,30}иных\s+мер\s+воздействи",
        "не конкретизирован перечень мер",
    ),
    (
        "Решение принимается с учетом специфики ситуации",
        r"решени\w*\s+.{0,22}уч[её]том\s+специфики.{0,30}ситуаци",
        "размытая формулировка без перечня факторов",
    ),
    (
        "Уполномоченное лицо самостоятельно определяет порядок действий",
        r"уполномоченн\w*\s+лиц\w*.{0,45}самостоятельно\s+определ\w*.{0,45}порядок\s+действи",
        "чрезмерная дискреция без регламентации",
    ),
    (
        "В отдельных случаях требования могут не применяться",
        r"отдельн\w*\s+случа\w*.{0,50}требовани\w*\s+могут\s+не\s+применяться",
        "не раскрыто, какие случаи считаются отдельными",
    ),
    (
        "Орган может учитывать иные обстоятельства",
        r"орган\w{0,20}\s+может\s+учитывать.{0,28}иные\s+обстоятельств",
        "отсутствует исчерпывающий перечень обстоятельств",
    ),
]


class OrderCheckerGUI:
    BLUE = "#0039A6"
    RED = "#D52B1E"
    WHITE = "#FFFFFF"
    GREEN = "#2ECC71"
    LIGHT_BLUE = "#3498DB"
    DARK_BLUE = "#1A5490"
    GRAY = "#F0F2F5"
    SIDEBAR_BG = "#1E3A5F"
    SIDEBAR_ACTIVE = "#0039A6"
    SIDEBAR_TEXT = "#FFFFFF"

    def __init__(self, root):
        self.root = root
        self.root.title("Система проверки приказов Минэкономразвития России")
        self.root.geometry("1280x780")
        self.root.minsize(1024, 660)
        self.root.configure(bg=self.GRAY)

        self.validator = OrderStructureValidator()
        self.model_available = False
        self.trainer = None
        self._model_loading = True  # флаг: идёт загрузка

        self.current_file = None
        self.current_text = None
        self.last_validation_result = None
        self.last_model_result = None
        self.active_section = None
        self.current_tree = None

        self._build_ui()

        # Загружаем модель в фоне — GUI не зависает
        threading.Thread(target=self._load_model_bg, daemon=True).start()

    # ------------------------------------------------------------------ model
    def _load_model_bg(self):
        """Фоновая загрузка модели; обновляет UI через after()."""
        try:
            model_path = os.path.join(config.MODELS_DIR, "best_error_detection_model.pt")
            if os.path.exists(model_path):
                trainer = ErrorDetectionTrainer()
                trainer.load_model("best_error_detection_model.pt")
                self.trainer = trainer
                self.model_available = True
                print("✓ Модель загружена")
                self.root.after(0, self._on_model_ready)
            else:
                print("⚠ Модель не найдена, используется только проверка структуры")
                self.root.after(0, self._on_model_missing)
        except Exception as e:
            print(f"Ошибка загрузки модели: {e}")
            self.root.after(0, self._on_model_missing)
        finally:
            self._model_loading = False

    def _on_model_ready(self):
        """Вызывается из главного потока после успешной загрузки модели."""
        try:
            self._status_label.config(text="✓ Модель активна", bg="#1E8449")
        except Exception:
            pass

    def _on_model_missing(self):
        """Вызывается из главного потока если модель не загружена."""
        try:
            self._status_label.config(text="⚠ Только структура", bg="#E67E22")
        except Exception:
            pass

    # ------------------------------------------------------------------ build
    def _build_ui(self):
        self._build_header()
        self._build_toolbar()
        self._build_file_info()
        self._build_main()
        self._build_footer()

    def _build_header(self):
        hf = tk.Frame(self.root, bg=self.RED, height=58)
        hf.pack(fill=tk.X)
        hf.pack_propagate(False)

        tk.Label(
            hf,
            text="СИСТЕМА ПРОВЕРКИ ПРИКАЗОВ МИНЭКОНОМРАЗВИТИЯ РОССИИ",
            font=("Arial", 13, "bold"),
            bg=self.RED, fg=self.WHITE,
        ).pack(side=tk.LEFT, padx=20, pady=10)

        # Начальное состояние — модель ещё грузится
        self._status_label = tk.Label(
            hf, text="⏳ Загрузка модели...",
            font=("Arial", 9, "bold"),
            bg="#7F8C8D", fg=self.WHITE,
            padx=10, pady=4, relief=tk.RAISED,
        )
        self._status_label.pack(side=tk.RIGHT, padx=15, pady=12)

    def _build_toolbar(self):
        tf = tk.Frame(self.root, bg=self.BLUE, padx=15, pady=10)
        tf.pack(fill=tk.X)

        btn_cfg = dict(font=("Arial", 10, "bold"), padx=14, pady=7,
                       cursor="hand2", relief=tk.RAISED, bd=2)

        self.load_btn = tk.Button(
            tf, text="📂 Загрузить документ",
            command=self.load_file,
            bg=self.WHITE, fg=self.BLUE, **btn_cfg)
        self.load_btn.pack(side=tk.LEFT, padx=4)

        self.check_btn = tk.Button(
            tf, text="✓ Проверить структуру",
            command=self.check_document,
            bg="#1E8449", fg=self.WHITE,
            state=tk.DISABLED, **btn_cfg)
        self.check_btn.pack(side=tk.LEFT, padx=4)

        self.save_btn = tk.Button(
            tf, text="💾 Скачать отчёт",
            command=self.save_report,
            bg=self.LIGHT_BLUE, fg=self.WHITE,
            state=tk.DISABLED, **btn_cfg)
        self.save_btn.pack(side=tk.LEFT, padx=4)

        self.clear_btn = tk.Button(
            tf, text="🗑 Очистить",
            command=self.clear_results,
            bg=self.RED, fg=self.WHITE, **btn_cfg)
        self.clear_btn.pack(side=tk.LEFT, padx=4)

    def _build_file_info(self):
        self.info_bar = tk.Frame(self.root, bg=self.WHITE,
                                 padx=12, pady=6, relief=tk.SOLID, bd=1)
        self.info_bar.pack(fill=tk.X, padx=8, pady=(4, 0))

        self.file_label = tk.Label(
            self.info_bar, text="📄 Файл не загружен",
            font=("Arial", 10), bg=self.WHITE, fg=self.BLUE, anchor="w")
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("G.Horizontal.TProgressbar",
                        background=self.GREEN, troughcolor=self.WHITE,
                        bordercolor=self.BLUE, lightcolor=self.GREEN, darkcolor=self.GREEN)
        self.progress = ttk.Progressbar(
            self.info_bar, mode="indeterminate",
            length=200, style="G.Horizontal.TProgressbar")

    def _build_main(self):
        main = tk.Frame(self.root, bg=self.GRAY)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)

        self._build_sidebar(main)
        self._build_content(main)

    def _build_sidebar(self, parent):
        sb = tk.Frame(parent, bg=self.SIDEBAR_BG, width=235)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        sb.pack_propagate(False)

        tk.Label(
            sb, text="РАЗДЕЛЫ",
            font=("Arial", 10, "bold"),
            bg=self.SIDEBAR_BG, fg=self.WHITE, pady=12,
        ).pack(fill=tk.X)

        tk.Frame(sb, bg="#4A90D9", height=1).pack(fill=tk.X, padx=8)

        self._section_btns = []
        for idx, sec in enumerate(SECTIONS):
            short = sec["full_title"]
            if len(short) > 42:
                short = short[:42] + "…"
            btn = tk.Button(
                sb,
                text=f"{sec['title']}\n{short}",
                font=("Arial", 8),
                bg=self.SIDEBAR_BG, fg=self.WHITE,
                activebackground=self.SIDEBAR_ACTIVE, activeforeground=self.WHITE,
                cursor="hand2", relief=tk.FLAT, bd=0,
                wraplength=215, justify=tk.LEFT, anchor="w",
                padx=10, pady=9,
                command=lambda i=idx: self._switch_section(i),
            )
            btn.pack(fill=tk.X, padx=2, pady=1)
            self._section_btns.append(btn)

        tk.Frame(sb, bg="#4A90D9", height=1).pack(fill=tk.X, padx=8, pady=(12, 6))

        self.portal_btn = tk.Button(
            sb, text="🌐 Открыть на портале",
            command=self._open_portal,
            font=("Arial", 9, "bold"),
            bg="#27AE60", fg=self.WHITE,
            cursor="hand2", relief=tk.RAISED, bd=2,
            padx=10, pady=8, state=tk.DISABLED,
        )
        self.portal_btn.pack(fill=tk.X, padx=10, pady=3)

        self.export_btn = tk.Button(
            sb, text="📊 Экспорт в CSV",
            command=self._export_csv,
            font=("Arial", 9, "bold"),
            bg="#8E44AD", fg=self.WHITE,
            cursor="hand2", relief=tk.RAISED, bd=2,
            padx=10, pady=8, state=tk.DISABLED,
        )
        self.export_btn.pack(fill=tk.X, padx=10, pady=3)

    def _build_content(self, parent):
        cf = tk.Frame(parent, bg=self.WHITE, relief=tk.SOLID, bd=1)
        cf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # content header bar
        ch = tk.Frame(cf, bg=self.DARK_BLUE, height=36)
        ch.pack(fill=tk.X)
        ch.pack_propagate(False)
        self.content_title = tk.Label(
            ch, text="📊 РЕЗУЛЬТАТЫ ПРОВЕРКИ",
            font=("Arial", 11, "bold"),
            bg=self.DARK_BLUE, fg=self.WHITE,
            anchor="w", padx=12,
        )
        self.content_title.pack(fill=tk.BOTH, expand=True)

        # doc results pane
        self.doc_pane = tk.Frame(cf, bg=self.WHITE)
        self.doc_pane.pack(fill=tk.BOTH, expand=True)

        self.result_text = scrolledtext.ScrolledText(
            self.doc_pane,
            font=("Consolas", 10), wrap=tk.WORD,
            bg=self.WHITE, relief=tk.FLAT, bd=0,
            padx=15, pady=15,
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)

        self.result_text.tag_config("success",  foreground=self.GREEN,     font=("Consolas", 11, "bold"))
        self.result_text.tag_config("error",    foreground=self.RED,       font=("Consolas", 11, "bold"))
        self.result_text.tag_config("warning",  foreground="#F39C12",      font=("Consolas", 10, "bold"))
        self.result_text.tag_config("header",   foreground=self.BLUE,      font=("Consolas", 12, "bold"))
        self.result_text.tag_config("section",  foreground=self.DARK_BLUE, font=("Consolas", 10, "bold"))
        self.result_text.tag_config("normal",   foreground="#2C3E50",      font=("Consolas", 10))
        self.result_text.tag_config("corr",     foreground="#C0392B",      font=("Consolas", 10, "bold"))
        self.result_text.tag_config("corr_note", foreground="#566573",    font=("Consolas", 9))
        self.result_text.tag_config("purple",      foreground="#7D3C98",    font=("Consolas", 10, "bold"))
        self.result_text.tag_config("hl_vague",    background="#FFF3CD", foreground="#7D5A00",
                                    font=("Consolas", 10, "bold"))
        self.result_text.tag_config("hl_corrupt",  background="#F8D7DA", foreground="#721C24",
                                    font=("Consolas", 10, "bold"))
        self.result_text.tag_config("hl_structure", background="#CCE5FF", foreground="#004085",
                                    font=("Consolas", 10, "italic"))

        # section data pane (hidden initially)
        self.sec_pane = tk.Frame(cf, bg=self.WHITE)

    def _build_footer(self):
        ff = tk.Frame(self.root, bg=self.BLUE, height=30)
        ff.pack(fill=tk.X, side=tk.BOTTOM)
        ff.pack_propagate(False)
        tk.Label(
            ff,
            text="Поддержка форматов: TXT • DOCX • PDF  |  © Министерство экономического развития России 2025",
            font=("Arial", 8), bg=self.BLUE, fg=self.WHITE,
        ).pack(pady=5)

    # ---------------------------------------------------------------- sidebar
    def _switch_section(self, idx):
        self.active_section = idx
        sec = SECTIONS[idx]

        for i, btn in enumerate(self._section_btns):
            btn.config(bg=self.SIDEBAR_ACTIVE if i == idx else self.SIDEBAR_BG,
                       relief=tk.RIDGE if i == idx else tk.FLAT)

        self.portal_btn.config(state=tk.NORMAL)
        self.export_btn.config(state=tk.NORMAL)

        self.doc_pane.pack_forget()
        self.sec_pane.pack(fill=tk.BOTH, expand=True)

        for w in self.sec_pane.winfo_children():
            w.destroy()

        # section info bar
        info = tk.Frame(self.sec_pane, bg="#E8EFF7", pady=8)
        info.pack(fill=tk.X)
        tk.Label(info, text=sec["full_title"],
                 font=("Arial", 10, "bold"), bg="#E8EFF7", fg=self.DARK_BLUE,
                 wraplength=800, justify=tk.LEFT, anchor="w", padx=12).pack(fill=tk.X)
        tk.Label(info, text=f"Источник данных: {sec['portal']}",
                 font=("Arial", 9), bg="#E8EFF7", fg="#555555",
                 anchor="w", padx=12).pack(fill=tk.X)

        # table
        tbl_frame = tk.Frame(self.sec_pane, bg=self.WHITE)
        tbl_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        style = ttk.Style()
        style.configure("Tbl.Treeview", rowheight=26, font=("Arial", 9))
        style.configure("Tbl.Treeview.Heading",
                        font=("Arial", 9, "bold"),
                        background=self.BLUE, foreground="white")
        style.map("Tbl.Treeview.Heading", background=[("active", self.DARK_BLUE)])

        cols = sec["columns"]
        tree = ttk.Treeview(tbl_frame, columns=cols, show="headings",
                            height=14, style="Tbl.Treeview")

        col_widths = {"№": 38, "Дата публикации": 120, "Дата начала экспертизы": 160,
                      "Дата внесения": 120, "Статус": 160, "Результат": 200,
                      "Стадия": 140, "Номер приказа": 110, "Комментариев": 110,
                      "Экспертов": 80}
        for col in cols:
            w = col_widths.get(col, 240)
            anchor = "center" if col in ("№", "Комментариев", "Экспертов", "Номер приказа") else "w"
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor=anchor, minwidth=40)

        for i, row in enumerate(sec["data"]):
            tree.insert("", tk.END, values=row, tags=("even" if i % 2 == 0 else "odd",))

        tree.tag_configure("even", background="#F4F6FB")
        tree.tag_configure("odd",  background=self.WHITE)

        vsb = ttk.Scrollbar(tbl_frame, orient="vertical",   command=tree.yview)
        hsb = ttk.Scrollbar(tbl_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side=tk.RIGHT,  fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        tree.pack(fill=tk.BOTH, expand=True)

        self.current_tree = tree

        title_short = sec["full_title"]
        if len(title_short) > 55:
            title_short = title_short[:55] + "…"
        self.content_title.config(text=f"📋 {sec['title'].upper()}: {title_short}")

    def _show_doc_pane(self):
        self.sec_pane.pack_forget()
        self.doc_pane.pack(fill=tk.BOTH, expand=True)
        self.content_title.config(text="📊 РЕЗУЛЬТАТЫ ПРОВЕРКИ")
        for btn in self._section_btns:
            btn.config(bg=self.SIDEBAR_BG, relief=tk.FLAT)
        self.active_section = None
        self.portal_btn.config(state=tk.DISABLED)
        self.export_btn.config(state=tk.DISABLED)

    def _open_portal(self):
        if self.active_section is not None:
            webbrowser.open(SECTIONS[self.active_section]["url"])

    def _export_csv(self):
        if self.active_section is None:
            messagebox.showwarning("Предупреждение", "Сначала выберите раздел")
            return

        sec = SECTIONS[self.active_section]
        path = filedialog.asksaveasfilename(
            title="Экспорт в CSV",
            defaultextension=".csv",
            filetypes=[("CSV файл", "*.csv"), ("Все файлы", "*.*")],
            initialfile=f"раздел{self.active_section + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(sec["columns"])
                w.writerows(sec["data"])
            messagebox.showinfo("Экспорт", f"Данные сохранены:\n{os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при экспорте:\n{e}")

    # --------------------------------------------------------- helpers / scan
    @staticmethod
    def _doc_stats(text: str) -> dict:
        """Базовая статистика документа."""
        import re
        lines  = text.splitlines()
        words  = re.findall(r'\w+', text)
        paras  = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
        sents  = re.split(r'[.!?]+', text)
        sents  = [s.strip() for s in sents if len(s.strip()) > 10]
        return {
            "chars":   len(text),
            "lines":   len(lines),
            "words":   len(words),
            "paras":   len(paras),
            "sents":   len(sents),
        }

    @staticmethod
    def _quick_scan(text: str) -> list:
        """
        Быстрая проверка присутствия ключевых элементов приказа.
        Возвращает список (название, найдено:bool, найденный фрагмент).
        """
        import re
        checks = []

        def first_match(patterns, t, flags=re.IGNORECASE):
            for p in patterns:
                m = re.search(p, t, flags)
                if m:
                    return m.group(0)[:60].strip()
            return None

        head = "\n".join(text.splitlines()[:25])

        # 1. Наименование органа
        frag = first_match([r'МИНИСТЕРСТВО[^\n]+', r'Минэкономразвития[^\n]+',
                             r'ФЕДЕРАЛЬН[А-ЯЁ ]+[^\n]+'], head)
        checks.append(("Наименование органа (шапка)", frag is not None, frag or ""))

        # 2. Слово ПРИКАЗ
        frag = first_match([r'^\s*ПРИКАЗ\s*$'], head, re.MULTILINE | re.IGNORECASE)
        if not frag:
            frag = first_match([r'ПРИКАЗ'], head)
        checks.append(("Слово «ПРИКАЗ»", frag is not None, frag or ""))

        # 3. Дата
        frag = first_match([r'«?\d{1,2}»?\s+[а-яё]+\s+\d{4}',
                             r'\d{2}\.\d{2}\.\d{4}'], text)
        checks.append(("Дата издания", frag is not None, frag or ""))

        # 4. Номер
        frag = first_match([r'№\s*[\d\w/-]+'], text)
        checks.append(("Регистрационный номер (№)", frag is not None, frag or ""))

        # 5. Место издания
        frag = first_match([r'г\.\s*[А-ЯЁ][а-яё-]+'], head)
        checks.append(("Место издания", frag is not None, frag or ""))

        # 6. Заголовок «О …»
        frag = first_match([r'^\s*О[бб]?\s+[А-ЯЁа-яё].{10,}'], text, re.MULTILINE)
        checks.append(("Заголовок к тексту (О / Об …)", frag is not None, frag or ""))

        # 7. Преамбула
        frag = first_match([r'В\s+соответствии\s+с\s+.{5,}',
                             r'На\s+основании\s+.{5,}',
                             r'Во\s+исполнение\s+.{5,}',
                             r'Руководствуясь\s+.{5,}'], text)
        checks.append(("Преамбула (основание издания)", frag is not None, frag or ""))

        # 8. Ссылка на НПА
        frag = first_match([r'[Фф]едеральн\w+ закон\w*[^\n]{0,40}',
                             r'[Пп]остановлени\w+ Правительства[^\n]{0,40}',
                             r'№\s*\d+[-\w]*\s+от\s+\d{2}\.\d{2}\.\d{4}'], text)
        checks.append(("Ссылка на НПА в преамбуле", frag is not None, frag or ""))

        # 9. ПРИКАЗЫВАЮ
        frag = first_match([r'ПРИКАЗЫВАЮ\s*:?'], text)
        checks.append(("Распорядительное слово «ПРИКАЗЫВАЮ:»", frag is not None, frag or ""))

        # 10. Нумерованные пункты
        items = re.findall(r'(?:^|\n)\s*\d+\.\s+\S', text, re.MULTILINE)
        frag = f"пунктов найдено: {len(items)}" if items else ""
        checks.append(("Нумерованные пункты в распорядительной части",
                        len(items) > 0, frag))

        # 11. Контроль за исполнением
        frag = first_match([r'[Кк]онтроль\s+за\s+исполнением[^\n]{0,50}',
                             r'[Кк]онтроль\s+исполнения[^\n]{0,50}'], text)
        checks.append(("Пункт о контроле исполнения", frag is not None, frag or ""))

        # 12. Подпись / должность подписанта
        frag = first_match([r'[Мм]инистр\s+.{0,40}',
                             r'[Зз]аместитель\s+министра\s+.{0,40}',
                             r'[Рр]уководитель\s+.{0,40}'], text)
        checks.append(("Подпись (должность подписанта)", frag is not None, frag or ""))

        # 13. Приложения
        frag = first_match([r'[Пп]риложение\s*(?:№\s*)?\d*[^\n]{0,40}'], text)
        checks.append(("Приложения", frag is not None, frag or "нет ссылок на приложения"))

        # 14. Регистрация в Минюсте (информационно)
        frag = first_match([r'[Зз]арегистрировано\s+в\s+[Мм]инюст[^\n]{0,50}'], text)
        checks.append(("Зарегистрировано в Минюсте", frag is not None, frag or "нет"))

        return checks

    @staticmethod
    def _scan_corruption_risks(text: str):
        """
        Ищет в тексте НПА фрагменты, близкие к типовым коррупциогенным конструкциям.
        Возвращает список словарей: label, risk, snippet.
        """
        import re
        hits = []
        seen_labels = set()
        flags = re.IGNORECASE | re.DOTALL
        for label, pat, risk in CORRUPTION_SCAN_RULES:
            if label in seen_labels:
                continue
            m = re.search(pat, text, flags)
            if not m:
                continue
            seen_labels.add(label)
            a, b = m.span()
            lo = max(0, a - 50)
            hi = min(len(text), b + 70)
            snippet = text[lo:hi]
            snippet = " ".join(snippet.split())
            if lo > 0:
                snippet = "… " + snippet
            if hi < len(text):
                snippet = snippet + " …"
            if len(snippet) > 220:
                snippet = snippet[:217] + "…"
            hits.append({"label": label, "risk": risk, "snippet": snippet})
        return hits

    # -------------------------------------------------------------- doc check
    def load_file(self):
        path = filedialog.askopenfilename(
            title="Выберите документ",
            filetypes=[
                ("Все поддерживаемые", "*.txt *.docx *.pdf"),
                ("Текстовые файлы", "*.txt"),
                ("Word документы", "*.docx"),
                ("PDF документы", "*.pdf"),
                ("Все файлы", "*.*"),
            ],
        )
        if not path:
            return
        try:
            text = load_file_by_type(path)
            if not text or len(text) < 50:
                messagebox.showerror("Ошибка",
                    "Не удалось прочитать файл или он слишком короткий.")
                return

            self.current_file = path
            self.current_text = text
            st = self._doc_stats(text)
            self.file_label.config(
                text=(f"📄 {os.path.basename(path)}  |  "
                      f"{st['chars']:,} симв.  {st['words']:,} слов  "
                      f"{st['lines']} строк  {st['paras']} абзацев"),
                fg=self.BLUE,
            )
            self.check_btn.config(state=tk.NORMAL)
            self.save_btn.config(state=tk.DISABLED)
            self._show_doc_pane()
            self._display_load_preview(text, st)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при загрузке файла:\n{e}")

    def _display_load_preview(self, text: str, st: dict):
        """Показывает предварительный анализ при загрузке файла."""
        rt = self.result_text
        rt.delete(1.0, tk.END)
        self.content_title.config(text="📄 ДОКУМЕНТ ЗАГРУЖЕН — ПРЕДВАРИТЕЛЬНЫЙ АНАЛИЗ")

        # ── заголовок ─────────────────────────────────────────────────────
        rt.insert(tk.END, "=" * 80 + "\n", "header")
        rt.insert(tk.END, "  ДОКУМЕНТ ЗАГРУЖЕН\n", "success")
        rt.insert(tk.END, "=" * 80 + "\n\n", "header")

        # ── статистика ────────────────────────────────────────────────────
        rt.insert(tk.END, "СТАТИСТИКА ДОКУМЕНТА\n", "header")
        rt.insert(tk.END, "-" * 40 + "\n")
        rt.insert(tk.END, f"  Символов  : {st['chars']:>8,}\n")
        rt.insert(tk.END, f"  Слов      : {st['words']:>8,}\n")
        rt.insert(tk.END, f"  Строк     : {st['lines']:>8,}\n")
        rt.insert(tk.END, f"  Абзацев   : {st['paras']:>8,}\n")
        rt.insert(tk.END, f"  Предложений: {st['sents']:>7,}\n\n")

        # ── быстрый скан элементов ────────────────────────────────────────
        rt.insert(tk.END, "ЭКСПРЕСС-СКАНИРОВАНИЕ СТРУКТУРЫ\n", "header")
        rt.insert(tk.END, "-" * 40 + "\n")

        checks = self._quick_scan(text)
        found  = sum(1 for _, ok, _ in checks if ok)
        total  = len(checks)

        for name, ok, frag in checks:
            if ok:
                rt.insert(tk.END, "  [+] ", "success")
                rt.insert(tk.END, f"{name}\n", "normal")
                if frag and frag not in ("нет", "нет ссылок на приложения"):
                    rt.insert(tk.END, f"       → {frag}\n", "section")
            else:
                rt.insert(tk.END, "  [-] ", "error")
                rt.insert(tk.END, f"{name}\n", "normal")

        rt.insert(tk.END, "\n")
        pct = found * 100 // total
        bar = "█" * (found * 20 // total) + "░" * (20 - found * 20 // total)
        rt.insert(tk.END, f"  Соответствие: [{bar}] {pct}% ({found}/{total})\n\n",
                  "success" if pct >= 75 else "warning" if pct >= 50 else "error")

        # ── начало текста ─────────────────────────────────────────────────
        rt.insert(tk.END, "НАЧАЛО ДОКУМЕНТА (первые 600 символов)\n", "header")
        rt.insert(tk.END, "-" * 40 + "\n")
        preview = text[:600].strip()
        for line in preview.splitlines():
            stripped = line.strip()
            if not stripped:
                rt.insert(tk.END, "\n")
            elif stripped.isupper() and len(stripped) > 2:
                rt.insert(tk.END, f"  {stripped}\n", "section")
            else:
                rt.insert(tk.END, f"  {stripped}\n")
        if len(text) > 600:
            rt.insert(tk.END, "  ...\n")

        rt.insert(tk.END, "\n" + "=" * 80 + "\n")
        rt.insert(tk.END, "  Нажмите «Проверить структуру» для полного анализа\n", "section")
        rt.insert(tk.END, "=" * 80 + "\n")

    def check_document(self):
        if not self.current_text:
            messagebox.showwarning("Предупреждение", "Сначала загрузите документ")
            return

        self._show_doc_pane()
        self.check_btn.config(state=tk.DISABLED)
        self.load_btn.config(state=tk.DISABLED)
        self.progress.pack(side=tk.RIGHT, padx=10)
        self.progress.start(10)

        t = threading.Thread(target=self._check_thread, daemon=True)
        t.start()

    def _check_thread(self):
        try:
            val = self.validator.validate(self.current_text)
            mdl = None
            if self.model_available and self.trainer:
                mdl = self.trainer.predict(self.current_text)
            self.last_validation_result = val
            self.last_model_result = mdl
            self.root.after(0, self._display_results, val, mdl)
        except Exception as e:
            self.root.after(0, messagebox.showerror,
                            "Ошибка", f"Ошибка при проверке:\n{e}")
        finally:
            self.root.after(0, self._check_done)

    def _check_done(self):
        self.progress.stop()
        self.progress.pack_forget()
        self.check_btn.config(state=tk.NORMAL)
        self.load_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.NORMAL)

    def _display_results(self, vr, mr):
        """
        Отображает полное экспертное заключение на экране (14 разделов).
        vr = validation_result (словарь от OrderStructureValidator.validate)
        mr = model_result (от ErrorDetectionTrainer.predict, может быть None)
        """
        self._show_doc_pane()
        self.content_title.config(text="📊 ЭКСПЕРТНОЕ ЗАКЛЮЧЕНИЕ")
        t = self.result_text
        t.delete(1.0, tk.END)

        def ins(text, tag="normal"):
            t.insert(tk.END, text, tag)

        def h1(text):
            ins("═" * 80 + "\n", "header")
            ins(f"  {text}\n", "header")
            ins("═" * 80 + "\n", "header")

        def h2(text):
            ins(f"\n{text}\n", "section")
            ins("─" * 80 + "\n", "section")

        def row(label, value, vtag="normal"):
            ins(f"  {label:<46}", "section")
            ins(f"{value}\n", vtag)

        def bullet(text, tag="normal"):
            ins(f"  • {text}\n", tag)

        def sep():
            ins("\n")

        # ══════════════════════════════════════════════════════════════════
        # ШАПКА
        # ══════════════════════════════════════════════════════════════════
        h1("ЭКСПЕРТНОЕ ЗАКЛЮЧЕНИЕ НА ПРОЕКТ ВЕДОМСТВЕННОГО НПА")
        ins("  Система комплексной интеллектуальной юридической экспертизы\n", "purple")
        ins("  Интеллектуальная правовая экспертиза нормативных правовых актов\n\n", "purple")

        # ──────────────────────────────────────────────────────────────────
        # РАЗДЕЛ I: ОБЩАЯ ИНФОРМАЦИЯ
        # ──────────────────────────────────────────────────────────────────
        h2("РАЗДЕЛ I.  ОБЩАЯ ИНФОРМАЦИЯ")
        ds = vr.get('doc_structure', {})
        file_name = os.path.basename(self.current_file)
        row("Наименование файла:", file_name)
        row("Тип акта:", "Приказ ведомственный нормативный")
        row("Орган:", "Министерство экономического развития РФ")
        row("Дата и время проверки:", datetime.now().strftime("%d.%m.%Y  %H:%M:%S"))
        row("Объём документа:",
            f"{len(self.current_text):,} символов  (≈ {ds.get('estimated_pages', 1)} страниц)")
        row("Пунктов распорядительной части:", str(ds.get('total_paragraphs', '—')))
        row("Подпунктов:", str(ds.get('total_subparagraphs', 0)))
        has_sig = ds.get('has_signature_block', False)
        row("Блок подписи руководителя:",
            "Обнаружен ✓" if has_sig else "Не обнаружен ⚠",
            "success" if has_sig else "warning")
        row("Приложения и разделы:",
            "С главами" if ds.get('has_chapters') else
            ("С разделами" if ds.get('has_sections') else "Без разделов / глав"))

        # ──────────────────────────────────────────────────────────────────
        # РАЗДЕЛ II: СТРУКТУРНАЯ / ПРАВОВАЯ ПРОВЕРКА
        # ──────────────────────────────────────────────────────────────────
        h2("РАЗДЕЛ II.  ПРАВОВАЯ ЭКСПЕРТИЗА (СТРУКТУРНАЯ ПРОВЕРКА)")
        is_valid = vr['is_valid']
        row("Общий статус:",
            "✓ СТРУКТУРА ДОКУМЕНТА КОРРЕКТНА" if is_valid else "✗ ОБНАРУЖЕНЫ ОШИБКИ В СТРУКТУРЕ",
            "success" if is_valid else "error")
        row("Критических ошибок:", str(vr['total_errors']),
            "success" if vr['total_errors'] == 0 else "error")
        row("Предупреждений:", str(vr['total_warnings']),
            "success" if vr['total_warnings'] == 0 else "warning")

        if vr['errors']:
            sep()
            ins("  КРИТИЧЕСКИЕ ОШИБКИ:\n", "error")
            for i, err in enumerate(vr['errors'], 1):
                ins(f"  {i}. [{err.section}] {err.error_type}\n", "error")
                ins(f"     {err.description}\n", "normal")

        if vr['warnings']:
            sep()
            ins("  ПРЕДУПРЕЖДЕНИЯ:\n", "warning")
            for i, w in enumerate(vr['warnings'], 1):
                ins(f"  {i}. [{w.section}] {w.error_type}\n", "warning")
                ins(f"     {w.description}\n", "normal")

        # ──────────────────────────────────────────────────────────────────
        # РАЗДЕЛ III: АНТИКОРРУПЦИОННАЯ ЭКСПЕРТИЗА
        # ──────────────────────────────────────────────────────────────────
        h2("РАЗДЕЛ III.  АНТИКОРРУПЦИОННАЯ ЭКСПЕРТИЗА")
        ins("  (Постановление Правительства РФ от 26.02.2010 № 96, методика Минюста России)\n\n",
            "normal")
        ac = vr.get('anticorruption', {})
        risk = ac.get('risk_level', 'н/д')
        risk_tag = {"низкий": "success", "умеренный": "warning",
                    "повышенный": "error", "высокий": "error"}.get(risk, "normal")
        row("Уровень коррупциогенного риска:", risk.upper(), risk_tag)
        row("Коррупциогенных факторов выявлено:", str(len(ac.get('factors', []))),
            "success" if not ac.get('factors') else "warning")

        factors = ac.get('factors', [])
        if factors:
            sep()
            ins("  Выявленные коррупциогенные факторы:\n", "warning")
            for f in factors:
                bullet(f, "warning")
        else:
            bullet("Коррупциогенные факторы не выявлены", "success")

        # ──────────────────────────────────────────────────────────────────
        # РАЗДЕЛ IV: ЮРИДИКО-ТЕХНИЧЕСКАЯ ЭКСПЕРТИЗА
        # ──────────────────────────────────────────────────────────────────
        h2("РАЗДЕЛ IV.  ЮРИДИКО-ТЕХНИЧЕСКАЯ ЭКСПЕРТИЗА")
        lt = vr.get('legal_technique', {})
        needs_rev = lt.get('requires_revision', False)
        row("Требует редакционной доработки:",
            "ДА — выявлены замечания" if needs_rev else "НЕТ — замечаний не выявлено",
            "warning" if needs_rev else "success")
        sep()

        vague = lt.get('vague_formulations', [])
        ins("  4.1. Точность формулировок (исключение неоднозначного толкования):\n", "section")
        row("  Неопределённых формулировок:",
            f"Обнаружено: {len(vague)}" if vague else "Не обнаружены",
            "warning" if vague else "success")
        if vague:
            for v in vague[:8]:
                bullet(v, "warning")
            if len(vague) > 8:
                bullet(f"…и ещё {len(vague) - 8} формулировок", "warning")
        sep()

        terms = lt.get('terminology_issues', [])
        ins("  4.2. Соответствие терминологии законодательным определениям:\n", "section")
        row("  Терминологических замечаний:",
            f"{len(terms)}" if terms else "Нет замечаний",
            "warning" if terms else "success")
        if terms:
            for term in terms:
                bullet(term, "warning")
        sep()

        struct_issues = lt.get('structure_issues', [])
        ins("  4.3. Соблюдение правил юридической техники и норм официального документооборота:\n",
            "section")
        row("  Нарушений юридической техники:",
            f"{len(struct_issues)}" if struct_issues else "Не выявлено",
            "warning" if struct_issues else "success")
        if struct_issues:
            for s in struct_issues:
                bullet(s, "warning")
        sep()

        contrad = lt.get('internal_contradictions', [])
        ins("  4.4. Обеспечение внутренней непротиворечивости нормативного регулирования:\n",
            "section")
        row("  Замечаний по непротиворечивости:",
            f"Выявлено: {len(contrad)}" if contrad else "Противоречия не выявлены",
            "warning" if contrad else "success")
        if contrad:
            for c in contrad:
                bullet(c, "warning")

        if needs_rev:
            sep()
            ins("  ⚠ Отдельные положения приказа требуют редакционной доработки в части:\n",
                "warning")
            for pt in [
                "точности формулировок, исключающей возможность неоднозначного толкования;",
                "соответствия используемой терминологии определениям, закреплённым "
                "в законодательстве;",
                "соблюдения правил юридической техники и норм официального документооборота;",
                "обеспечения внутренней непротиворечивости нормативного регулирования.",
            ]:
                bullet(pt, "warning")

        # ──────────────────────────────────────────────────────────────────
        # РАЗДЕЛ V: КАЛЬКУЛЯТОР ОБЯЗАТЕЛЬНЫХ ТРЕБОВАНИЙ
        # ──────────────────────────────────────────────────────────────────
        h2("РАЗДЕЛ V.  ПРОВЕРКА ОБЯЗАТЕЛЬНЫХ ТРЕБОВАНИЙ")
        ins("  (Федеральный закон № 247-ФЗ, реестр обязательных требований, "
            "механизм «регуляторной гильотины»)\n\n", "normal")
        mand = vr.get('mandatory', {})
        row("Всего обязательных требований:", str(mand.get('total', 0)))
        row("Пунктов, содержащих требования:", str(len(mand.get('by_paragraph', []))))
        sep()

        by_type = mand.get('by_type', {})
        if by_type:
            ins("  По видам обязательных требований:\n", "section")
            for req_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
                row(f"    {req_type}:", str(count))

        by_para = mand.get('by_paragraph', [])
        if by_para:
            sep()
            ins("  По пунктам распорядительной части:\n", "section")
            ins(f"  {'Пункт':<12}{'Кол-во':<10}{'Виды требований'}\n", "section")
            ins("  " + "─" * 72 + "\n", "normal")
            for p in by_para:
                row(f"    п. {p['number']}",
                    f"{p['count']}      {', '.join(p['requirements'])}")
        else:
            bullet("Структурированных обязательных требований по пунктам не выявлено", "warning")

        # ──────────────────────────────────────────────────────────────────
        # РАЗДЕЛ VI: ОРВ
        # ──────────────────────────────────────────────────────────────────
        h2("РАЗДЕЛ VI.  НЕОБХОДИМОСТЬ ПРОВЕДЕНИЯ ОЦЕНКИ РЕГУЛИРУЮЩЕГО ВОЗДЕЙСТВИЯ (ОРВ)")
        orv = vr.get('orv', {})
        orv_req = orv.get('required', False)
        row("Необходимость ОРВ:",
            orv.get('conclusion', '—'),
            "warning" if orv_req else "success")
        row("ОРВ присутствует в документе:",
            "Обнаружена ✓" if orv.get('found') else "Не обнаружена",
            "success" if orv.get('found') else "normal")
        row("Положений, влияющих на предпринимат. деятельность:",
            "Да — выявлены" if orv_req else "Нет",
            "warning" if orv_req else "success")

        triggers = orv.get('triggers', [])
        if triggers:
            sep()
            ins("  Выявленные основания для проведения ОРВ:\n", "warning")
            for trig in triggers:
                bullet(trig, "warning")

        # ──────────────────────────────────────────────────────────────────
        # РАЗДЕЛ VII: ОФВ
        # ──────────────────────────────────────────────────────────────────
        h2("РАЗДЕЛ VII.  НЕОБХОДИМОСТЬ ПРОВЕДЕНИЯ ОЦЕНКИ ФАКТИЧЕСКОГО ВОЗДЕЙСТВИЯ (ОФВ)")
        ofv = vr.get('ofv', {})
        ofv_req = ofv.get('required', False)
        row("Необходимость ОФВ:",
            ofv.get('conclusion', '—'),
            "warning" if ofv_req else "success")
        row("Требования с длительным сроком действия:",
            "Да — обнаружены" if ofv.get('long_term') else "Нет",
            "warning" if ofv.get('long_term') else "success")
        row("Административная нагрузка субъектов регулирования:",
            "Выявлена" if ofv.get('admin_burden') else "Не выявлена",
            "warning" if ofv.get('admin_burden') else "success")

        # ──────────────────────────────────────────────────────────────────
        # РАЗДЕЛ VIII: ФИНАНСОВО-ЭКОНОМИЧЕСКОЕ ОБОСНОВАНИЕ
        # ──────────────────────────────────────────────────────────────────
        h2("РАЗДЕЛ VIII.  ФИНАНСОВО-ЭКОНОМИЧЕСКОЕ ОБОСНОВАНИЕ")
        fin = vr.get('financial', {})
        fin_req = fin.get('required', False)
        fin_found = fin.get('found', False)
        row("Наличие ФЭО:",
            fin.get('conclusion', '—'),
            "warning" if fin_req and not fin_found else "success")
        row("Требуются бюджетные расходы:",
            "Да" if fin.get('budget_expenses') else "Нет")
        row("ФЭО присутствует в тексте:",
            "Да ✓" if fin_found else "Нет",
            "success" if fin_found else ("warning" if fin_req else "normal"))
        row("Наличие оценки затрат субъектов регулирования:",
            "Обнаружена ✓" if fin.get('cost_estimate_found') else "Не обнаружена")
        sep()
        ins("  Влияние акта на субъекты регулирования:\n", "section")
        row("    Организации / юридические лица:",
            "Да" if fin.get('affects_organizations') else "Нет")
        row("    Граждане / физические лица:",
            "Да" if fin.get('affects_citizens') else "Нет")
        row("    Предпринимательство / бизнес:",
            "Да" if fin.get('affects_business') else "Нет")
        row("    Бюджет (федеральный / региональный):",
            "Да" if fin.get('affects_budget') else "Нет")

        if fin.get('details'):
            sep()
            ins("  Обнаруженные финансовые индикаторы:\n", "section")
            for d in fin['details']:
                bullet(d)

        # ──────────────────────────────────────────────────────────────────
        # РАЗДЕЛ IX: СООТВЕТСТВИЕ АКТАМ БОЛЬШЕЙ ЮРИДИЧЕСКОЙ СИЛЫ
        # ──────────────────────────────────────────────────────────────────
        h2("РАЗДЕЛ IX.  СООТВЕТСТВИЕ АКТАМ БОЛЬШЕЙ ЮРИДИЧЕСКОЙ СИЛЫ")
        hl = vr.get('higher_law', {})
        sep()
        ins("  ✓  " + hl.get('statement',
            'Рассматриваемый ведомственный акт соответствует актам большей юридической силы.')
            + "\n", "success")
        sep()
        row("  Ссылки на Конституцию Российской Федерации:",
            "Обнаружены ✓" if hl.get('constitution_refs') else "Не обнаружены",
            "success" if hl.get('constitution_refs') else "normal")

        fl = hl.get('federal_law_refs', [])
        row("  Ссылки на федеральные законы:",
            f"{len(fl)} ссылок" if fl else "Не обнаружены")
        if fl:
            for ref in fl[:4]:
                bullet(ref[:80] + ("…" if len(ref) > 80 else ""))

        pp = hl.get('government_resolution_refs', [])
        row("  Постановления Правительства РФ:",
            f"{len(pp)} ссылок" if pp else "Не обнаружены")
        if pp:
            for ref in pp[:3]:
                bullet(ref[:80] + ("…" if len(ref) > 80 else ""))

        up = hl.get('presidential_decree_refs', [])
        row("  Указы Президента Российской Федерации:",
            f"{len(up)} ссылок" if up else "Не обнаружены")

        if hl.get('issues'):
            sep()
            for issue in hl['issues']:
                bullet(issue, "warning")

        # ──────────────────────────────────────────────────────────────────
        # РАЗДЕЛ X: ПРОВЕРКА ПОЛНОМОЧИЙ
        # ──────────────────────────────────────────────────────────────────
        h2("РАЗДЕЛ X.  ПРОВЕРКА ПОЛНОМОЧИЙ ОРГАНА НА ИЗДАНИЕ АКТА")
        auth = vr.get('authority', {})
        row("Статус:",
            auth.get('conclusion', '—'),
            "success" if auth.get('authority_stated') else "warning")
        row("Ссылка на основание полномочий:",
            "Имеется ✓" if auth.get('authority_stated') else "Не обнаружена",
            "success" if auth.get('authority_stated') else "warning")
        row("Ссылка на Положение о Министерстве:",
            "Обнаружена ✓" if auth.get('basis_found') else "Не обнаружена")

        # ──────────────────────────────────────────────────────────────────
        # РАЗДЕЛ XI: АНАЛИЗ СРОКОВ
        # ──────────────────────────────────────────────────────────────────
        h2("РАЗДЕЛ XI.  АНАЛИЗ СРОКОВ ИСПОЛНЕНИЯ")
        dl = vr.get('deadlines', {})
        spec = dl.get('specific', [])
        indef = dl.get('indefinite', [])
        row("Конкретные сроки исполнения:",
            f"Найдено: {len(spec)}" if spec else "Не обнаружены")
        if spec:
            for s in spec[:4]:
                bullet(str(s))
        row("Неопределённые (нечёткие) сроки:",
            f"Выявлено: {len(indef)}" if indef else "Не выявлены",
            "warning" if indef else "success")
        if indef:
            for idf in indef:
                bullet(f'«{idf}» — рекомендуется заменить конкретным сроком', "warning")

        if dl.get('issues'):
            for iss in dl['issues']:
                bullet(iss, "warning")

        # ──────────────────────────────────────────────────────────────────
        # РАЗДЕЛ XII: АНАЛИЗ НОРМАТИВНЫХ ССЫЛОК
        # ──────────────────────────────────────────────────────────────────
        h2("РАЗДЕЛ XII.  АНАЛИЗ НОРМАТИВНЫХ ССЫЛОК")
        refs = vr.get('references', {})
        row("Всего нормативных ссылок:", str(refs.get('total_refs', 0)))
        npa = refs.get('npa_refs', [])
        if npa:
            sep()
            ins("  Выявленные ссылки на нормативные правовые акты:\n", "section")
            for ref in npa[:6]:
                bullet(ref[:82] + ("…" if len(ref) > 82 else ""))

        # ──────────────────────────────────────────────────────────────────
        # РАЗДЕЛ XIII: НЕЙРОННАЯ МОДЕЛЬ (если доступна)
        # ──────────────────────────────────────────────────────────────────
        if mr:
            h2("РАЗДЕЛ XIII.  ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА НЕЙРОННОЙ МОДЕЛЬЮ")
            if mr['has_errors']:
                row("Результат модели:", "✗ Обнаружены ошибки", "error")
            else:
                row("Результат модели:", "✓ Ошибок не обнаружено", "success")
            row("Уверенность модели:", f"{mr['confidence'] * 100:.1f}%")
            if mr.get('pattern_errors'):
                sep()
                ins("  Ошибки по шаблонам (34 категории):\n", "section")
                for cat, errs in mr['pattern_errors'].items():
                    bullet(f"{cat}: {len(errs)} шт.", "warning")

        # ──────────────────────────────────────────────────────────────────
        # РАЗДЕЛ XIV: ОБЩИЙ ВЫВОД
        # ──────────────────────────────────────────────────────────────────
        h2("РАЗДЕЛ XIV.  ОБЩИЙ ВЫВОД И РЕКОМЕНДАЦИИ")
        total_issues = (
            vr['total_errors'] +
            len(ac.get('factors', [])) +
            len(lt.get('vague_formulations', [])) +
            (1 if orv_req else 0) +
            (1 if fin_req and not fin_found else 0)
        )
        sep()
        if total_issues == 0:
            ins("  ✓ По результатам комплексной экспертизы проект приказа соответствует\n"
                "    требованиям нормотворческой техники и может быть рекомендован к подписанию.\n",
                "success")
        elif total_issues <= 4:
            ins("  ⚠ Проект приказа в целом соответствует требованиям, однако требует\n"
                "    устранения выявленных замечаний до направления на подписание.\n", "warning")
        else:
            ins("  ✗ Проект приказа требует существенной доработки.\n"
                "    Рекомендуется устранить все критические замечания и провести повторную экспертизу.\n",
                "error")

        row("\n  Всего выявлено замечаний (сводно):", str(total_issues))
        sep()
        ins("  Рекомендации по доработке:\n", "section")
        if vr['errors']:
            bullet("Устранить все критические структурные ошибки", "error")
        if factors:
            bullet("Исключить коррупциогенные формулировки согласно методике Минюста", "warning")
        if vague:
            bullet("Заменить нечёткие формулировки конкретными нормами", "warning")
        if orv_req:
            bullet("Провести оценку регулирующего воздействия (ОРВ)", "warning")
        if fin_req and not fin_found:
            bullet("Подготовить финансово-экономическое обоснование (ФЭО)", "warning")
        if indef:
            bullet("Заменить неопределённые сроки конкретными датами/периодами", "warning")
        if not auth.get('authority_stated'):
            bullet("Указать нормативное основание полномочий органа на издание акта", "warning")

        # ══════════════════════════════════════════════════════════════════
        # СТРАНИЦА 2: ТЕКСТ ПРИКАЗА С ПОДСВЕТКОЙ ПРАВОТВОРЧЕСКИХ ОШИБОК
        # ══════════════════════════════════════════════════════════════════
        ins("\n\n")
        h1("СТРАНИЦА 2.  ТЕКСТ ПРОЕКТА ПРИКАЗА С АННОТАЦИЕЙ ПРАВОТВОРЧЕСКИХ ОШИБОК")

        ins("  Условные обозначения подсветки:\n", "section")
        ins("  ▌ Жёлтый фон   ", "hl_vague")
        ins("— неопределённые / нечёткие формулировки\n", "normal")
        ins("  ▌ Красный фон  ", "hl_corrupt")
        ins("— коррупциогенные конструкции\n", "normal")
        ins("  ▌ Синий фон    ", "hl_structure")
        ins("— структурные нарушения юридической техники\n\n", "normal")
        ins("─" * 80 + "\n", "normal")

        highlighted = vr.get('highlighted', [])
        self._insert_highlighted_text(self.current_text, highlighted)

        # Сводная таблица
        if highlighted:
            ins("\n\n" + "─" * 80 + "\n", "normal")
            ins("СВОДНАЯ ТАБЛИЦА ВЫЯВЛЕННЫХ ПРАВОТВОРЧЕСКИХ ОШИБОК\n", "section")
            ins("─" * 80 + "\n\n", "normal")
            ins(f"  {'№':<6}{'Пункт':<12}{'Тип ошибки':<18}{'Описание'}\n", "section")
            ins("  " + "─" * 74 + "\n", "normal")

            type_map = {
                'vague':     'Нечёткость',
                'corrupt':   'Коррупциог.',
                'structure': 'Структура',
            }
            tag_map = {
                'vague':     'hl_vague',
                'corrupt':   'hl_corrupt',
                'structure': 'hl_structure',
            }
            for i, issue in enumerate(highlighted, 1):
                type_name = type_map.get(issue['type'], issue['type'])
                tag = tag_map.get(issue['type'], 'normal')
                desc = issue['description']
                if len(desc) > 58:
                    desc = desc[:55] + "…"
                ins(f"  {i:<6}п.{issue['paragraph']:<10}{type_name:<18}{desc}\n", tag)

            sep()
            ins(f"  Итого правотворческих ошибок в тексте: {len(highlighted)}\n", "warning")

        # ══════════════════════════════════════════════════════════════════
        # ФИНАЛЬНАЯ СТРОКА
        # ══════════════════════════════════════════════════════════════════
        ins("\n")
        h1("ПРОВЕРКА ЗАВЕРШЕНА")
        ins("  Министерство экономического развития Российской Федерации\n", "section")
        ins("  Система интеллектуальной юридической экспертизы НПА\n", "section")
        ins("═" * 80 + "\n", "header")

    def _insert_highlighted_text(self, text: str, highlighted_issues: list):
        """Вставляет текст с цветовой подсветкой проблемных мест"""
        priority = {'corrupt': 0, 'vague': 1, 'structure': 2}
        sorted_issues = sorted(
            highlighted_issues,
            key=lambda x: (x['start'], priority.get(x['type'], 9))
        )

        # Удаляем перекрывающиеся диапазоны
        clean = []
        last_end = 0
        for issue in sorted_issues:
            if issue['start'] >= last_end:
                clean.append(issue)
                last_end = issue['end']

        tag_map = {
            'vague':     'hl_vague',
            'corrupt':   'hl_corrupt',
            'structure': 'hl_structure',
        }

        pos = 0
        for issue in clean:
            if issue['start'] > pos:
                self.result_text.insert(tk.END, text[pos:issue['start']], "normal")
            tag = tag_map.get(issue['type'], 'normal')
            self.result_text.insert(tk.END, text[issue['start']:issue['end']], tag)
            pos = issue['end']

        if pos < len(text):
            self.result_text.insert(tk.END, text[pos:], "normal")

    # ----------------------------------------------------------------- report
    def save_report(self):
        if not self.last_validation_result:
            messagebox.showwarning("Предупреждение",
                                   "Сначала выполните проверку документа")
            return

        path = filedialog.asksaveasfilename(
            title="Сохранить отчёт",
            defaultextension=".txt",
            filetypes=[("Текстовый файл", "*.txt"), ("Все файлы", "*.*")],
            initialfile=f"отчет_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig", newline="\n") as f:
                f.write(self._generate_report())
            messagebox.showinfo("Успешно",
                f"Отчёт сохранён:\n{os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при сохранении:\n{e}")

    def _generate_report(self) -> str:
        """Генерирует полное экспертное заключение в текстовом формате (14 разделов)"""
        vr = self.last_validation_result
        mr = self.last_model_result
        now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        ds = vr.get('doc_structure', {})
        file_name = os.path.basename(self.current_file)

        R = []

        def hr1(text=""):
            R.append("═" * 80)
            if text:
                R.append(f"  {text}")
                R.append("═" * 80)

        def hr2(text):
            R.append("")
            R.append(text)
            R.append("─" * 80)

        def row(label, value):
            R.append(f"  {label:<46}{value}")

        def bullet(text):
            R.append(f"  • {text}")

        def sep():
            R.append("")

        # ══ ШАПКА ════════════════════════════════════════════════════════
        hr1("ЭКСПЕРТНОЕ ЗАКЛЮЧЕНИЕ НА ПРОЕКТ ВЕДОМСТВЕННОГО")
        R.append("  НОРМАТИВНОГО ПРАВОВОГО АКТА (ПРИКАЗА)")
        hr1()
        R.append("  Система комплексной интеллектуальной юридической экспертизы")
        R.append("  LegalTech / GovTech — автоматизированная экспертиза НПА")
        sep()

        # ══ РАЗДЕЛ I ═════════════════════════════════════════════════════
        hr2("РАЗДЕЛ I.  ОБЩАЯ ИНФОРМАЦИЯ")
        row("Наименование файла:", file_name)
        row("Тип акта:", "Приказ ведомственный нормативный")
        row("Орган:", "Министерство экономического развития РФ")
        row("Дата и время проверки:", now)
        row("Объём документа:",
            f"{len(self.current_text):,} символов (≈{ds.get('estimated_pages', 1)} стр.)")
        row("Пунктов распорядительной части:", str(ds.get('total_paragraphs', '—')))
        row("Подпунктов:", str(ds.get('total_subparagraphs', 0)))
        row("Блок подписи:", "Обнаружен" if ds.get('has_signature_block') else "Не обнаружен")

        # ══ РАЗДЕЛ II ════════════════════════════════════════════════════
        hr2("РАЗДЕЛ II.  ПРАВОВАЯ ЭКСПЕРТИЗА (СТРУКТУРНАЯ ПРОВЕРКА)")
        is_valid = vr['is_valid']
        row("Общий статус:",
            "✓ СТРУКТУРА КОРРЕКТНА" if is_valid else "✗ ОБНАРУЖЕНЫ ОШИБКИ")
        row("Критических ошибок:", str(vr['total_errors']))
        row("Предупреждений:", str(vr['total_warnings']))

        if vr['errors']:
            sep()
            R.append("  КРИТИЧЕСКИЕ ОШИБКИ:")
            for i, err in enumerate(vr['errors'], 1):
                R.append(f"  {i}. [{err.section}] {err.error_type}")
                R.append(f"     {err.description}")

        if vr['warnings']:
            sep()
            R.append("  ПРЕДУПРЕЖДЕНИЯ:")
            for i, w in enumerate(vr['warnings'], 1):
                R.append(f"  {i}. [{w.section}] {w.error_type}")
                R.append(f"     {w.description}")

        # ══ РАЗДЕЛ III ═══════════════════════════════════════════════════
        hr2("РАЗДЕЛ III.  АНТИКОРРУПЦИОННАЯ ЭКСПЕРТИЗА")
        R.append("  (Постановление Правительства РФ от 26.02.2010 № 96, методика Минюста)")
        sep()
        ac = vr.get('anticorruption', {})
        risk = ac.get('risk_level', 'н/д')
        row("Уровень коррупциогенного риска:", risk.upper())
        row("Коррупциогенных факторов:", str(len(ac.get('factors', []))))
        factors = ac.get('factors', [])
        if factors:
            sep()
            R.append("  Выявленные коррупциогенные факторы:")
            for f in factors:
                bullet(f)
        else:
            bullet("Коррупциогенные факторы не выявлены")

        # ══ РАЗДЕЛ IV ════════════════════════════════════════════════════
        hr2("РАЗДЕЛ IV.  ЮРИДИКО-ТЕХНИЧЕСКАЯ ЭКСПЕРТИЗА")
        lt = vr.get('legal_technique', {})
        needs_rev = lt.get('requires_revision', False)
        row("Требует доработки:", "ДА" if needs_rev else "НЕТ")
        sep()

        R.append("  4.1. Точность формулировок:")
        vague = lt.get('vague_formulations', [])
        row("  Неопределённых формулировок:",
            f"{len(vague)}" if vague else "Не обнаружено")
        for v in vague[:10]:
            bullet(v)

        sep()
        R.append("  4.2. Соответствие терминологии законодательным определениям:")
        terms = lt.get('terminology_issues', [])
        row("  Терминологических замечаний:", f"{len(terms)}" if terms else "Нет")
        for term in terms:
            bullet(term)

        sep()
        R.append("  4.3. Правила юридической техники и официального документооборота:")
        struct_issues = lt.get('structure_issues', [])
        row("  Нарушений:", f"{len(struct_issues)}" if struct_issues else "Не выявлено")
        for s in struct_issues:
            bullet(s)

        sep()
        R.append("  4.4. Внутренняя непротиворечивость нормативного регулирования:")
        contrad = lt.get('internal_contradictions', [])
        row("  Замечаний:", f"{len(contrad)}" if contrad else "Противоречия не выявлены")
        for c in contrad:
            bullet(c)

        if needs_rev:
            sep()
            R.append("  ⚠ Отдельные положения приказа требуют редакционной доработки в части:")
            for pt in [
                "  — точности формулировок, исключающей неоднозначное толкование;",
                "  — соответствия терминологии определениям, закреплённым в законодательстве;",
                "  — соблюдения правил юридической техники и норм официального документооборота;",
                "  — обеспечения внутренней непротиворечивости нормативного регулирования.",
            ]:
                R.append(pt)

        # ══ РАЗДЕЛ V ═════════════════════════════════════════════════════
        hr2("РАЗДЕЛ V.  ПРОВЕРКА ОБЯЗАТЕЛЬНЫХ ТРЕБОВАНИЙ")
        R.append("  (ФЗ № 247-ФЗ, реестр обязательных требований, «регуляторная гильотина»)")
        sep()
        mand = vr.get('mandatory', {})
        row("Всего обязательных требований:", str(mand.get('total', 0)))
        row("Пунктов с требованиями:", str(len(mand.get('by_paragraph', []))))

        by_type = mand.get('by_type', {})
        if by_type:
            sep()
            R.append("  По видам обязательных требований:")
            for req_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
                row(f"    {req_type}:", str(count))

        by_para = mand.get('by_paragraph', [])
        if by_para:
            sep()
            R.append("  По пунктам распорядительной части:")
            R.append(f"  {'Пункт':<12}{'Кол-во':<10}{'Виды требований'}")
            R.append("  " + "─" * 65)
            for p in by_para:
                row(f"    п. {p['number']}", f"{p['count']}    {', '.join(p['requirements'])}")

        # ══ РАЗДЕЛ VI ════════════════════════════════════════════════════
        hr2("РАЗДЕЛ VI.  НЕОБХОДИМОСТЬ ПРОВЕДЕНИЯ ОРВ")
        orv = vr.get('orv', {})
        orv_req = orv.get('required', False)
        row("Необходимость ОРВ:", orv.get('conclusion', '—'))
        row("ОРВ в документе:", "Обнаружена" if orv.get('found') else "Не обнаружена")
        row("Положения, влияющие на бизнес:", "Да" if orv_req else "Нет")
        if orv.get('triggers'):
            sep()
            R.append("  Основания для ОРВ:")
            for trig in orv['triggers']:
                bullet(trig)

        # ══ РАЗДЕЛ VII ═══════════════════════════════════════════════════
        hr2("РАЗДЕЛ VII.  НЕОБХОДИМОСТЬ ПРОВЕДЕНИЯ ОФВ")
        ofv = vr.get('ofv', {})
        row("Необходимость ОФВ:", ofv.get('conclusion', '—'))
        row("Долгосрочные требования:", "Да" if ofv.get('long_term') else "Нет")
        row("Административная нагрузка:", "Выявлена" if ofv.get('admin_burden') else "Не выявлена")

        # ══ РАЗДЕЛ VIII ══════════════════════════════════════════════════
        hr2("РАЗДЕЛ VIII.  ФИНАНСОВО-ЭКОНОМИЧЕСКОЕ ОБОСНОВАНИЕ")
        fin = vr.get('financial', {})
        row("Наличие ФЭО:", fin.get('conclusion', '—'))
        row("Бюджетные расходы:", "Требуются" if fin.get('budget_expenses') else "Не требуются")
        row("ФЭО в тексте:", "Да" if fin.get('found') else "Нет")
        row("Оценка затрат субъектов:", "Обнаружена" if fin.get('cost_estimate_found') else "Нет")
        sep()
        row("  Влияние на организации:", "Да" if fin.get('affects_organizations') else "Нет")
        row("  Влияние на граждан:", "Да" if fin.get('affects_citizens') else "Нет")
        row("  Влияние на бизнес:", "Да" if fin.get('affects_business') else "Нет")
        row("  Влияние на бюджет:", "Да" if fin.get('affects_budget') else "Нет")

        # ══ РАЗДЕЛ IX ════════════════════════════════════════════════════
        hr2("РАЗДЕЛ IX.  СООТВЕТСТВИЕ АКТАМ БОЛЬШЕЙ ЮРИДИЧЕСКОЙ СИЛЫ")
        hl = vr.get('higher_law', {})
        sep()
        R.append("  ✓  " + hl.get('statement',
            'Рассматриваемый ведомственный акт соответствует актам большей юридической силы.'))
        sep()
        row("  Конституция РФ:", "Ссылки обнаружены" if hl.get('constitution_refs') else "Нет")
        fl = hl.get('federal_law_refs', [])
        row("  Федеральные законы:", f"{len(fl)} ссылок" if fl else "Не обнаружены")
        for ref in fl[:4]:
            bullet(ref[:85])
        pp = hl.get('government_resolution_refs', [])
        row("  Постановления Правительства:", f"{len(pp)} ссылок" if pp else "Нет")
        up = hl.get('presidential_decree_refs', [])
        row("  Указы Президента:", f"{len(up)} ссылок" if up else "Нет")
        if hl.get('issues'):
            sep()
            for issue in hl['issues']:
                bullet(issue)

        # ══ РАЗДЕЛ X ═════════════════════════════════════════════════════
        hr2("РАЗДЕЛ X.  ПРОВЕРКА ПОЛНОМОЧИЙ ОРГАНА")
        auth = vr.get('authority', {})
        row("Статус:", auth.get('conclusion', '—'))
        row("Основание полномочий:", "Указано" if auth.get('authority_stated') else "Не указано")
        row("Положение о Министерстве:", "Обнаружено" if auth.get('basis_found') else "Нет")

        # ══ РАЗДЕЛ XI ════════════════════════════════════════════════════
        hr2("РАЗДЕЛ XI.  АНАЛИЗ СРОКОВ ИСПОЛНЕНИЯ")
        dl = vr.get('deadlines', {})
        spec = dl.get('specific', [])
        indef = dl.get('indefinite', [])
        row("Конкретные сроки:", f"{len(spec)}" if spec else "Не обнаружены")
        for s in spec[:4]:
            bullet(str(s))
        row("Неопределённые сроки:", f"{len(indef)}" if indef else "Не выявлены")
        for idf in indef:
            bullet(f'«{idf}» — заменить конкретным сроком')

        # ══ РАЗДЕЛ XII ═══════════════════════════════════════════════════
        hr2("РАЗДЕЛ XII.  АНАЛИЗ НОРМАТИВНЫХ ССЫЛОК")
        refs = vr.get('references', {})
        row("Всего нормативных ссылок:", str(refs.get('total_refs', 0)))
        npa = refs.get('npa_refs', [])
        if npa:
            sep()
            R.append("  Выявленные ссылки на НПА:")
            for ref in npa[:6]:
                bullet(ref[:85])

        # ══ РАЗДЕЛ XIII: Модель ══════════════════════════════════════════
        if mr:
            hr2("РАЗДЕЛ XIII.  ПРОВЕРКА НЕЙРОННОЙ МОДЕЛЬЮ")
            row("Результат:", "✗ Ошибки обнаружены" if mr['has_errors'] else "✓ Ошибок нет")
            row("Уверенность:", f"{mr['confidence'] * 100:.1f}%")
            if mr.get('pattern_errors'):
                sep()
                R.append("  Ошибки по шаблонам:")
                for cat, errs in mr['pattern_errors'].items():
                    bullet(f"{cat}: {len(errs)} шт.")

        # ══ РАЗДЕЛ XIV: ВЫВОД ════════════════════════════════════════════
        hr2("РАЗДЕЛ XIV.  ОБЩИЙ ВЫВОД И РЕКОМЕНДАЦИИ")
        total_issues = (
            vr['total_errors'] +
            len(ac.get('factors', [])) +
            len(lt.get('vague_formulations', [])) +
            (1 if orv_req else 0) +
            (1 if fin.get('required') and not fin.get('found') else 0)
        )
        sep()
        if total_issues == 0:
            R.append("  ✓ По результатам комплексной экспертизы проект приказа соответствует")
            R.append("    требованиям нормотворческой техники и может быть рекомендован к подписанию.")
        elif total_issues <= 4:
            R.append("  ⚠ Проект приказа в целом соответствует требованиям, однако требует")
            R.append("    устранения выявленных замечаний до направления на подписание.")
        else:
            R.append("  ✗ Проект приказа требует существенной доработки.")
            R.append("    Рекомендуется устранить замечания и провести повторную экспертизу.")

        row("\n  Всего выявлено замечаний (сводно):", str(total_issues))
        sep()
        R.append("  Рекомендации:")
        if vr['errors']:
            bullet("Устранить критические структурные ошибки")
        if factors:
            bullet("Исключить коррупциогенные формулировки (методика Минюста)")
        if vague:
            bullet("Заменить нечёткие формулировки конкретными нормами")
        if orv_req:
            bullet("Провести оценку регулирующего воздействия (ОРВ)")
        if fin.get('required') and not fin.get('found'):
            bullet("Подготовить финансово-экономическое обоснование (ФЭО)")
        if indef:
            bullet("Заменить неопределённые сроки конкретными датами/периодами")
        if not auth.get('authority_stated'):
            bullet("Указать нормативное основание полномочий органа")
        if not (vr['errors'] or factors or vague or orv_req):
            bullet("Замечаний не выявлено — документ готов к подписанию")

        # ══════════════════════════════════════════════════════════════════
        # СТРАНИЦА 2: ТЕКСТ С АННОТАЦИЕЙ ОШИБОК
        # ══════════════════════════════════════════════════════════════════
        R.append("")
        hr1()
        R.append("  СТРАНИЦА 2.  ТЕКСТ ПРОЕКТА ПРИКАЗА")
        R.append("  С АННОТАЦИЕЙ ПРАВОТВОРЧЕСКИХ ОШИБОК")
        hr1()
        R.append("")
        R.append("  Условные обозначения:")
        R.append("  [НЕЧЁТКОСТЬ]     — неопределённая / нечёткая формулировка")
        R.append("  [КОРРУПЦИОГЕН.]  — коррупциогенная конструкция")
        R.append("  [СТРУКТУРА]      — нарушение юридической техники")
        R.append("")
        R.append("─" * 80)
        R.append("")

        highlighted = vr.get('highlighted', [])
        type_prefix = {
            'vague':     '⚠[НЕЧЁТКОСТЬ]',
            'corrupt':   '⛔[КОРРУПЦИОГЕН.]',
            'structure': '◆[СТРУКТУРА]',
        }

        if not highlighted:
            R.append(self.current_text)
        else:
            priority = {'corrupt': 0, 'vague': 1, 'structure': 2}
            sorted_issues = sorted(
                highlighted,
                key=lambda x: (x['start'], priority.get(x['type'], 9))
            )
            clean = []
            last_end = 0
            for issue in sorted_issues:
                if issue['start'] >= last_end:
                    clean.append(issue)
                    last_end = issue['end']

            pos = 0
            for issue in clean:
                if issue['start'] > pos:
                    R.append(self.current_text[pos:issue['start']])
                matched = self.current_text[issue['start']:issue['end']]
                prefix = type_prefix.get(issue['type'], '⚠')
                R.append(matched)
                R.append(f"    {prefix} {issue['description']}")
                pos = issue['end']
            if pos < len(self.current_text):
                R.append(self.current_text[pos:])

        if highlighted:
            R.append("")
            R.append("─" * 80)
            R.append("СВОДНАЯ ТАБЛИЦА ВЫЯВЛЕННЫХ ПРАВОТВОРЧЕСКИХ ОШИБОК")
            R.append("─" * 80)
            R.append(f"  {'№':<6}{'Пункт':<12}{'Тип':<18}{'Фрагмент / Описание'}")
            R.append("  " + "─" * 72)
            for i, issue in enumerate(highlighted, 1):
                type_name = type_prefix.get(issue['type'], '?')[:14]
                desc = issue['description']
                if len(desc) > 50:
                    desc = desc[:47] + "…"
                R.append(f"  {i:<6}п.{issue['paragraph']:<10}{type_name:<18}{desc}")
            R.append("")
            R.append(f"  Итого правотворческих ошибок: {len(highlighted)}")

        # ══ КОНЕЦ ════════════════════════════════════════════════════════
        R.append("")
        hr1()
        R.append("  Министерство экономического развития Российской Федерации")
        R.append("  Система интеллектуальной юридической экспертизы НПА")
        hr1()

        return '\n'.join(R)

    # ------------------------------------------------------------------ clear
    def clear_results(self):
        self.result_text.delete(1.0, tk.END)
        self.file_label.config(text="📄 Файл не загружен", fg=self.BLUE)
        self.current_file = None
        self.current_text = None
        self.last_validation_result = None
        self.last_model_result = None
        self.check_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)
        self._show_doc_pane()


def main():
    root = tk.Tk()
    app = OrderCheckerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
