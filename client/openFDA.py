import os
import requests
import pandas as pd
from mlxtend.frequent_patterns import apriori, fpgrowth, association_rules
from mlxtend.preprocessing import TransactionEncoder
from data_handling import fetch_data, fetch_events
from scipy.stats import chi2_contingency

import constants

# Function to apply the association rule mining
def association_rule_mining(transactions, min_support):
    # Initialize TransactionEncoder
    te = TransactionEncoder()
    te_ary = te.fit(transactions).transform(transactions)
    df = pd.DataFrame(te_ary, columns=te.columns_)

    # Apply the Apriori algorithm to get frequent itemsets
    # We can modify min_support: the lower it is, the more results we get, however they might be less reliable and take longer
    frequent_itemsets = apriori(df, min_support=min_support, use_colnames=True)

    #print("DEBUG Frequent itemsets:", frequent_itemsets.head())

    if frequent_itemsets.empty:
        print('No frequent itemsets found. You may need to lower the min_support.')
        return pd.DataFrame()

    # Generate the rules with their corresponding support, confidence, and lift
    rules = association_rules(frequent_itemsets, metric='lift', min_threshold=1)

    # print("DEBUG Generated rules:", rules.head())

    return rules

# Constructs the 2x2 contingency table for calculating ROR
def generate_contingency_table(data, drug_names, symptom):
    symptom_with_drug_a_only = 0
    symptom_with_drug_a_and_others = 0
    no_symptom_with_drug_a_only = 0
    no_symptom_with_drug_a_and_others = 0

    for entry in data:
        drugs_in_report = [drug['medicinalproduct'].upper() for drug in entry['patient']['drug']]
        reactions_in_report = [reaction['reactionmeddrapt'].upper() for reaction in entry['patient']['reaction']]

        # Check if symptom is reported
        symptom_reported = symptom in reactions_in_report
        # Check if only drug of interest is reported
        only_drug_a_reported = any(drug_name in drugs_in_report for drug_name in drug_names) and len(drugs_in_report) == 1

        if symptom_reported and only_drug_a_reported:
            symptom_with_drug_a_only += 1
        elif symptom_reported and not only_drug_a_reported:
            symptom_with_drug_a_and_others += 1
        elif not symptom_reported and only_drug_a_reported:
            no_symptom_with_drug_a_only += 1
        elif not symptom_reported and not only_drug_a_reported:
            no_symptom_with_drug_a_and_others += 1

    #print(aki_with_drug_a_only, aki_with_drug_a_and_others, no_aki_with_drug_a_only, no_aki_with_drug_a_and_others)
    # Construct the 2x2 contingency table
    contingency_table = [[symptom_with_drug_a_only, symptom_with_drug_a_and_others],
                         [no_symptom_with_drug_a_only, no_symptom_with_drug_a_and_others]]

    return contingency_table, symptom_with_drug_a_only + symptom_with_drug_a_and_others

# Function to calculate Reporting Odds Ratio (ROR)
def calculate_ror(contingency_table):
    odds_ratio, p_value = chi2_contingency(contingency_table)[:2]
    return odds_ratio, p_value

def get_transactions(data, drug_names, symptom):
    transactions = []
    potential_interactors = set()
    drug_names = set(name.upper() for name in drug_names)
    symptom = symptom.upper()

    for report in data:
        transaction = set()
        drugs_in_report = [drug['medicinalproduct'].upper() for drug in report['patient']['drug']]
        reactions_in_report = [reaction['reactionmeddrapt'].upper() for reaction in report['patient']['reaction']]

        # Check if symptom is reported and if drug of interest (brand or generic) is in the report
        if symptom in reactions_in_report and any(drug_name in drugs_in_report for drug_name in drug_names):
            transaction.add('DRUG OF INTEREST')  # Unified identifier for drug of interest
            
            # Add other drugs in the report to the transaction and potential interactors
            for drug in drugs_in_report:
                if drug not in drug_names:
                    transaction.add(drug)
                    potential_interactors.add(drug)

            # Add symptom of interest to the transaction
            transaction.add(symptom)

        # Add the transaction to the list
        if transaction:
            transactions.append(list(transaction))

    return transactions, potential_interactors

# Main function to orchestrate the DDI analysis
def run_analysis(drug_name, symptom, min_support, generic_drug_name=None):
    # Ensure consistent casing with drug_name and symptom
    drug_name, symptom = drug_name.upper(), symptom.upper()

    print("Fetching adverse effect data...")
    data_brand = fetch_data(drug_name)

    if generic_drug_name:
        generic_drug_name = generic_drug_name.upper()
        data_generic = fetch_data(generic_drug_name)
    
    data = data_brand + data_generic

    if data:
        print("Preprocessing data for mining...")
        transactions, potential_interactors = get_transactions(data, 
                                                               [drug_name, generic_drug_name] if generic_drug_name else [drug_name], 
                                                               symptom)
        print("Calculating ROR...")
        contingency_table, symptom_count = generate_contingency_table(data, 
                                                                      [drug_name, generic_drug_name] if generic_drug_name else [drug_name], 
                                                                      symptom)
        ror, p_val = calculate_ror(contingency_table)
        print(f"Rate of Return: {ror}, P value: {p_val}")
        
        print(f"Number of transactions to mine: {len(transactions)}")

        print("Mining association rules...")
        rules = association_rule_mining(transactions, float(min_support))
        print("Finished mining association rules...")

        # Filter for rules where drug of interest is an antecedent and the symptom is a consequent
        drug_to_symptom_rules = rules[(rules['antecedents'].apply(lambda x: 'DRUG OF INTEREST' in x and x.issubset(potential_interactors.union({drug_name}))))
                                & (rules['consequents'] == {symptom})]

        # Analyze the rules involving drug of interest and other potential interactors leading to symptom of interest
        for index, row in drug_to_symptom_rules.iterrows():
            antecedents = row['antecedents']
            consequents = row['consequents']
            support = row['support']
            confidence = row['confidence']
            lift = row['lift']

            # Output the rule and its metrics
            print(f"Rule: {antecedents} -> {consequents}")
            print(f"Support: {support}, Confidence: {confidence}, Lift: {lift}\n")

        # Filter the rules to find all instances where drug of interest is in the antecedents
        drug_a_rules = rules[rules['antecedents'].apply(lambda x: drug_name in x) & (rules['consequents'] == {symptom})]
        if drug_a_rules.empty:
            print("No relevant rules ouputted from mining.")
            return drug_name, None, [], 0
        
        # Find the lift for drug of interest -> symptom of interest
        lift_drug_a_symptom = rules[(rules['antecedents'] == {drug_name}) & (rules['consequents'] == {symptom})]['lift'].values[0]
        
        print(drug_a_rules)

        # Initialize a dictionary to store the DDI index for each drug B
        ddi_index_dict = {}

        for drug_b in potential_interactors:
            # Find the lift for drug of interest + other compounds -> symptom of interest
            rule = rules[(rules['antecedents'] == {drug_name, drug_b}) & (rules['consequents'] == {symptom})]
            if not rule.empty:
                lift_drug_a_b_symptom = rule['lift'].values[0]
                # Calculate the DDI index
                ddi_index = lift_drug_a_b_symptom / lift_drug_a_symptom
                ddi_index_dict[drug_b] = ddi_index
        
        # Sort the DDI index dictionary by values (DDI index) in descending order
        sorted_ddi_index = sorted(ddi_index_dict.items(), key=lambda item: item[1], reverse=True)

        # Print out the DDI index for each Drug B
        for drug_b, ddi_index in sorted_ddi_index:
            print(f'DDI Index of {drug_name} with {drug_b}: {ddi_index}')
        return drug_name, ror, sorted_ddi_index, symptom_count
    else:
        return drug_name, 'N/A', [], 0

# Main function call (not used with Flask, useful for debugging however)
if __name__ == "__main__":
    drug_of_interest = "narcan"
    symptom = "Acute kidney injury"

    print(run_analysis(drug_of_interest.upper(), symptom.upper(), .01))