"""Airflow DAGs for the PGA Tour ETL.

SCAFFOLD: wiring is in place; revisit schedules, retries and alerting once the
ETL is stable.

* ``golf_etl_incremental`` - daily refresh of players + current-season stats
* ``golf_etl_backfill``    - manual trigger; optional params ``seasons`` and
  ``force`` (e.g. {"seasons": [2024, 2025], "force": true})

The ETL runs in its own virtualenv (see docker/airflow.Dockerfile) because
Airflow 2.x pins SQLAlchemy<2.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow.models.param import Param
from airflow.operators.bash import BashOperator

from airflow import DAG

PYTHON = "/opt/airflow/etl-venv/bin/python"
ETL_DIR = "/opt/airflow/etl"

default_args = {
    "owner": "bryce",
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}

with DAG(
    dag_id="golf_etl_incremental",
    description="Daily incremental load: players + current season stats",
    start_date=datetime(2026, 1, 1),
    schedule="0 8 * * *",  # 08:00 UTC daily
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["golf", "etl"],
) as incremental_dag:
    BashOperator(
        task_id="run_incremental_etl",
        bash_command=f"cd {ETL_DIR} && {PYTHON} full_pipeline.py --mode incremental",
    )

with DAG(
    dag_id="golf_etl_backfill",
    description="Manual backfill of historical seasons",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    params={
        "seasons": Param([], type="array", description="Empty = last 4 seasons"),
        "force": Param(False, type="boolean"),
    },
    tags=["golf", "etl"],
) as backfill_dag:
    BashOperator(
        task_id="run_backfill_etl",
        bash_command=(
            f"cd {ETL_DIR} && {PYTHON} full_pipeline.py --mode backfill "
            "{% if params.seasons %}--seasons {{ params.seasons | join(' ') }} {% endif %}"
            "{% if params.force %}--force{% endif %}"
        ),
    )
