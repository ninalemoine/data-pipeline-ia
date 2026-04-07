FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y cron && mkdir -p /app/data

COPY app/ /app/
COPY crontab.sh /etc/cron.d/data-pipeline-cron

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN chmod +x /etc/cron.d/data-pipeline-cron
RUN crontab /etc/cron.d/data-pipeline-cron

CMD ["cron", "-f"]
