import os
import requests
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
from data_handling import fetch_data, load_data

import constants



# Function to create transactions with and without AKI
def create_transactions(data, drug_of_interest):
    transactions_with_aki = []
    transactions_without_aki = []

    for event in data:
        transaction = set(event['drugs'])
        if drug_of_interest.upper() in transaction:
            if event['aki_report']:
                transactions_with_aki.append(transaction)
            else:
                transactions_without_aki.append(transaction)

    return transactions_with_aki, transactions_without_aki
# Function to apply the association rule mining
def association_rule_mining(data, min_support):
    
    # Initialize the TransactionEncoder
    te = TransactionEncoder()
    te_ary = te.fit(data).transform(data)
    df_apriori = pd.DataFrame(te_ary, columns=te.columns_)

    # Apply the Apriori algorithm to get frequent itemsets
    # We can modify min_support: the lower it is, the more results we get, however they might be less reliable and take longer
    frequent_itemsets = apriori(df_apriori, min_support=min_support, use_colnames=True)

    # print("DEBUG Frequent itemsets:", frequent_itemsets.head())

    if frequent_itemsets.empty:
        print('No frequent itemsets found. You may need to lower the min_support.')
        return pd.DataFrame()

    # Generate the rules with their corresponding support, confidence, and lift
    rules = association_rules(frequent_itemsets, metric='lift', min_threshold=1)

    # print("DEBUG Generated rules:", rules.head())

    return rules

def sorting_function(e):
  return e['ddi_index']

# Function to extract DDI index from association rules for meaningful drug-drug interactions
def extract_ddi_index(rules, drug, symptom):
    '''
    # Previous logic
    ddi_index_list = []
    for _, rule in association_rules.iterrows():
        if symptom not in rule['antecedents']:
            ddi_index_list.append({
                'drug_combination': ', '.join(sorted(rule['antecedents'])),
                'ddi_index': rule['lift'],
                'confidence': rule['confidence'],
                'support': rule['support']
            })
    return ddi_index_list
    '''
    
    # Filtered rules contain those with SYMPTOM=1 in their consequent

    # All rules now have the form {___} -> {Symtom = 1}
    filtered_rules = rules[(rules['consequents'] == {(symptom.upper())})]

    # print("filtered rules, ", filtered_rules)

    drug_of_interest = filtered_rules[(filtered_rules['antecedents'] == {(drug.upper())})]
    if drug_of_interest.empty:
        # Use 1 for the ratio instead
        drug_of_interest_lift = 1 
    else:
        drug_of_interest_lift = drug_of_interest['lift']

    # calculate DDI indexes
    # All rules in correlated are now in the form of {Drug Of Interest=1, Other Drug = 1} -> {Symptom = 1}
    correlated_drug_rules = filtered_rules[(filtered_rules['antecedents'].apply(lambda x: drug.upper() in x)) & 
                            (filtered_rules['antecedents'].apply(lambda x: len(x) == 2))]

    # print("correlated rules, ", correlated_drug_rules)
    lift_antecedent_pairs = []

    for _, row in correlated_drug_rules.iterrows():
        lift_value = row['lift']
        antecedent_values = row['antecedents']
        antecedent_value = None
        for val in antecedent_values:
            if val != drug.upper():
                antecedent_value = val
        
        # These are the values to display
        lift_antecedent_pairs.append({
                'drug_combination': antecedent_value,
                'ddi_index': lift_value/drug_of_interest_lift,
            })
    # print("final lift rules", lift_antecedent_pairs)
    lift_antecedent_pairs.sort(key=sorting_function, reverse=False)
    # print("final lift rules", lift_antecedent_pairs)
    return lift_antecedent_pairs

# Function to calculate Reporting Odds Ratio (ROR)
def calculate_ror(drug_of_interest, symptom):
    #A: Count: drug taken, event occurs
    a_query = f'https://api.fda.gov/drug/event.json?search=patient.drug.medicinalproduct:{drug_of_interest}+AND+patient.reaction.reactionmeddrapt:"{symptom}"&count=patient.reaction.reactionmeddrapt.exact'
    #B: Count: drug taken, even does not occur
    b_query = f'https://api.fda.gov/drug/event.json?search=patient.drug.medicinalproduct:{drug_of_interest}+NOT+patient.reaction.reactionmeddrapt:"{symptom}"&count=patient.reaction.reactionmeddrapt.exact'
    #C: Count: drug is not taken, event occurs.
    c_query = f'https://api.fda.gov/drug/event.json?search=NOT+patient.drug.medicinalproduct:{drug_of_interest}+AND+patient.reaction.reactionmeddrapt:"{symptom}"&count=patient.reaction.reactionmeddrapt.exact'
    #D: Count: drug is not taken, even does not occur
    d_query = f'https://api.fda.gov/drug/event.json?search=NOT+patient.drug.medicinalproduct:{drug_of_interest}+NOT+patient.reaction.reactionmeddrapt:"{symptom}"&count=patient.reaction.reactionmeddrapt.exact'

    a_response = requests.get(a_query).json()
    b_response = requests.get(b_query).json()
    c_response = requests.get(c_query).json()
    d_response = requests.get(d_query).json()

    a_count = 0
    for i in a_response['results']:
        if i['term'] == 'ACUTE KIDNEY INJURY':
            a_count = i['count']

    b_count = 0
    for i in b_response['results']:
        if i['count']:
            b_count += i['count']

    c_count = 0
    for i in c_response['results']:
        if i['term'] == 'ACUTE KIDNEY INJURY':
            c_count = i['count']

    d_count = 0
    for i in d_response['results']:
        if i['count']:
            d_count = i['count']

    #print(a_count, b_count, c_count, d_count)
    # Calculate ROR
    ror = (c_count / a_count) / (d_count / b_count)
    return ror

def print_ddi_analysis_results(aki_cases, ddi_potential, association_rules, drug_of_interest):
    # Print the number of AKI cases
    print(f"Number of AKI cases: {aki_cases}")
    
    # Print the DDI potential (ROR)
    print(f"DDI potential: {ddi_potential:.2f} (ROR values) {ddi_potential:.2f} fold increase in AKI risk.")
    
    # Calculate DDI index and print
    print("DDI index:")
    ddi_index_list = []
    for _, rule in association_rules.iterrows():
        # Ensure that the rule is for the drug of interest and that AKI is a consequent
        if drug_of_interest in rule['antecedents']:
            # Calculate the DDI index as per the lift value
            ddi_index = rule['lift']
            # Extract other drugs in the rule
            other_drugs = rule['antecedents'] - set([drug_of_interest])
            # Append to the list including the drug names and their DDI index
            ddi_index_list.append((other_drugs, ddi_index))
    
    # Sort the list by DDI index in descending order and print
    ddi_index_list.sort(key=lambda x: x[1], reverse=True)
    for drugs, ddi_index in ddi_index_list:
        drug_names = ''.join(drugs)
        print(f"{drug_names}, {ddi_index:.2f}")

'''
Instead of hardcoded, try and query the API
'''

def fetch_events(drug_name):
    # Parameters
    results = []
    skip = 0  # Used for pagination
    total_limit = 1000  # Set this to None or a large number if you want to get all records.
    limit_per_request = 1000    # The maximum allowed by openFDA per request is 1000.

    # Define the search query to include AKI
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


# Main function to orchestrate the DDI analysis
def run_analysis(drug_name, symptom, min_support):
    print("Fetching adverse effect data...")
    # Load saved data
    # print(os.getcwd())
    data = fetch_events(drug_name)
    
    if data:
        # Prepare the transactions for mining
        print("Preprocessing data for mining...")
        processed_data, transactions_with_symptom, transactions_without_symptom = filter_raw_API_data(data, symptom)   
        print("Total cases with symptom: ", transactions_with_symptom)
        print("Total cases without symptom: ", transactions_without_symptom)

        # Calculate Rate of Return
        print("Calculating ROR...")
        ddi_potential = calculate_ror(drug_name, symptom)
        
        print("Mining association rules...")
        rules = association_rule_mining(processed_data, float(min_support))
        print("Finished mining association rules...")
        # Do not need these for analysis, only need counts
        #association_rules_without_aki = association_rule_mining(transactions_without_aki)
        

        ddi_index = extract_ddi_index(rules, drug_name, symptom)
        # Print results
        # print_ddi_analysis_results(aki_cases, ddi_potential, association_rules_with_aki, constants.DRUG_OF_INTEREST)
        # print(ddi_index)
        
        return {
            'drug_name': drug_name,
            'aki_cases': transactions_with_symptom,
            'non_aki_cases': transactions_without_symptom,
            'ddi_potential': ddi_potential,
            'ddi_index': ddi_index
        }
    else:
        return {
            'drug_name': drug_name,
            'aki_cases': None,
            'non_aki_cases': None,
            'ror': None,
            'ddi_index': None
        }
    
def filter_raw_API_data(data, symptom):
    # Cleaning the data to only what we need
    drug_data = []
    with_symptom_count = 0
    without_symptom_count = 0
    for event in data:
        patient = event['patient']
        drug = patient['drug']
        reaction = patient['reaction']
        drugs = []
        for d in drug:
            drugs.append(d['medicinalproduct'])
        for r in reaction:
            # print(r)
            name = r['reactionmeddrapt']
            if name.upper()==symptom.upper():
                drugs.append(name.upper())
                with_symptom_count += 1
            else:
                without_symptom_count += 1
        
        drug_data.append(drugs)
    
    return drug_data, with_symptom_count, without_symptom_count

def filter_data(drug_of_interest: str, symptom: str, min_support: float):
    try:
        ddi_analysis = run_analysis(drug_of_interest, symptom, min_support) 

        print("ddi_analysis :\n")
        print(ddi_analysis.keys())

        filtered_data = []
        seen_combinations = set()

        for entry in ddi_analysis['ddi_index']:
            combination = entry['drug_combination']
            if combination not in seen_combinations:
                filtered_data.append(entry)
                seen_combinations.add(combination)

        filtered_data = sorted(filtered_data, key=lambda x: x['ddi_index'])
        filtered_data = [[entry['drug_combination'], entry['ddi_index']] for entry in filtered_data]

        return filtered_data
    except:
        return []

# useful for testing
if __name__ == "__main__":
    drug_of_interest = "Truvada"
    symptom = "Acute kidney injury"
    print(run_analysis(drug_of_interest, symptom, .005))


