from sqlalchemy import MetaData

def tables(engine):
    "return metadata for players and player stats table in tuple form (player, player_stats)"
    metadata = MetaData()

    metadata.reflect(
        bind=engine,
        schema="golf",
    )

    players_table = metadata.tables["golf.players"]

    player_stats_table = metadata.tables["golf.player_stats"]

    stat_reference_table = metadata.tables["golf.stats_reference"]

    return players_table, player_stats_table, stat_reference_table
