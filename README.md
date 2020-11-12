This is a package for interacting with the APHL API to send verification codes to people with a COVID-19 positive test result.

You will need access to an APHL verification server, ideally both test and prod. If you don't have that work with the APHL to get it.

It uses pyenv and pipenv to help manage versions and packages.

It's important to have pyenv and pipenv already installed.

## To install dependencies

Use pipenv: `pipenv install`

## To try things out

Set the env to fake inside sendcodes and run the script below

## To generate codes from encv test or prod environment

1. Set the env to test
2. `cp configfake.py configtest.py` and edit the values to be real values from your server.

For prod do the above 2 steps with `prod` instead of test.

## To run a script 

Use pipenv: `pipenv run python sendcodes.py`


## Manually testing the code:

The testfile-sample.csv should be copied to testfile.csv and modified so the 3rd-6th rows are real phone numbers.

The testfile.csv supports 4 test scenarios.

1. The first line is a bad phone number (too short). Should get logged.
2. The second line has a test date that is too old. Should get rejected by APHL and logged.
3. The 3rd and 4th lines are fine, but test that prefixing the number with 1 works.
4. The 5th line is an empty phone number - not super common, but can happen.
5. Test toggling the APHL_ADMIN_URL and/or APHL_ADMIN_API_KEY to test failures at server connection are logged when testing the 3rd/4th lines.

Running the file with **valid** APHL url and creds - `grep :root: log-sendcodes.log` should produce:

```
WARNING:root:Skipping CEDRS '703967' phone number '303555121' because it is invalid.
WARNING:root:Failedrow - invalid_phone:703967,Confirmed,303555121,11/06/2020.
WARNING:root:Failedrow - 400_error:703966,Confirmed,7203105623,09/06/2020.
WARNING:root:400 error for CEDRS '703966' phone number '7203105623' status  '400' error 'test date must be on/after 2020-10-15 and on/before 2020-11-12 2020-09-06' errorcode ''.
INFO:root:Success for CEDRS '703965' phone number '7203105623'. :thumbsup:.
INFO:root:Success for CEDRS '703964' phone number '17203105623'. :thumbsup:.
WARNING:root:Skipping CEDRS '703963' phone number '' because it is invalid.
WARNING:root:Failedrow - very_invalid_phone:703963,Confirmed,,11/06/2020.
```

Running the file with **invalid** APHL url and creds - `grep :root: log-sendcodes.log` should produce:

```
WARNING:root:Skipping CEDRS '703967' phone number '303555121' because it is invalid.
WARNING:root:Failedrow - invalid_phone:703967,Confirmed,303555121,11/06/2020.
WARNING:root:Failedrow - server_talk_error:703966,Confirmed,7203105623,09/06/2020.
WARNING:root:APHL error for CEDRS '703966' phone number '7203105623' exception: '<class 'requests.exceptions.ConnectionError'>'.
WARNING:root:Failedrow - server_talk_error:703965,Confirmed,7203105623,11/06/2020.
WARNING:root:APHL error for CEDRS '703965' phone number '7203105623' exception: '<class 'requests.exceptions.ConnectionError'>'.
WARNING:root:Failedrow - server_talk_error:703964,Confirmed,17203105623,11/06/2020.
WARNING:root:APHL error for CEDRS '703964' phone number '17203105623' exception: '<class 'requests.exceptions.ConnectionError'>'.
WARNING:root:Skipping CEDRS '703963' phone number '' because it is invalid.
WARNING:root:Failedrow - very_invalid_phone:703963,Confirmed,,11/06/2020.
```
