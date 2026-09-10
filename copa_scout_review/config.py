"""config.py — Configuração centralizada"""
import os
from pathlib import Path

from dotenv import load_dotenv
from elasticsearch import Elasticsearch
import requests

load_dotenv(Path(__file__).with_name(".env"))

ES_URL = os.environ["ES_URL"]
API_KEY = os.environ["API_KEY"]
KIBANA_URL = os.environ["KIBANA_URL"]

es = Elasticsearch(ES_URL, api_key=API_KEY, request_timeout=120)
HEADERS = {"Authorization": f"ApiKey {API_KEY}", "kbn-xsrf": "true", "Content-Type": "application/json"}
CACHE_DIR = "cache"
TOURNAMENTS = [(43, 106, "FIFA World Cup 2022"), (43, 3, "FIFA World Cup 2018")]

def kb_api(method, endpoint, body=None):
    url = f"{KIBANA_URL}{endpoint}"
    fn = {"GET": requests.get, "POST": requests.post, "PUT": requests.put, "DELETE": requests.delete}[method]
    return fn(url, headers=HEADERS, **({"json": body} if body else {}))
