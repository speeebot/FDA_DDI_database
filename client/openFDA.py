import os
import requests
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
from data_handling import fetch_data, load_data

import constants

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 150)


# Function to create transactions with and without AKI
def create_transactions(data, drug_of_interest):
    transactions_with_aki = []
    transactions_without_aki = []

    for event in data:
        transaction = set(event['drugs'])
        if drug_of_interest.lower() in transaction:
            if event['aki_report']:
                transactions_with_aki.append(transaction)
            else:
                transactions_without_aki.append(transaction)

    return transactions_with_aki, transactions_without_aki
# Function to apply the association rule mining
def association_rule_mining(transactions, min_support):
    
    print(f'min support: {min_support}')
    # Initialize the TransactionEncoder
    te = TransactionEncoder()
    te_ary = te.fit(transactions).transform(transactions)
    df = pd.DataFrame(te_ary, columns=te.columns_)

    # Apply the Apriori algorithm to get frequent itemsets
    frequent_itemsets = apriori(df, min_support=float(min_support), use_colnames=True)

    print("DEBUG Frequent itemsets:", frequent_itemsets.head())

    if frequent_itemsets.empty:
        print('No frequent itemsets found. You may need to lower the min_support.')
        return pd.DataFrame()

    # Generate the rules with their corresponding support, confidence, and lift
    rules = association_rules(frequent_itemsets, metric='lift', min_threshold=1)

    print("DEBUG Generated rules:", rules.head())

    return rules

# Function to extract DDI index from association rules for meaningful drug-drug interactions
def extract_ddi_index(association_rules, symptom):
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

# Main function to orchestrate the DDI analysis
def run_analysis(drug_name, symptom, min_support):
    print("Loading saved adverse effect data...")
    # Load saved data
    # print(os.getcwd())
    print(constants.DATA_FILENAME)
    data = load_data(constants.DATA_FILENAME)
    
    if data:
        # Prepare the transactions for mining
        print("Preprocessing data for mining...")
        transactions_with_aki, transactions_without_aki = create_transactions(data, drug_name)
        
        # Calculate Rate of Return
        print("Calculating ROR...")
        aki_cases = len(transactions_with_aki)
        non_aki_cases = len(transactions_without_aki)
        #print(f"Number of AKI cases for {drug_name}: {aki_cases}, Number of non-AKI cases for {drug_name}: {non_aki_cases}")
        ddi_potential = calculate_ror(drug_name, symptom)
        
        print("Mining association rules...")
        association_rules_with_aki = association_rule_mining(transactions_with_aki, min_support)
        # Do not need these for analysis, only need counts
        #association_rules_without_aki = association_rule_mining(transactions_without_aki)

        ddi_index = extract_ddi_index(association_rules_with_aki, symptom)
        # Print results
        # print_ddi_analysis_results(aki_cases, ddi_potential, association_rules_with_aki, constants.DRUG_OF_INTEREST)
        
        return {
            'drug_name': drug_name,
            'aki_cases': aki_cases,
            'non_aki_cases': non_aki_cases,
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

if __name__ == "__main__":

    drug_of_interest = "Vancomycin"
    symptom = "acute kidney injury"
    print(filter_data(drug_of_interest, symptom))
#     ddi_analysis = run_analysis(drug_of_interest, symptom) 

#     # Create a new list to store filtered data
#     filtered_data = []
#     # Create a set to keep track of seen 'drug_combination' values
#     seen_combinations = set()

#     for entry in ddi_analysis['ddi_index']:
#         combination = entry['drug_combination']
#         if combination not in seen_combinations:
#             filtered_data.append(entry)
#             seen_combinations.add(combination)

#     filtered_data = sorted(filtered_data, key=lambda x: x['ddi_index'])
#     filtered_data = [[entry['drug_combination'], entry['ddi_index']] for entry in filtered_data]


#     print("testing :\n")
#     print(len(filtered_data))
#     print(type(filtered_data))
#     for i in range(10):
#         print(type(filtered_data[i]))
#         print(filtered_data[i])