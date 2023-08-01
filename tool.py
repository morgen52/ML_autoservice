from flask import Flask, request, jsonify
import os
import zipfile
import random
import json
import sqlite3
import re

CONST_IP = "0.0.0.0"

app = Flask(__name__)

def gen_Dockerfile(workspace, base_image="pytorch/pytorch:2.0.0-cuda11.7-cudnn8-runtime"):
    with open("Dockerfile.template", "r", encoding="utf8") as f:
        template = f.read()
    template = template.replace("$base_image", base_image)
    with open(f"{workspace}/Dockerfile", "w", encoding="utf8") as f:
        f.write(template)

def gen_servicepy(workspace, entrypoint, input_path, input_type, output_path):
    with open("service.py.template", "r", encoding="utf8") as f:
        template = f.read()
    template = template.replace("$entrypoint", entrypoint)
    template = template.replace("$input_path", input_path)
    template = template.replace("$input_type", input_type)
    template = template.replace("$output_path", output_path)
    with open(f"{workspace}/service.py", "w", encoding="utf8") as f:
        f.write(template)

def gen_callpy(workspace, input_type, url):
    with open("call.py.template", "r", encoding="utf8") as f:
        template = f.read()

    input_types = input_type.split(';')[:-1]

    prepare = []
    content = {
        "input": []
    }
    for idx, t in enumerate(input_types):
        if t == "image":
            prepare.append(f"with open(\"{idx}.jpg\", \"rb\") as image_file:\n    ipt_{idx} = base64.b64encode(image_file.read()).decode('utf-8')\n")
            content["input"].append({
                "content": f"ipt_{idx}"
            })
        elif t == "text":
            prepare.append(f"ipt_{idx} = \"hello world!\"\n")
            content["input"].append({
                "content": f"ipt_{idx}"
            })

    template = template.replace("$prepare", '\n'.join(prepare))
    template = template.replace("$content", json.dumps(content, indent=4))
    template = template.replace("$url", url)
    # 正则表达式将所有"ipt_[0-9]"替换为ipt_[0-9]
    template = re.sub(r"\"(ipt_[0-9])\"", r"\1", template)

    with open(f"{workspace}/call.py", "w", encoding="utf8") as f:
        f.write(template)

    return template

'''
创建数据库，数据库内容是
port: 项目端口，从5000开始，每次加1。
name: 项目名
used: 是否被使用
'''
def handle_database(name, mode="create"):
    # 如果数据库不存在，就创建一个
    if not os.path.exists('ports.db'):
        conn = sqlite3.connect('ports.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE ports (name text, port integer, used integer)''')
        for i in range(5000, 5100): # 初始化端口池子
            c.execute(f"INSERT INTO ports VALUES ('', {i}, 0)")
        conn.commit()
        conn.close()
    conn = sqlite3.connect('ports.db')
    c = conn.cursor()
    if mode == "create":
        c.execute(f"SELECT * FROM ports WHERE name='{name}'")
        if len(c.fetchall()) > 0:
            return False, "项目名已存在"
        c.execute(f"SELECT * FROM ports WHERE used=0")
        port = c.fetchall()[0][1]
        c.execute(f"UPDATE ports SET name='{name}', used=1 WHERE port={port}")
        conn.commit()
    elif mode == "delete":
        c.execute(f"SELECT * FROM ports WHERE name='{name}'")
        if len(c.fetchall()) == 0:
            return False, "项目名不存在"
        c.execute(f"SELECT * FROM ports WHERE name='{name}'")
        port = c.fetchall()[0][1]
        c.execute(f"UPDATE ports SET name='', used=0 WHERE port={port}")
        conn.commit()
    elif mode == "get":
        c.execute(f"SELECT * FROM ports WHERE name='{name}'")
        if len(c.fetchall()) == 0:
            return False, "项目名不存在"
        c.execute(f"SELECT * FROM ports WHERE name='{name}'")
        port = c.fetchall()[0][1]
    conn.close()
    return True, port

def check_config(pid, config):
    try:
        assert config["name"] != ""
        assert config["entrypoint"] != ""
        assert len(config["input"]) > 0
    except:
        return False, jsonify({'result': 'error', 'message': 'name, entrypoint and input should not be empty'})

    name = config["name"] + pid
    entrypoint = config["entrypoint"]
    input_path = ""
    input_type = ""
    for ipt in config["input"]:
        input_path += f"{ipt['path']};"
        input_type += f"{ipt['type']};"
    
    try:
        assert len(config["output"]) == 1
    except:
        return False, jsonify({'result': 'error', 'message': 'output should be a list with one element'})
    
    try:
        assert config["output"][0]["type"] == "json"
    except:
        return False, jsonify({'result': 'error', 'message': 'output type should be json'})

    output_path = config["output"][0]["path"]

    base_image = config.get("base_image", "pytorch/pytorch:2.0.0-cuda11.7-cudnn8-runtime")

    return True, (name, entrypoint, input_path, input_type, output_path, base_image)

def gen_docker(root_dir, workspace, name, port, version="0.0"):
    # 生成docker镜像
    cur_dir = os.getcwd()
    os.chdir(f"{root_dir}/{workspace}")
    try:
        os.system(f"docker build -t {name}:{version} .")
    except Exception as e:
        return False, jsonify({'result': 'error', 'message': str(e)})
    
    # 启动docker容器
    try:
        if version != "0.0":
            os.system(f"docker run -d --rm --name {name} {name}:{version} python3 service.py")
        else:
            os.system(f"docker run -d --rm --name {name} -p {port}:5000 {name}:{version} python3 service.py")
    except Exception as e:
        return False, jsonify({'result': 'error', 'message': str(e)})
    
    os.chdir(cur_dir)
    return True, True


@app.route('/create', methods=['POST'])
def create():
    exist_pids = [f[:-5] for f in os.listdir("workspace") if os.path.isdir(os.path.join("workspace", f))]
    pid = ''.join(random.sample('zyxwvutsrqponmlkjihgfedcba1234567890', 5)) # 新的项目名为5位随机字母和数字的组合，可以重复
    while pid in exist_pids:     # 如果项目名已存在，重新生成
        pid = ''.join(random.sample('zyxwvutsrqponmlkjihgfedcba1234567890', 5))
    
    # 创建新的workspace文件夹
    root_dir = f"workspace/{pid}"
    os.mkdir(root_dir)

    # 解析上传的zip文件
    file = request.files['file']
    file.save(f"{root_dir}/{file.filename}")
    
    # 解压zip文件为文件夹
    zip_ref = zipfile.ZipFile(f"{root_dir}/{file.filename}", 'r')
    zip_ref.extractall(root_dir)
    zip_ref.close()
    os.remove(f"{root_dir}/{file.filename}")     # 删除zip文件

    # 获取解压后的文件夹名
    workspace = os.listdir(root_dir)[0]
    
    # 读取配置文件
    with open(f"{root_dir}/{workspace}/config.json", 'r', encoding="utf8") as f:
        config = json.load(f)
    r, confs = check_config(pid, config)
    if not r:
        return confs
    name, entrypoint, input_path, input_type, output_path, base_image = confs

    # 生成Dockerfile
    gen_Dockerfile(f"{root_dir}/{workspace}", base_image)
    gen_servicepy(f"{root_dir}/{workspace}", entrypoint, input_path, input_type, output_path)

    # 改变workspace文件夹的名字
    os.rename(f"{root_dir}", f"workspace/{name}")
    root_dir = f"workspace/{name}"

    # 分配端口，写入数据库
    r, port = handle_database(name, mode="create")
    if not r:
        return jsonify({'result': 'error', 'message': port})

    # 生成docker镜像
    r, error = gen_docker(root_dir, workspace, name, port)
    if not r:
        return error

    url = f"http://{CONST_IP}:{port}/inference"
    # 返回一个调用示例
    template = gen_callpy(f"{root_dir}/{workspace}", input_type, url)

    result = {
        "name": name,
        "result": "success",
        "url": url,
        "call": template
    }
    
    return jsonify(result)


@app.route('/delete', methods=['POST'])
def delete():
    # 读取json中的name
    content = request.get_json(silent=True)
    if content is None:
        return jsonify({'result': 'error', 'message': 'request body should not be empty'})
    name = content.get("name", None)
    if name is None:
        return jsonify({'result': 'error', 'message': 'name should not be empty'})
    r, port = handle_database(name, mode="delete")
    if not r:
        return jsonify({'result': 'error', 'message': port})
    
    try:# 停止docker容器
        os.system(f"docker stop {name}")
    except Exception as e:
        return jsonify({'result': 'error', 'message': str(e)})
    # 删除workspace文件夹
    os.system(f"rm -rf workspace/{name}")
    # 删除docker镜像
    os.system(f"docker rmi {name}:0.0")
    return jsonify({'result': 'success', 'message': 'delete success'})

@app.route('/get', methods=['POST'])
def get():
    content = request.get_json(silent=True)
    if content is None:
        return jsonify({'result': 'error', 'message': 'request body should not be empty'})
    name = content.get("name", None)
    if name is None:
        return jsonify({'result': 'error', 'message': 'name should not be empty'})
    r, port = handle_database(name, mode="get")
    if not r:
        return jsonify({'result': 'error', 'message': port})
    
    # get the call file
    workspace = os.listdir(f"workspace/{name}")[0]
    with open(f"workspace/{name}/{workspace}/call.py", 'r', encoding="utf8") as f:
        call = f.read()
        # 从call.py中获取url，有一行代码是url = "http://0.0.0.0:5001/inference"
        url = re.findall(r'url = "(.*)"', call)[0]
    result = {
        "name": name,
        "result": "success",
        "url": url,
        "call": call
    }
    return jsonify(result)

@app.route('/list', methods=['GET'])
def list():
    files = [f for f in os.listdir("workspace") if os.path.isdir(os.path.join("workspace", f))]
    return jsonify({'result': 'success', 'message': files})

@app.route('/update', methods=['POST']) # update a zip file, and keep the same port
def update():
    name = request.form.get('name', None)
    if name is None:
        return jsonify({'result': 'error', 'message': 'name should not be empty'})
    
    file = request.files.get('file', None)
    if file is None:
        return jsonify({'result': 'error', 'message': 'file should not be empty'})
    
    # 读取数据库，获取端口
    r, port = handle_database(name, mode="get")
    if not r:
        return jsonify({'result': 'error', 'message': port})
    
    # 先创建一个暂时的文件夹
    root_dir = f"workspace/{name}_new"
    os.mkdir(root_dir)
    file.save(f"{root_dir}/{file.filename}")
    zip_ref = zipfile.ZipFile(f"{root_dir}/{file.filename}", 'r')
    zip_ref.extractall(root_dir)
    zip_ref.close()
    os.remove(f"{root_dir}/{file.filename}")

    workspace = os.listdir(root_dir)[0]
    with open(f"{root_dir}/{workspace}/config.json", 'r', encoding="utf8") as f:
        config = json.load(f)
    r, confs = check_config(name, config)
    if not r:
        return confs
    _, entrypoint, input_path, input_type, output_path, base_image = confs

    gen_Dockerfile(f"{root_dir}/{workspace}", base_image)
    gen_servicepy(f"{root_dir}/{workspace}", entrypoint, input_path, input_type, output_path)

    # 生成docker镜像，作为是否可用的检测
    r, error = gen_docker(root_dir, workspace, f"{name}_new", port, version="0.1")
    if not r:
        return error
    # 如果这一步出错了，则之前的文件夹都不会被删除，也不会有新的镜像生成，之前的容器仍然可用
    
    # 停止旧的容器
    try:
        os.system(f"docker stop {name}")
        os.system(f"docker stop {name}_new")
    except Exception as e:
        return jsonify({'result': 'error', 'message': str(e)})
    # 删除旧的文件夹
    os.system(f"rm -rf workspace/{name}")
    # 改变workspace文件夹的名字
    os.rename(f"{root_dir}", f"workspace/{name}")
    root_dir = f"workspace/{name}"

    os.system(f"docker rmi {name}:0.0")
    os.system(f"docker rmi {name}_new:0.1")

    # 启动新的容器
    r, error = gen_docker(root_dir, workspace, name, port)
    if not r:
        return error

    url = f"http://{CONST_IP}:{port}/inference"
    # 返回一个调用示例
    template = gen_callpy(f"{root_dir}/{workspace}", input_type, url)

    result = {
        "name": name,
        "result": "success",
        "url": url,
        "call": template
    }

    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)