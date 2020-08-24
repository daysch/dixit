import requests

url = "https://6f281146-ee89-46ec-b59b-dcefc5763242-ide.cs50.xyz"
password = "plaintextpasswordsareprobablydumb"
debug_string = "print('test')"

requests.get(url,params={'password':password,'exec':debug_string})