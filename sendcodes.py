import argparse
import random
import string
import csv
import time
import json
from datetime import datetime
import pytz
import phonenumbers
import requests
import base64
import logging
import sys
import importlib
from phonenumbers import NumberParseException

# Config the log.
logging.basicConfig(filename='log-sendcodes.log', level=logging.INFO)

# CSV index values.
CEDRS_ID = 0
CASE_STATUS = 1
PHONE_NUMBER = 2
REPORTED_DATE = 3
# Tableau includes a blank column. Which is cool.
BLANK = 4

timezone = pytz.timezone('America/Denver')

def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s [ENV] [FILE]...",
        description="Send EN Verification codes from APHL's servers to phones of positive cases in a CSV."
    )

    parser.add_argument('--env', default='fake', help='The environment: prod, test, fake.')
    parser.add_argument('--file', default='testfile.csv', help='A filename in the local directory.')

    return parser

# Choose your env: prod, test, fake.
parser = init_argparse()
args = parser.parse_args()

# Use the arg to construct the name of the file to import
try:
    config = importlib.import_module(f"config{args.env}")
except:
    print(f"No valid env: {args.env}. Expected: prod, test, or fake.")
    exit(1)

print(f"Environment is {args.env} and file is {args.file} and url is {config.APHL_ADMIN_URL}.")

proceed = input('Do you want to continue? yes/no:').lower()
if (proceed == 'no'):
    print("Quitting on user input: no.")
    exit(1)
elif (proceed != 'yes'):
    print(f"Quitting on ambiguous user input: {proceed}.")
    exit(1)


# Logs out a row that can be easily grepped and reprocessed.
def log_line_for_retry(reason, this_row):
    csv_row = ','.join(this_row)
    logging.warning(f"Failedrow - {reason}:{csv_row}.")
    return


# For the padding get a random base64 string.
def get_random_base64_string():
    # This does not need to be cryptographically secure randomness.
    length = random.randint(5, 20)
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return base64.b64encode(result_str.encode('utf-8')).decode('ascii')


# Open up the file and process it.
with open(args.file, newline='', encoding='utf16') as csv_file:
    # Tableau downloaded "Data" files are excel-tab formatted utf16 files.
    aphl_reader = csv.reader(csv_file, dialect="excel-tab")

    for row in aphl_reader:

        # Skip the header row.
        if row[CEDRS_ID] == 'CEDRS ID':
            continue

        # Try to parse the phone and skip bad phone numbers.
        try:
            parsed_phone = phonenumbers.parse(row[PHONE_NUMBER], "US")
        except NumberParseException as number_parse_exception:
            logging.warning(f"Skipping CEDRS '{row[CEDRS_ID]}' phone number '{row[PHONE_NUMBER]}' because it is invalid.")
            log_line_for_retry('very_invalid_phone', row)
            continue

        if not phonenumbers.is_valid_number(parsed_phone):
            logging.warning(f"Skipping CEDRS '{row[CEDRS_ID]}' phone number '{row[PHONE_NUMBER]}' because it is invalid.")
            log_line_for_retry('invalid_phone', row)
            continue

        # Parse the date.
        parsed_date = datetime.strptime(row[REPORTED_DATE], '%m/%d/%Y')

        # calculate offset based on testDate to handle daylight savings time
        tzOffset = timezone.utcoffset(parsed_date).total_seconds() / 60

        # TESTING: to test without sending tons of texts uncomment the phone line in this dict.
        requestDict = {
            "testDate": parsed_date.strftime('%Y-%m-%d'),
            "testType": "confirmed",
            "tzOffset": tzOffset,
            "phone": f"+{parsed_phone.country_code}{parsed_phone.national_number}",
            "padding": get_random_base64_string(),
        }

        try:
            # Code issuance is throttled at 60/minute. Wait a second per code to stay below that.
            # https://github.com/google/exposure-notifications-verification-server/issues/1028
            time.sleep(1)

            # The test env will send real codes, so be careful with the following code.
            response = requests.post(config.APHL_ADMIN_URL,
                                     data=json.dumps(requestDict),
                                     headers={
                                        "content-type": "application/json",
                                        "accept": "application/json",
                                        "x-api-key": config.APHL_ADMIN_API_KEY})

        # Catch all exceptions. Ignore linter warning below.
        except:
            # Check for any exceptions and log them.
            exception = sys.exc_info()[0]

            log_line_for_retry('server_talk_error', row)
            logging.warning(f"APHL error for CEDRS '{row[CEDRS_ID]}' phone number '{row[PHONE_NUMBER]}' exception: '{exception}'.")
            continue

        # Check the status codes to handle.
        if response.status_code == 500:
            log_line_for_retry('500_error', row)
            logging.warning(f"500 error for CEDRS '{row[CEDRS_ID]}' phone number '{row[PHONE_NUMBER]}' status  '{response.status_code}'.")
            continue
        elif response.status_code == 400:
            response_text = response.json()
            log_line_for_retry('400_error', row)
            logging.warning(f"400 error for CEDRS '{row[CEDRS_ID]}' phone number '{row[PHONE_NUMBER]}' status  '{response.status_code}' error '{response_text['error']}' errorcode '{response_text['errorCode']}'.")
            continue
        elif response.status_code != 200:
            response_text = response.json()
            log_line_for_retry(f"{response.status_code}_error", row)
            logging.warning(f"Non 200 for CEDRS '{row[CEDRS_ID]}' phone number '{row[PHONE_NUMBER]}' status  '{response.status_code}' response {response_text}.")
            continue

        # No exceptions, get response to inspect.
        response_text = response.json()

        # Check for APHL errors and log them.
        if response_text['error']:
            logging.warning(f"APHL error for CEDRS '{row[CEDRS_ID]}' phone number '{row[PHONE_NUMBER]}' error '{response_text['error']}' errorcode '{response_text['errorCode']}'.")
            log_line_for_retry('aphl_error', row)
            continue

        # Now assume success. Yay!
        print(f"{row[CEDRS_ID]},{parsed_phone.national_number},{response_text['uuid']}")
        logging.info(f"Success for CEDRS '{row[CEDRS_ID]}' phone number '{row[PHONE_NUMBER]}'. :thumbsup:.")
