import requests

# Create session
payload = {"agent": "ab1997ea-fbc7-4743-8757-9e4220030421", "hash": "a4657a589c8fb67e689b44ba42d4b55a", "identifier": "another.txt", "parts": "2" }

response = requests.request("PUT", "http://127.0.0.1:8000/storage/api/upload/new", data=payload)
session = response.split(':')[1]

# upload file 1

files = {'file': open('file1.txt','rb')}
values = {'session': session, 'hash': 'afe0db7354d6aa2d1d6f58e1851d224e', 'sequenceno': '0'}

r = requests.post("http://127.0.0.1:8000/storage/api/upload/append", files=files, data=values)

# upload file 2

files = {'file': open('file2.txt','rb')}
values = {'session': session, 'hash': '<hash>', 'sequenceno': '1'}

r = requests.post("http://127.0.0.1:8000/storage/api/upload/append", files=files, data=values)

# finalise

payload = {'session': session}
response = requests.request("PUT", "http://127.0.0.1:8000/storage/api/upload/finalize", data=payload)

print(response.text)
