from flask import Flask, jsonify, request
from jms import jms_publish
app = Flask(__name__)
location = []
@app.route('/')
def homepage():
    return "My first APp"
@app.route('/location',methods=['GET'])
def get():
    return str(location)
@app.route('/location',methods=['POST'])
def post():
    response = request.get_data(parse_form_data=True)
    location.append(response)
    jms_publish.connect_JMS(location[-1])
    return '', 201