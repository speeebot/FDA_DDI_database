import requests
import constants
def calculate_ror():
    #A: Count: drug taken, event occurs
    a_query = f'https://api.fda.gov/drug/event.json?search=patient.drug.medicinalproduct:{constants.DRUG_OF_INTEREST}+AND+patient.reaction.reactionmeddrapt:%22Acute%20Kidney%20Injury%22&count=patient.reaction.reactionmeddrapt.exact'
    #B: Count: drug taken, even does not occur
    b_query = f'https://api.fda.gov/drug/event.json?search=patient.drug.medicinalproduct:{constants.DRUG_OF_INTEREST}+NOT+patient.reaction.reactionmeddrapt:%22Acute%20Kidney%20Injury%22&count=patient.reaction.reactionmeddrapt.exact'
    #C: Count: drug is not taken, event occurs.
    c_query = f'https://api.fda.gov/drug/event.json?search=NOT+patient.drug.medicinalproduct:{constants.DRUG_OF_INTEREST}+AND+patient.reaction.reactionmeddrapt:%22Acute%20Kidney%20Injury%22&count=patient.reaction.reactionmeddrapt.exact'
    #D: Count: drug is not taken, even does not occur
    d_query = f'https://api.fda.gov/drug/event.json?search=NOT+patient.drug.medicinalproduct:{constants.DRUG_OF_INTEREST}+NOT+patient.reaction.reactionmeddrapt:%22Acute%20Kidney%20Injury%22&count=patient.reaction.reactionmeddrapt.exact'

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
    ror = (a_count * d_count) / (b_count * c_count)
    return ror