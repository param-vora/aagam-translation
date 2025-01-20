# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the application files
COPY . .

# Expose the port Streamlit will run on
EXPOSE 8080

# Command to run the application
CMD streamlit run --server.port 8080 --server.address 0.0.0.0 v1_translation_dashboard.py