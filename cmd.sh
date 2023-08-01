zip -r 2.zip inference_example
mv 1.zip service_tool/test/

docker images | grep "^regnet-classification.*" | awk '{print $3}' | xargs docker rmi
docker stop $(docker ps -aq)

rm -rf workspace/* ports.db

docker build -t regnet-classification:0.0 .

docker run -it --rm \
    -v $(pwd)/:/app \
    -p 6000:5000 \
    regnet-classification:0.0\
    python3 service.py


