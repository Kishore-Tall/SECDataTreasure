
from flask import Flask, render_template, request, jsonify, send_file
from functions import process_input_and_download_reports, generate_options
import os

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-options', methods=['GET'])
def get_options():
    options = generate_options()
    return jsonify(options)



@app.route('/get-data', methods=['POST'])
def get_data():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    ticker = data.get('company')
    formtype = data.get('formtype')
    year = data.get('year')

    # process inputs, download reports, generate zip file and return zip file path
    zip_file_path = process_input_and_download_reports(ticker, formtype, year)

    # send zip file to frontend
    if zip_file_path and os.path.exists(zip_file_path):
        return send_file(zip_file_path, as_attachment=True, mimetype='application/zip')

    return jsonify({"error": "Failed to generate ZIP file"}), 500  
 

    
    
if __name__ == '__main__':
    app.run(debug=True)
