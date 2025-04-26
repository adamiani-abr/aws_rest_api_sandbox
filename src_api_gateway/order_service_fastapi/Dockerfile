FROM python:3.13-slim

# Install redis-tools, telnet, iputils-ping, and dnsutils (for nslookup)
RUN apt-get update && \
    apt-get install -y redis-tools telnet iputils-ping dnsutils && \
    rm -rf /var/lib/apt/lists/*

# non-root user for security
RUN useradd -m myuser

# writes python output to ECS logs
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install uv
RUN uv pip install -r requirements.txt --system

COPY app.py .
COPY aws_app_config/ ./aws_app_config

EXPOSE 5003

# switch to non-root user
USER myuser

# Run using Uvicorn instead of Python
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5003", "--workers", "4", "--proxy-headers", "--forwarded-allow-ips", "*"]
