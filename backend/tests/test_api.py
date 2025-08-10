#####################################################
# Тесты бекенда
#####################################################

import pytest
from fastapi.testclient import TestClient
from main import app, get_db
from shared.models import Base, FDList, Measurements
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

# Создаем тестовую базу данных в памяти
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

# Создаем движок и сессию
test_engine = create_async_engine(TEST_DB_URL)
async_session_for_tests = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


# Переопределяем зависимость для тестирования
async def override_get_db():
    session = async_session_for_tests()
    try:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        # Добавляем тестовые данные, аналогичные предоставленному примеру
        device_a = FDList(id=1, name="DeviceA", latitude=55.7558, longitude=37.6173)
        device_b = FDList(id=2, name="DeviceB", latitude=40.7128, longitude=-74.0060)
        device_c = FDList(id=3, name="DeviceC", latitude=51.5074, longitude=-0.1278)
        session.add_all([device_a, device_b, device_c])
        await session.commit()

        # Тестовые данные для измерений, соответствующие предоставленному ответу
        timestamp1 = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
        timestamp2 = datetime(2023, 1, 1, 0, 1, tzinfo=timezone.utc)
        timestamp3 = datetime(2023, 1, 1, 0, 2, tzinfo=timezone.utc)
        timestamp4 = datetime(2023, 1, 1, 0, 3, tzinfo=timezone.utc)
        timestamp5 = datetime(2023, 1, 1, 0, 4, tzinfo=timezone.utc)
        timestamp6 = datetime(2023, 1, 1, 0, 5, tzinfo=timezone.utc)

        measurements = [
            # DeviceA
            Measurements(
                device_id=1, timestamp=timestamp1, frequency=2400000000, rssi=-40
            ),
            Measurements(
                device_id=1, timestamp=timestamp2, frequency=2400000000, rssi=-45
            ),
            Measurements(
                device_id=1, timestamp=timestamp2, frequency=900000000, rssi=-30
            ),
            Measurements(
                device_id=1, timestamp=timestamp3, frequency=2400000000, rssi=-48
            ),
            Measurements(
                device_id=1, timestamp=timestamp4, frequency=5800000000, rssi=-35
            ),
            Measurements(
                device_id=1, timestamp=timestamp4, frequency=2400000000, rssi=-42
            ),
            Measurements(
                device_id=1, timestamp=timestamp5, frequency=2400000000, rssi=-49
            ),
            # DeviceB
            Measurements(
                device_id=2, timestamp=timestamp6, frequency=2400000000, rssi=-47
            ),
            # DeviceC (без превышений для порога -50)
            Measurements(
                device_id=3, timestamp=timestamp1, frequency=2400000000, rssi=-60
            ),
        ]
        session.add_all(measurements)
        await session.commit()
        yield session
    finally:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await session.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


# Тест валидации некорректного формата даты
def test_validate_invalid_datetime():
    response = client.get(
        "/api/noise-exceedances?start_datetime=invalid&end_datetime=2023-01-01T00:00:00Z&rssi_threshold=-50"
    )
    assert response.status_code == 422
    assert "Input should be a valid datetime" in response.json().get("detail", [{}])[
        0
    ].get("msg", "")


# Тест валидации, когда начальная дата позже конечной
def test_validate_start_after_end():
    error = ""
    try:
        response = client.get(
            "/api/noise-exceedances?start_datetime=2023-01-01T00:05:00Z&end_datetime=2023-01-01T00:00:00Z&rssi_threshold=-50"
        )
    except Exception as e:
        error = e
    assert "end_datetime must be after start_datetime" in str(error)


# Тест валидации некорректного значения RSSI (выше 0)
def test_validate_rssi_above_zero():
    response = client.get(
        "/api/noise-exceedances?start_datetime=2023-01-01T00:00:00Z&end_datetime=2023-01-01T00:05:00Z&rssi_threshold=10"
    )
    assert response.status_code == 422
    assert "Input should be less than or equal to 0" in response.json().get(
        "detail", [{}]
    )[0].get("msg", "")


# Тест валидации некорректного значения RSSI (ниже -100)
def test_validate_rssi_below_minus_100():
    response = client.get(
        "/api/noise-exceedances?start_datetime=2023-01-01T00:00:00Z&end_datetime=2023-01-01T00:05:00Z&rssi_threshold=-101"
    )
    assert response.status_code == 422
    assert "Input should be greater than or equal to -100" in response.json().get(
        "detail", [{}]
    )[0].get("msg", "")


# Тест валидации отсутствия обязательного параметра
def test_validate_missing_rssi_threshold():
    response = client.get(
        "/api/noise-exceedances?start_datetime=2023-01-01T00:00:00Z&end_datetime=2023-01-01T00:05:00Z"
    )
    assert response.status_code == 422
    assert "Field required" in response.json().get("detail", [{}])[0].get("msg", "")


# Тест получения данных о превышениях для предоставленного примера
def test_get_exceedances_example():
    response = client.get(
        "/api/noise-exceedances?start_datetime=2023-01-01T00:00:00Z&end_datetime=2023-01-01T00:05:00Z&rssi_threshold=-50"
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Нормализуем данные: сортируем частоты и сам список
    for item in data:
        item["frequencies"] = sorted(item["frequencies"])
    data = sorted(data, key=lambda x: (x["timestamp"], x["device_name"]))

    expected = [
        {
            "timestamp": "2023-01-01T00:00:00",
            "device_name": "DeviceA",
            "frequencies": [2400000000],
        },
        {
            "timestamp": "2023-01-01T00:01:00",
            "device_name": "DeviceA",
            "frequencies": [900000000, 2400000000],
        },
        {
            "timestamp": "2023-01-01T00:02:00",
            "device_name": "DeviceA",
            "frequencies": [2400000000],
        },
        {
            "timestamp": "2023-01-01T00:03:00",
            "device_name": "DeviceA",
            "frequencies": [2400000000, 5800000000],
        },
        {
            "timestamp": "2023-01-01T00:04:00",
            "device_name": "DeviceA",
            "frequencies": [2400000000],
        },
        {
            "timestamp": "2023-01-01T00:05:00",
            "device_name": "DeviceB",
            "frequencies": [2400000000],
        },
    ]

    assert data == expected


# Тест получения данных с более высоким порогом RSSI
def test_get_exceedances_higher_threshold():
    response = client.get(
        "/api/noise-exceedances?start_datetime=2023-01-01T00:00:00Z&end_datetime=2023-01-01T00:05:00Z&rssi_threshold=-40"
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    for item in data:
        item["frequencies"] = sorted(item["frequencies"])
    data = sorted(data, key=lambda x: (x["timestamp"], x["device_name"]))

    expected = [
        {
            "timestamp": "2023-01-01T00:01:00",
            "device_name": "DeviceA",
            "frequencies": [900000000],
        },
        {
            "timestamp": "2023-01-01T00:03:00",
            "device_name": "DeviceA",
            "frequencies": [5800000000],
        },
    ]

    assert data == sorted(expected, key=lambda x: (x["timestamp"], x["device_name"]))


# Тест получения данных для другого временного диапазона
def test_get_exceedances_different_time_range():
    response = client.get(
        "/api/noise-exceedances?start_datetime=2023-01-01T00:01:00Z&end_datetime=2023-01-01T00:03:00Z&rssi_threshold=-50"
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    for item in data:
        item["frequencies"] = sorted(item["frequencies"])
    data = sorted(data, key=lambda x: (x["timestamp"], x["device_name"]))

    expected = [
        {
            "timestamp": "2023-01-01T00:01:00",
            "device_name": "DeviceA",
            "frequencies": [900000000, 2400000000],
        },
        {
            "timestamp": "2023-01-01T00:02:00",
            "device_name": "DeviceA",
            "frequencies": [2400000000],
        },
        {
            "timestamp": "2023-01-01T00:03:00",
            "device_name": "DeviceA",
            "frequencies": [2400000000, 5800000000],
        },
    ]

    assert data == expected


# Тест получения пустого результата для будущего времени
def test_get_exceedances_future_time():
    response = client.get(
        "/api/noise-exceedances?start_datetime=2024-01-01T00:00:00Z&end_datetime=2024-01-01T00:05:00Z&rssi_threshold=-50"
    )
    assert response.status_code == 200
    assert len(response.json()) == 0


# Тест для проверки обработки нескольких частот в одном временном слоте
def test_get_exceedances_multiple_frequencies():
    response = client.get(
        "/api/noise-exceedances?start_datetime=2023-01-01T00:03:00Z&end_datetime=2023-01-01T00:03:00Z&rssi_threshold=-50"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1

    # Проверяем основные поля
    assert data[0]["timestamp"] == "2023-01-01T00:03:00"
    assert data[0]["device_name"] == "DeviceA"

    # Проверяем частоты независимо от порядка
    assert sorted(data[0]["frequencies"]) == [2400000000, 5800000000]
