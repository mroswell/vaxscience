import csv
from datetime import datetime
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
SHEETS = {
    'Vaccine Publication': 'VaxPublicationsONLY',
    'COVID‐19 Publication': 'Covid Relevant Publications',
}

HERE = Path(__file__).resolve().parent
CREDENTIALS = HERE / 'credentials.json'

PUBMED_BASE_URL = 'https://pubmed.ncbi.nlm.nih.gov/'
PMCID_BASE_URL = 'https://www.ncbi.nlm.nih.gov/'

IDCONV_URL = 'https://www.ncbi.nlm.nih.gov/pmc/tools/idconv/'
IDCONV_RESULT_URL = 'https://www.ncbi.nlm.nih.gov/pmc/tools/idconv/result/'
CSRF_COOKIE_NAME = 'pmc-idconv-csrftoken'

FIELDS = {'PMID', 'TI', 'FAU', 'MH', 'DP', 'AD', 'AB'}
MULTI_FIELDS = {'FAU', 'MH', 'AD'}


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
        spreadsheetId=SPREADSHEET_ID,
        range=range_name
    ).execute()
    json.dump(result, open('result.json', 'w'))
    data = result.get('values', [])
    return data


def get_pubmed_id(column):
    column = column.replace(':https://', ': https://')
    pmid, pmcid = '', ''
    content = column.rsplit(None, 1)
    if content[-1].startswith(PUBMED_BASE_URL):
        pmid = urlsplit(content[-1]).path.split('/')[1]
    elif content[-1].startswith(PMCID_BASE_URL):
        pmcid = urlsplit(content[-1]).path.strip('/').rsplit('/', 1)[-1]
    return pmid, pmcid


def get_pubmed_ids(rows):
    pmids, pmcids = set(), set()
    for i, row in enumerate(rows):
        pmid, pmcid = '', ''
        try:
            for idx in (2, 3):
                pmid, pmcid = get_pubmed_id(row[idx].strip())
                if pmid or pmcid:
                    break
        except IndexError:
            continue
        if pmid:
            pmids.add((pmid, i))
        elif pmcid:
            pmcids.add((pmcid, i))
    return list(pmids), list(pmcids)


def search_pubmed(ids, is_pmc=False):
    batch_size = 1 if is_pmc else 100
    n = len(ids)
    pubmed_objects = []
    for start in range(0, n, batch_size):
        end = start + batch_size
        print(f'\rSearching pubmed: {start: 5d} - {end: 5d}', end='')
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
                    current[current_field] += f' {line}'
                else:
                    current[current_field][-1] += f' {line}'
    return objects


def datetime_string(value):
    if not value:
        return ''

    value = value.replace('-', ' ')
    if len(value.split()) == 1:
        dt = datetime.strptime(value, '%Y')
    elif len(value.split()) == 2:
        dt = datetime.strptime(value, '%Y %b')
    else:
        try:
            dt = datetime.strptime(value, '%Y %b %d')
        except:
            dt = datetime.strptime(' '.join(value.split()[:2]), '%Y %b')
    return dt.strftime('%Y-%m-%d 00:00:00')


def get_pmc_ids(ids):
    session = requests.Session()
    resp = session.get(IDCONV_URL)
    resp.raise_for_status()
    csrftoken = resp.cookies.get(CSRF_COOKIE_NAME)
    batch_size=100
    n = len(ids)
    id_map = {}
    for start in range(0, n, batch_size):
        end = start + batch_size
        batch_ids = [pubmed_id for pubmed_id, _ in ids[start:end]]
        data = {
            'format': 'json',
            'ids': ','.join(batch_ids),
            'csrfmiddlewaretoken': csrftoken,
        }
        headers = {**session.headers, 'origin': PUBMED_BASE_URL, 'referer': IDCONV_URL}
        resp = session.post(IDCONV_RESULT_URL, data=data, headers=headers)
        resp.raise_for_status()
        for record in resp.json()['records']:
            id_map[record['pmid']] = record.get('pmcid', '')
    return id_map


def main():
    creds = authenticate()
    rows_map = {pubtype: read_sheet(creds, sheet) for pubtype, sheet in SHEETS.items()}

    with open('vaxpub.csv', 'w') as fh:
        header = ['Section', 'Subsection', '', 'Link(s)', 'Title', 'Author(s)', 'Affiliation', 'PMID', 'PMCID', 'PubDate', 'MeSH', 'Abstract', 'PubType']
        writer = csv.writer(fh)
        writer.writerow(header)

        for pubtype, rows in rows_map.items():
            pmids, pmcids = get_pubmed_ids(rows)
            pm2pmc = get_pmc_ids(pmids)
            pmobjects = {o['PMID']: {'PMCID': pm2pmc[o['PMID']], **o} for o in search_pubmed(pmids)}
            pmcobjects = {o['PMCID']: o for o in search_pubmed(pmcids, True)}
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
                        row[2],
                        f"{PUBMED_BASE_URL}{obj['PMID']} {PMCID_BASE_URL + 'pmc/articles/' + obj['PMCID'] + '/' if obj['PMCID'] else '' }",
                        obj['TI'],
                        '; '.join(obj.get('FAU') or []),
                        '; '.join(obj.get('AD') or []),
                        obj['PMID'],
                        obj['PMCID'],
                        datetime_string(obj['DP']),
                        '; '.join(obj.get('MH') or []),
                        obj.get('AB'),
                        pubtype,
                    ])
                else:
                    writer.writerow(row)




if __name__ == '__main__':
    main()
