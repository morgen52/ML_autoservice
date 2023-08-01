

# HTTP POST call to the tool

import requests
import json

base_url = "http://0.0.0.0:8000"

def create(filepath="1.zip"):
    url= f"{base_url}/create"
    # upload a zip file to the tool
    files = {'file': open(filepath, 'rb')}
    r = requests.post(url, files=files)
    print(r.text)

    content = json.loads(r.text)
    if content["result"] == "success":
        with open("call_gen.py", "w", encoding="utf8") as f:
            f.write(content["call"])
        return content["name"]

def delete(name):
    url = f"{base_url}/delete"
    content = {"name": name}
    r = requests.post(url, json=content)
    print(r.text)
    
def get(name):
    url = f"{base_url}/get"
    content = {"name": name}
    r = requests.post(url, json=content)
    print(r.text)

def list():
    url = f"{base_url}/list"
    r = requests.get(url)
    print(r.text)
    return json.loads(r.text)

def update(name, filepath="2.zip"):
    url = f"{base_url}/update"
    files = {'file': open(filepath, 'rb')}
    content = {"name": name}
    r = requests.post(url, files=files, data=content)
    print(r.text)

    content = json.loads(r.text)
    if content["result"] == "success":
        with open("call_gen.py", "w", encoding="utf8") as f:
            f.write(content["call"])

if __name__ == "__main__":
    name = create()
    list()
    get(name)
    delete(name)
    list()

    # name = create()
    # name = list()["message"][0]
    # update(name)
    






