
from flask import Flask, render_template, request, jsonify, send_file
from functions import process_input_and_download_reports
import os

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-data', methods=['POST'])
def get_data():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    ticker = data.get('company')
    formtype = data.get('formtype')
    year = data.get('year')

    process_input_and_download_reports(ticker, formtype, year)

    return jsonify({"message": "Processing completed"}), 200  

    
    
if __name__ == '__main__':
    app.run(debug=True)
