import csv
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import requests
from bs4 import BeautifulSoup

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# The ID and range of a sample spreadsheet.
SPREADSHEET_ID = '18_KIuQdkmPVfK8A7JIwEYol3YRlLfPSz032g-VBbd6Q'
RANGE_NAME = 'VaxPublicationsONLY'

HERE = Path(__file__).resolve().parent
CREDENTIALS = HERE / 'credentials.json'
PUBMED_BASE_URL = 'https://pubmed.ncbi.nlm.nih.gov/'
PMCID_BASE_URL = 'https://www.ncbi.nlm.nih.gov/'
FIELDS = {
    'PMID': 'PMID',
    'TI': 'Title',
    'AU': 'Author',
    'MH': 'MeSH',
    'DP': 'PubDate',
}
MULTI_FIELDS = {'AU': ', ', 'MH': '; '}


def authenticate():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    token = HERE / 'token.json'
    if token.exists():
        creds = Credentials.from_authorized_user_file(token, SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token, 'w') as fh:
            fh.write(creds.to_json())

    return creds


def read_sheet(creds, sheet_id, range_name):
    # sheet_data = HERE / 'sheet.json'
    # if sheet_data.exists():
    #     return json.load(open(sheet_data))

    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId=sheet_id,
        range=range_name
    ).execute()
    json.dump(result, open('result.json', 'w'))
    data = result.get('values', [])
    # json.dump(data, open(sheet_data, 'w'))
    return data


def get_pubmed_id(column):
    pmid, pmcid = '', ''
    content = column.rsplit(None, 1)
    if content[-1].startswith(PUBMED_BASE_URL):
        pmid = urlsplit(content[-1]).path.strip('/')
    elif content[-1].startswith(PMCID_BASE_URL):
        pmcid = urlsplit(content[-1]).path.strip('/').rsplit('/', 1)[-1]
    return pmid, pmcid


def get_pubmed_ids(rows):
    pmids, pmcids = [], []
    for i, row in enumerate(rows):
        if len(row) < 3:
            continue
        column = row[2].strip()
        if not column:
            continue
        pmid, pmcid = get_pubmed_id(column)
        if pmid:
            pmids.append((pmid, i))
        elif pmcid:
            pmcids.append((pmcid, i))
    return pmids, pmcids


def search_pubmed(ids, is_pmc=False):
    batch_size = 1 if is_pmc else 100
    n = len(ids)
    pubmed_objects = []
    for start in range(0, n, batch_size):
        end = start + batch_size
        print(f'\r{start}-{end}', end='')
        batch_ids = [pubmed_id for pubmed_id, _ in ids[start:end]]
        resp = requests.get(PUBMED_BASE_URL, {'term': ','.join(batch_ids), 'size': batch_size,
                                              'format': 'pubmed'})
        resp.raise_for_status()
        objects = get_pubmed_content(resp.text)
        if is_pmc and objects:
            objects[0]['PMCID'] = batch_ids[0]
        pubmed_objects.extend(objects)
    return pubmed_objects


def get_pubmed_content(html):
    objects = []
    current = {}
    current_field = ''
    tree = BeautifulSoup(html, features='html.parser')
    tag = tree.find('pre')
    if not tag:
        return objects

    for line in tag.text.strip().splitlines():
        line = line.strip()
        if not current:
            objects.append(current)
        if not line:
            current = {}
        elif m := re.match(r'(\w+)\s*-(.+)$', line):
            identifier, text = m.groups()
            text = text.strip()
            current_field = identifier
            if current_field in FIELDS:
                if identifier not in MULTI_FIELDS:
                    current[current_field] = text
                else:
                    if not current.get(current_field):
                        current[current_field] = []
                    current[current_field].append(text)
        else:
            if current_field in FIELDS:
                if current_field not in MULTI_FIELDS:
                    current[current_field] += line
                else:
                    current[current_field].append(line)
    return objects


def main():
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    creds = authenticate()
    rows = read_sheet(creds, SPREADSHEET_ID, RANGE_NAME)

    pmids, pmcids = get_pubmed_ids(rows)
    pmobjects = {o['PMID']: o for o in search_pubmed(pmids)}
    pmcobjects = {o['PMCID']: o for o in search_pubmed(pmcids, True)}
    # json.dump(pmobject_map, open('pmobjects.json', 'w'))
    header = ['Section', 'Subsection', 'Title', 'Link', 'Author(s)', 'PubDate',
              'MeSH']
    with open('vaxpub.csv', 'w') as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        pmids = {y: x for x, y in pmids}
        pmcids = {y: x for x, y in pmcids}
        for i, row in enumerate(rows):
            if i in pmids:
                obj = pmobjects.get(pmids[i])
            elif i in pmcids:
                obj = pmcobjects.get(pmcids[i])
            else:
                obj = None

            if obj:
                writer.writerow([
                    '',
                    '',
                    obj['TI'],
                    f"{PUBMED_BASE_URL}{obj['PMID']}",
                    ', '.join(obj.get('AU') or []),
                    obj['DP'], '; '.join(obj.get('MH') or [])
                ])
            else:
                writer.writerow(row)




if __name__ == '__main__':
    main()
