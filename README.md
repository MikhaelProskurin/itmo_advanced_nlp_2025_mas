# CoffeeShopAnalystAsistant agent

Проект представляет из себя AI-агента (мульти-агентную систему / MAS ), облегчающую работу аналитику продукта, а именно, сети кофеен в Нью-Йорке.

Агент выполняет роль персонального ассистента, который помогает аналитику:
* Выполнять качественную ad-hoc аналитику быстрее
* Составлять эффективные sql-запросы к доступным данным.
* Извлекать данные из БД через текстовые инструкции.
* Составлять саммари результатов работы.


## Project Description

*   **stack** &rarr; langchain, langgraph, pydantic, sqlalchemy, asyncio
*   **Цель** &rarr; Снять часть нагрузки с аналитика продукта, повысить скорость ad-hoc анализа данных и выполнения небольших задач. 
*   **Функционал** &rarr; sql-generation, sql-explanation, sql-debugging, data-extraction, insights-extraction, report-summarization

```
root/
│
├── src/
│   ├── agent/            # Бизнес-логика ассистента, инструменты и утилиты       
│   ├── database/         # PostgreSQL менеджер и маппинги таблиц
│   ├── models/           # Pydantic модели для structured i/o, системные промпты, граф состояний
│   ├── example.ipynb     
│   └── app.py
│
├── requirements.txt
└── README.md
```

### Database

```
           ┌──────────────────────────┐
           │      stores_t            │
           │──────────────────────────│
           │ PK store_id (int)        │
           │    store_name (str)      │
           │    city (str)            │
           │    address (str)         │
           │    manager (str)         │
           └──────────┬───────────────┘
                      │
                      │ 1:N
                      │
┌─────────────────────▼────────────────┐
│        transactions_t                │
│──────────────────────────────────────│
│ PK transaction_id (int)              │
│    transaction_date (datetime)       │
│    transaction_time (time)           │
│    transaction_qty (int)             │
│ FK store_id (int) ───────────────────┤
│ FK product_id (int) ─────────────┐   │
│    unit_price (float)            │   │
└──────────────────────────────────┼───┘
                                   │
                                   │ N:1
                                   │
                      ┌────────────▼────────────┐
                      │      products_t         │
                      │─────────────────────────│
                      │ PK product_id (int)     │
                      │    product_name (str)   │
                      └──────────┬──────────────┘
                                 │
                                 │ 1:1
                                 │
                      ┌──────────▼──────────────┐
                      │     nutritions_t        │
                      │─────────────────────────│
                      │ PK product_id (int)     │
                      │    calories (int)       │
                      │    fat (int)            │
                      │    carb (int)           │
                      │    fiber (int)          │
                      │    sodium (int)         │
                      └─────────────────────────┘


┌──────────────────────────────────────┐
│  service__session_tracing_t          │
│──────────────────────────────────────│
│ PK session_id (uuid)                 │
│    session_history (array[json])     │
└──────────────────────────────────────┘
```

**Основные связи:**
- `transactions_t.store_id` → `stores_t.store_id` (N:1)
- `transactions_t.product_id` → `products_t.product_id` (N:1)
- `nutritions_t.product_id` → `products_t.product_id` (1:1)


### Agents

Система состоит из пяти специализированных агентов, координируемых через LangGraph:

*   **Router** &rarr; главный координатор системы. Анализирует запрос пользователя и текущее состояние графа, принимает решение о маршрутизации к следующему агенту. Создает пошаговый план (`routing_plan`) решения задачи и определяет необходимость извлечения данных из внешних источников (`user_data_file`).

*   **SQL Writer** &rarr; специализируется на генерации SQL-запросов. Принимает запрос пользователя и схему базы данных (`database_model`), генерирует оптимизированный SQL-запрос с детальным объяснением логики (`sql_explanation`). Обновляет состояние графа полями `sql` и `sql_explanation`.

*   **Insight Generator** &rarr; аналитик данных. Извлекает данные из PostgreSQL или пользовательских файлов, выполняет анализ и генерирует инсайты (`insights`). Может вызывать инструмент `search_postgres_database` или `read_provided_data` для получения данных перед анализом.

*   **Answer Summarizer** &rarr; финальный агент в пайплайне. Агрегирует результаты работы всех предыдущих агентов (SQL, объяснения, инсайты, данные) и формирует итоговый ответ пользователю (`answer`). Работает на основе всех артефактов в состоянии графа.

*   **Simple QA** &rarr; обрабатывает простые вопросы, не требующие работы с базой данных или сложной аналитики (например, общие вопросы о системе, приветствия). Завершает выполнение сразу с простым ответом.

### Tool Calling

Система предоставляет следующие инструмента для взаимодействия с данными и дополнительных возможностей:

*   **search_postgres_database** — асинхронный инструмент для выполнения SQL-запросов к PostgreSQL. Используется агентом **Insight Generator** для извлечения данных из базы.

*   **read_provided_data** — инструмент для чтения CSV-файлов, предоставленных пользователем. Вызывается агентом **Insight Generator** для анализа внешних данныхю.

*   **with_fallback** — вспомогательная утилита. Обеспечивает устойчивость выполнения chain с автоматическим переключением на fallback LLM при ошибках парсинга (`OutputParserException`). Используется всеми агентами для повышения надежности structured output.

### Memory Management

Система управления памятью реализована на трех уровнях:

*   **Graph State** - центральное хранилище состояния выполнения через `MultiAgentWorkflow` (TypedDict). Содержит:
    *   Входные данные: `request` (запрос пользователя)
    *   Артефакты агентов: `sql`, `sql_explanation`, `insights`, `queried_data`, `routing_plan`
    *   Метаданные: `routing_decision`, `user_data_file`
    *   Трейсинг: `interactions_history` (последовательность вызовов агентов), `reasoning_traces` (логи рассуждений)

*   **State Updates & Routing Logic** - каждый агент возвращает словарь обновлений, которые мерджатся в состояние графа через аннотации (`Annotated[list, operator.add]` для аккумулирующих полей). Функция `routing_gate` проверяет `interactions_history` для предотвращения циклов и форсирует переход к `answer_summarizer` при достижении `max_interactions_count` (защита от бесконечных итераций).

*   **Session Persistence** - после завершения сессии все состояние сериализуется в объект `SessionTracing` (uuid сессии + история взаимодействий с reasoning traces) и асинхронно дампится в PostgreSQL через `PostgresAlchemyManager.dump_object()`. Это обеспечивает:
    *   Трейсинг всех агентских решений для дебаггинга
    *   Возможность аудита и анализа сессий
    *   Накопление данных для дальнейшего улучшения промптов


## Usage

### Core requirements
*   Установленный [Python 3.10+](https://www.python.org/)
*   Перечень пакетов, описанных в requirements.txt проекта.

### Installation
1.  Клонируйте репозиторий:
    ```bash
    git clone https://github.com/MikhaelProskurin/itmo_advanced_nlp_2025.git
    cd <your_directory>
    ```

2.  Установите зависимости:
    ```bash
    pip install -r requirements.txt
    ```

3.  Настройте переменные окружения и инфраструктуру (при необходимости):
    *   Создайте файл ```.env```.
    *   Заполните необходимые ключи (LLM_API_KEY, BASE_URL, WEATHER_API_KEY) в созданном ```.env``` файле. 
    *   Создайте ```docker-compose.yaml```, заполните его и разверните инфраструктуру (PostgreSQL instance, etc.).

    Команда запуска сервисов

    ```bash
    docker-compose up -d --build
    ```

    Переменные окружения:

    ```python
    LLM_API_KEY=... # (typical api-key for llm access)
    BASE_URL=... # (endpoint of llm-inference-server)
    POSTGRES_USER=...# (personal user)
    POSTGRES_PASSWORD=...# (personal password)
    POSTGRES_DB=...# (database name)
    POSTGRES_HOST=...# (for example, localhost)
    POSTGRES_PORT=...# (mapped port to default 5432)
    POSTGRES_DSN=...# (asyncpg postgres dsn for better QoL)
    ```

4. Выполните развёртывание снапшота базы данных (при необходимости):
    *   Создайте физическую модель данных при помощи ```PostgresAlchemyManager```
    *   Добавьте данные в таблицы вручную или при помощи ```upload_database_snapshot()``` из ```src/agent/toolkit.py```


### Примеры использования

Примеры использования агента, а также рефлексия находятся в ```app.py``` и ```example.ipynb```
