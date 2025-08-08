import os

# load environment variables
from dotenv import find_dotenv, load_dotenv

_ = load_dotenv(find_dotenv())


class Config:
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    CHATAI_API_KEY = os.environ.get("CHATAI_API_KEY", "")
    SPARQL_ENDPOINT = os.environ.get("SPARQL_ENDPOINT", "")
    LOCAL_SPARQL_ENDPOINT = os.environ.get("LOCAL_SPARQL_ENDPOINT", "")
    DBLP_QUAD_1_SPARQL_ENDPOINT = os.environ.get("DBLP_QUAD_1_SPARQL_ENDPOINT", "")
    DBLP_ENTITY_LINKER = os.environ.get("DBLP_ENTITY_LINKER", "")
    APACHE_JEANA_ARQ_PATH = os.environ.get("APACHE_JEANA_ARQ_PATH", "")
    LLMS = {
        "openai": {
            "url_chat_completions": "https://api.openai.com/v1/chat/completions",
            "open_api_key": os.environ.get("OPENAI_API_KEY", ""),
            "model": os.environ.get("OPENAI_MODEL", "")
        },
        "llama3": {
            "url": os.environ.get("LLAMA3_URL", ""),
            "username": os.environ.get("LLAMA3_USERNAME", ""),
            "password": os.environ.get("LLAMA3_PASSWORD", "")
        },
        "chatai": {
            "url": os.environ.get("CHATAI_API_URL", ""),
            "chatai_api_key": os.environ.get("CHATAI_API_KEY", ""),
            "model": os.environ.get("CHATAI_MODEL", "")
        }
    }