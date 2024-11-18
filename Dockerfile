# Use the official Python 3.12 image as a base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# Set working directory
WORKDIR /app

# Copy application code
COPY . /app

# Install dependencies
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Expose a port (optional, for debugging or monitoring)
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]
