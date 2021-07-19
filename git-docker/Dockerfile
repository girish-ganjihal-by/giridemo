FROM python:3.8-slim-buster

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]
EXPOSE 8080
# Admin interface
EXPOSE 8161
# Active MQ's default port (Listen port)
EXPOSE 61613

