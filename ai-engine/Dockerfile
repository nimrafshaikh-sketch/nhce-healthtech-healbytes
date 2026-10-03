FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt requirements-dev.txt* ./
RUN pip install --no-cache-dir -r requirements.txt && \
    if [ -f "requirements-dev.txt" ]; then pip install --no-cache-dir -r requirements-dev.txt; fi
COPY . .
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
