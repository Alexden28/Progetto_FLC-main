"""
Step 2: Co-occurrence Classification

This module processes the co-occurrence matrix generated in Step 1. It filters 
term pairs based on a frequency threshold (100 occurrences) to remove statistical 
noise, eliminates symmetric duplicates, and produces a ranked classification file.
The output serves as input for semantic mapping in Step 3.
"""

import pandas as pd


def rebuild_cooccurrences(input_path: str, threshold: int = 100) -> pd.DataFrame:
    """
    Restructure co-occurrence matrix into ranked list.
    
    Args:
        input_path: Path to the co-occurrence matrix Excel file
        threshold: Minimum co-occurrence count to include
        
    Returns:
        DataFrame with filtered and ranked term pairs
    """
    df = pd.read_excel(input_path, index_col=0)
    
    stack = df.stack().reset_index()
    stack.columns = ['Parola1', 'Parola2', 'Cooccorrenze']
    
    ranking = stack[stack['Cooccorrenze'] > threshold]
    ranking = ranking[ranking['Parola1'] < ranking['Parola2']]
    
    return ranking.sort_values(by='Cooccorrenze', ascending=False)


def main():
    origin = "matrice_cooccorrenze.xlsx"
    output = "classifica_cooccorrenze.xlsx"
    
    df_result = rebuild_cooccurrences(origin)
    df_result.to_excel(output, index=False)


if __name__ == "__main__":
    main()
