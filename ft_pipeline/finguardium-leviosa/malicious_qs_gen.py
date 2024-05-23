# Label Search + Malicious Q Gen -> Harshith

from step2funs import *
from groq import Groq
from urllib.parse import urlparse, urljoin
from urllib.parse import urlparse
from openai import OpenAI
import time


search_url = "https://api.bing.microsoft.com/v7.0/news/search"


API_KEY = "AIzaSyDMXlOxb2PPlLJofl0sqEzBGVJPfwLstOA"
SEARCH_ENGINE_ID = "e2fd271d0f6d641d3"

YOUR_API_KEY = "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"

ppx_client = OpenAI(api_key=YOUR_API_KEY, base_url="https://api.perplexity.ai")

no_of_cases =4

def step_2(oai_client, labels):
    test_labels = ['Market manipulation']
    final_store = {}
    used_examples = []
    final_backup= {}
    support_links = []

    for lab in test_labels:
        print(f'starting for {lab}')
        for case in range(no_of_cases):
        # k is the number of case studis we want. 
            support_links =[]
            src_links = []
            case_summary = get_example_summary(ppx_client, lab, used_examples)
            time.sleep(1)
            case_heading = get_heading(case_summary)
            used_examples.append(case_heading)
            support_links = google_engine(case_heading)
            if support_links == []:
                support_links = bing_engine(case_heading)
            src_links = support_links[:3]
            text_content = text_builder(src_links)
            print('text_content build success')
            # Update final_store directly inside thes loop
            final_store = store_info(final_store, lab,case_summary,text_content)
            final_backup.update(final_store)

    return final_backup
