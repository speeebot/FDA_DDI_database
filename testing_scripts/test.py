import requests
import json

# basic fetch of api
url = 'https://api.fda.gov/drug/drugsfda.json?limit=1'

# https://open.fda.gov/apis/drug/drugsfda/example-api-queries/


request = requests.get(url)

my_dict = dict(request.json())
print(my_dict)



