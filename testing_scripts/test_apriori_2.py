import numpy as np 
import pandas as pd 
import requests
from mlxtend.frequent_patterns import apriori, association_rules 
from mlxtend.preprocessing import TransactionEncoder

# Attempt #1 to use apriori algorithm on hardcoded data and get results
DRUG_OF_INTEREST = 'TRUVADA'
OPENFDA_API_ENDPOINT = 'https://api.fda.gov/drug/event.json'
SEARCH_AFTER_FILENAME = 'FDA_DDI_database/data/search_after_token.json'
DATA_FILENAME = 'FDA_DDI_database/data/fda_data.json'
DRUG_EVENT_FIELDS = ['patient.drug.medicinalproduct', 'patient.reaction.reactionmeddrapt']

def fetch_adverse_events_with_aki(drug_name):
    # Parameters
    results = []
    skip = 0  # Used for pagination
    total_limit = 5000  # Set this to None or a large number if you want to get all records.
    limit_per_request = 1000  # The maximum allowed by openFDA per request is 1000.

    # Define the search query to include AKI
    search_query = f'patient.drug.medicinalproduct:"{drug_name}" AND patient.reaction.reactionmeddrapt.exact:"acute kidney injury"'

    while True:
        params = {
            'search': search_query,
            'limit': limit_per_request,
            'skip': skip
        }
        try:
            response = requests.get(OPENFDA_API_ENDPOINT, params=params)
            response.raise_for_status()
            batch_results = response.json()['results']
            results.extend(batch_results)
            skip += limit_per_request
            print(f"Pagination step (AKI present): {skip}")

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

data = fetch_adverse_events_with_aki(DRUG_OF_INTEREST)

drug_data = []
for event in data:
    patient = event['patient']
    info = patient['drug']
    drugs = []
    for drug in info:
        drugs.append(drug['medicinalproduct'])
    drug_data.append(drugs)



# Print out some information on the original data
# print("LOG: Columns in data\n", data.columns)
# print("LOG: Number of rows in data\n", len(data))

# Formatting the data
# Only using the 'Suspect Product Names' row

# Remove rows that don't have the target drug - greatly reduces time spent in algorithm if done in preprocessing
print("Rows before filtering target drug:", len(drug_data))
filtered_data = [drug_list for drug_list in drug_data if DRUG_OF_INTEREST in drug_list]
print("Rows after filtering target drug:", len(filtered_data))

# Encoder is used by Apriori
te = TransactionEncoder()
te_ary = te.fit(filtered_data).transform(filtered_data)
df_apriori = pd.DataFrame(te_ary, columns=te.columns_)
# This prints out the table neatly showing True/False for every row in the original table, and the drugs
# print(df_apriori)

# Apply Apriori Algorithm
# We can modify min_support: the lower it is, the more results we get, however they might be less reliable
frequent_itemsets = apriori(df_apriori, min_support=0.05, use_colnames=True)

# Collecting the inferred rules in a dataframe 
rules = association_rules(frequent_itemsets, metric ="lift", min_threshold = 1) 
rules = rules.sort_values(['lift'], ascending =[False]) 

# Print all association rules
pd.set_option('display.max_rows', None)
print(rules) 

filtered_rules = rules[(rules['antecedents'] == {(DRUG_OF_INTEREST)})]
print(filtered_rules)