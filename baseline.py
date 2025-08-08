import utils
from config import Config
import question_similarity
import kgqa
import llms
from prompts import question_to_sparql_prompt
import dblp_schema
import logging
from SPARQLWrapper import SPARQLWrapper, JSON
import sys,os,json
import random

os.environ["TOKENIZERS_PARALLELISM"] = "false"
LOCAL_SPARQL_ENDPOINT = Config.LOCAL_SPARQL_ENDPOINT
DBLP_QUAD_1_SPARQL_ENDPOINT = Config.DBLP_QUAD_1_SPARQL_ENDPOINT
SPARQL_ENDPOINT = LOCAL_SPARQL_ENDPOINT

def random_split(data_path, test_ratio=0.2, seed=42):
    """
    Split data into test and train sets based on date.

    Args:
      data (list of dict): Each dict contains a date under `date_key`.
      date_key (str): The key in each dict where the date is stored.
      test_ratio (float): Fraction of data to assign to test set (default 0.2).
      date_format (str or None): Optional strptime format if dates are strings.

    Returns:
      (train_data, test_data): two lists split by date.
    """
    random.seed(seed)
    data = utils.load_json_data(data_path)
    data_shuffled = data[:]  # make a shallow copy

    random.shuffle(data_shuffled)

    split_index = int(len(data_shuffled) * test_ratio)
    test_data = data_shuffled[:split_index]
    train_data = data_shuffled[split_index:]
    utils.write_to_json(test_data,"experiment/ask-dblp/test_data.json")
    utils.write_to_json(train_data, "experiment/ask-dblp/train_data.json")


def collect_answers(data_source):
    output = []
    for item in data_source:
        if not isinstance(item, dict):
            continue
        for qid, data in item.items():
            extracted_strings = []
            if isinstance(data, dict) and 'answer' in data and isinstance(data['answer'], list):
                for entry in data['answer']:
                    if isinstance(entry, dict):
                        # Extract string values from all keys in the dict
                        for v in entry.values():
                            if isinstance(v, str):
                                extracted_strings.append(v)
            output.append({'id': qid, 'answer': extracted_strings})
    return output


def postprocess_predictions_for_eval_dblp_quad():
    answers_data = utils.load_json_data("experiment/DBLP-QuAD/test/answers.json")
    d = answers_data["answers"]
    test_set_answers = []
    for item in d:
        newanswer = []
        answer = item["answer"]
        if 'results' in answer:
            if 'bindings' in answer['results']:
                for ans in answer['results']['bindings']:
                    for k, v in ans.items():
                        newanswer.append(ans[k]["value"])
                test_set_answers.append({"id": item["id"], "answer": newanswer})
        elif 'boolean' in answer:
            test_set_answers.append({"id": item["id"], "answer": answer['boolean']})

    utils.write_to_json(test_set_answers,'experiment/DBLP-QuAD/test/question_answer_pairs.json')
    answer_predictions = utils.load_json_data("experiment/DBLP-QuAD/answer_predictions_test.json")
    utils.write_to_json(collect_answers(answer_predictions),"experiment/DBLP-QuAD/answer_predictions_id_answer.json")


def postprocess_predictions_for_eval_ask_dblp():
    gold_answers_data = utils.load_json_data("experiment/ask-dblp/test_data.json")
    gold_answers = []
    for item in gold_answers_data:
        answer = item['answer']
        temp = []
        if answer:
            for ans in answer:
                for k, v in ans.items():
                    temp.append(v)
        gold_answers.append({"id": item["id"], "answer": temp})
    utils.write_to_json(gold_answers,'experiment/ask-dblp/test_question_answer_pairs.json')

    answer_predictions = utils.load_json_data("experiment/ask-dblp/answer_predictions_test.json")
    utils.write_to_json(collect_answers(answer_predictions),"experiment/ask-dblp/test_set_answer_predictions_id_answer.json")



def get_question_to_sparql_prompt(question, selected_entities=[], similar_questions_pool={}):
    examples = utils.get_examples("build_sparql")
    selected_entities_string = ''
    if selected_entities:
        selected_entities_string = '\n  '.join(
            f"ENTITY_LABEL: {entity['normalized_label']} ; ENTITY_TYPE: {entity['entity_type']} ; URI: {entity['uri']}"
            for entity in selected_entities
        )
        examples = utils.get_examples("buidl_sparql_with_uri")
    prompt_template = question_to_sparql_prompt.QUESTION_TO_SPARQL_PROMPT
    prompt = prompt_template.format(
        question=question,
        dblp_schema=dblp_schema.properties_uri_and_description,
        examples=examples,
        entities=selected_entities_string,
        similar_questions_pool=similar_questions_pool,
    )
    return prompt


def answer_questions(qsim, question, top_k = 5):
    try:
        similar_questions = question_similarity.identify_similar_questions(qsim, question)
        similar_questions_pool = {}
        if similar_questions:
            for qid, qu, score, q_sparql, q_entities in similar_questions[:top_k]:
                similar_questions_pool.update({'question':qu, 'entities':q_entities, 'sparql':q_sparql})
        all_entities, selected_entities = kgqa.entity_linker(question)
        if not all_entities and selected_entities:
            all_entities = []
            selected_entities = []
        prompt = get_question_to_sparql_prompt(question, selected_entities, similar_questions_pool)
        chatai_llm_model = 'qwen2.5-coder-32b-instruct'
        sparql_query, confidence = llms.chatai_models(prompt=prompt, model=chatai_llm_model)
        if 'sparql' in sparql_query:
            sparql = sparql_query['sparql']
            sparql_result = SPARQLWrapper(SPARQL_ENDPOINT)
            sparql_result.setQuery(sparql)
            sparql_result.setReturnFormat(JSON)
            results = sparql_result.query().convert()
            answer = utils.extruct_values(results)
            return {'answer':answer, 'sparql':sparql, 'confidence':confidence,
                'all_entities':all_entities, 'selected_entities':selected_entities,
                'similar_questions':similar_questions, 'top_k': top_k}
    except Exception as e:
        logging.error(f"An error occurred during SPARQL Generation: {e}", exc_info=e)
        return {}


def eval_dblp_quad(test_set, prediction_file="experiment/DBLP-QuAD/answer_predictions_test.json"):
    test_set = utils.load_json_data(test_set)
    answer_predictions = utils.load_json_data(prediction_file)
    qsim = question_similarity.QuestionSimilarityIdentifier()
    for q in test_set['questions']:
        qid = q["id"]
        question = utils.get_value_from_dict(q["paraphrased_question"],"string")
        answer_result = answer_questions(qsim, question)
        answer_predictions.append({qid:answer_result})
        utils.write_to_json(answer_predictions,prediction_file)


def eval_ask_dblp(test_set, prediction_file="experiment/ask-dblp/answer_predictions_test.json"):
    test_set = utils.load_json_data(test_set)
    answer_predictions = utils.load_json_data(prediction_file)
    qsim = question_similarity.QuestionSimilarityIdentifier()
    for q in test_set:
        qid = q["id"]
        question = q["formal_question"]
        answer_result = answer_questions(qsim, question)
        answer_predictions.append({qid:answer_result})
        utils.write_to_json(answer_predictions,prediction_file)


if __name__ == '__main__':
    sparql = """PREFIX dblp: <https://dblp.org/rdf/schema#>
            SELECT ?paper ?title ?year WHERE {
              ?paper dblp:title ?title .
              ?paper dblp:publishedIn "SIGIR" .
              ?paper dblp:yearOfPublication ?year
            }
            ORDER BY DESC(?year)
            LIMIT 10    
    """
    #result = utils.run_sparql_query(sparql_endpoint=LOCAL_SPARQL_ENDPOINT,sparql_query=sparql)
    # print(result)
    #print(utils.extruct_values(result))
    eval_ask_dblp("experiment/ask-dblp/test_data.json")
    # postprocess_predictions_for_eval_ask_dblp()
    # random_split("log_data/question_sparql_answer_updated.json")