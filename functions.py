# intalls and imports
import os, requests
import pandas as pd
from datetime import datetime, timedelta
import zipfile
from typing import Dict, Any, List, Optional
from tqdm import tqdm
from flask import send_file, Response

# api key
Api_Key = "f4f1973fd18e51bfd9dd824dbee7dbc5d4b875e26ce043a34819ec336a1608ee"

# limiting the options for PoC
def generate_options():
    options = {
        "companies": ["AAPL", "GOOG", "MSFT", "AMZN", "TSLA"],
        "formtypes": ["10-K", "10-Q", "8-K", "S-1", "DEF 14A"],
        "years": [str(year) for year in range(2000, 2025)]
    }
    return options


# helper function : build date range from date
def build_date_range(year: int) -> tuple[str, str]:
    return f"{year}-01-01", f"{year}-12-31"



# create target folder
folder_path = './reports'
if not os.path.exists(folder_path):
    os.makedirs(folder_path)

# create query api object
from sec_api import QueryApi
queryAPI = QueryApi(api_key=Api_Key)

# function to build search query
def build_search_query(ticker: str, formtype: str, fromDate: str, toDate: str) -> Dict[str, Any]:
    """
    Builds a query given a ticker, form type, fromDate, and toDate.
    """

    form_type_query = f'formType:("{formtype}") AND NOT formType:("{formtype}/A", NT)'
    ticker_query = f'ticker:({ticker})'
    date_range_query = f'filedAt:[{fromDate} TO {toDate}]'

    lucene_query = f"{form_type_query} AND {ticker_query} AND {date_range_query}"

    search_query = {
        "query": lucene_query,
        "from": 0,
        "size": 200,
        "sort": [{"filedAt": {"order": "desc"}}]
    }
    return search_query

# function to get filings' metadata from QueryApi

def fetch_filings(query: Dict[str, Any]) -> pd.DataFrame:
    '''
    get metadata of filings (to be downloaded later)
    '''
    from_param = 0
    size_param = 200 # not needed for PoC but super userul for prod implementation
    all_filings = []

    while True:
        query['from'] = from_param
        query['size'] = size_param

        response = queryAPI.get_filings(query)
        filings = response['filings']

        if len(filings) == 0:
            break

        all_filings.extend(filings)

        from_param += size_param

    return pd.json_normalize(all_filings)

# to convert the dataframe into a list of dicts and build the url for the fin report

def process_filings_dataframe(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    adds a new field 'financialReportsUrl' based on the 'filingUrl' column and converts the dataframe into a list of dictionaries
    """

    # create a new DF and rename 'linkToFilingDetails' column
    filings_list = df[['ticker', 'formType', 'periodOfReport', 'filedAt', 'linkToFilingDetails']].rename(
        columns={'linkToFilingDetails': 'filingUrl'}
    ).copy()

    # build 'financialReportsUrl' based on 'filingUrl' column
    filings_list['financialReportsUrl'] = filings_list['filingUrl'].apply(
        lambda url: '/'.join(url.split('/')[:-1]) + '/Financial_Report.xlsx'
    )

    # conert dataframe to list of dicts
    return filings_list.to_dict('records')

########
# download reports
def download_report(filingDict: Dict[str, Any]) -> Optional[str]:
    '''
    For a given filing, which is a dict, download the report to the target folder.
    Adds file paths to list and returns the list.
    '''
    try:
        reports_path = filingDict['financialReportsUrl'].replace(
            'https://www.sec.gov/Archives/edgar/data/', ''
        )
        base_url = 'https://archive.sec-api.io/' + reports_path
        render_api_url = base_url + '?token=' + Api_Key

        response = requests.get(render_api_url, timeout=10)
        response.raise_for_status()


        file_name = f"{filingDict['ticker']}-{filingDict['periodOfReport']}-{filingDict['formType']}.xlsx"


        file_path = os.path.join(folder_path, file_name)

        with open(file_path, 'wb') as output:
            output.write(response.content)

        print(f"Downloaded: {file_name}")
        return file_path


    except requests.exceptions.RequestException as e:
        print(f"Failed to download {filingDict['financialReportsUrl']}: {e}")
        return None

# create zip file
def create_zip_archive(filepaths: List[Optional[str]]) -> Optional[str]:
    '''Creates a zip archive of the downloaded files.'''
    try:
        zip_file_name = "reports.zip"
        zip_file_path = os.path.join(folder_path, zip_file_name)

        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in filepaths:
                if file_path:
                    zipf.write(file_path, os.path.basename(file_path))

        print(f"Created zip archive: {zip_file_path}")
        return zip_file_path
    except Exception as e:
        print(f"Error creating zip archive: {e}")
        return None

# send files to user
def send_files_to_user(zip_file_path: Optional[str]) -> Response:
    if not zip_file_path or not os.path.exists(zip_file_path):
        return Response("File not found", status=404)

    return send_file(
        zip_file_path,
        as_attachment=True,
        download_name=os.path.basename(zip_file_path),
        mimetype='application/zip'
    )

# delete files locally
def delete_files(list_of_file_paths: List[Optional[str]]) -> bool:
    # pass
    print(f"Deleting files: {list_of_file_paths}")
    return True

def process_input_and_download_reports(ticker: str, formtype: str, year: int) -> Optional[str]:
    file_paths: List[Optional[str]] = []
    from_date, to_date = build_date_range(year)
    search_query = build_search_query(ticker, formtype, from_date, to_date)
    filings_data = fetch_filings(search_query)  # get filings metadata
    filings_list = process_filings_dataframe(filings_data)  # get URLs
    
    for filingDict in filings_list:  # download reports and append file paths to list
        downloaded_file_path = download_report(filingDict)
        file_paths.append(downloaded_file_path)

    zip_file_path = create_zip_archive(file_paths)  # create zip file

    if zip_file_path:
        return zip_file_path  # return zip file path 
    
    return None

'''
####################################################################################################
"""# Testing """

#Testing final function call
ticker='AAPL'
formtype='10-Q'
year = '2022'
process_input_and_download_reports(ticker,formtype,year)
#####################################################################################################
"""# TEST individual functions for easy debugging

user input
"""

#Testing
ticker='AAPL'
formtype='10-Q'
year = '2022'

"""run individual functions"""

#Testing
from_date, to_date = build_date_range(year)
print(f"year = {year}, from_date = {from_date}, to_date = {to_date }")

#Testing
search_query = build_search_query(ticker, formtype, from_date, to_date)
print(search_query)

#Testing
filings_data = fetch_filings(search_query)
print (f"type of filings_data = {type(filings_data)}")
print(filings_data)

#Testing
filings_list = process_filings_dataframe(filings_data)
print(f"type of filings_list = {type(filings_list)}")
#print(filings_list)
print(filings_list[0])

#Testing
for filing in filings_list:
  step1=f"type of filing = {type(filing)}"
  print(step1)
  step2=filing['financialReportsUrl']
  print(step2)
  step3=step2.replace('https://www.sec.gov/Archives/edgar/data/','')
  print('step3')
  step4='https://archive.sec-api.io/'+ step3
  print(step4)
  print(step4+'?token='+Api_Key)

# Testing
print(filings_list[0]['financialReportsUrl'])
print(filings_list[0])
download_report(filings_list[0])
download_report(filings_list[1])

#Testing

def process_input_and_download_reports(ticker, formtype, year):
  from_date, to_date = build_date_range(year)
  search_query = build_search_query(ticker, formtype, from_date, to_date)
  filings_data = fetch_filings(search_query)
  filings_list = process_filings_dataframe(filings_data)
  for filingDict in (filings_list):
    download_report(filingDict)



"""# People data


---

# Compensation data
"""

import requests
import pandas as pd


baseurl = "https://api.sec-api.io/compensation/TSLA"
url = baseurl + "?token=" + Api_Key
# GET request
response = requests.get(url)

# if successful
if response.status_code == 200:
    data = response.json()  # parse json
    df = pd.DataFrame(data) # conver to dataframe
    file = "compData.xlsx"
    df.to_excel(file, index=False)
    print(f"Data saved to {file}")

else:
    print(f"Error: {response.status_code}, {response.text}")

"""# Directors and Board members"""

def fetch_and_save_directors(ticker):
    api_url = "https://api.sec-api.io/directors-and-board-members"
    headers = {"Authorization": Api_Key, "Content-Type": "application/json"}
    payload = {
        "query": f"ticker:{ticker}",
        "from": 0,
        "size": 50,
        "sort": [{"filedAt": {"order": "desc"}}]
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()  # Raise error for bad responses
        data = response.json()
        return data


    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except Exception as e:
        print(f"Error processing data: {e}")

# test
json_data = fetch_and_save_directors("MSFT")

# flatten the JSON into a structured list
records = []
for company in json_data["data"]:
    for director in company["directors"]:
        records.append({
            "Company ID": company["id"],
            "Filed At": company["filedAt"],
            "Accession No": company["accessionNo"],
            "CIK": company["cik"],
            "Ticker": company["ticker"],
            "Company Name": company["entityName"],
            "Director Name": director["name"],
            "Position": director["position"],
            "Age": director["age"],
            "Director Class": director["directorClass"],
            "Date First Elected": director["dateFirstElected"],
            "Is Independent": director["isIndependent"],
            "Committee Memberships": ", ".join(director["committeeMemberships"]),
            "Qualifications & Experience": ", ".join(director["qualificationsAndExperience"])
        })

# Convert to DataFrame
df = pd.DataFrame(records)

# Save to Excel
df.to_excel("directors_data.xlsx", index=False, engine="openpyxl")
'''