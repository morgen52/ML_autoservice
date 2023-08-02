

# HTTP POST call to the tool

import requests
import json

base_url = "http://0.0.0.0:8000"

'''
输入：zip文件路径
输出：一个json字典，包括{"call": 一个简单的模型服务调用示例, "url": 模型服务的url, "name": 模型服务的名称}
'''
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

'''
输入：创建时返回的模型服务名称
输出：无
'''
def delete(name):
    url = f"{base_url}/delete"
    content = {"name": name}
    r = requests.post(url, json=content)
    print(r.text)
    
'''
输入：创建时返回的模型服务名称
输出：一个json字典，包括{"call": 一个简单的模型服务调用示例, "url": 模型服务的url, "name": 模型服务的名称}
'''
def get(name):
    url = f"{base_url}/get"
    content = {"name": name}
    r = requests.post(url, json=content)
    print(r.text)

'''
输入：无
输出：一个json字典，包括{"message": 所有目前已有服务的列表}
'''
def list():
    url = f"{base_url}/list"
    r = requests.get(url)
    print(r.text)
    return json.loads(r.text)

'''
输入：创建时返回的模型服务名称，zip文件路径
输出：保留原有服务的url不变，返回一个json字典，包括{"call": 一个简单的模型服务调用示例, "url": 模型服务的url, "name": 模型服务的名称}
'''
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

    name = create()
    name = list()["message"][0]
    update(name)
    delete(name)
    list()


