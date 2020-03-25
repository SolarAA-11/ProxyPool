FROM python:3.8
WORKDIR /app
COPY ["./requirements", "./"]
RUN pip install -r requirements -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY ["./main.py", "./.cfg", "./"]
COPY ["./ProxyPool", "./ProxyPool"]
CMD uvicorn --host 0.0.0.0 --port 5050 main:app
