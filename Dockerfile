FROM python:3.9-slim


WORKDIR /app

COPY requirements.txt /app/
COPY app_v0.1.py /app/
COPY static/ /app/static/
COPY templates/ /app/templates/
COPY config.yaml /app/

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc \
 && pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt \
 && apt-get purge -y --auto-remove build-essential gcc \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*




RUN useradd --no-log-init --system --create-home appuser
USER appuser

EXPOSE 8501

ENTRYPOINT ["streamlit", "run"]

CMD ["app_v0.1.py"]
