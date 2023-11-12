import requests

def fetch_side_effect(drug_name : str, side_effect: str):
    base_url = "https://api.fda.gov/drug/event.json?"
    query = f'search=patient.drug.medicinalproduct:{drug_name}+AND+patient.reaction.reactionmeddrapt:{side_effect}'
    request = requests.get(base_url+query)
    brand_name_dict = dict(request.json())
    return brand_name_dict

print(fetch_side_effect("vancomycin", "Acute Kidney Injury"))
