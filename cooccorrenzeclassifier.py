"""Step 2/6 of the enrichment pipeline.

Consumes the square co-occurrence matrix and produces a ranked list of
unordered term pairs with joint frequency above `COOCCURRENCE_THRESHOLD`.
The ranking is the input to the semantic mapping step in `findcouples.py`.

Input : matrice_cooccorrenze.xlsx
Output: classifica_cooccorrenze.xlsx (columns: Parola1, Parola2, Cooccorrenze)
"""
import pandas as pd

from config import (
    COOCCURRENCE_MATRIX_XLSX,
    COOCCURRENCE_RANK_XLSX,
    COOCCURRENCE_THRESHOLD,
)


def rebuild_cooccurrences(path, threshold: int) -> pd.DataFrame:
    df = pd.read_excel(path, index_col=0)
    stack = df.stack().reset_index()
    stack.columns = ["Parola1", "Parola2", "Cooccorrenze"]

    ranking = stack[stack["Cooccorrenze"] > threshold]
    ranking = ranking[ranking["Parola1"] < ranking["Parola2"]]
    return ranking.sort_values(by="Cooccorrenze", ascending=False)


def run() -> None:
    ranked = rebuild_cooccurrences(COOCCURRENCE_MATRIX_XLSX, COOCCURRENCE_THRESHOLD)
    ranked.to_excel(COOCCURRENCE_RANK_XLSX, index=False)


if __name__ == "__main__":
    run()
