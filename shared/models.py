from sqlalchemy import Column, Integer, String, Float, BigInteger, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship, declarative_base
from datetime import timezone

# Модель базы данных

Base = declarative_base()

# Список устройств 
class FDList(Base):
    __tablename__ = "fd_list" 
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

# Измерения
class Measurements(Base):
    __tablename__ = "measurements"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("fd_list.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    frequency = Column(BigInteger, nullable=False)
    rssi = Column(Integer, nullable=False)
    device = relationship("FDList", back_populates="measurements")

# Связи между устройствами и измерениями
FDList.measurements = relationship("Measurements", back_populates="device")
