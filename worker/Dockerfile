FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

RUN apt update && apt install -y blender python3 python3-pip

COPY requirements.txt .
RUN pip3 install -r requirements.txt

WORKDIR /app
COPY worker.py .

CMD ["python3", "worker.py"]