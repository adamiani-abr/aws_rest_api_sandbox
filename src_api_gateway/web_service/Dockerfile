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

COPY app.py .
COPY aws_app_config/ ./aws_app_config
COPY templates ./templates
COPY static ./static

EXPOSE 5001

# * switch to non-root user
USER myuser

CMD ["python", "app.py"]
