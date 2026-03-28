FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

RUN apt update && apt install -y blender python3

WORKDIR /app
COPY worker.py .
RUN mkdir data
RUN mkdir data/jobs
RUN mkdir data/renders

CMD ["python3", "worker.py"]