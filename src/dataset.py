"""
Loads data/Movies.csv once and works out which column is which.

If a column is not found automatically, add its name to the matching
list in CANDIDATES below (use lowercase).
"""

import ast
import json
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "Movies.csv"
FEATURES_PATH = BASE_DIR / "data" / "scaled_features.npy"


# Possible names for each column (lowercase). The first one found is used.
CANDIDATES = {
    "title":    ["title", "movie_title", "original_title", "movie_name", "movie", "series_title", "name"],
    "genres":   ["genres", "genre", "listed_in", "category"],
    "year":     ["year", "release_year", "released_year", "startyear", "release_date", "released"],
    "rating":   ["vote_average", "rating", "imdb_rating", "imdb_score", "averagerating", "score"],
    "overview": ["overview", "description", "plot", "storyline", "summary"],
    "poster":   ["poster_path", "poster", "poster_link", "poster_url", "image", "image_url"],
    "director": ["director", "directors", "director_name"],
    "votes":    ["vote_count", "votes", "numvotes", "num_votes", "imdb_votes", "no_of_votes"],
}


# ---- load the CSV (try common encodings) ----------------------------------
try:
    df = pd.read_csv(DATA_PATH)
except UnicodeDecodeError:
    df = pd.read_csv(DATA_PATH, encoding="latin-1")

df = df.reset_index(drop=True)

_lookup = {str(col).lower().strip(): col for col in df.columns}


def _pick(key):
    for name in CANDIDATES[key]:
        if name in _lookup:
            return _lookup[name]
    return None


COL_TITLE = _pick("title")
COL_GENRES = _pick("genres")
COL_YEAR = _pick("year")
COL_RATING = _pick("rating")
COL_OVERVIEW = _pick("overview")
COL_POSTER = _pick("poster")
COL_DIRECTOR = _pick("director")
COL_VOTES = _pick("votes")

if COL_TITLE is None:
    raise ValueError(
        "Could not find a movie title column in Movies.csv. "
        f"Columns found: {list(df.columns)}. "
        "Add the right name to CANDIDATES['title'] in src/dataset.py."
    )


def _names(value):
    """Turn "[{'name': 'Action'}, ...]" or "['Action', 'Drama']" into 'Action|Drama'.
    Plain text such as 'Action|Drama' or 'Action, Drama' is returned unchanged."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""

    text = str(value).strip()

    if text.startswith("["):
        items = None
        for parser in (ast.literal_eval, json.loads):
            try:
                items = parser(text)
                break
            except (ValueError, SyntaxError):
                continue

        if isinstance(items, list):
            out = []
            for item in items:
                out.append(str(item.get("name", "")) if isinstance(item, dict) else str(item))
            return "|".join(o for o in out if o)

    return text


# Clean list-style columns so every part of the app sees the same format
if COL_GENRES:
    df[COL_GENRES] = df[COL_GENRES].apply(_names)

if COL_DIRECTOR:
    df[COL_DIRECTOR] = df[COL_DIRECTOR].apply(_names)