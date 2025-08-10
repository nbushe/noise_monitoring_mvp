#####################################################
# Это основной файл бекенда
#####################################################

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Request
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import List
import os
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import aiofiles
import logging
from logging.handlers import TimedRotatingFileHandler

from shared.models import Base, Measurements, FDList
from shared.config_db import engine, async_session


# Получаем конфигурацию из .env
if not Path("./.env").exists():
    raise FileNotFoundError(
        "Please create .env file in the root directory of the project"
    )

load_dotenv()

# Создаем экземпляр FastAPI
app = FastAPI()

# Ограничиваем количество запросов в минуту
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Настраивае CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Определяем типы данных для валидации
class QueryParams(BaseModel):
    start_datetime: datetime = Field(..., description="Start timestamp in ISO 8601")
    end_datetime: datetime = Field(..., description="End timestamp in ISO 8601")
    rssi_threshold: int = Field(..., ge=-100, le=0, description="RSSI threshold")

    @field_validator("end_datetime")
    def validate_dates(cls, v: datetime, info) -> datetime:
        if "start_datetime" in info.data and v < info.data["start_datetime"]:
            raise ValueError("end_datetime must be after start_datetime")
        return v


class ExceedanceResponse(BaseModel):
    timestamp: str
    device_name: str
    frequencies: List[int]


# Внедряем зависимость (сессию) в FastApi
async def get_db():
    async with async_session() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            raise HTTPException(status_code=503, detail="Database error") from e


# Логируем все операции в бекенде - настройка хэндлера для ротации
# Используем TimedRotatingFileHandler: ротация каждую минуту, храним 10080 файлов (7 дней * 1440 мин)
# Формат логов: timestamp, уровень, модуль, сообщение
def configure_logging():
    logger = logging.getLogger(__name__)

    # Получаем уровень логирования из переменных окружения или используем значение по умолчанию
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logger.setLevel(log_level)

    # Получаем конфигурацию логирования из переменных окружения или используем значения по умолчанию
    log_path = os.getenv("LOG_PATH", "/logs")
    log_filename = os.getenv("LOG_FILENAME", "app.log")
    full_log_path = os.path.join(log_path, log_filename)

    # Создаем директорию для логов, если она не существует
    try:
        os.makedirs(log_path, exist_ok=True)
    except PermissionError:
        # Если нет прав на запись в папку логов, то используем текущую директорию
        log_path = "./logs"
        full_log_path = os.path.join(log_path, log_filename)
        os.makedirs(log_path, exist_ok=True)

    # Настраиваем хэндлер с параметрами из переменных окружения или значениями по умолчанию
    handler = TimedRotatingFileHandler(
        filename=full_log_path,
        when=os.getenv("LOG_WHEN", "M"),  # По умолчанию: ротация по минутам
        interval=int(os.getenv("LOG_INTERVAL", "1")),  # По умолчанию: каждую минуту
        backupCount=int(
            os.getenv("LOG_BACKUP_COUNT", "10080")
        ),  # По умолчанию: храним логи за неделю
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(module)s - %(message)s")
    )
    logger.addHandler(handler)
    return logger


# Зависимость для инъекции логгера - DI, чтоб легко тестировать и менять
async def get_logger():
    return configure_logging()  # Конфигурим при каждом вызове, но в реале кэшировать

@app.on_event("startup")
async def startup_event():
    logger = await get_logger()
    logger.info("Приложение стартует")
    max_retries = 5
    retry_interval = 5
    for i in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Таблицы созданы")
            async with async_session() as session:
                stmt_check = select(func.count()).select_from(FDList)
                result = await session.execute(stmt_check)
                count = result.scalar_one()
                if count == 0:
                    logger.info("БД пустая - выполняем сидирование")
                    async with aiofiles.open('/app/db/init_data.sql', mode='r') as f:
                        sql_script = await f.read()
                    statements = sql_script.split(';')
                    for statement in statements:
                        if statement.strip():
                            await session.execute(text(statement))
                    await session.commit()
                    logger.info("Сидирование завершено")
            break
        except Exception as e:
            if i == max_retries - 1:
                logger.error(f"Не удалось подключиться к БД после {max_retries} попыток: {str(e)}")
                raise
            logger.warning(f"Попытка {i+1} не удалась, повтор через {retry_interval} сек: {str(e)}")
            await sleep(retry_interval)

# Почему-то с lifespan таблицы не создаются (?)

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     logger = configure_logging()
#     logger.info("Приложение стартует - создаем таблицы и сидируем данные")

#     # Ждем пока БД будет готова
#     max_retries = 5
#     retry_interval = 5
#     for i in range(max_retries):
#         try:
#             async with engine.begin() as conn:
#                 await conn.run_sync(Base.metadata.create_all)
#             break
#         except Exception as e:
#             if i == max_retries - 1:
#                 logger.error(
#                     f"Не удалось подключиться к БД после {max_retries} попыток"
#                 )
#                 raise
#             logger.warning(
#                 f"Попытка {i+1} не удалась, повтор через {retry_interval} сек..."
#             )
#             await asyncio.sleep(retry_interval)

#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)

#     async with async_session() as session:
#         stmt_check = select(func.count()).select_from(FDList)
#         result = await session.execute(stmt_check)
#         count = result.scalar_one()
#         if count == 0:
#             logger.info("БД пустая - выполняем сидирование из SQL скрипта")
#             async with aiofiles.open("/app/db/init_data.sql", mode="r") as f:
#                 sql_script = await f.read()
#             statements = sql_script.split(";")
#             for statement in statements:
#                 if statement.strip():
#                     await session.execute(text(statement))
#             await session.commit()
#             logger.info("Сидирование завершено успешно")
#     yield


# app.lifespan = lifespan


# Наш endpoint
@app.get("/api/noise-exceedances", response_model=List[ExceedanceResponse])
@limiter.limit("100/minute")
async def get_exceedances(
    request: Request,
    params: QueryParams = Depends(),
    db: AsyncSession = Depends(get_db),
    logger: logging.Logger = Depends(get_logger),
):
    logger.info(f"Получен запрос: {params.model_dump()} от {request.client.host}")

    try:
        dialect = db.bind.dialect.name
        is_sqlite = dialect == "sqlite"

        if is_sqlite:
            agg_func = func.group_concat(Measurements.frequency)
        else:
            agg_func = func.array_agg(Measurements.frequency)

        stmt = (
            select(
                Measurements.timestamp,
                FDList.name,
                agg_func.label("frequencies"),
            )
            .join(FDList, Measurements.device_id == FDList.id)
            .where(
                Measurements.timestamp.between(
                    params.start_datetime, params.end_datetime
                ),
                Measurements.rssi > params.rssi_threshold,
            )
            .group_by(Measurements.timestamp, FDList.name)
            .having(func.count(Measurements.frequency) > 0)
        )

        result = await db.execute(stmt)
        rows = result.fetchall()

        response = []
        for row in rows:
            if is_sqlite:
                frequencies = (
                    [int(f) for f in row.frequencies.split(",")]
                    if row.frequencies
                    else []
                )
            else:
                frequencies = row.frequencies or []
            response.append(
                ExceedanceResponse(
                    timestamp=row.timestamp.isoformat(),
                    device_name=row.name,
                    frequencies=frequencies,
                )
            )
        logger.info(f"Запрос выполнен успешно, возвращено {len(response)} записей")
        return response
    except Exception as e:
        logger.error(f"Ошибка при выполнении запроса: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# @app.get("/api/noise-exceedances", response_model=List[ExceedanceResponse])
# @limiter.limit("100/minute")
# async def get_exceedances(
#     request: Request,
#     params: QueryParams = Depends(),
#     db: AsyncSession = Depends(get_db),
#     logger: logging.Logger = Depends(get_logger),  # Инъектируем логгер через DI
# ):
#     logger.info(f"Получен запрос: {params.dict()} от {request.client.host}")

#     # Вот, собственно, требуемый SELECT
#     try:
#         stmt = (
#             select(
#                 Measurements.timestamp,
#                 FDList.name,
#                 func.array_agg(Measurements.frequency).label("frequencies"), # Поле в group не входит => аггрегируем его
#             )
#             .join(FDList, Measurements.device_id == FDList.id)
#             .where(
#                 Measurements.timestamp.between(
#                     params.start_datetime, params.end_datetime
#                 ),
#                 Measurements.rssi > params.rssi_threshold,
#             )
#             .group_by(Measurements.timestamp, FDList.name)
#             .having(func.count(Measurements.frequency) > 0)
#         )

#         result = await db.execute(stmt)
#         rows = result.fetchall()

#         response = [
#             ExceedanceResponse(
#                 timestamp=row.timestamp.isoformat(),
#                 device_name=row.name,
#                 frequencies=row.frequencies,
#             )
#             for row in rows
#         ]
#         logger.info(f"Запрос выполнен успешно, возвращено {len(response)} записей")
#         return response
#     except Exception as e:
#         logger.error(f"Ошибка при выполнении запроса: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e)) from e
