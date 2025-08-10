# Техническая документация: MVP системы мониторинга уровня шума

## Введение

Этот документ описывает минимально жизнеспособный продукт (MVP) для мониторинга уровня фонового шума, созданный разработчиком. Проект реализован на Python, использует PostgreSQL для хранения данных RSSI, FastAPI для REST API и Docker для контейнеризации. Основной функционал: хранение измерений, вставка тестовых данных и GET-эндпоинт для получения превышений порога RSSI. Проект включает в себя  проектирование ТЗ, архитектуры, решения вопросов тестирования и готовность к масштабированию.

- Срок: 1 день. 
- Нагрузка: до 100 запросов/мин, 1 млн записей.
- Фокус: простота, надежность, расширяемость.

## Словарь терминов и сокращений

- **RSSI**: Индикатор силы сигнала (дБм, отрицательные значения; превышение — rssi > порога).
- **MVP**: Минимально жизнеспособный продукт.
- **REST API**: Интерфейс для обмена данными по HTTP.
- **PostgreSQL**: Реляционная СУБД с поддержкой асинхронных операций.
- **FastAPI**: Асинхронный веб-фреймворк Python.
- **SQLAlchemy**: ORM-библиотека для работы с БД.
- **Alembic**: Инструмент миграций БД.
- **Pydantic**: Валидация данных и модели.
- **Docker Compose**: Оркестрация контейнеров.
- **CI**: Непрерывная интеграция (GitHub Actions).
- **DI**: Инъекция зависимостей.
- **Ограничение запросов**: Защита от перегрузки API (slowapi).
- **ER-диаграмма**: Схема сущностей и связей.
- **dBm**: Децибел-милливатты, единица мощности.
- **fd_list**: Таблица устройств.
- **measurements**: Таблица измерений.
- **ISO 8601**: Формат дат (например, 2023-01-01T00:00:00Z).
- **Логирование**: Запись событий приложения.
- **Транзакция**: Атомарная операция в БД.

## Задание

**Цель**: Создать систему для хранения и анализа данных шума от устройств (id, частота в Гц, RSSI в дБм). Устройства в таблице `fd_list` (id, name, latitude, longitude).

**Требования** (ТЗ, составленное разработчиком):
- Нормализованная структура PostgreSQL для измерений.
- SQL-скрипт для вставки тестовых данных (3 устройства, 5+ измерений на каждое).
- Микросервис на Python с GET /api/noise-exceedances: возвращает время, имя устройства, частоты с rssi > порога.
- Параметры GET: start_datetime, end_datetime (ISO 8601), rssi_threshold (-100..0).
- Один запрос = один SELECT.
- Добавить: асинхронность, контейнеризацию, тесты, логи, миграции.

**Особенности**: Простая архитектура, высокая производительность, готовность к расширению (аналитика, интеграции).

## Решение

- **БД**: Две таблицы (`fd_list`, `measurements`) с FK, UNIQUE, индексами. Миграции через Alembic.
- **Данные**: `init_data.sql` вставляет тестовые данные в транзакции.
- **API**: FastAPI, асинхронный GET с валидацией (Pydantic). SELECT с JOIN, GROUP BY, array_agg.
- **Ошибки**: 400 (некорректные параметры), 503 (ошибка БД, retry x3), 200 (пустой список).
- **Тесты**: Unit (валидация), интеграционные (API+БД), >75% покрытие.
- **Логи**: Ротация по минутам, хранение 7 дней, асинхронный QueueHandler.
- **Контейнеры**: PostgreSQL, shared (модели, миграции), backend (API).

## Архитектура

**Компоненты**:
1. **PostgreSQL**: Persistent volume (/data/postgres). Хранит `fd_list`, `measurements`. Миграции через Alembic.
2. **Shared**: Модели (`models.py`), конфиг (`config_db.py`), миграции. Volume для backend.
3. **FastAPI Backend**: Асинхронный сервер (uvicorn). GET /api/noise-exceedances. DI для db, logger.

**ER-диаграмма**:
```
fd_list
- id: SERIAL PK
- name: VARCHAR(255) NOT NULL
- latitude: DECIMAL(9,6) NOT NULL
- longitude: DECIMAL(9,6) NOT NULL
  | (1:N)
measurements
- id: SERIAL PK
- device_id: INTEGER FK (fd_list.id, CASCADE) NOT NULL
- timestamp: TIMESTAMP TZ NOT NULL
- frequency: BIGINT NOT NULL
- rssi: INTEGER NOT NULL
- UNIQUE (device_id, timestamp, frequency)
- Indexes: BTREE(timestamp, device_id), BTREE(rssi)
```

**Поток**:
- Startup: Создание таблиц (`Base.metadata.create_all`), seeding (`init_data.sql` via aiofiles).
- Запрос: GET -> Pydantic -> Async SELECT -> JSON.
- Логи: /logs, cron (clean_logs.sh).

**Оптимизации**: Async sessions, pool (20+10), rate-limiting (100/min/IP).

## Преимущества

1. **Эффективность**:
   - Асинхронность (FastAPI, SQLAlchemy) минимизирует задержки.
   - Один SELECT с array_agg: минимум запросов к БД.
   - Индексы: быстрые фильтры по времени и RSSI.
   - Нормализация: экономия места, нет дубликатов.

2. **Масштабируемость**:
   - Docker scale (backend=2-4).
   - Готовность к nginx (load balancing).
   - Пул соединений: устойчивость к нагрузке.

3. **Надежность**:
   - Retry (x3) на ошибки БД.
   - Транзакции для seeding.
   - Тесты (>75%): валидация, edge-cases (пустой ответ, некорректные параметры).

4. **Безопасность**:
   - Pydantic: защита от инъекций.
   - Parameterized queries: SQL-инъекции исключены.
   - Rate-limiting: защита от DoS.

5. **Гибкость**:
   - Модульность: shared для новых сервисов.
   - Alembic: легкое изменение схемы.
   - DI: тестируемость, замена компонентов.

6. **SQLite в тестах**:
   - **Почему выбран**: Быстрый (in-memory, <1s), изолированный (чистая БД на тест), без внешнего сервера (упрощает CI). Проверяет логику API и валидацию, минимизируя зависимости.
   - Доказывает переносимость: код работает на SQLite и PostgreSQL, что упрощает поддержку MSSQL, ClickHouse.

7. **Простота эксплуатации**:
   - .env для конфигурации.
   - Скрипты: install.sh, start_prod.sh, run_tests.sh.
   - Чистый код: PEP8, type hints, Black.

**Суммарно**: Быстрая реализация, надежность, готовность к росту (аналитика, real-time), ТЗ, архитектура, тесты — всё спроектировано для качества и масштаба.

## Технологии

- **Язык**: Python 3.10+.
- **Backend**: FastAPI, Uvicorn.
- **БД**: PostgreSQL 14+, SQLAlchemy (async), Asyncpg, Alembic.
- **Валидация**: Pydantic.
- **Логи**: logging, TimedRotatingFileHandler, QueueHandler.
- **Тесты**: pytest, pytest-asyncio, aiosqlite (in-memory).
- **Безопасность**: slowapi (ограничение запросов).
- **Контейнеры**: Docker, Docker Compose.
- **DI**: FastAPI Depends.
- **Конфиг**: python-dotenv, aiofiles.
- **CI**: GitHub Actions.

**requirements.txt**: fastapi, uvicorn, sqlalchemy, asyncpg, pydantic, python-dotenv, pytest, slowapi, alembic, aiofiles, httpx, aiosqlite, pytest-asyncio.

## Установка

Предполагается: Docker, Docker Compose, .env (DB_URL, API_PORT=8000, LOG_LEVEL=INFO) уже есть.

1. Клонировать: `git clone <repo>`.
2. Проверить .env: DB_URL=postgresql+asyncpg://user:pass@postgres:5432/db.
3. Выполнить: `bash install.sh` (build, pip install).

## Запуск

- Dev: `bash start_dev.sh` (docker-compose up).
- Prod: `bash start_prod.sh` (up -d --scale backend=2).

API: http://localhost:8000/api/noise-exceedances.

## Остановка

`bash stop_prod.sh` (docker-compose down).

## Вход в контейнеры

- БД: `docker exec -it postgres psql -U user -d db`.
- Backend: `docker exec -it backend bash`.
- Shared: `docker exec -it shared bash`.

## Проверка логов

- Контейнер: `tail -f /logs/app.log`.
- Хост: `docker cp backend:/logs .`.
- Cron: `docker exec backend crontab -l` (0 0 * * * clean_logs.sh).

## Тесты

`bash run_tests.sh` (pytest в Docker). Покрытие: >75%. Проверки: валидация (422 на ошибки), API (ожидаемый JSON, сортировка частот), edge-cases (пустой ответ, future time).

## Ограничения

- Нагрузка: до 100 req/min, 1 млн записей.
- Нет аутентификации (добавить JWT).
- Нет real-time ввода данных.
- CI: только тесты, без автодеплоя.

## Масштабирование

- Docker: scale backend=4.
- Nginx: добавить для балансировки.
- БД: read replicas, партиции по timestamp.
- Кэш: Redis для частых запросов.
- Мониторинг: Prometheus, Grafana.

## Заключение

MVP решает задачу мониторинга шума с акцентом на качество, производительность и масштабируемость. SQLite в тестах упрощает разработку и подтверждает переносимость. Проект готов к production (с доработками: auth, CI/CD) и отвечает требовниям простоты, надежности. Имеет потенциал для развития и интеграций.