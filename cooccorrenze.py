"""
Step 1: Co-occurrence Matrix Generation

This module processes the Cyber_Events_Database.xlsx file to extract meaningful 
term co-occurrences from event descriptions. It performs text preprocessing using 
NLTK (tokenization, stopword removal, lemmatization), identifies the top 1000 most 
frequent terms, and builds a co-occurrence matrix capturing term relationships.
The output is saved as matrice_cooccorrenze.xlsx for downstream semantic mapping.
"""

import pandas as pd
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from collections import Counter
from itertools import combinations

nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)
nltk.download('punkt_tab', quiet=True)

stop_words = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()


def clean_text(text):
    text = str(text).lower()
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    tokens = nltk.word_tokenize(text)
    tokens = [lemmatizer.lemmatize(w) for w in tokens if w not in stop_words]
    return tokens


def main():
    df = pd.read_excel("Cyber_Events_Database.xlsx")
    df["tokens"] = df["description"].apply(clean_text)

    all_tokens = [w for tokens in df["tokens"] for w in tokens]
    word_counts = Counter(all_tokens)

    top_n = 1000
    top_words = [w for w, _ in word_counts.most_common(top_n)]
    top_words_set = set(top_words)

    cooc = Counter()

    for tokens in df["tokens"]:
        unique_tokens = set(tokens) & top_words_set
        for w1, w2 in combinations(unique_tokens, 2):
            cooc[(w1, w2)] += 1
            cooc[(w2, w1)] += 1

    cooc_matrix = pd.DataFrame(0, index=top_words, columns=top_words)

    for (w1, w2), count in cooc.items():
        cooc_matrix.at[w1, w2] = count

    cooc_matrix.to_excel("matrice_cooccorrenze.xlsx", index=False)


if __name__ == "__main__":
    main()
