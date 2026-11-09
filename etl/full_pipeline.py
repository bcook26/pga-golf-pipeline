import time

from pipeline.players import run_players_pipeline
from pipeline.stats import run_stats_pipeline


def main():
    YEAR = 2026

    pipeline_start = time.perf_counter()

    players_df = run_players_pipeline()

    run_stats_pipeline(
        players_df,
        year=YEAR,
        max_workers=10,
    )

    pipeline_end = time.perf_counter()

    total_run_time = pipeline_end - pipeline_start
    minutes, seconds = divmod(total_run_time, 60)

    print(
        f"Total pipeline runtime for {YEAR}: "
        f"{int(minutes)}m {seconds:.2f}s"
    )


if __name__ == "__main__":
    main()
