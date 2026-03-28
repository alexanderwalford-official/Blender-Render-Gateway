FROM python:3.11

WORKDIR /app
COPY app.py .

COPY requirements.txt .
RUN pip3 install -r requirements.txt

RUN pip install fastapi uvicorn python-multipart

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]