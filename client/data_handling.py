import requests
import urllib.parse
import json
import os

import constants

os.chdir(os.path.dirname(os.getcwd()))

# Function to load data
def load_data(filename):
    data = []
    try:
        with open(filename, 'r') as file:
            data = [json.loads(line) for line in file]
    except FileNotFoundError:
        # Handle the case where no data file exists
        print(f"No saved data file found at {filename}.")
        return None
    
    return data

# Function to save data to a file in append mode
def save_data_batch(batch_results, existing_ids):
    updated = False
    if os.path.exists(constants.DATA_FILENAME):
        op = 'a' # append if already exists
    else:
        op = 'w' # make a new file if not
    with open(constants.DATA_FILENAME, op) as file:
        for event in batch_results:
            event_id = event.get('safetyreportid')  # 'safetyreportid' is the unique identifier for adverse event case reports
            if event_id and event_id not in existing_ids:
                # Extract only the drug names from each event's drugs (the drugs that had interacted with drug_of_interest)
                drugs_in_event = {drug_info.get('medicinalproduct', '').lower() for drug_info in event.get('patient', {}).get('drug', [])}
                if constants.DRUG_OF_INTEREST.lower() in drugs_in_event:
                    # Create a reduced record containing only the drug names and AKI reaction if it's present
                    reduced_record = {
                        'safetyreportid': event_id,
                        'drugs': list(drugs_in_event),
                        'aki_report': any(reaction.get('reactionmeddrapt', '').lower() == 'acute kidney injury' for reaction in event.get('patient', {}).get('reaction', []))
                    }
                    file.write(json.dumps(reduced_record) + '\n')  # Write each reduced record as a new line
                    existing_ids.add(event_id)
                    updated = True
    if updated:            
        print(f"Saved data to {constants.DATA_FILENAME}")
    
    return updated

# Function to load the search_after token from a file
def load_search_after_token(token_type):
    try:
        with open(constants.SEARCH_AFTER_FILENAME, 'r') as file:
            tokens = json.load(file)
        return tokens.get(token_type)
    except FileNotFoundError:
        return None

# Function to save the search_after token to a file for next use
def save_search_after_token(token_type, new_token):
    # Load the existing tokens
    try:
        with open(constants.SEARCH_AFTER_FILENAME, 'r') as file:
            tokens = json.load(file)
    except FileNotFoundError:
        # If the file does not exist, initialize an empty dictionary
        tokens = {'AND': None, 'NOT': None}
    
    # Update the relevant token
    tokens[token_type] = new_token
    
    # Save the updated tokens back to the file
    with open(constants.SEARCH_AFTER_FILENAME, 'w') as file:
        json.dump(tokens, file)

def parse_link_header(link_header):
    links = link_header.split(',')
    next_link = [link for link in links if 'rel="next"' in link]
    if next_link:
        next_url = next_link[0].split(';')[0].strip('<>')
        return next_url
    return None

def load_existing_ids():
    existing_ids = set()
    try:
        with open(constants.DATA_FILENAME, 'r') as file:
            for line in file:
                record = json.loads(line)
                existing_ids.add(record.get('safetyreportid'))
    except FileNotFoundError:
        pass  # It's fine if the file doesn't exist yet
    return existing_ids

# Function to fetch data using the search_after feature
def fetch_data_(token_type):
    existing_ids = load_existing_ids()  # Load the set of existing record IDs
    token = load_search_after_token(token_type)  # Load the last search_after token if it exists

    while True:
        if token:
            api_url = f"{constants.OPENFDA_API_ENDPOINT}?search=patient.drug.medicinalproduct%3A%22{constants.DRUG_OF_INTEREST}%22%20{token_type}%20patient.reaction.reactionmeddrapt.exact%3A%22acute%20kidney%20injury%22&limit=1000&sort=receivedate%3Aasc&skip=0&search_after={token}"
        else:
            api_url = f"{constants.OPENFDA_API_ENDPOINT}?search=patient.drug.medicinalproduct%3A%22{constants.DRUG_OF_INTEREST}%22%20{token_type}%20patient.reaction.reactionmeddrapt.exact%3A%22acute%20kidney%20injury%22&limit=1000&sort=receivedate%3Aasc"
        
        response = requests.get(api_url)
        response.raise_for_status()
        batch_results = response.json().get('results', [])
        
        # Save the batch immediately to the file
        updated = save_data_batch(batch_results, existing_ids)

        # Check for the 'Link' header for the next page URL
        if 'Link' in response.headers:
            link_header = response.headers['Link']
            next_url = parse_link_header(link_header)
            print(next_url)
            if next_url:
                # Extract search_after value for the next request
                token = next_url.split('search_after=')[1].split('&')[0]
            else:
                break
        else:
            break

    # Save the last search_after token for future updates
    if updated:
        save_search_after_token(token, token_type)

def fetch_data():
    token_types = ['AND', 'NOT']
    for t in token_types:
        fetch_data_(t)