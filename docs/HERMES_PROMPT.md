Ты — senior AI systems engineer, architect и performance engineer.

Твоя цель: улучшить существующий проект `langgraph-agent-blueprint`, вдохновляясь архитектурными и поведенческими идеями Hermes Agent, но реализовать всё нативно на LangGraph, сохранив архитектурную чистоту текущего blueprint.

Главный результат: получить быстрый, качественный, расширяемый LangGraph-агент, который по пользовательскому опыту, автономности, скорости реакции, качеству tool-use и устойчивости приближается к Hermes Agent, но не превращается в копию Hermes и не ломает текущую архитектуру проекта.

Контекст:
- У меня уже есть существующий `langgraph-agent-blueprint`.
- Есть open-source Hermes Agent как референс по UX, автономности, памяти, работе с проектным контекстом, инструментами, shell/dev workflow и скорости.
- Нужно не переписать проект хаотично, а улучшить его инженерно: через анализ, план, минимальные чистые изменения, тесты и измеримые метрики.
- Всё новое должно быть реализовано через LangGraph: graph nodes, edges, state, checkpointers, memory, tool nodes, routing, conditional edges, interrupt/human-in-the-loop при необходимости.

Основные приоритеты, строго по порядку:

1. Скорость работы агента
   - Уменьши latency первого ответа.
   - Уменьши количество лишних LLM-вызовов.
   - Уменьши количество лишних tool calls.
   - Добавь fast-path для простых задач.
   - Добавь smart routing: простые задачи не должны проходить через тяжёлый planning pipeline.
   - Используй параллельное выполнение независимых операций, где это безопасно.
   - Добавь caching для повторяемых операций: project scan, tool schema loading, repo metadata, memory retrieval, dependency inspection.
   - Реализуй lazy loading тяжёлых инструментов и контекста.
   - Не загружай весь репозиторий в контекст без необходимости.
   - Сначала измерь текущие bottlenecks, потом оптимизируй.
   - Любое ускорение должно быть подтверждено benchmark или хотя бы reproducible timing report.

2. Качество работы агента
   - Агент должен лучше понимать проектный контекст.
   - Агент должен уметь анализировать задачу, выбирать минимально достаточный workflow и не делать лишних действий.
   - Улучши tool-use: агент должен выбирать правильные инструменты, проверять результат инструментов и корректно восстанавливаться после ошибок.
   - Добавь или улучши memory layer:
     - краткосрочная память текущей задачи;
     - долговременная память проекта;
     - user/project preferences;
     - learned facts about repo;
     - индекс навыков/паттернов, если это уместно.
   - Добавь механизм self-review перед финальным ответом или PR summary, но только там, где это действительно нужно.
   - Добавь quality gates:
     - tests;
     - lint/typecheck;
     - smoke tests для graph execution;
     - regression tests для tool routing;
     - eval cases для agent behavior.
   - Агент должен давать понятные, короткие, actionable ответы, а не длинные рассуждения.
   - Агент должен честно сообщать, что было изменено, что проверено, какие риски остались.

3. Архитектурная чистота
   - Сохрани текущую философию `langgraph-agent-blueprint`.
   - Не превращай проект в монолит.
   - Раздели слои:
     - graph orchestration;
     - state schema;
     - prompts;
     - tools;
     - memory;
     - runtime/config;
     - evaluation;
     - observability;
     - API/interface layer.
   - Не смешивай бизнес-логику, LangGraph nodes, tool definitions и prompt templates в одном месте.
   - Все новые компоненты должны иметь понятные имена, маленький API и быть тестируемыми отдельно.
   - Не добавляй тяжелые зависимости без причины.
   - Не добавляй абстракции «на будущее», если они не используются.
   - Любой новый модуль должен иметь понятную ответственность.
   - Предпочитай incremental refactor вместо full rewrite.
   - Существующие публичные интерфейсы не ломать без необходимости.

Что именно нужно сделать:

1. Сначала изучи проект
   - Определи текущую структуру.
   - Найди LangGraph graph definition.
   - Найди state schema.
   - Найди tools layer.
   - Найди memory/checkpointing.
   - Найди prompts.
   - Найди entrypoints/API/CLI.
   - Найди tests/evals.
   - Найди performance bottlenecks.
   - Составь краткую карту текущей архитектуры.

2. Изучи Hermes Agent как референс
   - Определи, какие идеи Hermes можно безопасно перенести в LangGraph-проект.
   - Не копируй код слепо.
   - Не нарушай лицензии.
   - Не тащи весь Hermes внутрь проекта.
   - Выдели только архитектурные идеи:
     - persistent project memory;
     - skill/tool registry;
     - fast command execution workflow;
     - project awareness;
     - async/background-style orchestration внутри текущего runtime, если поддерживается;
     - intelligent context loading;
     - robust shell/dev loop;
     - multi-step autonomous workflow;
     - clear user-facing progress updates.
   - Каждую идею адаптируй под LangGraph idioms.

3. Спроектируй целевую LangGraph-архитектуру
   Создай или улучши graph примерно такого типа:

   - input_classification_node:
     Быстро определяет тип задачи: simple answer, coding task, repo analysis, tool task, long-running task, memory update, debugging.

   - context_router_node:
     Решает, какой контекст нужен: none, small project summary, specific files, memory, tools, full planning.

   - memory_retrieval_node:
     Достаёт только релевантную память, а не всё подряд.

   - planner_node:
     Используется только для сложных задач. План должен быть коротким и исполнимым.

   - tool_execution_node:
     Выполняет инструменты с retry/error handling/timeouts.

   - reflection_or_review_node:
     Используется только для задач с высоким риском: code changes, migrations, architectural changes.

   - response_node:
     Формирует короткий, полезный ответ пользователю.

   - memory_write_node:
     Записывает только полезные долговременные факты: проектные решения, предпочтения, найденные паттерны, стабильные выводы.

   Обязательно используй conditional edges, чтобы простые задачи проходили короткий путь, а сложные — полный pipeline.

4. Оптимизируй скорость
   Реализуй следующие performance improvements, если они подходят проекту:

   - Fast path:
     Простые вопросы и маленькие изменения не должны запускать полный агентный цикл.

   - Context budgeter:
     Компонент, который ограничивает количество файлов, памяти и tool outputs в контексте.

   - Lazy tool registry:
     Tool schemas и тяжелые clients загружаются только при необходимости.

   - Parallel safe operations:
     Независимые проверки, чтение файлов, grep/search, metadata collection выполняются параллельно.

   - Caching:
     Кэшируй project structure, dependency graph, file summaries, memory retrieval results, tool metadata.

   - Bounded loops:
     Любой agent loop должен иметь max_iterations, max_tool_calls, timeout и graceful fallback.

   - Early stopping:
     Если задача решена, не продолжай planning/review без необходимости.

   - Streaming:
     Если проект поддерживает streaming, включи быстрые промежуточные обновления для пользователя.

   - Minimal prompts:
     Убери раздутые prompt templates. Раздели system/developer/task prompts. Не отправляй лишний контекст.

5. Улучши качество
   Добавь или улучши:

   - task classifier;
   - tool selection policy;
   - error recovery policy;
   - structured state;
   - structured outputs, где это полезно;
   - validation of tool outputs;
   - final answer checklist;
   - eval dataset с типовыми задачами;
   - smoke tests для graph routes;
   - tests для memory retrieval/write;
   - tests для fast-path routing;
   - tests для bounded loops;
   - tests для tool failure recovery.

6. Улучши память
   Реализуй память так, чтобы она была полезной, но не тормозила агента:

   - project_memory:
     стабильные сведения о проекте, архитектуре, соглашениях, командах запуска, тестах.

   - user_preferences:
     стиль ответов, предпочтения по архитектуре, preferred tools.

   - task_memory:
     временный контекст текущей задачи.

   - skill_memory / pattern_memory:
     повторно используемые паттерны решения задач внутри этого проекта.

   Требования к памяти:
   - retrieval должен быть релевантным и ограниченным;
   - write должен быть selective;
   - не сохраняй шум;
   - не сохраняй секреты;
   - не раздувай контекст;
   - добавь tests на memory filtering.

7. Улучши developer experience
   - Добавь понятные команды запуска.
   - Добавь `.env.example`, если нужно.
   - Добавь README-секцию по новой архитектуре.
   - Добавь диаграмму или текстовое описание graph flow.
   - Добавь инструкции для benchmark.
   - Добавь инструкции для evals.
   - Добавь troubleshooting.
   - Все изменения должны быть понятны следующему разработчику.

8. Observability
   Добавь минимальную наблюдаемость:
   - timing per node;
   - количество LLM calls;
   - количество tool calls;
   - выбранный route;
   - cache hit/miss;
   - memory retrieval size;
   - errors/retries;
   - total latency.

   Это должно помогать улучшать скорость и качество без чрезмерной сложности.

9. Безопасность и надежность
   - Не выполняй опасные shell-команды без явного контроля.
   - Для file writes используй аккуратный patch-based подход.
   - Не удаляй важные файлы без необходимости.
   - Не сохраняй секреты в память.
   - Не логируй API keys.
   - Добавь allowlist/denylist для risky tools, если в проекте есть shell/browser/file tools.
   - Любые destructive actions должны быть явно отделены от safe actions.

10. Критерии приемки
   Работа считается завершенной только если:

   - Проект запускается.
   - Основной LangGraph graph работает.
   - Есть быстрый путь для простых задач.
   - Есть полный путь для сложных задач.
   - Есть bounded agent loop.
   - Есть memory retrieval и selective memory write, если это совместимо с проектом.
   - Есть tests или smoke tests.
   - Есть benchmark до/после или хотя бы reproducible timing report.
   - Архитектура стала чище, а не сложнее.
   - README обновлен.
   - Все изменения описаны в финальном отчете.
   - Нет неподтвержденных заявлений вроде “стало быстрее”, если это не измерено.

Формат работы:

Сначала выведи краткий engineering plan:

1. Current architecture summary
2. Hermes-inspired improvements worth porting
3. Proposed LangGraph architecture
4. Performance plan
5. Quality/eval plan
6. Files to change
7. Risks

Затем внеси изменения маленькими логическими шагами.

После каждого крупного шага:
- запусти релевантные проверки;
- исправь ошибки;
- не продолжай строить поверх сломанного состояния.

В финале выведи отчет:

- Что изменено
- Какие LangGraph nodes/routes добавлены или изменены
- Какие speed optimizations добавлены
- Какие quality improvements добавлены
- Какие architecture improvements добавлены
- Какие tests/evals добавлены
- Какие benchmark результаты получены
- Какие команды запускать
- Какие риски или TODO остались

Важные ограничения:

- Не делай full rewrite без крайней необходимости.
- Не копируй Hermes Agent напрямую.
- Не внедряй чужую архитектуру, если она конфликтует с LangGraph.
- Не добавляй лишнюю сложность ради “agentic” вида.
- Не ломай существующие сценарии blueprint.
- Не скрывай ошибки.
- Не заявляй о performance improvement без измерений.
- Не добавляй глобальные mutable singleton’ы без причины.
- Не смешивай prompts, graph nodes, tools и memory в одном файле.
- Не добавляй heavy dependencies без объяснения.

Главный принцип:

Сделай мой `langgraph-agent-blueprint` похожим на Hermes Agent по ощущению скорости, автономности, памяти и качеству работы, но оставь его чистым, idiomatic, maintainable LangGraph-проектом.