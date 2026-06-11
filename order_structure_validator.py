# -*- coding: utf-8 -*-
"""
Система комплексной юридической экспертизы проектов нормативных правовых актов

Реализует многоуровневый анализ проектов ведомственных актов (приказов):
  I.   Структурная проверка (шапка, заголовок, преамбула, распоряжение, приложения)
  II.  Финансово-экономическое обоснование
  III. Оценка регулирующего воздействия (ОРВ)
  IV.  Оценка фактического воздействия (ОФВ)
  V.   Юридико-техническая экспертиза
  VI.  Калькулятор обязательных требований
  VII. Соответствие актам большей юридической силы
  VIII.Антикоррупционная экспертиза (по методике Минюста)
  IX.  Проверка полномочий органа
  X.   Анализ сроков
  XI.  Анализ нормативных ссылок
  XII. Структурный анализ документа
  XIII.Поиск правотворческих ошибок для подсветки
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ValidationError:
    """Класс для представления ошибки валидации"""
    section: str
    error_type: str
    description: str
    line_number: int = None


class OrderStructureValidator:
    """
    Система комплексной интеллектуальной юридической экспертизы проектов приказов.
    Превращает проверку ведомственного акта в полноценное экспертное заключение.
    """

    # ── Нечёткие / неопределённые формулировки ──────────────────────────────
    VAGUE_PATTERNS = [
        (r'при\s+необходимости',                   'неопределённая формулировка "при необходимости"'),
        (r'по\s+возможности',                      'неопределённая формулировка "по возможности"'),
        (r'в\s+разумный\s+срок',                   'неопределённый срок "в разумный срок"'),
        (r'иные\s+(?:случаи|основания|обстоятельства|документы)',
                                                   'незакрытый перечень "иные случаи/основания"'),
        (r'и\s+т\.\s*д\.',                         'незакрытый перечень "и т.д."'),
        (r'и\s+т\.\s*п\.',                         'незакрытый перечень "и т.п."'),
        (r'и\s+(?:т\.\s*д\.|т\.\s*п\.|др\.)',      'незакрытый перечень'),
        (r'в\s+установленном\s+порядке(?!\s*,\s*определённом)',
                                                   'отсылочная норма без указания конкретного порядка'),
        (r'надлежащим\s+образом',                  'оценочная категория "надлежащим образом"'),
        (r'в\s+кратчайшие\s+сроки',               'неопределённый срок "в кратчайшие сроки"'),
        (r'по\s+мере\s+(?:возможности|необходимости)',
                                                   'неопределённая формулировка "по мере возможности/необходимости"'),
        (r'в\s+ближайшее\s+время',                'неопределённый срок "в ближайшее время"'),
        (r'своевременно(?!\s*(?:до|не\s+позднее|в\s+течение))',
                                                   'неопределённый срок "своевременно"'),
        (r'в\s+необходимых\s+случаях',            'неопределённая категория "в необходимых случаях"'),
        (r'при\s+наличии\s+возможности',           'неопределённая формулировка "при наличии возможности"'),
        (r'надлежащее\s+(?:качество|исполнение)',  'оценочная категория "надлежащее качество/исполнение"'),
        (r'разумн\w+\s+(?:срок|меры|цен)',         'оценочная категория "разумный срок/меры/цена"'),
    ]

    # ── Дискреционные (коррупциогенные) конструкции ─────────────────────────
    DISCRETION_PATTERNS = [
        (r'по\s+усмотрению\s+(?:органа|должностного|руководителя|министра|лица)',
         'широкое усмотрение должностного лица без установленных критериев'),
        (r'(?:вправе|может)\s+отказать(?!\s+(?:в\s+случае|при\s+наличии\s+следующих|только))',
         'право на немотивированный отказ без установленных оснований'),
        (r'по\s+решению\s+(?:органа|руководителя|должностного\s+лица)(?!\s+(?:в\s+случае|при\s+наличии))',
         'принятие решения без установленных критериев'),
        (r'по\s+согласованию\s+с(?!\s+\w+\s+(?:в\s+течение|в\s+срок|не\s+позднее))',
         'согласование без установления срока и оснований'),
        (r'в\s+исключительных\s+случаях(?!\s*[:,])',
         'исключения без чётко определённых критериев'),
        (r'при\s+наличии\s+оснований(?!\s*[\(,:])',
         'ссылка на основания без их конкретного перечисления'),
        (r'уполномоченн\w+\s+(?:орган|лицо|организаци\w+)(?!\s+(?:определяется|в\s+соответствии|является))',
         '"уполномоченный орган/лицо" без конкретной идентификации'),
        (r'без\s+(?:объяснения\s+причин|обоснования|мотивировки)',
         'допускается действие без обоснования'),
        (r'оценочн\w+\s+(?:категори|критери|понятия)(?!\s+раскрыт)',
         'использование оценочных категорий без раскрытия содержания'),
        (r'и\s+иные\s+(?:основания|документы|случаи)(?!\s+(?:указанные|перечисленные|определённые))',
         'незакрытый перечень без исчерпывающего регулирования'),
    ]

    # ── Типы обязательных требований (для калькулятора) ─────────────────────
    OBLIGATION_PATTERNS = [
        (r'(?:должен|должна|должно|должны|обязан[аы]?|обязуется|обязаны)',
         'обязанность'),
        (r'(?:запрещается|запрещено|не\s+допускается|не\s+вправе|не\s+имеет\s+права|недопустимо)',
         'запрет'),
        (r'(?:не\s+более|не\s+менее|не\s+превышает|ограничивается\s+до|в\s+пределах)',
         'ограничение'),
        (r'(?:уведомить|уведомляет|сообщить|информировать|извещать|уведомление)',
         'уведомление'),
        (r'(?:представить|направить|предоставить)\s+(?:отчёт|отчет|сведения|информацию|доклад|данные)',
         'отчётность'),
        (r'(?:контролировать|проверять|осуществлять\s+(?:надзор|контроль)|мониторинг\s+(?:за|исполнения))',
         'контрольная функция'),
        (r'(?:лицензи[яюей]|разрешени[яюей]|согласовани[яюей]|аккредитаци[яюей])',
         'лицензирование/разрешение'),
        (r'в\s+течение\s+\d+|не\s+позднее\s+(?:\d+|чем\s+через\s+\d+)',
         'срок исполнения'),
        (r'(?:штраф\w*|взыскани\w+|ответственност\w+\s+(?:за|в\s+виде))',
         'санкция/ответственность'),
        (r'(?:регистраци[яю]\s+в|постановк[аие]\s+на\s+(?:учёт|учет)|государственн\w+\s+учёт)',
         'регистрация/учёт'),
    ]

    def __init__(self):
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []

    def validate(self, text: str) -> Dict:
        """
        Основной метод комплексной экспертизы проекта приказа.
        Возвращает расширенный словарь со всеми результатами анализа.
        """
        self.errors = []
        self.warnings = []
        lines = text.split('\n')

        # I. Структурная проверка
        self._check_header(text, lines)
        self._check_title(text, lines)
        self._check_preamble(text, lines)
        self._check_directive_part(text, lines)
        self._check_attachments(text, lines)

        # II–XIII. Расширенная экспертиза
        financial     = self._analyze_financial_justification(text)
        orv           = self._analyze_orv(text)
        ofv           = self._analyze_ofv(text)
        legal_tech    = self._analyze_legal_technique(text)
        mandatory     = self._analyze_mandatory_requirements(text)
        higher_law    = self._analyze_higher_law_compliance(text)
        anticorrupt   = self._analyze_anticorruption(text)
        authority     = self._analyze_authority(text)
        deadlines     = self._analyze_deadlines(text)
        references    = self._analyze_references(text)
        doc_structure = self._analyze_document_structure(text, lines)
        highlighted   = self._find_highlighted_issues(text)

        return {
            'is_valid':         len(self.errors) == 0,
            'errors':           self.errors,
            'warnings':         self.warnings,
            'total_errors':     len(self.errors),
            'total_warnings':   len(self.warnings),
            'financial':        financial,
            'orv':              orv,
            'ofv':              ofv,
            'legal_technique':  legal_tech,
            'mandatory':        mandatory,
            'higher_law':       higher_law,
            'anticorruption':   anticorrupt,
            'authority':        authority,
            'deadlines':        deadlines,
            'references':       references,
            'doc_structure':    doc_structure,
            'highlighted':      highlighted,
        }

    # ═══════════════════════════════════════════════════════════════════════
    # I. СТРУКТУРНЫЕ ПРОВЕРКИ
    # ═══════════════════════════════════════════════════════════════════════

    def _check_header(self, text: str, lines: List[str]):
        """Проверка реквизитов шапки документа"""
        header_text = '\n'.join(lines[:20])

        ministry_patterns = [
            r'министерство', r'минэкономразвития', r'федеральн',
            r'департамент', r'управление', r'служба', r'агентство'
        ]
        if not any(re.search(p, header_text, re.IGNORECASE) for p in ministry_patterns):
            self.errors.append(ValidationError(
                section="Шапка документа",
                error_type="Отсутствует наименование органа",
                description="В начале документа не найдено наименование организации "
                            "(министерства, департамента, агентства и т.п.)"
            ))

        has_order_word = re.search(r'^ПРИКАЗ$', header_text, re.MULTILINE | re.IGNORECASE)
        if not has_order_word:
            has_order_word = re.search(r'ПРИКАЗ', header_text, re.IGNORECASE)
            if has_order_word:
                self.warnings.append(ValidationError(
                    section="Шапка документа",
                    error_type="Некорректное оформление слова ПРИКАЗ",
                    description="Слово 'ПРИКАЗ' должно располагаться отдельной строкой в верхнем регистре"
                ))
            else:
                self.errors.append(ValidationError(
                    section="Шапка документа",
                    error_type="Отсутствует тип документа",
                    description="Не найдено слово 'ПРИКАЗ' в начале документа"
                ))

        date_patterns = [
            r'\d{2}\.\d{2}\.\d{4}',
            r'\d{2}\s+[а-яё]+\s+\d{4}',
            r'«\d{1,2}»\s+[а-яё]+\s+\d{4}'
        ]
        if not any(re.search(p, header_text, re.IGNORECASE) for p in date_patterns):
            self.errors.append(ValidationError(
                section="Шапка документа",
                error_type="Отсутствует дата",
                description="Не найдена дата издания приказа (форматы: ДД.ММ.ГГГГ, «ДД» месяц ГГГГ)"
            ))

        if not re.search(r'№\s*\d+', header_text):
            self.errors.append(ValidationError(
                section="Шапка документа",
                error_type="Отсутствует номер",
                description="Не найден регистрационный номер приказа (формат: № <цифры>)"
            ))

        has_city = re.search(r'г\.\s*[А-ЯЁ][а-яё-]+', header_text)
        is_registered = re.search(r'Зарегистрировано в Минюсте', header_text, re.IGNORECASE)
        if not has_city and not is_registered:
            self.warnings.append(ValidationError(
                section="Шапка документа",
                error_type="Отсутствует место издания",
                description="Не найдено место издания (формат: г. <Город>). "
                            "Обязательно для незарегистрированных документов."
            ))

    def _check_title(self, text: str, lines: List[str]):
        """Проверка заголовка к тексту"""
        title_patterns = [
            r'(?:^|\n)\s*О\s+[а-яёА-ЯЁ\s]{10,}',
            r'(?:^|\n)\s*Об\s+[а-яёА-ЯЁ\s]{10,}'
        ]
        title_match = None
        for p in title_patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                title_match = m
                break

        if not title_match:
            self.warnings.append(ValidationError(
                section="Заголовок",
                error_type="Отсутствует заголовок",
                description="Не найден заголовок к тексту, начинающийся с 'О' или 'Об'. "
                            "Рекомендуется для структурированных приказов."
            ))
        else:
            title_text = title_match.group(0)
            if len(title_text.split()) < 3:
                self.errors.append(ValidationError(
                    section="Заголовок",
                    error_type="Заголовок слишком короткий",
                    description=f"Заголовок содержит менее 3 слов: '{title_text.strip()}'"
                ))

    def _check_preamble(self, text: str, lines: List[str]):
        """Проверка преамбулы (основания издания)"""
        preamble_keywords = [
            r'В\s+соответствии\s+с', r'На\s+основании',
            r'Во\s+исполнение', r'Руководствуясь',
            r'В\s+целях', r'В\s+связи\s+с'
        ]
        has_preamble = any(re.search(p, text, re.IGNORECASE) for p in preamble_keywords)

        if not has_preamble:
            self.errors.append(ValidationError(
                section="Преамбула",
                error_type="Отсутствует преамбула",
                description="Не найдено основание издания приказа. Обязательны формулы: "
                            "'В соответствии с', 'На основании', 'Руководствуясь' и т.п."
            ))
        else:
            npa_patterns = [
                r'[Фф]едеральн\w+\s+закон\w*',
                r'[Пп]остановлени\w+\s+[Пп]равительства',
                r'[Пп]риказ\w*\s+.*№\s*\d+',
                r'№\s*\d+[-\w]*\s+от\s+\d{2}\.\d{2}\.\d{4}',
                r'от\s+\d{2}\.\d{2}\.\d{4}\s+№\s*\d+'
            ]
            if not any(re.search(p, text, re.IGNORECASE) for p in npa_patterns):
                self.warnings.append(ValidationError(
                    section="Преамбула",
                    error_type="Отсутствует ссылка на НПА",
                    description="В преамбуле желательно указать ссылку на нормативно-правовой акт "
                                "(закон, постановление, приказ с номером и датой)"
                ))

    def _check_directive_part(self, text: str, lines: List[str]):
        """Проверка распорядительной части"""
        has_prikazyvayu = re.search(r'(?:^|\n)\s*ПРИКАЗЫВАЮ\s*:', text, re.IGNORECASE)
        if not has_prikazyvayu:
            self.errors.append(ValidationError(
                section="Распорядительная часть",
                error_type="Отсутствует слово ПРИКАЗЫВАЮ",
                description="Распорядительная часть должна начинаться со слова 'ПРИКАЗЫВАЮ:' "
                            "отдельной строкой в верхнем регистре"
            ))
            return

        directive_text = text[has_prikazyvayu.end():]
        numbered_items = re.findall(r'(?:^|\n)\s*(\d+)\.\s+([^\n]+)', directive_text, re.MULTILINE)

        if not numbered_items:
            self.errors.append(ValidationError(
                section="Распорядительная часть",
                error_type="Отсутствуют нумерованные пункты",
                description="После 'ПРИКАЗЫВАЮ:' должны следовать нумерованные пункты (1., 2., 3., …)"
            ))
            return

        numbers = [int(num) for num, _ in numbered_items]
        expected = list(range(1, len(numbers) + 1))
        if numbers != expected:
            missing = set(expected) - set(numbers)
            duplicates = [n for n in numbers if numbers.count(n) > 1]
            desc = "Нарушена последовательность нумерации пунктов. "
            if missing:
                desc += f"Пропущены номера: {sorted(missing)}. "
            if duplicates:
                desc += f"Повторяющиеся номера: {sorted(set(duplicates))}."
            self.errors.append(ValidationError(
                section="Распорядительная часть",
                error_type="Некорректная нумерация",
                description=desc
            ))

        action_verbs = [
            r'утвердить', r'установить', r'назначить', r'признать', r'внести',
            r'обеспечить', r'создать', r'организовать', r'возложить', r'определить',
            r'провести', r'разработать', r'направить', r'представить', r'рассмотреть',
            r'ввести', r'отменить', r'приостановить', r'поручить', r'запретить',
        ]
        empty_items = []
        for num, content in numbered_items:
            if len(content.strip()) < 10:
                empty_items.append(num)
            elif not any(re.search(v, content, re.IGNORECASE) for v in action_verbs):
                self.warnings.append(ValidationError(
                    section="Распорядительная часть",
                    error_type=f"Пункт {num} не содержит действия",
                    description=f"Пункт {num} не содержит распорядительного глагола "
                                f"(утвердить, установить, назначить и т.п.): '{content[:60]}...'"
                ))

        if empty_items:
            self.errors.append(ValidationError(
                section="Распорядительная часть",
                error_type="Пустые пункты",
                description=f"Следующие пункты слишком короткие или пустые: {empty_items}"
            ))

        control_patterns = [
            r'контроль\s+за\s+исполнением',
            r'контроль\s+исполнения',
            r'возложить\s+контроль'
        ]
        if not any(re.search(p, directive_text, re.IGNORECASE) for p in control_patterns):
            self.warnings.append(ValidationError(
                section="Распорядительная часть",
                error_type="Отсутствует пункт о контроле",
                description="Рекомендуется включить пункт о контроле за исполнением приказа "
                            "(например: 'Контроль за исполнением настоящего приказа возложить на…')"
            ))

    def _check_attachments(self, text: str, lines: List[str]):
        """Проверка приложений"""
        attachment_mentions = re.findall(
            r'[Пп]риложени[еия]\s*(?:№\s*)?(\d+)?', text, re.IGNORECASE
        )
        if not attachment_mentions:
            return

        attachment_blocks = re.findall(
            r'(?:^|\n)\s*Приложение\s*(?:№\s*)?(\d+)?\s*\n.*?к\s+приказу',
            text, re.IGNORECASE | re.DOTALL
        )

        if len(attachment_mentions) > 0 and len(attachment_blocks) == 0:
            self.errors.append(ValidationError(
                section="Приложения",
                error_type="Отсутствуют приложения",
                description=f"В тексте упоминаются приложения ({len(attachment_mentions)} раз.), "
                            f"но разделы приложений не найдены"
            ))
        elif len(attachment_blocks) > 0:
            for i, _ in enumerate(attachment_blocks, 1):
                idx = text.find('Приложение')
                has_req = re.search(
                    r'к\s+приказу.*?(?:от|№)',
                    text[idx:idx + 200] if idx >= 0 else '',
                    re.IGNORECASE | re.DOTALL
                )
                if not has_req:
                    self.warnings.append(ValidationError(
                        section="Приложения",
                        error_type=f"Неполные реквизиты приложения {i}",
                        description=f"Приложение {i} должно содержать реквизиты: "
                                    f"'Приложение к приказу от <дата> № <номер>'"
                    ))

            attachment_numbers = [int(n) for n in attachment_mentions if n and str(n).isdigit()]
            if attachment_numbers:
                expected = list(range(1, max(attachment_numbers) + 1))
                if sorted(set(attachment_numbers)) != expected:
                    self.warnings.append(ValidationError(
                        section="Приложения",
                        error_type="Некорректная нумерация приложений",
                        description=f"Номера приложений должны быть последовательными: "
                                    f"найдены {sorted(set(attachment_numbers))}"
                    ))

    # ═══════════════════════════════════════════════════════════════════════
    # II. ФИНАНСОВО-ЭКОНОМИЧЕСКОЕ ОБОСНОВАНИЕ
    # ═══════════════════════════════════════════════════════════════════════

    def _analyze_financial_justification(self, text: str) -> Dict:
        """Анализ необходимости и наличия финансово-экономического обоснования"""
        r = {
            'required': False,
            'found': False,
            'budget_expenses': False,
            'affects_organizations': False,
            'affects_citizens': False,
            'affects_business': False,
            'affects_budget': False,
            'cost_estimate_found': False,
            'details': [],
            'conclusion': '',
        }

        financial_triggers = [
            (r'финансирование|финансовые\s+средства|бюджетные\s+ассигновани',
             'финансирование из бюджета'),
            (r'расход\w+\s+(?:федерального\s+)?бюджета',
             'расходы федерального/регионального бюджета'),
            (r'субсиди[яию]|субвенци[яию]|трансферт',
             'субсидии / субвенции / трансферты'),
            (r'государственны[ейх]\s+(?:закупк|контракт)',
             'государственные закупки'),
            (r'внебюджетны[ейх]\s+средств',
             'внебюджетные средства'),
        ]
        for pat, desc in financial_triggers:
            if re.search(pat, text, re.IGNORECASE):
                r['required'] = True
                r['budget_expenses'] = True
                r['details'].append(f'Обнаружено: {desc}')

        feo_patterns = [
            r'финансово-экономическое\s+обоснование',
            r'\bФЭО\b',
            r'экономическое\s+обоснование',
            r'оценка\s+(?:затрат|расходов)',
        ]
        r['found'] = any(re.search(p, text, re.IGNORECASE) for p in feo_patterns)

        if re.search(r'организаци[яию]|предприяти[яию]|юридическ\w+\s+лиц', text, re.IGNORECASE):
            r['affects_organizations'] = True
            r['required'] = True
        if re.search(r'гражданин|физическ\w+\s+лиц|населени', text, re.IGNORECASE):
            r['affects_citizens'] = True
            r['required'] = True
        if re.search(r'предпринимател|хозяйствующ\w+\s+субъект|малый\s+бизнес', text, re.IGNORECASE):
            r['affects_business'] = True
            r['required'] = True
        if re.search(r'бюджет\w*\s+(?:Российской|Федерации|субъект)', text, re.IGNORECASE):
            r['affects_budget'] = True
            r['required'] = True

        r['cost_estimate_found'] = bool(
            re.search(
                r'\d+\s*(?:тыс\.|млн\.|млрд\.)\s*руб|затрат\w+\s+составляет',
                text, re.IGNORECASE
            )
        )

        if r['required'] and not r['found']:
            r['conclusion'] = 'ТРЕБУЕТСЯ — финансово-экономическое обоснование не обнаружено'
        elif r['required'] and r['found']:
            r['conclusion'] = 'ИМЕЕТСЯ — финансово-экономическое обоснование присутствует'
        else:
            r['conclusion'] = 'НЕ ТРЕБУЕТСЯ — приказ не предполагает дополнительных бюджетных расходов'

        return r

    # ═══════════════════════════════════════════════════════════════════════
    # III. ОЦЕНКА РЕГУЛИРУЮЩЕГО ВОЗДЕЙСТВИЯ (ОРВ)
    # ═══════════════════════════════════════════════════════════════════════

    def _analyze_orv(self, text: str) -> Dict:
        """Анализ необходимости проведения ОРВ"""
        r = {'required': False, 'found': False, 'triggers': [], 'conclusion': ''}

        orv_triggers = [
            (r'запрет\w*|запрещается',
             'введение запретов'),
            (r'ограничени\w+\s+(?:деятельности|прав|осуществления)',
             'ограничения деятельности'),
            (r'лицензирование|лицензи[яию]',
             'лицензирование'),
            (r'аккредитаци[яию]',
             'аккредитация'),
            (r'обязательн\w+\s+(?:требовани|уведомлени|представлени)',
             'обязательные требования'),
            (r'контрольно-надзорн\w+|плановые?\s+проверки',
             'контрольно-надзорные процедуры'),
            (r'(?:обязательн\w+\s+)?отчётность|периодическ\w+\s+предоставлени',
             'обязательная периодическая отчётность'),
            (r'предпринимател\w+|малый\s+(?:и\s+средний\s+)?бизнес|хозяйствующ\w+\s+субъект',
             'влияние на предпринимательскую деятельность'),
            (r'государственн\w+\s+(?:контроль|надзор)',
             'государственный контроль/надзор'),
            (r'административн\w+\s+(?:барьер|процедур|регламент)',
             'административные процедуры/барьеры'),
            (r'(?:обязательн\w+\s+)?сертификаци[яию]|стандартизаци',
             'сертификация / стандартизация'),
            (r'разрешительн\w+\s+(?:процедур|порядок|документ)',
             'разрешительные процедуры'),
        ]
        for pat, desc in orv_triggers:
            if re.search(pat, text, re.IGNORECASE):
                r['triggers'].append(desc)
                r['required'] = True

        r['found'] = bool(
            re.search(r'оценка\s+регулирующего\s+воздействия|(?<!\S)ОРВ(?!\S)', text, re.IGNORECASE)
        )

        if r['required']:
            r['conclusion'] = ('ТРЕБУЕТСЯ — выявлены положения, влияющие на предпринимательскую '
                               'и иную экономическую деятельность')
        else:
            r['conclusion'] = 'НЕ ТРЕБУЕТСЯ — положения, требующие обязательной ОРВ, не выявлены'

        return r

    # ═══════════════════════════════════════════════════════════════════════
    # IV. ОЦЕНКА ФАКТИЧЕСКОГО ВОЗДЕЙСТВИЯ (ОФВ)
    # ═══════════════════════════════════════════════════════════════════════

    def _analyze_ofv(self, text: str) -> Dict:
        """Анализ необходимости проведения ОФВ"""
        r = {'required': False, 'long_term': False, 'admin_burden': False, 'conclusion': ''}

        if re.search(
            r'(?:действует|вступает\s+в\s+силу|вводится)\s+с\s+\d{4}|бессрочно|без\s+ограничения\s+срока',
            text, re.IGNORECASE
        ):
            r['long_term'] = True
            r['required'] = True

        burden_patterns = [
            r'обязательно\w*\s+(?:предоставлени|направлени|уведомлени)',
            r'(?:ежегодн|ежеквартальн|ежемесячн)\w+\s+(?:отчёт|представлени|направлени)',
            r'регулярн\w+\s+(?:отчёт|проверк|мониторинг)',
        ]
        if any(re.search(p, text, re.IGNORECASE) for p in burden_patterns):
            r['admin_burden'] = True
            r['required'] = True

        if r['required']:
            r['conclusion'] = ('ТРЕБУЕТСЯ — выявлены положения с длительным сроком действия '
                               'и/или значительной административной нагрузкой')
        else:
            r['conclusion'] = 'НЕ ТРЕБУЕТСЯ — длительных обязательных требований не выявлено'

        return r

    # ═══════════════════════════════════════════════════════════════════════
    # V. ЮРИДИКО-ТЕХНИЧЕСКАЯ ЭКСПЕРТИЗА
    # ═══════════════════════════════════════════════════════════════════════

    def _analyze_legal_technique(self, text: str) -> Dict:
        """
        Юридико-техническая экспертиза:
        • точность формулировок
        • соответствие терминологии законодательству
        • правила юридической техники
        • внутренняя непротиворечивость
        """
        r = {
            'vague_formulations': [],
            'terminology_issues': [],
            'structure_issues': [],
            'internal_contradictions': [],
            'requires_revision': False,
        }

        # Нечёткие формулировки
        for pattern, desc in self.VAGUE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                r['vague_formulations'].append(desc)

        # Терминологические проблемы
        term_checks = [
            (r'\bфирма\b',
             '"фирма" — неюридический термин; используйте "организация" или конкретную ОПФ'),
            (r'(?i)\bЭВМ\b',
             '"ЭВМ" — устаревший термин; рекомендуется "автоматизированная система" / "компьютер"'),
            (r'(?i)\bинтернет\b(?!\s*-)',
             '"интернет" — в официальных документах: "сеть Интернет"'),
            (r'(?i)\be-?mail\b|\bэлектронн\w+\s+адрес\b(?!\s+электронн)',
             'уточните: "электронная почта" или "адрес электронной почты"'),
            (r'(?i)\bсотрудник\b(?!\s+(?:органа|министерства|ведомства|государственного))',
             '"сотрудник" — уточните категорию: "работник", "должностное лицо", '
             '"государственный гражданский служащий"'),
            (r'(?i)\bпредприятие\b(?!\s+(?:государственное|муниципальное|унитарное|казённое))',
             '"предприятие" без указания типа — уточните организационно-правовую форму'),
        ]
        for pat, desc in term_checks:
            if re.search(pat, text, re.IGNORECASE):
                r['terminology_issues'].append(desc)

        # Структурные нарушения юридической техники
        sentences = re.split(r'(?<=[.!?])\s+', text)
        long_sents = [s for s in sentences if len(s) > 300]
        if long_sents:
            r['structure_issues'].append(
                f'Обнаружено {len(long_sents)} чрезмерно длинных предложений (>300 символов) — '
                f'затрудняют однозначное толкование нормы'
            )

        if re.search(r'(?:^|\n)\s*\d+\.\d+\.\d+\.', text, re.MULTILINE):
            r['structure_issues'].append(
                'Трёхуровневая нумерация пунктов — рекомендуется не более двух уровней вложенности'
            )

        if re.search(
            r'не\s+(?:\w+\s+){0,3}не\s+(?:вправе|может|допускается|разрешается)',
            text, re.IGNORECASE
        ):
            r['structure_issues'].append(
                'Обнаружено двойное отрицание — может вызвать неоднозначное толкование нормы'
            )

        if re.search(r'(?:^|\n)(?!\s*\d)\s*[а-яё]', text, re.MULTILINE):
            r['structure_issues'].append(
                'Обнаружены абзацы, начинающиеся со строчной буквы вне списков — '
                'проверьте структуру пунктов'
            )

        # Внутренняя непротиворечивость (анализ пунктов)
        paragraphs = self._extract_paragraphs(text)
        para_texts = [p['text'] for p in paragraphs]
        checked_pairs = set()
        for i in range(len(para_texts)):
            for j in range(i + 1, len(para_texts)):
                pair = (i, j)
                if pair in checked_pairs:
                    continue
                checked_pairs.add(pair)
                words1 = set(re.findall(r'[а-яё]{5,}', para_texts[i].lower()))
                words2 = set(re.findall(r'[а-яё]{5,}', para_texts[j].lower()))
                if len(words1) >= 4 and len(words2) >= 4:
                    overlap = len(words1 & words2) / min(len(words1), len(words2))
                    if overlap > 0.65:
                        r['internal_contradictions'].append(
                            f'Пункты {paragraphs[i]["number"]} и {paragraphs[j]["number"]} '
                            f'могут содержать дублирующиеся положения '
                            f'(схожесть содержания ~{int(overlap * 100)}%)'
                        )

        r['requires_revision'] = bool(
            r['vague_formulations'] or r['terminology_issues'] or
            r['structure_issues'] or r['internal_contradictions']
        )
        return r

    # ═══════════════════════════════════════════════════════════════════════
    # VI. КАЛЬКУЛЯТОР ОБЯЗАТЕЛЬНЫХ ТРЕБОВАНИЙ
    # ═══════════════════════════════════════════════════════════════════════

    def _analyze_mandatory_requirements(self, text: str) -> Dict:
        """
        Калькулятор обязательных требований по пунктам НПА.
        Соответствует методологии Федерального закона № 247-ФЗ
        и реестра обязательных требований.
        """
        r = {'total': 0, 'by_paragraph': [], 'by_type': {}, 'summary': ''}

        paragraphs = self._extract_paragraphs(text)
        for para in paragraphs:
            para_r = {'number': para['number'], 'requirements': [], 'count': 0}
            for pattern, req_type in self.OBLIGATION_PATTERNS:
                matches = re.findall(pattern, para['text'], re.IGNORECASE)
                if matches:
                    para_r['requirements'].append(req_type)
                    r['by_type'][req_type] = r['by_type'].get(req_type, 0) + len(matches)
                    r['total'] += len(matches)
                    para_r['count'] += len(matches)
            if para_r['count'] > 0:
                r['by_paragraph'].append(para_r)

        if not paragraphs:
            for pattern, req_type in self.OBLIGATION_PATTERNS:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    r['by_type'][req_type] = r['by_type'].get(req_type, 0) + len(matches)
                    r['total'] += len(matches)

        r['summary'] = (
            f'Итого: {r["total"]} обязательных требований '
            f'в {len(r["by_paragraph"])} пунктах распорядительной части'
        )
        return r

    # ═══════════════════════════════════════════════════════════════════════
    # VII. СООТВЕТСТВИЕ АКТАМ БОЛЬШЕЙ ЮРИДИЧЕСКОЙ СИЛЫ
    # ═══════════════════════════════════════════════════════════════════════

    def _analyze_higher_law_compliance(self, text: str) -> Dict:
        """Проверка соответствия иерархии нормативных правовых актов"""
        r = {
            'constitution_refs': False,
            'federal_law_refs': [],
            'presidential_decree_refs': [],
            'government_resolution_refs': [],
            'issues': [],
            'statement': (
                'Рассматриваемый ведомственный акт соответствует актам большей юридической силы.'
            ),
        }

        r['constitution_refs'] = bool(
            re.search(r'[Кк]онституци\w+\s+Российской\s+Федерации', text)
        )
        r['federal_law_refs'] = list({
            m.strip()[:90]
            for m in re.findall(r'[Фф]едеральн\w+\s+закон\w*[^,\n]{0,80}', text)
        })[:6]
        r['presidential_decree_refs'] = list({
            m.strip()[:90]
            for m in re.findall(r'[Уу]каз\w*\s+[Пп]резидента[^,\n]{0,80}', text)
        })[:4]
        r['government_resolution_refs'] = list({
            m.strip()[:90]
            for m in re.findall(r'[Пп]остановлени\w+\s+[Пп]равительства[^,\n]{0,80}', text)
        })[:4]

        if not any([
            r['constitution_refs'],
            r['federal_law_refs'],
            r['presidential_decree_refs'],
            r['government_resolution_refs']
        ]):
            r['issues'].append(
                'Отсутствуют ссылки на акты большей юридической силы — '
                'необходима дополнительная проверка соответствия законодательству'
            )

        return r

    # ═══════════════════════════════════════════════════════════════════════
    # VIII. АНТИКОРРУПЦИОННАЯ ЭКСПЕРТИЗА
    # ═══════════════════════════════════════════════════════════════════════

    def _analyze_anticorruption(self, text: str) -> Dict:
        """
        Антикоррупционная экспертиза по методике Минюста России
        (Постановление Правительства РФ от 26.02.2010 № 96).
        """
        r = {'factors': [], 'risk_level': 'низкий'}

        corruption_factors = [
            (r'по\s+усмотрению\s+(?:органа|должностного|руководителя|министра|лица)',
             'широкое усмотрение должностного лица без установленных критериев '
             '(фактор коррупциогенности по методике Минюста)'),
            (r'(?:вправе|может)\s+отказать(?!\s+(?:в\s+случае|при\s+наличии\s+следующих|только\s+в))',
             'право на немотивированный отказ без установленных оснований'),
            (r'без\s+(?:объяснения\s+причин|обоснования|мотивировки)',
             'допускается действие без обоснования — исключает ответственность за произвольные решения'),
            (r'по\s+согласованию\s+с(?!\s+\w+\s+(?:в\s+течение|в\s+срок|не\s+позднее))',
             'согласование без установления срока и оснований для отказа'),
            (r'в\s+исключительных\s+случаях(?!\s*[:,])',
             'исключения без чётко определённых критериев (возможность субъективного толкования)'),
            (r'при\s+наличии\s+оснований(?!\s*[\(,:])',
             'ссылка на основания без их конкретного перечисления'),
            (r'уполномоченн\w+\s+(?:орган|лицо|организаци\w+)'
             r'(?!\s+(?:определяется|в\s+соответствии|является|утверждается))',
             '"уполномоченный орган/лицо" без конкретной идентификации — '
             'создаёт неопределённость субъекта полномочий'),
            (r'по\s+решению\s+(?:органа|руководителя)(?!\s+(?:в\s+случае|при\s+наличии))',
             'принятие решения без установленных критериев и процедур'),
            (r'и\s+иные\s+(?:основания|документы|случаи)'
             r'(?!\s+(?:указанные|перечисленные|определённые|предусмотренные))',
             'незакрытый перечень без исчерпывающего регулирования'),
            (r'оценочн\w+\s+(?:категори|критери|понятия)(?!\s+раскрыт)',
             'оценочные категории без раскрытия содержания'),
        ]

        for pat, factor in corruption_factors:
            if re.search(pat, text, re.IGNORECASE):
                r['factors'].append(factor)

        n = len(r['factors'])
        if n == 0:
            r['risk_level'] = 'низкий'
        elif n <= 2:
            r['risk_level'] = 'умеренный'
        elif n <= 4:
            r['risk_level'] = 'повышенный'
        else:
            r['risk_level'] = 'высокий'

        return r

    # ═══════════════════════════════════════════════════════════════════════
    # IX. ПРОВЕРКА ПОЛНОМОЧИЙ
    # ═══════════════════════════════════════════════════════════════════════

    def _analyze_authority(self, text: str) -> Dict:
        """Проверка наличия нормативных оснований полномочий органа на издание акта"""
        r = {'authority_stated': False, 'basis_found': False, 'conclusion': ''}

        auth_patterns = [
            r'в\s+соответствии\s+с\s+(?:положением|уставом|регламентом)',
            r'на\s+основании\s+(?:положения|устава|регламента)',
            r'в\s+пределах\s+(?:своей\s+)?компетенции',
            r'[Пп]оложение[мо]\s+о\s+[Мм]инистерстве',
            r'[Пп]остановлени\w+\s+[Пп]равительства[^,\n]{0,50}(?:функции|полномочия)',
        ]
        r['authority_stated'] = any(re.search(p, text, re.IGNORECASE) for p in auth_patterns)
        r['basis_found'] = bool(
            re.search(r'[Пп]оложени\w+\s+о\s+[Мм]инистерстве|функции?\s+и\s+полномочия',
                      text, re.IGNORECASE)
        )

        if r['authority_stated']:
            r['conclusion'] = 'Основания для издания акта указаны — компетенция подтверждена'
        else:
            r['conclusion'] = ('Рекомендуется явно указать нормативное основание полномочий '
                               'органа на издание данного акта')

        return r

    # ═══════════════════════════════════════════════════════════════════════
    # X. АНАЛИЗ СРОКОВ
    # ═══════════════════════════════════════════════════════════════════════

    def _analyze_deadlines(self, text: str) -> Dict:
        """Анализ определённости сроков исполнения"""
        r = {'specific': [], 'indefinite': [], 'issues': []}

        spec_patterns = [
            r'в\s+течение\s+\d+\s+(?:рабочих\s+)?(?:дней|месяцев|лет)',
            r'не\s+позднее\s+\d+\s+(?:рабочих\s+)?(?:дней|месяцев)',
            r'до\s+\d{2}\.\d{2}\.\d{4}',
            r'с\s+\d{2}\.\d{2}\.\d{4}',
        ]
        for p in spec_patterns:
            r['specific'].extend(re.findall(p, text, re.IGNORECASE)[:4])

        indef_patterns = [
            r'в\s+разумный\s+срок',
            r'в\s+кратчайшие\s+сроки',
            r'своевременно(?!\s*(?:до|не\s+позднее))',
            r'в\s+ближайшее\s+время',
        ]
        for p in indef_patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                r['indefinite'].append(m.group(0))

        if r['indefinite']:
            r['issues'].append(
                f'Неопределённые сроки: {", ".join(r["indefinite"])} — '
                f'замените конкретными датами или периодами'
            )

        return r

    # ═══════════════════════════════════════════════════════════════════════
    # XI. АНАЛИЗ НОРМАТИВНЫХ ССЫЛОК
    # ═══════════════════════════════════════════════════════════════════════

    def _analyze_references(self, text: str) -> Dict:
        """Анализ ссылок на нормативные правовые акты"""
        npa_refs = re.findall(
            r'(?:[Фф]едеральн\w+\s+закон\w*|[Уу]каз\w*\s+[Пп]резидента'
            r'|[Пп]остановлени\w+\s+[Пп]равительства|[Пп]риказ\w*)[^,\n]{0,100}',
            text, re.IGNORECASE
        )
        return {
            'total_refs': len(npa_refs),
            'npa_refs': list({r.strip()[:90] for r in npa_refs})[:8],
            'has_refs': len(npa_refs) > 0,
        }

    # ═══════════════════════════════════════════════════════════════════════
    # XII. СТРУКТУРНЫЙ АНАЛИЗ ДОКУМЕНТА
    # ═══════════════════════════════════════════════════════════════════════

    def _analyze_document_structure(self, text: str, lines: List[str]) -> Dict:
        """Общий структурный анализ документа"""
        paragraphs = re.findall(r'(?:^|\n)\s*\d+\.\s+\S', text, re.MULTILINE)
        subparagraphs = re.findall(r'(?:^|\n)\s*\d+\.\d+\.\s+\S', text, re.MULTILINE)
        return {
            'total_paragraphs':   len(paragraphs),
            'total_subparagraphs': len(subparagraphs),
            'has_chapters':       bool(re.search(r'(?:^|\n)\s*(?:ГЛАВА|Глава)\s+', text, re.MULTILINE)),
            'has_sections':       bool(re.search(r'(?:^|\n)\s*(?:РАЗДЕЛ|Раздел)\s+', text, re.MULTILINE)),
            'document_length':    len(text),
            'estimated_pages':    max(1, len(text) // 1800),
            'has_signature_block': bool(
                re.search(r'(?:Министр|Руководитель|Заместитель\s+министра)', text, re.IGNORECASE)
            ),
        }

    # ═══════════════════════════════════════════════════════════════════════
    # XIII. ПОИСК ПРАВОТВОРЧЕСКИХ ОШИБОК ДЛЯ ПОДСВЕТКИ
    # ═══════════════════════════════════════════════════════════════════════

    def _find_highlighted_issues(self, text: str) -> List[Dict]:
        """
        Поиск конкретных мест в тексте, содержащих типовые правотворческие ошибки.
        Возвращает список словарей с позицией, типом и описанием ошибки.
        """
        issues = []
        paragraphs = self._extract_paragraphs(text)

        def get_para(pos):
            best = None
            for p in paragraphs:
                if p['start'] <= pos:
                    best = p['number']
            return best or '—'

        for pattern, desc in self.VAGUE_PATTERNS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                issues.append({
                    'type':        'vague',
                    'start':       m.start(),
                    'end':         m.end(),
                    'paragraph':   get_para(m.start()),
                    'matched':     m.group(0),
                    'description': f'Неопределённая формулировка: {desc}',
                })

        for pattern, desc in self.DISCRETION_PATTERNS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                issues.append({
                    'type':        'corrupt',
                    'start':       m.start(),
                    'end':         m.end(),
                    'paragraph':   get_para(m.start()),
                    'matched':     m.group(0),
                    'description': f'Коррупциогенный фактор: {desc}',
                })

        for m in re.finditer(r'[А-ЯЁ][^.!?]{300,}[.!?]', text):
            issues.append({
                'type':        'structure',
                'start':       m.start(),
                'end':         m.end(),
                'paragraph':   get_para(m.start()),
                'matched':     m.group(0)[:80] + '…',
                'description': 'Чрезмерно длинное предложение — затрудняет однозначное толкование нормы',
            })

        for m in re.finditer(r'\b(\w{4,})\s+\1\b', text, re.IGNORECASE):
            issues.append({
                'type':        'structure',
                'start':       m.start(),
                'end':         m.end(),
                'paragraph':   get_para(m.start()),
                'matched':     m.group(0),
                'description': 'Дублирование слова — возможная опечатка или лишний повтор',
            })

        return sorted(issues, key=lambda x: x['start'])

    # ═══════════════════════════════════════════════════════════════════════
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ═══════════════════════════════════════════════════════════════════════

    def _extract_paragraphs(self, text: str) -> List[Dict]:
        """Извлечение нумерованных пунктов из текста"""
        paragraphs = []
        pattern = r'(?:^|\n)\s*(\d+)\.\s+([^\n]+(?:\n(?!\s*\d+\.)[^\n]*)*)'
        for m in re.finditer(pattern, text, re.MULTILINE):
            content = m.group(2).strip()
            if len(content) > 5:
                paragraphs.append({
                    'number': m.group(1),
                    'text':   content,
                    'start':  m.start(),
                })
        return paragraphs

    def get_report(self, validation_result: Dict) -> str:
        """Форматирование краткого отчёта (для совместимости)"""
        report = ['=' * 80, 'ОТЧЕТ О ПРОВЕРКЕ СТРУКТУРЫ ПРИКАЗА', '=' * 80]
        if validation_result['is_valid']:
            report.append('\n✓ СТРУКТУРА ДОКУМЕНТА КОРРЕКТНА')
        else:
            report.append('\n✗ ОБНАРУЖЕНЫ ОШИБКИ')
            report.append(f"Ошибок: {validation_result['total_errors']}, "
                          f"предупреждений: {validation_result['total_warnings']}")
        if validation_result['errors']:
            report.append('\nКРИТИЧЕСКИЕ ОШИБКИ:')
            for i, e in enumerate(validation_result['errors'], 1):
                report.append(f'{i}. [{e.section}] {e.error_type}')
                report.append(f'   {e.description}')
        if validation_result['warnings']:
            report.append('\nПРЕДУПРЕЖДЕНИЯ:')
            for i, w in enumerate(validation_result['warnings'], 1):
                report.append(f'{i}. [{w.section}] {w.error_type}')
                report.append(f'   {w.description}')
        report.append('\n' + '=' * 80)
        return '\n'.join(report)


def validate_order(text: str) -> Dict:
    """Вспомогательная функция для проверки одного приказа"""
    validator = OrderStructureValidator()
    return validator.validate(text)


if __name__ == "__main__":
    test_text = """
МИНИСТЕРСТВО ЭКОНОМИЧЕСКОГО РАЗВИТИЯ РОССИЙСКОЙ ФЕДЕРАЦИИ

ПРИКАЗ

от 15.01.2025 № 123
г. Москва

О назначении комиссии по проведению проверки

В соответствии с Федеральным законом от 27.07.2010 № 210-ФЗ
"Об организации предоставления государственных и муниципальных услуг"
и постановлением Правительства Российской Федерации от 16.05.2011 № 373

ПРИКАЗЫВАЮ:

1. Утвердить состав комиссии при необходимости.
2. Установить срок проведения проверки в кратчайшие сроки.
3. Обеспечить надлежащим образом проведение всех мероприятий.
4. Контроль за исполнением настоящего приказа возложить на заместителя министра.

Министр                                                    И.О. Фамилия
"""
    validator = OrderStructureValidator()
    result = validator.validate(test_text)
    print(validator.get_report(result))
    print(f"\nПодсветка: {len(result['highlighted'])} проблемных мест")
    print(f"ОРВ: {result['orv']['conclusion']}")
    print(f"ФЭО: {result['financial']['conclusion']}")
    print(f"Антикоррупция: риск {result['anticorruption']['risk_level']}, "
          f"факторов: {len(result['anticorruption']['factors'])}")
    print(f"Обязательных требований: {result['mandatory']['total']}")
