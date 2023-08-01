import requests
import json
import base64

with open("0.jpg", "rb") as image_file:
    ipt_0 = base64.b64encode(image_file.read()).decode('utf-8')

ipt_1 = "hello world!"

content = {
    "input": [
        {
            "content": ipt_0
        },
        {
            "content": ipt_1
        }
    ]
}
url = "http://0.0.0.0:5000/inference"

headers = {"Content-type": "application/json"}
response = requests.post(url, data=json.dumps(content), headers=headers)
print(response.json())
