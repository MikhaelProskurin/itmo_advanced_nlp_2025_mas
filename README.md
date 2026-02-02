# KinoteatrRu recomendations agent

Проект представляет из себя AI-агента (мульти-агентную систему / MAS ), облегчающую работу аналитику продукта, а именно, сети кофеен в Нью-Йорке.

Агент выполняет роль персонального ассистента, который помогает аналитику:
* Выполнять качественную ad-hoc аналитику быстрее
* Составлять эффективные sql-запросы к доступным данным.
* Извлекать данные из БД через текстовые инструкции.
* Составлять саммари результатов работы.

## Project Description

*   **stack** -> langchain, langgraph, pydantic, sqlalchemy, asyncio
*   **Цель** -> Снять часть нагрузки с аналитика продукта, повысить скорость ad-hoc анализа данных и выполнения небольших задач. 
*   **Функционал** -> sql-generation, sql-explanation, sql-debugging, data-extraction, insights-extraction, report-summarization

```
root/
│
├── src/
│   ├── agent/            # Бизнес-логика агента, инструменты и утилиты       
│   ├── database/         # PostgreSQL менеджер и маппинги таблиц
│   ├── models/           # Pydantic модели для structured i/o, системные промпты, граф состояний
│   ├── example.ipynb     
│   └── app.py
│
├── requirements.txt
└── README.md
```

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
    *   Разверните инфраструктуру (PostgreSQL instance, etc.)

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
