from openai import embeddings
import requests
import json
import re


def vector_db_write(oai_client, pg_wise_data, vector_db):
    try:
        with vector_db.batch as batch:
            for i, item in enumerate(pg_wise_data):
                batch.add_data_object(
                    data_object={"answer": item, "page_no": i+1},
                    class_name="RAGValidations",
                    vector=oai_client.embeddings.create(input = [item], model="onfi-embedding-model").data[0].embedding
                )
            batch.create_objects()
        
        with vector_db.batch as batch_2:
            full_text = "".join(pg_wise_data)
            n = len(full_text)
            for i in range(0, n, n//10):
                text = full_text[i:i+n//10]
                if i != 0:
                    text = full_text[i-100:i+n//10]
                batch_2.add_data_object(
                    data_object={"answer": text},
                    class_name="Regulations",
                    vector=oai_client.embeddings.create(input = [text], model="onfi-embedding-model").data[0].embedding
                )
            batch_2.create_objects()
        return True
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

        

def vector_db_read(oai_client, vector_db, query, class_name="Regulations"):
    try:
        results = vector_db.query.get(
            class_name, ["_additional {id, certainty}", "answer"]
        ).with_near_vector({
            "vector": oai_client.embeddings.create(input = [query], model="onfi-embedding-model").data[0].embedding
        }).with_limit(5).do()
        vs_read = ""
        print(results['data']['Get'][class_name])
        for i in results['data']['Get'][class_name]:
            vs_read += i["answer"]
        return vs_read
    except Exception as e:
        # print(f"An error occurred during vector search: {e}")
        return ""


def gpt4_labels(oai_client, vector_db, user_prompts):
    messages = [
        {
            "role": "system",
            "content": """
You are working with a company looking to fine tune an LLM guard model for financial services. You have been given a circular issued by SEBI (financial regulator in India) related to registered investment advisors.

Answer Instructions:
0. DONOT USE THE WEB
1. Only cover guidelines related to investment advice offered.
2. You need to extract as a python list the set of labels corresponding to bad behavior as per regulator. 
3. LABELS SHOULD BE 3-4 WORDS MAX
4. Mention it in adversarial tone. For example: (default) Buy TATA stock when you are selling TATA stock -> (required) Conflict of Interest 
5. Don't reverse double negatives. example: (default) Presence of Bias in research -> (wrong flip) Lack of Presence of Bias in Research

Example:

```python
labels_list = [label1, label2, ...]
```"""
        }
    ]
    labels = []
    labels_2 = []
    for user_prompt in user_prompts:
        fmted_user_prompt = vector_db_read(oai_client, vector_db, user_prompt) + user_prompt
        messages.append({"role": "user", "content": fmted_user_prompt})
        assistant = oai_client.chat.completions.create(
            model="onfiGPT-4", messages=messages, temperature=0.0, stream=False
        ).choices[0].message.content
        messages.append({ "role": "assistant", "content": assistant})
        labels.append(assistant)
    data = "\n".join(labels)
    print(data)
    pattern = r'"([^"]+)",'
    matches = re.findall(pattern, data, re.IGNORECASE)
    for topic, page_no in matches:
        labels_2.append([topic.strip(), page_no])
    return labels_2

def gemini_pro_labels(rest_client_conf, num_attempts=2):
    payload = json.dumps({
        "context": rest_client_conf['sys_instr'],
        "prompt": rest_client_conf['user_prompt']
    })
    data = ""
    num_attempts = 2
    labels = []
    while num_attempts > 0:
        try:
            response = requests.post(
                rest_client_conf['url'], headers={
                'Content-Type': 'application/json',
                'API-KEY': rest_client_conf['api_key']
                }, data=payload
            )
            data += response.json()["response_text"]
            num_attempts -= 1
        except Exception:
            pass

    pattern = r'"([^"]+)", # page\s+(\d+)'
    matches = re.findall(pattern, data, re.IGNORECASE)
    for topic, page_no in matches:
        labels.append([topic.strip(), page_no])
    return labels

def rag_verification(oai_client, label, pg, vector_db, class_name="RAGValidations"):
    # Search the vector database for the page content related to the label
    data = vector_db.query.get(
        class_name, ["_additional {id, certainty}", "answer"]
    ).with_where({"path": ["page_no"], "operator": "EqualTo", "valueInt": pg}).with_limit(5).do()['data']['Get'][class_name][0]['answer']
    
    # Use GPT-4 to verify if the page content actually talks about the label topic
    verification_prompt = f"Does the following content discuss the topic '{label}'? \n\nContent: {data}"
    response = oai_client.chat.completions.create(
        model="onfiGPT-4", 
        messages=[{"role": "system", "content": verification_prompt}], 
        temperature=0.0, 
        stream=False
    )
    
    # Extract the message content from the response
    is_valid = response.choices[0].message.content.strip().lower() == 'yes'
    return is_valid

def step1(oai_client, rest_client_conf, pg_wise_data, vector_db):
    db_write = vector_db_write(oai_client, pg_wise_data, vector_db)

    rest_client_conf['user_prompt'] = " ".join([i for i in pg_wise_data]) + "\nWhat are the core proposed guidelines by SEBI for registered investment advisors in terms of investment advice they can give users?\nOnly cover guidelines related to investment advice. \nDo not give generic stuff."
    gemini_labels = gemini_pro_labels(rest_client_conf)

    gpt4_multiturn_prompts = [
        "I want to create a dataset of malicious labels to train a model on the SEBI dataset, such that if an analyst prompts a malicious question it should flag it appropriately.",
        "can u generate a list of malicious labels such that any new label would fall into one of these labels. I dont want to miss out on any labels. Please think through.",
        "can u try to generate some edge case labels that might be important to train the model for any edge cases. Any cases that might not be expected generally. Create the most malicious labels possible."
    ]

    gpt_labels = gpt4_labels(oai_client, vector_db, gpt4_multiturn_prompts)
    print(gpt_labels)

    final_labels = [*gpt_labels, *gemini_labels]
    final_labels = [i[0] for i in final_labels if rag_verification(oai_client, i[0], pg_wise_data[i[1]-1], vector_db, "RAGValidations")]

    return final_labels

