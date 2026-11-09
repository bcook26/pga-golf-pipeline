FROM apache/airflow:2.10.5-python3.12

# Airflow 2.x pins SQLAlchemy<2, but the ETL uses SQLAlchemy 2. Isolate the ETL
# dependencies in their own virtualenv and call it from the DAG.
RUN python -m venv /opt/airflow/etl-venv \
 && /opt/airflow/etl-venv/bin/pip install --no-cache-dir \
      requests beautifulsoup4 pandas numpy tqdm "sqlalchemy>=2.0" \
      python-dotenv "psycopg[binary]>=3.3" redis
