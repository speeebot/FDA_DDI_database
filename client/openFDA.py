import os
import requests
import pandas as pd
from mlxtend.frequent_patterns import apriori, fpgrowth, association_rules
from mlxtend.preprocessing import TransactionEncoder
from data_handling import fetch_data, fetch_events
from scipy.stats import chi2_contingency

import constants

# Function to apply the association rule mining
def association_rule_mining(transactions, potential_interactors, min_support, drug_name):
    # Initialize TransactionEncoder
    te = TransactionEncoder()
    te_ary = te.fit(transactions).transform(transactions)
    df = pd.DataFrame(te_ary, columns=te.columns_)

    # Apply the Apriori algorithm to get frequent itemsets
    # We can modify min_support: the lower it is, the more results we get, however they might be less reliable and take longer
    frequent_itemsets = apriori(df, min_support=min_support, use_colnames=True)
    # FP-growth is probably faster
    #frequent_itemsets = fpgrowth(df, min_support=min_support, use_colnames=True)
    print("DEBUG Frequent itemsets:", frequent_itemsets.head())

    if frequent_itemsets.empty:
        print('No frequent itemsets found. You may need to lower the min_support.')
        return pd.DataFrame()

    # Generate the rules with their corresponding support, confidence, and lift
    rules = association_rules(frequent_itemsets, metric='lift', min_threshold=1)

    # print("DEBUG Generated rules:", rules.head())
    # Filter for rules where drug of interest is an antecedent and the symptom is a consequent
    symptom_rules = rules[rules['antecedents'].apply(lambda x: drug_name in x and x.issubset(potential_interactors.union({drug_name})))]

    return symptom_rules

# Constructs the 2x2 contingency table for calculating ROR
def generate_contingency_table(data, drug_name, symptom):
    aki_with_drug_a_only = 0
    aki_with_drug_a_and_others = 0
    no_aki_with_drug_a_only = 0
    no_aki_with_drug_a_and_others = 0

    for entry in data:
        drugs_in_report = [drug['medicinalproduct'].upper() for drug in entry['patient']['drug']]
        reactions_in_report = [reaction['reactionmeddrapt'].upper() for reaction in entry['patient']['reaction']]

        # Check if AKI is reported
        aki_reported = symptom in reactions_in_report
        # Check if only Drug A is reported
        only_drug_a_reported = drugs_in_report == [drug_name]

        if aki_reported and only_drug_a_reported:
            aki_with_drug_a_only += 1
        elif aki_reported and not only_drug_a_reported:
            aki_with_drug_a_and_others += 1
        elif not aki_reported and only_drug_a_reported:
            no_aki_with_drug_a_only += 1
        elif not aki_reported and not only_drug_a_reported:
            no_aki_with_drug_a_and_others += 1

    #print(aki_with_drug_a_only, aki_with_drug_a_and_others, no_aki_with_drug_a_only, no_aki_with_drug_a_and_others)
    # Construct the 2x2 contingency table
    contingency_table = [[aki_with_drug_a_only, aki_with_drug_a_and_others],
                         [no_aki_with_drug_a_only, no_aki_with_drug_a_and_others]]

    return contingency_table

# Function to calculate Reporting Odds Ratio (ROR)
def calculate_ror(contingency_table):
    odds_ratio, p_value = chi2_contingency(contingency_table)[:2]
    return odds_ratio, p_value

def get_transactions(data, drug_name, symptom):
    transactions = []
    # Initialize a set to keep track of all drugs that appear in transactions with Drug A
    potential_interactors = set()

    for report in data:
        # Initialize a transaction set for the current report
        transaction = set()

        # Check if Drug A is in the current report
        drugs_in_report = [drug['medicinalproduct'].upper() for drug in report['patient']['drug']]
        if drug_name in drugs_in_report: 
            # Add all drugs from the report to the transaction
            transaction.update(drugs_in_report)

            # Add AKI to the transaction if it's reported as a reaction
            reactions_in_report = [reaction['reactionmeddrapt'].upper() for reaction in report['patient']['reaction']]
            if symptom in reactions_in_report:
                transaction.add(symptom)

            # Add the transaction to the list if it contains more than just Drug A
            if len(transaction) > 1:
                transactions.append(list(transaction))

                # Update the set of potential interactors (excluding Drug A itself)
                potential_interactors.update(transaction.difference({drug_name}))
    
    return transactions, potential_interactors

# Main function to orchestrate the DDI analysis
def run_analysis(drug_name, symptom, min_support):
    # Ensure consistent casing with drug_name and symptom
    drug_name, symptom = drug_name.upper(), symptom.upper()

    print("Fetching adverse effect data...")
    # Load data using caching mechanism to mitigate redundant API calls
    data = fetch_data(drug_name)
    
    if data:
        # Prepare the transactions for mining
        print("Preprocessing data for mining...")
        transactions, potential_interactors = get_transactions(data, drug_name, symptom)

        # Calculate Rate of Return
        print("Calculating ROR...")
        contingency_table = generate_contingency_table(data, drug_name, symptom)
        ror, p_val = calculate_ror(contingency_table)
        print(f"Rate of Return: {ror}, P value: {p_val}")
        
        print("Mining association rules...")
        rules = association_rule_mining(transactions, potential_interactors, float(min_support), drug_name)
        print("Finished mining association rules...")

        # Filter for rules where drug of interest is an antecedent and symptom of interest is a consequent
        aki_rules = rules[(rules['antecedents'].apply(lambda x: drug_name in x and x.issubset(potential_interactors.union({drug_name}))))
                        & (rules['consequents'] == {symptom})]

        # Analyze the rules involving drug of interest and other potential interactors leading to symptom of interest
        for index, row in aki_rules.iterrows():
            antecedents = row['antecedents']
            consequents = row['consequents']
            support = row['support']
            confidence = row['confidence']
            lift = row['lift']

            # Output the rule and its metrics
            print(f"Rule: {antecedents} -> {consequents}")
            print(f"Support: {support}, Confidence: {confidence}, Lift: {lift}\n")

        # Filter rules for those that involve Drug of interest and symptom of interest
        #rules_drug_a_aki = rules[rules['antecedents'].apply(lambda x: drug_name in x and symptom in x)]

        # Filter the rules to find all instances where drug of interest is in the antecedents
        drug_a_rules = rules[rules['antecedents'].apply(lambda x: drug_name in x) & (rules['consequents'] == {symptom})]
        if drug_a_rules.empty:
            return drug_name, None, [] 
        
        # Find the lift for drug of interest -> symptom of interest
        lift_drug_a_aki = rules[(rules['antecedents'] == {drug_name}) & (rules['consequents'] == {symptom})]['lift'].values[0]
        
        print(drug_a_rules)

        # Initialize a dictionary to store the DDI index for each drug B
        ddi_index_dict = {}

        for drug_b in potential_interactors:
            # Find the lift for drug of interest + other compounds -> symptom of interest
            rule = rules[(rules['antecedents'] == {drug_name, drug_b}) & (rules['consequents'] == {symptom})]
            if not rule.empty:
                lift_drug_a_b_aki = rule['lift'].values[0]
                # Calculate the DDI index
                ddi_index = lift_drug_a_b_aki / lift_drug_a_aki
                ddi_index_dict[drug_b] = ddi_index
        
        # Sort the DDI index dictionary by values (DDI index) in descending order
        sorted_ddi_index = sorted(ddi_index_dict.items(), key=lambda item: item[1], reverse=True)

        # Print out the DDI index for each Drug B
        for drug_b, ddi_index in sorted_ddi_index:
            print(f'DDI Index of {drug_name} with {drug_b}: {ddi_index}')

        return drug_name, ror, sorted_ddi_index
    else:
        return drug_name, 'N/A', []

# Main function call (not used with Flask, useful for debugging however)
if __name__ == "__main__":
    drug_of_interest = "narcan"
    symptom = "Acute kidney injury"

    print(run_analysis(drug_of_interest.upper(), symptom.upper(), .01))
