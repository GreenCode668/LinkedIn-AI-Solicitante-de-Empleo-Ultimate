# Use the official Python 3.12.10 image as the base
FROM python:3.12.10-slim

# Set environment variables to prevent Python from writing bytecode and buffering output
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies for Playwright browsers and Python packages
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    tzdata \
    linux-headers-generic \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set timezone
ENV TZ=Europe/Moscow
RUN cp /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Set the working directory
WORKDIR /app

# Copy Python dependencies first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium)
RUN playwright install chromium

# Copy application code
COPY config config
COPY src src
COPY main.py .

# Copy .env file if it exists (optional, can be mounted as volume)
COPY .env* ./

# Create necessary directories for data persistence
RUN mkdir -p data/resumes data/output data/cover_letters browser_session logs

# Run the application
CMD ["python3", "main.py"]
