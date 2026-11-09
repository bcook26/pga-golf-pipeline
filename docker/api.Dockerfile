FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" "sqlalchemy>=2.0" \
      "psycopg[binary]>=3.3" python-dotenv
COPY backend/app ./app

RUN useradd --create-home api
USER api
EXPOSE 8000
# Hosts such as Render provide the port in $PORT.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
