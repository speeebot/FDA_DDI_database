import numpy as np 
import pandas as pd 
from mlxtend.frequent_patterns import apriori, association_rules 
from mlxtend.preprocessing import TransactionEncoder

# Attempt #1 to use apriori algorithm on hardcoded data and get results

# Loading the Data 
# The data should be filtered to already have AKI in the results
data = pd.read_excel('../test_data/test_data_bigger.xlsx') 
data.head() 
target_drug = "Viread"
# Print out some information on the original data
# print("LOG: Columns in data\n", data.columns)
# print("LOG: Number of rows in data\n", len(data))

# Formatting the data
# Only using the 'Suspect Product Names' row

# Drop rows without data 
data.dropna(axis = 0, subset =['Suspect Product Names'], inplace = True) 
# Drop '-' - null indicator in FDA DDI
data.drop(data[data['Suspect Product Names'] == '-'].index, inplace=True)
# Separate by ;
data['Suspect Product Names'] = data['Suspect Product Names'].str.split(';')


# TODO: Trying to do this, but not working - too large. Use suspect product name for now - seems accurate enough
# data['Combined Drugs'] = data['Suspect Product Names'] + data['Concomitant Product Names']
data['Combined Drugs'] = data['Suspect Product Names'] 
# Remove rows that don't have the target drug - greatly reduces time spent in algorithm if done in preprocessing
print("Rows before filtering target drug:", len(data))
filtered_data = data[data['Combined Drugs'].apply(lambda x: target_drug in x)]
print("Rows after filtering target drug:", len(filtered_data))

# Encoder is used by Apriori
te = TransactionEncoder()
te_ary = te.fit(filtered_data['Combined Drugs']).transform(filtered_data['Combined Drugs'])
df_apriori = pd.DataFrame(te_ary, columns=te.columns_)
# This prints out the table neatly showing True/False for every row in the original table, and the drugs
# print(df_apriori)

# Apply Apriori Algorithm
# We can modify min_support: the lower it is, the more results we get, however they might be less reliable
frequent_itemsets = apriori(df_apriori, min_support=0.01, use_colnames=True)

# Collecting the inferred rules in a dataframe 
rules = association_rules(frequent_itemsets, metric ="lift", min_threshold = 1) 
rules = rules.sort_values(['lift'], ascending =[False]) 

# Print all association rules
pd.set_option('display.max_rows', None)
print(rules) 

# Next TODO: Remove duplicates, print _ _ pairs with lift > 1 