import requests
import json
import os
import hashlib
from os.path import abspath
import constants

#os.chdir(os.path.dirname(os.getcwd()))

def get_cache_filename(drug_name, skip):
    # Generate a unique filename for caching based on the drug name and pagination step
    hashed_key = hashlib.md5(f"{drug_name}_{skip}".encode('utf-8')).hexdigest()
    return f"cache_{hashed_key}.json"

def fetch_data(drug_name):
    results = []
    skip = 0
    total_limit = 5000
    limit_per_request = 1000

    while True:
        cache_filename = get_cache_filename(drug_name, skip)
        filepath = f"cached_results/{cache_filename}"

        if os.path.exists(filepath):
            # Read from cache if available
            with open(filepath, 'r') as file:
                batch_results = json.load(file)
            print(f"Loaded data from cache for {drug_name} at skip {skip}")
        else:
            try:
                # Fetch data from the API
                params = {'search': f'patient.drug.medicinalproduct:"{drug_name}"',
                          'limit': limit_per_request, 'skip': skip}
                response = requests.get(constants.OPENFDA_API_ENDPOINT, params=params)
                response.raise_for_status()
                batch_results = response.json()['results']

                # Cache the results
                with open(filepath, 'w') as file:
                    json.dump(batch_results, file)

                print(f"Fetched and cached data for {drug_name} at skip {skip}")

            except requests.HTTPError as http_err:
                print(f"HTTP error occurred: {http_err}")
                break
            except Exception as err:
                print(f"An error occurred: {err}")
                break

        results.extend(batch_results)
        skip += limit_per_request

        if len(batch_results) < limit_per_request or (total_limit and skip >= total_limit):
            break

    return results

def fetch_events(drug_name):
    # Parameters
    results = []
    skip = 0  # Used for pagination
    total_limit = 1000  # Set this to None or a large number if you want to get all records.
    limit_per_request = 1000    # The maximum allowed by openFDA per request is 1000.

    # Define the search query
    search_query = f'patient.drug.medicinalproduct:"{drug_name}"'

    while True:
        params = {
            'search': search_query,
            'limit': limit_per_request,
            'skip': skip
        }
        try:
            response = requests.get(constants.OPENFDA_API_ENDPOINT, params=params)
            response.raise_for_status()
            batch_results = response.json()['results']
            results.extend(batch_results)
            skip += limit_per_request
            print(f"Pagination step: {skip}")
            

            # Check if the last page has been reached or if a total limit has been set and reached
            if len(batch_results) < limit_per_request or (total_limit and skip >= total_limit):
                break

        except requests.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            break
        except Exception as err:
            print(f"An error occurred: {err}")
            break
        
    return results