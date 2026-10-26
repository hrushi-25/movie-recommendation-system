"""
Builds the feature matrix used to compare movies, directly from Movies.csv.

It is only used when data/scaled_features.npy does not exist yet.
Row i of the matrix always describes row i of Movies.csv.
"""

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MinMaxScaler, MultiLabelBinarizer

from src.dataset import df, COL_GENRES, COL_OVERVIEW, COL_DIRECTOR, COL_RATING, COL_YEAR


# How much each part matters when comparing movies
W_GENRES = 2.0
W_OVERVIEW = 1.0
W_DIRECTOR = 0.5
W_NUMERIC = 0.5


def _split(text):
    return [p.strip() for p in pd.Series([text]).astype(str).str.split(r"[|,;]").iloc[0] if p.strip()]


def build_features():
    blocks = []

    # Genres: one column per genre
    if COL_GENRES:
        genre_lists = df[COL_GENRES].fillna("").astype(str).apply(_split)
        genre_matrix = MultiLabelBinarizer().fit_transform(genre_lists)
        if genre_matrix.shape[1]:
            blocks.append(genre_matrix * W_GENRES)

    # Overview: TF-IDF keeps the words that make a plot description distinctive
    if COL_OVERVIEW:
        text = df[COL_OVERVIEW].fillna("").astype(str)
        try:
            tfidf = TfidfVectorizer(
                stop_words="english",
                max_features=500,
                min_df=2 if len(df) > 50 else 1,
            )
            blocks.append(tfidf.fit_transform(text).toarray() * W_OVERVIEW)
        except ValueError:
            pass  # no usable words in the overview column

    # Director: one column for each of the 100 most frequent directors
    if COL_DIRECTOR:
        directors = df[COL_DIRECTOR].fillna("").astype(str).str.split(r"[|,;]").str[0].str.strip()
        top = directors[directors != ""].value_counts().head(100).index
        if len(top):
            matrix = np.array([[1.0 if d == name else 0.0 for name in top] for d in directors])
            blocks.append(matrix * W_DIRECTOR)

    # Rating and year, scaled to 0-1
    numeric = {}
    if COL_RATING:
        numeric["rating"] = pd.to_numeric(df[COL_RATING], errors="coerce")
    if COL_YEAR:
        numeric["year"] = pd.to_numeric(
            df[COL_YEAR].astype(str).str.extract(r"(\d{4})")[0], errors="coerce"
        )
    if numeric:
        frame = pd.DataFrame(numeric)
        frame = frame.fillna(frame.median()).fillna(0)
        blocks.append(MinMaxScaler().fit_transform(frame) * W_NUMERIC)

    if not blocks:
        raise ValueError(
            "No usable columns (genres, overview, director, rating or year) were "
            "found in Movies.csv, so features cannot be built."
        )

    return np.hstack(blocks).astype("float32")