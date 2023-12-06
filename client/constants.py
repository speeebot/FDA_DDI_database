# Constants
DRUG_OF_INTEREST = 'Vancomycin'
ADVERSE_REACTION = 'acute kidney injury'
OPENFDA_API_ENDPOINT = 'https://api.fda.gov/drug/event.json'
SEARCH_AFTER_FILENAME = 'client/search_after_token.json'
DATA_FILENAME = 'client/fda_data.json'
DRUG_EVENT_FIELDS = ['patient.drug.medicinalproduct', 'patient.reaction.reactionmeddrapt']