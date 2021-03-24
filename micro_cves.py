import requests
import json
import re
from datetime import datetime
import pandas as pd
import argparse


def get_data(path):  # fetch data from Microsoft API
    try:
        api_url = 'https://api.msrc.microsoft.com/sug/v2.0/en-US'
        raw_data = json.loads(requests.get(api_url + path).text)
        return raw_data
    except Exception, e:
        print e
        exit()


def check_date_format(date):  # validate date format of args
    regex = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    if not regex.match(date):
        msg = "Not a valid date: '{date}'.".format(date=date)
        raise argparse.ArgumentTypeError(msg)

    return date


def get_ack(from_date, to_date):  # get acknowledgement list since a specific date
    try:
        acks_api = '/acknowledgement?%24orderBy=releaseDate+desc&%24filter=%28releaseDate+gt+{from_date}T00%3A00%3A00%2B02%3A00%29' \
                   '+and+%28releaseDate+lt+{to_date}T23%3A59%3A59%2B02%3A00%29'.format(to_date=to_date, from_date=from_date)
        acks = get_data(acks_api)
        return acks
    except Exception, e:
        print e
        exit()


def get_cvss(cve):  # get CVSS score for specific CVE
    try:
        cvss_score_api = '/affectedProduct?%24filter=cveNumber+eq+%27{cve}%27'.format(cve=cve)
        cvss_score = get_data(cvss_score_api)['value'][0]['baseScore']
        return cvss_score
    except:
        return ''


def get_desc(cve):  # get description for specific CVE
    try:
        desc_api = '/vulnerability/' + cve
        desc_raw = get_data(desc_api)
        desc = clean_html(desc_raw['articles'][0]['description'].split("\n")[1])
        return desc
    except:
        return 'No additional description'


def clean_html(text):  # removes HTML tags from fields
    regex = re.compile(r'<[^>]+>')
    return regex.sub('', text)


def get_cves(from_date, to_date, output):
    try:
        acks = get_ack(from_date, to_date)
        records = []
        for cve in acks['value']:
            if cve['cveNumber'] and cve['ackText']:
                record = {'cve': cve['cveNumber'],
                          'date': cve['releaseDate'],
                          'ack': clean_html(cve['ackText']),
                          'name': cve['cveTitle']}

                record['desc'] = get_desc(cve['cveNumber'])
                record['cvss'] = get_cvss(cve['cveNumber'])
                records.append(record)

        df = pd.DataFrame(records)
        df.to_csv(output + '.csv', index=None, encoding='utf-8',
                  columns=['date', 'cve', 'cvss', 'ack', 'name', 'desc'])

    except Exception, e:
        print e


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Microsoft CVEs crawler")
    parser.add_argument('-f',
                        dest='from_date',
                        type=check_date_format,
                        required=True,
                        help='Choose date to start from. format YYYY-MM-DD. Example: 2021-02-10')

    parser.add_argument('-t',
                        dest='to_date',
                        type=check_date_format,
                        required=False,
                        default=datetime.today().strftime('%Y-%m-%d'),
                        help='Choose end to. Default is today. format YYYY-MM-DD. Example: 2021-03-22')

    parser.add_argument('-o',
                        dest='output',
                        required=False,
                        default='microsoft_cves',
                        help='CVS file name to export to.')
    args = parser.parse_args()
    get_cves(args.from_date, args.to_date, args.output)
