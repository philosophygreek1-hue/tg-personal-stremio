FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" motor pymongo pyrofork TgCrypto python-dotenv pydantic httpx aiofiles jinja2 python-multipart
RUN chmod +x start.sh
EXPOSE 8000
CMD ["python3", "-m", "Backend"]
