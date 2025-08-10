# Используем slim-образ Python 3.10 для легковесности
FROM python:3.10-slim
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt

RUN export PYTHONPATH=/app/backend:$PYTHONPATH

# Настраиваем логирование 
# (удаление старых логов)

# Ставим cron для удаления старых логов
RUN apt-get update && apt-get install -y cron
# Копируем скрипт очистки 
COPY clean_logs.sh /app/clean_logs.sh  
# Делаем исполняемым
RUN chmod +x /app/clean_logs.sh 
# Копируем crontab
COPY crontab.txt /etc/cron.d/clean-logs 
# Права доступа 
RUN chmod 0644 /etc/cron.d/clean-logs 
# Устанавливаем задачу
RUN crontab /etc/cron.d/clean-logs

 # Запускаем cron в фоне и uvicorn
CMD ["bash", "-c", "cron && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"] 