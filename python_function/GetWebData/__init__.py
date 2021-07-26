import logging
import json
import os 
from pprint import pprint
import requests
from bs4 import BeautifulSoup
import re

import azure.functions as func

def main(req: func.HttpRequest, outputblob: func.Out[str]) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    # Query term(s) to search for. 
    query = req.params.get('query')
    if not query:
        query = "Nuclear Medicine"
    logging.info(f'Query : {query}')

    # Use custom Bing Search API
    response = call_custom_bing_search(query)

    # Get list of URL to scrap
    url_list = get_url_list(response)
    
    # Get data for each URL
    crps = []
    for url in url_list:
        crps.append(get_crp_data(url))

    crp_json = json.dumps(crps)

    # Write data to a blob file
    outputblob.set(crp_json)
    logging.info("Website content sent to blob")

    return func.HttpResponse(
        f'Called URLs: {str(url_list)}',
        status_code=response.status_code
    )


def call_custom_bing_search(query):
    # Get the Bing Search API information
    subscription_key = os.environ.get('SubscriptionKey') 
    custom_config_id = os.environ.get('ConfigId') 
    endpoint = "https://api.bing.microsoft.com/v7.0/custom/search"

    # Construct the request
    mkt = 'en-US'
    params = { 'q': query, 'customconfig': custom_config_id, 'mkt': mkt, 'count': 20 }
    headers = { 'Ocp-Apim-Subscription-Key': subscription_key }

    try:
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()
    except Exception as ex:
        raise ex
    
    return response


def get_url_list(response):
    search_result = response.json()['webPages']
    url_list = []

    for web_pages in search_result['value']:
        url_list.append(web_pages['url'])

    return url_list

def get_crp_data(url):
    # Create new crp object
    crp = {}

    #Prepare the soup
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')

    title = soup.find('h1')
    project_type = soup.find('div', class_='field-project-type')
    project_approved_date = soup.find('span', class_='date-display-single')
    project_status = soup.find('div', class_='field-project-status')
    project_start_date = soup.find('div', class_='field-project-start-date').find('span', class_='date-display-single')
    expected_end_date = soup.find('div', class_='field-project-expected-end-date').find('span', class_='date-display-single')
    project_description = soup.find('div', class_='field-project-body')
    project_objectives = soup.find('div', class_='field-project-objectives')
    project_specific_objectives = soup.find('div', class_='field-specific-objectives')
    project_impact = soup.find('div', class_='field-project-impact')
    project_relevance = soup.find('div', class_='field-project-relevance')
    participating_countries = soup.find('div', class_='pane-node-field-participating-countries').find_all('div', class_='field-participating-countries')
    countries = []
    if participating_countries != []:
        for country in participating_countries:
            countries.append(country.text.strip())

    # Get CRP info
    crp = {
        "title": title.text.strip() if title is not None else title,
        "project_type": project_type.text.strip() if project_type is not None else project_type,
        "project_approved_date": project_approved_date.text.strip() if project_approved_date is not None else project_approved_date,
        "project_status": project_status.text.strip() if project_status is not None else project_status,
        "project_start_date": project_start_date.text.strip() if project_start_date is not None else project_start_date,
        "expected_end_date": expected_end_date.text.strip() if expected_end_date is not None else expected_end_date,
        "participating_countries": countries,
        "project_description": clean(project_description.text.strip()) if project_description is not None else project_description,
        "project_objectives": clean(project_objectives.text.strip()) if project_objectives is not None else project_objectives,
        "project_specific_objectives": clean(project_specific_objectives.text.strip()) if project_specific_objectives is not None else project_specific_objectives,
        "project_impact": clean(project_impact.text.strip()) if project_impact is not None else project_impact,
        "project_relevance": clean(project_relevance.text.strip()) if project_relevance is not None else project_relevance
    }
    return crp

def clean(text):
    t = text.replace("\\", "")
    return t.replace("\"", "")