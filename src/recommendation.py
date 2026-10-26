import difflib
import re

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

from src.features import build_features
from src.dataset import (
    df, FEATURES_PATH,
    COL_TITLE, COL_GENRES, COL_YEAR, COL_RATING, COL_OVERVIEW, COL_POSTER, COL_VOTES,
)


POSTER_BASE_URL = "https://image.tmdb.org/t/p/w342"


# Load the feature matrix. If the file is missing, build it from Movies.csv
# and save it, so this only happens once.
if FEATURES_PATH.exists():
    features = np.load(FEATURES_PATH)
else:
    print("scaled_features.npy not found - building it from Movies.csv ...")
    features = build_features()
    np.save(FEATURES_PATH, features)
    print(f"Saved {FEATURES_PATH} with shape {features.shape}")

if len(df) != len(features):
    raise ValueError(
        f"Movies.csv has {len(df)} rows but scaled_features.npy has {len(features)}. "
        "The features must be built from the same rows, in the same order. "
        "Delete data/scaled_features.npy and restart: it will be rebuilt automatically."
    )


# Create Nearest Neighbors model
model = NearestNeighbors(
    n_neighbors=6,
    metric="cosine",
    algorithm="brute"
)

model.fit(features)


# Prepared once so each search is fast
_titles_lower = df[COL_TITLE].astype(str).str.lower().str.strip()

_genre_lists = (
    df[COL_GENRES].fillna("").astype(str).apply(
        lambda text: [g.strip().lower() for g in re.split(r"[|,;]", text) if g.strip()]
    )
    if COL_GENRES else pd.Series([[]] * len(df))
)

# Genre name as written in the data, keyed by lowercase ("sci-fi" -> "Sci-Fi")
_genre_names = {}
if COL_GENRES:
    for text in df[COL_GENRES].fillna("").astype(str):
        for g in re.split(r"[|,;]", text):
            if g.strip():
                _genre_names.setdefault(g.strip().lower(), g.strip())


def _clean(value):
    """Return None for missing values, otherwise a plain Python value."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value.item() if hasattr(value, "item") else value


def _get_year(row):
    if not COL_YEAR:
        return None

    value = _clean(row[COL_YEAR])
    if value is None:
        return None

    text = str(value)
    try:
        return int(float(text))          # 2010, 2010.0, "2010"
    except ValueError:
        pass

    date = pd.to_datetime(text, errors="coerce")   # "2010-07-16", "16/07/2010"
    return None if pd.isna(date) else int(date.year)


def _get_rating(row):
    if not COL_RATING:
        return None

    value = _clean(row[COL_RATING])
    try:
        return round(float(value), 1)
    except (TypeError, ValueError):
        return None


def _get_poster(row):
    if not COL_POSTER:
        return None

    value = _clean(row[COL_POSTER])
    if not value:
        return None

    value = str(value)
    if value.startswith("http"):
        return value
    return POSTER_BASE_URL + (value if value.startswith("/") else "/" + value)


def _movie_dict(index, similarity, kind, label):
    """One movie in the format the template expects."""
    row = df.iloc[index]
    return {
        "title": row[COL_TITLE],
        "genres": _clean(row[COL_GENRES]) if COL_GENRES else None,
        "year": _get_year(row),
        "rating": _get_rating(row),
        "overview": _clean(row[COL_OVERVIEW]) if COL_OVERVIEW else None,
        "poster": _get_poster(row),
        "similarity": similarity,
        "kind": kind,        # "similar" or "genre"
        "label": label,      # movie title or genre shown in the page heading
    }


def _find_movie(query):
    """Exact title first, then 'contains', then a close spelling."""
    exact = _titles_lower[_titles_lower == query]
    if not exact.empty:
        return exact.index[0]

    partial = _titles_lower[_titles_lower.str.contains(query, regex=False)]
    if not partial.empty:
        # Prefer the shortest title, which is usually the closest match
        return partial.str.len().idxmin()

    close = difflib.get_close_matches(query, _titles_lower.tolist(), n=1, cutoff=0.8)
    if close:
        return _titles_lower[_titles_lower == close[0]].index[0]

    return None


def _top_in_genre(genre_key, limit):
    """Best-rated movies in a genre (used when the search is a genre, not a title)."""
    mask = _genre_lists.apply(lambda genres: genre_key in genres)
    subset = df[mask]

    # Ignore movies with very few votes, so one 10/10 vote doesn't win
    if COL_VOTES:
        votes = pd.to_numeric(subset[COL_VOTES], errors="coerce")
        subset = subset[votes >= votes.median()]

    if COL_RATING:
        ratings = pd.to_numeric(subset[COL_RATING], errors="coerce")
        subset = subset.loc[ratings.sort_values(ascending=False).index]

    label = _genre_names.get(genre_key, genre_key.title())
    return [_movie_dict(i, None, "genre", label) for i in subset.head(limit).index]


def recommend_movies(movie_name, num_recommendations=5):

    query = movie_name.lower().strip()
    if not query:
        return []

    movie_index = _find_movie(query)

    # Not a title: maybe the person searched for a genre such as "Crime"
    if movie_index is None:
        if query in _genre_names:
            return _top_in_genre(query, num_recommendations)
        return []

    # Find nearest movies (the first result is the movie itself)
    distances, indices = model.kneighbors(
        features[movie_index].reshape(1, -1),
        n_neighbors=num_recommendations + 1
    )

    matched_title = df.iloc[movie_index][COL_TITLE]
    recommendations = []

    for distance, index in zip(distances[0], indices[0]):

        if index == movie_index:
            continue

        # Cosine distance -> similarity between 0 and 1
        similarity = max(0.0, min(1.0, 1 - float(distance)))

        recommendations.append(
            _movie_dict(index, round(similarity, 3), "similar", matched_title)
        )

    return recommendations[:num_recommendations]