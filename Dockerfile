FROM python:3.9

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 8501

ENTRYPOINT ["streamlit", "run"]

CMD ["app_v0.1.py"]
