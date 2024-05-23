import groq
from groq import Groq
import requests
import json
from IPython.display import HTML
from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from openai import OpenAI
import re
import json
import fitz  
final_labels = [
    "Unsegregated Advisory Distribution",
    "Forced Asset Liquidation",
    "Unverified Client Segregation",
    "Non-Disclosure of Fees",
    "Unapproved Risk Profiling",
    "Cash Fee Acceptance",
    "Undisclosed Complaints Status",
    "Conflict of Interest",
    "Manipulative Market Conduct",
    "Guaranteed Returns Offer",
    "Unauthorized Fund Handling",
    "Unverified Information Circulation",
    "Unrestricted Blog Access",
    "Non-Compliant Advertisement",
    "Misuse of SEBI Logo",
    "Outsourcing Core Activities",
    "Neglecting KYC Procedures",
    "Indiscriminate Client Risk Profiling",
    "Undisclosed Conflict Interest",
    "Data Privacy Breach",
    "Unlawful Information Sharing",
    "Neglected Client Segregation",
    "Unauthorized Advisory Claims",
    "Inadequate Disaster Recovery",
    "Unregulated Outsourcing Practices",
    "Misleading Performance Assurance",
    "Compromised Regulatory Compliance",
    "Misleading Testimonials",
    "Unrealistic Projections",
    "Past Performance Reference",
    "Free Service Misrepresentation",
    "Discrediting Competitors",
    "Unsuitable Product Incentive",
    "False Advertising Claims",
    "Exaggerated Service Quality",
    "Non-Disclosure of Risks",
    "Unapproved Advertisement Material",
    "Improper Segregation of Services"
]

# returns heading via groq
def get_heading(text_content):
    system_prompt = """  
        You are a text summary title generation tool in the finance domain, designed to generate very sharp and consise headings based on detailed text content.
        
        Input Details:  
        1. Text content provided by the user  
        
        Task: Your task is to generate very short and sharp heading based on the provided text content. I will be searching this heading on google. I should get relevant news articles.
        """
    
    ideal_output = [
        {"role": "system", "content": system_prompt}, 
        {"role": "user", "content": """One example of SEBI taking action against a company for market manipulation violations is the case of BPL Limited. In this case, SEBI investigated and found that BPL Limited had indulged in violating regulation 4(a) and (d) of the 1995 Regulations, which prohibit fraudulent and unfair trade practices. The investigation revealed that the company had created a false market and manipulated the prices of its scrip in connivance with Harshad Mehta by aiding, abetting, and being instrumental in effecting transactions. SEBI issued show cause notices to the company and its officers/directors, asking them to explain their conduct. After adjudicating the show cause notice, SEBI confirmed the charges and passed an order directing the company to cease and desist from accessing the capital market for a period of three years.
This case demonstrates SEBI's efforts to prevent market manipulation and protect the interests of investors in the Indian securities market. SEBI's actions in this case are in line with its mandate to regulate the securities market and prevent fraudulent and unfair trade practices."""}, 
        {"role": "assistant", "content": "SEBI vs Samir Arora: SEBI takes action against HDFC Bank "},
        {"role": "user", "content": text_content}
        ]

    client = Groq(api_key='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')
    completion = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=ideal_output,
        temperature=0,
        max_tokens=100,
        top_p=1
    )
    title_text = completion.choices[0].message.content
    return title_text

# returns url
def bing_engine(ques):
    ques = """Samir Arora**: SEBI took action against Samir Arora"""
    headers = {"Ocp-Apim-Subscription-Key" : subscription_key}
    params  = {"q": ques, "textDecorations": True, "textFormat": "HTML"}

    response = requests.get(search_url, headers=headers, params=params)
    response.raise_for_status()
    search_results = response.json()  # Parse JSON response into a dictionary

    # print(search_results)
    urls = [article["url"] for article in search_results["value"]]
    # print(urls)

    description = [article["description"] for article in search_results["value"]]
    # print(description)
    # rows = "\n".join(["<tr><td>{0}</td></tr>".format(desc) for desc in descriptions])

    # html_content = HTML("<table>"+rows+"</table>")
    # html_content
    return urls 

#returns urls
def google_engine(ques):
    base_url = f"https://www.googleapis.com/customsearch/v1?key={API_KEY}&cx={SEARCH_ENGINE_ID}&q={ques}"
    try:
        response = requests.get(base_url)
        response.raise_for_status()  # Raises HTTPError for bad responses
        data = response.json()
        return [item["link"] for item in data.get("items", [])]
    except requests.exceptions.HTTPError as errh:
        print(f"HTTP Error: {errh}")
    except requests.exceptions.ConnectionError as errc:
        print(f"Error Connecting: {errc}")
    except requests.exceptions.Timeout as errt:
        print(f"Timeout Error: {errt}")
    except requests.exceptions.RequestException as err:
        print(f"Error: {err}")
    return [] 

#checks for valid url
def is_valid_url(link):
    """Checks if the link is a valid URL with http or https scheme."""
    return link.startswith("https://") or link.startswith("http://")

#using re to filter out texts
def clean_text(text):
    text_no_urls = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA]))+', '', text)
    text_no_non_ascii = re.sub(r'[^\x00-\x7F]+', '', text_no_urls)
    cleaned_text = re.sub(r'[^\w\s]', '', text_no_non_ascii)
    return cleaned_text

#cleans dicts by re for long pdfs n websites
def clean_dict(data):
    for src, nested_dict in data.items():
        if isinstance(nested_dict, dict):
            for key, text in nested_dict.items():
                if isinstance(text, str):
                    nested_dict[key] = clean_text(text)
    return data

#uses fitz to extract from pdf
def extract_pdf_text(pdf_url):
    response = requests.get(pdf_url)
    response.raise_for_status()
    pdf_document = fitz.open(stream=response.content, filetype="pdf")
    text = ""
    print('pdf read:200')
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        text += page.get_text("text")
    return text

#scarping engine w pdf logic
def text_builder(urls):
    """Generate a schema where each source maps to a dictionary containing the index and its full concatenated text."""
    extracted_text = {}
    clean_extracted_text = {}

    for index, link in enumerate(urls, start=1):
        try:
            response = requests.head(link)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type')
            
            if content_type and 'pdf' in content_type.lower():
                combined_link_text = extract_pdf_text(link)
            else:
                response = requests.get(link)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                texts = list(soup.stripped_strings)
                combined_link_text = ' '.join(texts)
            
            # Store the index as a sub-key inside the source dictionary
            if link not in extracted_text:
                extracted_text[link] = {}
            extracted_text[link][index] = combined_link_text

            print(f'Text from {link} ...done')
        except requests.RequestException as e:
            print(f"Error fetching URL {link}: {e}")
            continue

    clean_extracted_text = clean_dict(extracted_text)
    return clean_extracted_text

#storing in defined format
def store_info(total_store, label_name, case_studies, link_text):
    if label_name not in total_store:
        total_store[label_name] = {
            'case_studies': [case_studies],  # Wrap in list if multiple entries expected
            'link_text': [link_text]  # Wrap in list if multiple entries expected
        }
    else:
        total_store[label_name]['case_studies'].append(case_studies)
        total_store[label_name]['link_text'].append(link_text)
    return total_store

#pplx client
def get_example_summary(ppx_client, label,used_examples):
    messages = [
    {
        "role": "system",
        "content": (
            f"""You are a finance consultant tasked with providing a strong and detailed case study of SEBI enforcement actions against companies/entities for a specific violation. 
            Task: 
            Create a comprehensive, highly technical summary of SEBI's action.

            Strict Rules:
            1. DO NOT use any examples from here: {str(used_examples)}. 

            Instructions:
            1. Focus on one specific violation: {label}.
            2. Deliver one detailed 400-token summary of SEBI's action for the specified violation.
            3. Ensure the summary is accurate and highly technical, with no fabricated information.
            4. Select a strong example that effectively illustrates SEBI's regulatory impact.
            """
        ),
    },
    {
        "role": "user",
        "content": (
            f"Provide a strong example of SEBI taking action against a company for {label} violations."
        ),
    },  
]

    # print(messages)

    response = ppx_client.chat.completions.create(
        model="llama-3-sonar-small-32k-online",
        messages=messages,
        max_tokens = 1024,
        temperature=0.2
    )

    content = response.choices[0].message.content
    return content
