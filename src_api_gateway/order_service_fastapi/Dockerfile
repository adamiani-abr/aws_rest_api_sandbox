FROM python:3.12-slim

# * Install redis-tools, telnet, iputils-ping, and dnsutils (for nslookup)
RUN apt-get update --fix-missing && \
    apt-get install -y redis-tools telnet iputils-ping dnsutils && \
    rm -rf /var/lib/apt/lists/*

# * non-root user for security
RUN useradd -m myuser

# * writes python output to ECS logs
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install uv
RUN uv pip install -r requirements.txt --system

COPY . .

EXPOSE 5003

# * switch to non-root user
USER myuser

# * Run using Uvicorn instead of Python
# * single worker so have consistent in memory-database of `ORDERS` - in PROD use multiple workers
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5003", "--proxy-headers", "--forwarded-allow-ips", "*"]
