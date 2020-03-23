FROM python:3.8
COPY . /code
WORKDIR /code
RUN pip install -r requirements
CMD ["uvicore", "main:app", "--host 0.0.0.0", "--port 8080"]