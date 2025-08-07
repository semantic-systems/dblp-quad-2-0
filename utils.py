import json
from SPARQLWrapper import SPARQLWrapper, JSON
import csv

def get_value_from_dict(data, key):
    if key in data:
        return data[key]


def run_sparql_query(sparql_endpoint, sparql_query, param='', flag=False):
    if flag:
        sparql_query = sparql_query % param
    try:
        sparql = SPARQLWrapper(sparql_endpoint)
        sparql.setQuery(sparql_query)
        sparql.setReturnFormat(JSON)
        result = sparql.query().convert()
        return result
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None
    return


def load_json_data(file_name):
    try:
        with open(file_name, 'r') as json_file:
            data = json.load(json_file)
        return data
    except FileNotFoundError:
        print(f"Error: File '{file_name}' not found.")
        return []

def write_to_json(result, out_file_path):
    with open(out_file_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)
    print("Successfully written to file!")


def extruct_values(results):
    return_result = []
    for result in results["results"]["bindings"]:
        converted_result = {}
        for key, value_info in result.items():
            value = value_info.get('value')
            if value:
                converted_result[key] = value
        return_result.append(converted_result)
    return return_result


def get_examples(key, file_path="examples.json"):
    with open(file_path, 'r', encoding='utf-8') as file:
        examples_data = json.load(file)
    examples = '\n'.join(f"{key}: {value}" for d in examples_data.get(key, None) for key, value in d.items())
    return examples


def convert_csv_to_json(input_csv, output_json):
    data = []

    with open(input_csv, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            entry = {
                'id': int(row['id']),
                'question': row['question'],
                'query': row['query']
            }
            data.append(entry)

    with open(output_json, mode='w', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile, ensure_ascii=False, indent=2)
    print(len(data))
    print("CSV has been converted to JSON.")