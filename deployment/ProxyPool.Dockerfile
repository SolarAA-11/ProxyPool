# Docker Context ../src
FROM python:3.8
WORKDIR /app
COPY ["./requirements", "."]
RUN pip install -r requirements -i https://pypi.tuna.tsinghua.edu.cn/simple && rm -f requirements
COPY ["./ProxyPool/", "./"]
CMD python main.py