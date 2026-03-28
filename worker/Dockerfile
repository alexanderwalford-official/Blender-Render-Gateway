FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

RUN apt update && apt install -y python3 python3-pip wget xz-utils \
    libxrender1 libxi6 libxkbcommon0 libsm6 libgl1 \
    libegl1 libegl-mesa0 libgles2

# Install Blender 5.1 to match host version
RUN wget https://download.blender.org/release/Blender5.1/blender-5.1.0-linux-x64.tar.xz \
    && tar -xf blender-5.1.0-linux-x64.tar.xz -C /opt/ \
    && ln -s /opt/blender-5.1.0-linux-x64/blender /usr/local/bin/blender \
    && rm blender-5.1.0-linux-x64.tar.xz

COPY requirements.txt .
RUN pip3 install -r requirements.txt

WORKDIR /app
COPY worker.py .

ENTRYPOINT ["python3", "worker.py"]