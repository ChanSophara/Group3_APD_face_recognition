FROM python:3.10-slim

WORKDIR /workspace

# System dependencies (runtime + ML)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libpq-dev \
    libmagic1 \
    poppler-utils \
    curl \
    chromium \
    libx11-6 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libnss3 \
    libgtk-3-0 \
    libatk-bridge2.0-0 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

# VERY IMPORTANT: allow binary wheels
RUN pip install --upgrade pip setuptools wheel
RUN pip install --prefer-binary --no-cache-dir -r requirements.txt

COPY . .

RUN adduser --disabled-password --gecos '' --uid 1000 appuser
USER appuser

EXPOSE 5005

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5005"]
