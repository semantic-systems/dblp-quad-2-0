import csv
import hashlib
import subprocess
import tempfile
import os
from typing import Optional
# from config import Config
import re
from typing import Tuple
from tqdm import tqdm

APACHE_JEANA_ARQ_PATH = "/Users/tilahun/Documents/GitHub/dblp-quad-2-0/apache-jena-5.5.0/bin/arq" #Config.APACHE_JEANA_ARQ_PATH

def split_leading_string(query: str) -> Tuple[str, str]:
    """
    Splits the input into leading non-SPARQL text and the actual SPARQL query.

    Parameters:
        query (str): The full input string (may include description and query).

    Returns:
        Tuple[str, str]: (leading_text, sparql_query)
    """
    sparql_keywords = ['PREFIX', 'BASE', 'SELECT', 'CONSTRUCT', 'DESCRIBE', 'ASK']
    pattern = re.compile(r'\b(?:' + '|'.join(sparql_keywords) + r')\b', re.IGNORECASE)

    match = pattern.search(query)
    if match:
        return query[:match.start()].strip(), query[match.start():].strip()
    else:
        return query.strip(), ""


def canonicalize_with_jena(sparql_query: str, jena_path: str = APACHE_JEANA_ARQ_PATH) -> Optional[str]:
    try:
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.rq') as tmp_file:
            tmp_file.write(sparql_query)
            tmp_file_path = tmp_file.name

        result = subprocess.run(
            [jena_path, "--query", tmp_file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        os.remove(tmp_file_path)

        if result.returncode != 0:
            print(f"[ERROR] Jena failed:\n{result.stderr}")
            return None

        return result.stdout.strip()

    except Exception as e:
        print(f"[EXCEPTION] {e}")
        return None


if __name__ == '__main__':

    input_csv = "log_data/dblp-sparql-logs-2025-05-13.csv"
    output_csv = "log_data/dedup/deduplicated_queries.csv"

    with open(input_csv, newline='', encoding='utf-8') as infile, \
            open(output_csv, 'w', newline='', encoding='utf-8') as outfile:

        reader = csv.DictReader(infile)
        fieldnames = ['id', 'datetime', 'question', 'query']  # New output columns
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        seen_hashes = set()
        total = 400000
        for row in tqdm(reader, total=total, desc="Processing queries", unit="query"):
            full_query = row['query']
            desc, sparql = split_leading_string(full_query)

            # Skip if there's no valid SPARQL portion
            if not sparql.strip():
                continue

            # Canonicalize (replace with your method or Jena wrapper)
            canonical = canonicalize_with_jena(sparql)
            if canonical is None:
                continue

            # Hash for deduplication
            query_hash = hashlib.sha1(canonical.encode('utf-8')).hexdigest()

            if query_hash not in seen_hashes:
                seen_hashes.add(query_hash)
                writer.writerow({
                    'id': row['id'],
                    'datetime': row['datetime'],
                    'question': desc,
                    'query': sparql
                })
    print(f"Deduplicated {len(seen_hashes)} unique queries saved to {output_csv}")