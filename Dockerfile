FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY configs/ configs/
COPY data/sample/ data/sample/
COPY src/ src/
COPY tests/ tests/

ENTRYPOINT ["python", "-m", "src.benchmark", "--config", "configs/config.yaml"]
CMD ["--sample"]
