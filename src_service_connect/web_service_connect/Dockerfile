FROM python:3.11

# Install redis-tools, telnet, iputils-ping, and dnsutils (for nslookup)
RUN apt-get update && \
    apt-get install -y redis-tools telnet iputils-ping dnsutils && \
    rm -rf /var/lib/apt/lists/*

# non-root user for security
RUN useradd -m myuser

WORKDIR /app

COPY requirements.txt .

RUN pip install uv
RUN uv pip install -r requirements.txt --system

COPY app.py .

EXPOSE 5001

# switch to non-root user
USER myuser

CMD ["python", "app.py"]
