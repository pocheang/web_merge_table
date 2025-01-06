FROM python:3.9-slim


WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc \
 && pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt \
 && apt-get purge -y --auto-remove build-essential gcc \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

COPY . /app


RUN useradd --no-log-init --system --create-home appuser
USER appuser

EXPOSE 8501

ENTRYPOINT ["streamlit", "run"]

CMD ["app_v0.1.py"]
