FROM python:3.9

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends \
 && pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt \
 && apt-get clean && rm -rf /var/lib/apt/lists/*


COPY . /app

EXPOSE 8501

ENTRYPOINT ["streamlit", "run"]

CMD ["app_v0.1.py"]
