-- Metadata database for the optional Airflow service (docker compose profile "airflow").
SELECT 'CREATE DATABASE airflow'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow')\gexec
