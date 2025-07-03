
        FROM python:3.10-slim

        RUN apt-get update && apt-get install -y \
            git \
            libgl1-mesa-glx \
            libglib2.0-0 \
            libsm6 \
            libxext6 \
            libxrender-dev \
            libgomp1 \
            && pip install --no-cache-dir opencv-python numpy matplotlib pillow scikit-image \
            && apt-get clean \
            && rm -rf /var/lib/apt/lists/*

        WORKDIR /app

        COPY code/ /app/
        COPY input/ /input/
        VOLUME /output/

        CMD ["python", "main.py"]
        