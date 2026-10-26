import pandas as pd

from src.dataset import df, COL_GENRES, COL_DIRECTOR, COL_RATING


def _split_values(series):
    """Split cells like 'Action|Adventure' or 'Action, Adventure' into separate values."""
    values = (
        series.dropna()
        .astype(str)
        .str.split(r"[|,;]")
        .explode()
        .str.strip()
    )
    return values[(values != "") & (values.str.lower() != "(no genres listed)")]


def get_analytics():

    genres = _split_values(df[COL_GENRES]) if COL_GENRES else pd.Series(dtype=str)
    directors = _split_values(df[COL_DIRECTOR]) if COL_DIRECTOR else pd.Series(dtype=str)

    average_rating = 0
    if COL_RATING:
        average_rating = round(float(pd.to_numeric(df[COL_RATING], errors="coerce").mean()), 2)

    return {
        "total_movies": int(len(df)),
        "total_genres": int(genres.nunique()),
        "total_directors": int(directors.nunique()),
        "average_rating": average_rating,
        "top_genres": genres.value_counts().head(5).to_dict(),
        "top_directors": directors.value_counts().head(5).to_dict(),
    }