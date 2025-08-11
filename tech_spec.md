Техническое Задание (ТЗ) на Разработку Минимально Жизнеспособного Продукта (MVP) для Системы Мониторинга Уровня Фонового Шума
1. Общая Информация
1.1. Название Проекта
Система Мониторинга Уровня Фонового Шума (Noise Monitoring System MVP).
1.2. Цель Проекта
Разработать минимально жизнеспособный продукт (MVP) на Python, предназначенный для хранения данных об уровнях фонового шума (RSSI) от устройств, их обработки и предоставления через REST API. MVP включает проектирование структуры базы данных PostgreSQL, вставку тестовых данных и создание микросервиса с единственным GET-эндпоинтом для извлечения информации о превышениях порога RSSI. 
MVP ориентирован на быструю реализацию в срок 1 день, с фокусом на основных функциях и возможностями для дальнейшего развития.
1.3. Область Применения
    • Хранение измерений RSSI от устройств, описанных в таблице fd_list. 
    • Извлечение данных о превышениях порога RSSI в заданном временном интервале через API с использованием единственного SQL-запроса. 
    • Использование в качестве базы для расширения, такого как интеграция с внешними источниками данных или аналитика. 
1.4. Требования к Окружению
    • Операционная система: Linux Ubuntu (версия 20.04 или выше). 
    • Контейнеризация: Docker и Docker Compose. 
    • Языки и Фреймворки: Python 3.10+, FastAPI (для backend), SQLAlchemy (ORM с async поддержкой). 
    • База Данных: PostgreSQL 14+. 
    • Дополнительные Инструменты: .env для конфигурации, Alembic для миграций, pytest для тестов, logging с ротацией файлов, Pydantic для валидации. 
    • Репозиторий: Git, с настройкой для GitHub Actions (базовый CI для тестов). 
1.5. Ограничения и Предположения
    • MVP ориентирован на умеренную нагрузку (до 100 запросов в минуту, объем данных до 1 миллиона записей); оптимизации включают индексацию, асинхронность и пул соединений. 
    • Упрощенная архитектура: 3 Docker-контейнера (БД, общие модули, backend). 
    • Структура БД определяется в одном файле для простоты изменений. 
    • Доменные аспекты: RSSI в dBm (отрицательные значения; превышение порога как rssi > threshold, где более высокое значение указывает на более сильный сигнал). 
    • Срок реализации: 1 день, с приоритетом на основные функции; дополнительные функции указаны как пути развития. 
2. Функциональные Требования
2.1. Архитектура Проекта
Проект состоит из 3 Docker-контейнеров:
    1. PostgreSQL: Persistent volume в /data/postgres. 
    2. Shared Library: SQLAlchemy модели, миграции; shared volume для backend. 
    3. FastAPI Backend: REST API с асинхронными эндпоинтами. 
Оркестрация через Docker Compose. Масштабируемость: Поддержка scale=2-4 для backend.
2.2. Структура Базы Данных
    • Конфигурация: В файле config_db.py (загружает параметры из .env, такие как DB_URL). 
    • Нормализованная схема: 
        ◦ fd_list: 
            ▪ id: SERIAL PRIMARY KEY. 
            ▪ name: VARCHAR(255) NOT NULL. 
            ▪ latitude: DECIMAL(9,6) NOT NULL. 
            ▪ longitude: DECIMAL(9,6) NOT NULL. 
        ◦ measurements: 
            ▪ id: SERIAL PRIMARY KEY. 
            ▪ device_id: INTEGER NOT NULL REFERENCES fd_list(id) ON DELETE CASCADE. 
            ▪ timestamp: TIMESTAMP WITH TIME ZONE NOT NULL. 
            ▪ frequency: BIGINT NOT NULL. 
            ▪ rssi: INTEGER NOT NULL. 
            ▪ UNIQUE (device_id, timestamp, frequency). 
    • Индексация и Оптимизация: 
      sql
    • ER-диаграмма (текстовое представление): 
      text
    • Инициализация: Alembic миграции; автоматический create_all() с проверкой в общих модулях. 
2.3. Вставка Тестовых Данных
    • SQL-скрипт (init_data.sql, выполняется в Docker entrypoint): 
      sql
    • Выполнение: В транзакции; проверка на существование таблиц. 
2.4. Backend (FastAPI)
    • Эндпоинт: GET /api/noise-exceedances. 
    • Параметры (query): start_datetime (str, ISO 8601), end_datetime (str, ISO 8601), rssi_threshold (int, -100..0). 
    • Схемы Данных (Pydantic): 
        ◦ QueryParams: 
          python
        ◦ Response Model: 
          python
    • Алгоритм: 
        ◦ Валидация: Pydantic; проверка start < end. 
        ◦ SELECT (единственный, асинхронный): 
          python
        ◦ Возврат: List[ExceedanceResponse] в JSON. 
    • Примеры: 
        ◦ Запрос: /api/noise-exceedances?start_datetime=2023-01-01T00:00:00Z&end_datetime=2023-01-01T00:05:00Z&rssi_threshold=-60 
        ◦ Ответ: [{"timestamp": "2023-01-01T00:00:00+00:00", "device_name": "DeviceA", "frequencies": [2400000000]}] 
2.5. Обработка Ошибок
    • Глобально: Middleware для catch Exception; возврат {"error": "description", "code": HTTP статус}. 
    • Сценарии: 
        ◦ Invalid params: 400 Bad Request. 
        ◦ DB disconnect: 503 Service Unavailable с retry (3 попытки). 
        ◦ Empty result: 200 OK с пустым списком. 
    • Классификация: Операционные (валидация) — пользовательские сообщения; Системные (DB) — логирование и retry. 
2.6. Тестирование
    • Unit: Валидация params, query building (mocks). 
        ◦ Пример: 
          python
    • Интеграционные: API -> БД (тестовая БД в Docker). 
        ◦ Пример: Тест на exceedances с тестовыми данными; coverage >75%. 
    • Запуск: run_tests
2.7. Логирование
    • TimedRotatingFileHandler (ротация/мин, хранение 10080 файлов). 
    • Cron в контейнере: find /logs -mtime +7 -delete. 
    • Асинхронное: QueueHandler. 
2.8. Конфигурация и Развертывание
    • .env: DB_URL, API_PORT=8000, LOG_LEVEL=INFO. 
    • Скрипты: install.sh (Docker/Python), start_prod (up -d --scale backend=2), start_dev (up), run_tests , stop_prod, build (build + dev)
    • CI: GitHub Actions workflow для тестов на push. 
3. Нефункциональные Требования
3.1. Производительность
    • Асинхронность: Async SQLAlchemy sessions. 
    • Пул: pool_size=20, max_overflow=10. 
    • Метрики: <500ms на запрос при 1 млн записей. 
3.2. Безопасность
    • Parameterized queries. 
    • Rate-limiting: slowapi, 100 req/min/IP. 
3.3. Масштабируемость
    • Docker scale; hooks для Prometheus. 
3.4. Документация
    • README.md: Установка, запуск. 
    • user_guide.md: API примеры. 
    • Docstrings: В коде. 
3.5. Качество Кода
    • PEP8, type hints, Black форматирование. 
    • Conventional commits. 
