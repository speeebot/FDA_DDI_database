import requests
import time
import urllib.parse
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

drug = 'narcan'

def calculate_ror(a, b, c, d):
    """
    Calculate the Reporting Odds Ratio (ROR).
    
    :param a: The number of cases with both the drug and AKI.
    :param b: The number of cases with the drug and without AKI.
    :param c: The number of cases without the drug and with AKI.
    :param d: The number of cases without the drug and without AKI.
    :return: The ROR value.
    """
    print(f"a: {a}, b: {b}, c: {c}, d: {d}")
    # Make sure to handle the case where b, c or d is zero to avoid division by zero
    ror = (c / d) / (a / b) if b != 0 and d != 0 and a != 0 else float('inf')
    return ror

def get_ror_values(aki_rules, df):
    for index, rule in aki_rules.iterrows():
        antecedents = rule['antecedents']
        
        # Calculate the contingency table values
        a = rule['support']
        b = df[list(antecedents)].all(axis=1).sum() - a
        c = df['AKI'].sum() - a
        d = len(df) - (a + b + c)
        
        # Calculate ROR
        ror = calculate_ror(a, b, c, d)
        
        # Add the ROR to the rule in the DataFrame
        aki_rules.loc[index, 'ROR'] = ror

        return aki_rules

def get_transactions(drug: str):
    # Empty list to store all transactions
    all_transactions = []

    # Payload parameters
    base_url = "https://api.fda.gov/drug/event.json?"
    limit = 100

    payload = {
        'search': f"patient.drug.medicinalproduct:{drug}+AND+patient.reaction.reactionmeddrapt:acute kidney injury",
        'limit': limit,
        'skip': ""
    }

    payload_str = urllib.parse.urlencode(payload, safe=':+')
    response = requests.get(base_url, params=payload_str)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the response JSON
        data = response.json()
        
        # Process each result (each report)
        for result in data.get('results', []):
            # Initialize a transaction for this report
            transaction = []
            
            # Add the drug names to the transaction
            for drug in result['patient']['drug']:
                transaction.append(drug['medicinalproduct'].lower())
            
            # Add 'AKI' if acute kidney injury is reported
            for reaction in result['patient']['reaction']:
                if 'acute kidney injury' in reaction['reactionmeddrapt'].lower():
                    transaction.append('AKI')
                    break
            
            # Add the transaction to the list
            all_transactions.append(transaction)

        return all_transactions
    else:
        print(f"Failed to retrieve data: {response.status_code}")
        return 0

# Count the drugs with and without AKI in each transaction
def get_drug_counts(all_transactions):    
    drug_counts = {}
    # Process the transactions to get the drug counts
    for transaction in all_transactions:
        has_aki = 'AKI' in transaction
        
        # Iterate through each drug in the transaction
        for drug in transaction:
            if drug == 'AKI':
                continue  # Skip the AKI label itself
            
            # Initialize the drug entry if not already present
            if drug not in drug_counts:
                drug_counts[drug] = {'with_aki': 0, 'without_aki': 0}
            
            # Increment the count based on presence of AKI in the transaction
            if has_aki:
                drug_counts[drug]['with_aki'] += 1
            else:
                drug_counts[drug]['without_aki'] += 1

    # Now, drug_counts contains the number of times each drug was reported with and without AKI
    return drug_counts

# Returns a list of transactions for association rule mining
transactions = get_transactions(drug)

# drug_counts contains the number of times each drug was reported with and without AKI
drug_counts = get_drug_counts(transactions)

# Step 3: Association Rule Mining
# Convert the dataset into a one-hot encoded DataFrame
te = TransactionEncoder()
te_ary = te.fit(transactions).transform(transactions)
df = pd.DataFrame(te_ary, columns=te.columns_)

# Apply Apriori algorithm to find frequent itemsets
frequent_itemsets = apriori(df, min_support=0.2, use_colnames=True)

# Generate association rules
rules = association_rules(frequent_itemsets, metric="lift", min_threshold=.2)
print("ASSOCIATION RULES:")
print(rules)
# Filter for rules where the consequence is AKI
aki_rules = rules[rules['consequents'] == {'AKI'}].copy()
# The total number of reports with AKI
aki_reports_count = sum(1 for transaction in transactions if 'AKI' in transaction)

# Add ROR values to the aki_rules
aki_rules_ror = get_ror_values(aki_rules, df)

# Sort the rules by the lift and ROR
aki_rules_sorted = aki_rules_ror.sort_values(by=['lift', 'ROR'], ascending=[False, False])

# Output the results
# Gives a DataFrame with each rule and its metrics
print("AKI_RULES_SORTED:")
print(aki_rules_sorted[['antecedents', 'consequents', 'support', 'confidence', 'lift', 'ROR']])

# Assuming `aki_rules` is a DataFrame with the relevant rules
# and it contains columns for 'antecedents', 'consequents', and 'lift'

# Find the rule for Drug A -> AKI
rule_drug_a = rules[(rules['antecedents'] == {drug}) & (rules['consequents'] == {'AKI'})]
print(rule_drug_a)
lift_drug_a = rule_drug_a['lift'].values[0]  # Get the lift value

# Initialize a dictionary to store DDI indices
ddi_indices = {}

# Iterate over the rules to find combinations of Drug A with other drugs
for index, rule in rules.iterrows():
    if drug in rule['antecedents'] and len(rule['antecedents']) > 1:
        # Calculate the DDI index
        lift_combination = rule['lift']
        ddi_index = lift_combination / lift_drug_a
        # Store the DDI index with the drug combination as key
        ddi_indices[frozenset(rule['antecedents'])] = ddi_index

# Now `ddi_indices` contains the DDI index for each drug combination with Drug A
for index in ddi_indices.items():
    print(index)