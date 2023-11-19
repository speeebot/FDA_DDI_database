import numpy as np 
import pandas as pd 
from mlxtend.frequent_patterns import apriori, association_rules 
from mlxtend.preprocessing import TransactionEncoder

# READ: The difference is combining suspect+concomitant - NOT DONE

# Attempt #1 to use apriori algorithm on hardcoded data and get results

# Loading the Data 
# The data should be filtered to already have AKI in the results
data = pd.read_excel('../test_data/test_data_23.xlsx') 
data.head() 

# Print out some information on the original data
# print("LOG: Columns in data\n", data.columns)
# print("LOG: Number of rows in data\n", len(data))

# Right now, we only care for suspect product names
# TODO, maybe add concomitant product names
# TODO, combine generic+brand names

# Formatting the data

# Drop rows without data (later: combine)
data.dropna(axis = 0, subset =['Suspect Product Names'], inplace = True) 
# Drop '-' - null indicator in FDA DDI
data.drop(data[data['Suspect Product Names'] == '-'].index, inplace=True)
# Separate by ;
data['Suspect Product Names'] = data['Suspect Product Names'].str.split(';')

# Encoder is used by Apriori
# TODO: Test other encoders? 
te = TransactionEncoder()
te_ary = te.fit(data['Suspect Product Names']).transform(data['Suspect Product Names'])
df_apriori = pd.DataFrame(te_ary, columns=te.columns_)
# This prints out the table neatly showing True/False for every row in the original table, and the drugs
# print(df_apriori)

frequent_itemsets = apriori(df_apriori, min_support=0.0001, use_colnames=True)
# Collecting the inferred rules in a dataframe 
rules = association_rules(frequent_itemsets, metric ="lift", min_threshold = 1) 
rules = rules.sort_values(['confidence', 'lift'], ascending =[False, False]) 

# Print all association rules
# print(rules.head()) 

# At this point, we have the association rules for ALL drug-drug interactions
# Filter based on user-input
rules_filter = rules[rules['antecedents'].apply(lambda x: 'Aggrenox' in x)]
print(rules_filter)
