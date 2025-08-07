import json
from typing import List
import llms
import utils
import csv
from config import Config



def chunk_list(lst, batch_size):
    for i in range(0, len(lst), batch_size):
        yield lst[i:i + batch_size]


def format_prompt(input_batch: List[dict]):
    INPUT_FORMAT = '''\
    Input format: JSON objects, each with at least query and sparql fields.
    Batch processing: Handle a list (array) of JSON objects per batch.
    '''

    OUTPUT_FORMAT = '''\
    Output: For each input JSON object, output should be a JSON object with these keys:
    original_query
    sparql
    formal_question
    entities — a list of objects, each with mention (entity text from the query, e.g., 'Hannah Bast'), and uri (the corresponding URI from the SPARQL, e.g., 'https://dblp.org/pid/b/HannahBast' or full URI).
    Return: A list (array) of such JSON objects.
    '''

    PROMPT_TEMPLATE = '''
    You are given a batch of examples, each represented as a JSON object with the following keys:
    "q_id": a unique identifier of the question.
    "query": a natural language question or phrase (not necessarily well-formed).
    "sparql": the corresponding SPARQL query.
    Input Example:
    json
    [{{
        "id": "0024",
        "original_query": "Hannah Bast publications",
        "sparql": "PREFIX dblp: <https://dblp.org/rdf/schema#>             SELECT * WHERE {{             ?pubs dblp:authoredBy <https://dblp.org/pid/b/HannahBast> .  ?pubs dblp:title ?title .}}"
      }},
      {{
        "id": "3024",
        "original_query": "Aidan Hogan papers in World Wide Web (WWW) conference",
        "sparql": "PREFIX dblp: <https://dblp.org/rdf/schema#>      SELECT ?pubs ?title  WHERE {{VALUES ?author {{<https://dblp.org/pid/h/AidanHogan> }} .  VALUES ?stream {{ <https://dblp.org/streams/conf/www> }} .  ?pubs dblp:authoredBy ?author .  ?pubs dblp:title ?title .    ?pubs dblp:publishedInStream ?stream .}}"
      }}]
    Your task for each example:
    Analyze both query and sparql.
    Write a clear, formal, fact-seeking question in English that matches the intent, using the context in both the query and SPARQL to resolve ambiguity.
    Identify all entities mentioned in the query, and pair each with its URI as used in the SPARQL query. If an entity in the text does not have a matching URI in the SPARQL, set the uri field to null.
    Output, for each example, a JSON object in this format:
    json
    {{
      "id": "0024"
      "original_query": "Hannah Bast publications",
      "formal_question": "What are the publications of Hannah Bast?",
      "entities": [
        {{ "mention": "Hannah Bast", "uri": "<https://dblp.org/pid/b/HannahBast>" }}
      ]
    }}
    If no entities are present or mappable, return an empty list for entities.
    Input batch (array of examples):
    json
    {input_batch}

    Expected Output (for above input):
    json
    [
      {{
        "id": "0024",
        "original_query": "Hannah Bast publications",
        "formal_question": "What are the publications of Hannah Bast?",
        "entities": [
        {{ "mention": "Hannah Bast", "uri": "<https://dblp.org/pid/b/HannahBast>" }}
      ]
      }},
      {{
        "id": "3024",
        "original_query": "Aidan Hogan papers in World Wide Web (WWW) conference",
        "formal_question": "Can you provide a list of papers by Aidan Hogan presented at the World Wide Web (WWW) conference?",
        "entities": [
          {{ "mention": "Aidan Hogan", "uri": "<https://dblp.org/pid/h/AidanHogan>" }}
          {{ "mention": "World Wide Web (WWW)", "uri": "<https://dblp.org/streams/conf/www>" }}
        ]
      }}
    ]
    '''

    INSTRUCTIONS = '''
    Instructions:
    For each pair, analyze both 'query' and 'sparql'.
    Write a clear, formal, fact-seeking question in English that best reflects the intent and the information need as expressed by both 'query' and 'sparql'.
    If the 'query' is ambiguous or incomplete, use the 'sparql' to resolve the ambiguity and make the formal question self-contained.
    Use the SPARQL variable assignments and triples to align entity mentions in the query text with their respective URIs, even if the query substitution is not exact or is ambiguous.
    If there are multiple entities, include each as an object in the entities list.
    Guidelines:
    The formal_question should be a direct, fact-seeking question suitable for a QA dataset.
    Disambiguate entities, relations, or timeframes as specified in the SPARQL.
    If the SPARQL contains an aggregation (COUNT, SUM, etc.), reflect it in the question (e.g., "How many ...").
    Use precise, unambiguous English.

    Always deliver the output as a JSON array in the specified format, matching the batch size of the input.
    '''
    input_json = json.dumps(input_batch, ensure_ascii=False, indent=2)
    prompt = INPUT_FORMAT + OUTPUT_FORMAT + PROMPT_TEMPLATE.format(input_batch=input_json) + INSTRUCTIONS
    return prompt


def process_batch(input_batch):
    prompt = format_prompt(input_batch)
    try:
        result = llms.chatgpt(prompt, 3)
        return result
    except Exception as e:
        print("Failed to parse output:", result)
        raise e


def main(input_filename, output_filename, batch_size=10):
    input_data = utils.load_json_data(file_name=input_filename)
    output_data = utils.load_json_data(file_name=output_filename)
    id_counter = 0
    for batch in chunk_list(input_data[32:], batch_size):
        print(f"Processing batch {id_counter // batch_size + 1} ...")
        batch_result = process_batch(batch)
        output_data.extend(batch_result['outputs'])
        utils.write_to_json(output_data,output_filename)


def generate_answer(out_file="log_data/question_sparql_answer.json"):
    questions = utils.load_json_data("log_data/generated_questions.json")
    question_sparql = utils.load_json_data("log_data/filter_queries_by_jaccard_similarity.json")
    questions_sparql_ids = {}
    question_sparql_answer = utils.load_json_data(out_file)
    for item in question_sparql:
        questions_sparql_ids.update({str(item['id']):item['query']})

    for qs in questions[516:]:
        if qs['entities']:
            sparql = questions_sparql_ids[qs['id']]
            result = utils.run_sparql_query(sparql_endpoint=Config.SPARQL_ENDPOINT,sparql_query=sparql)
            if result:
                answer = utils.extruct_values(result)
                qs.update({'answer':answer, 'sparql':sparql})
                question_sparql_answer.append(qs)
                utils.write_to_json(question_sparql_answer,out_file)


def update_data():
    data = utils.load_json_data("log_data/question_sparql_answer.json")
    id_sparql_pairs = {}
    filtered_data = []
    for item in data:
        if item["id"] == "373251":
            continue
        filtered_data.append(item)
        id_sparql_pairs.update({item["id"]:item["sparql"]})
    utils.write_to_json(filtered_data,"log_data/question_sparql_answer_updated.json")
    utils.write_to_json(id_sparql_pairs,"log_data/question_id_sparql_pairs.json")


if __name__ == "__main__":
    # convert_csv_to_json("log_data/filter_queries_by_jaccard_2.csv", "log_data/filter_queries_by_jaccard_similarity.json")
    # main("log_data/filter_queries_by_jaccard_similarity.json", "log_data/generated_questions.json", batch_size=2)
    # generate_answer()
    update_data()