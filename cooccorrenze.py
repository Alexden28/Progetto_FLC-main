"""Step 1/6 of the enrichment pipeline.

Produces a word-by-word co-occurrence matrix from the cyber-event descriptions.
The matrix feeds `cooccorrenzeclassifier.py`, which ranks the strongest
domain-relevant term pairs.

Input : Cyber_Events_Database.xlsx (column `description`)
Output: matrice_cooccorrenze.xlsx (dense top-N square matrix)
"""
from collections import Counter
from itertools import combinations
import re

import nltk
import pandas as pd
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

from config import (
    COOCCURRENCE_MATRIX_XLSX,
    CYBER_EVENTS_XLSX,
    TOP_TOKEN_COUNT,
)

for resource in ("punkt", "stopwords", "wordnet", "punkt_tab"):
    nltk.download(resource, quiet=True)

_STOP_WORDS = set(stopwords.words("english"))
_LEMMATIZER = WordNetLemmatizer()
_NON_ALPHA = re.compile(r"[^a-zA-Z\s]")


def clean_text(text: str) -> list[str]:
    text = _NON_ALPHA.sub("", str(text).lower())
    tokens = nltk.word_tokenize(text)
    return [_LEMMATIZER.lemmatize(w) for w in tokens if w not in _STOP_WORDS]


def build_cooccurrence_matrix() -> pd.DataFrame:
    df = pd.read_excel(CYBER_EVENTS_XLSX)
    df["tokens"] = df["description"].apply(clean_text)

    all_tokens = [w for tokens in df["tokens"] for w in tokens]
    word_counts = Counter(all_tokens)
    top_words = [w for w, _ in word_counts.most_common(TOP_TOKEN_COUNT)]
    top_words_set = set(top_words)

    cooc: Counter = Counter()
    for tokens in df["tokens"]:
        unique_tokens = set(tokens) & top_words_set
        for w1, w2 in combinations(unique_tokens, 2):
            cooc[(w1, w2)] += 1
            cooc[(w2, w1)] += 1

    matrix = pd.DataFrame(0, index=top_words, columns=top_words)
    for (w1, w2), count in cooc.items():
        matrix.at[w1, w2] = count
    return matrix


def run() -> None:
    matrix = build_cooccurrence_matrix()
    matrix.to_excel(COOCCURRENCE_MATRIX_XLSX)


if __name__ == "__main__":
    run()
