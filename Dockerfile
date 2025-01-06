FROM python:3.9

WORKDIR /app

RUN apt-get update

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 8501

ENTRYPOINT ["streamlit", "run"]

CMD ["app_v0.1.py"]
