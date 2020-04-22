# TFL-Open-Data-Processor
A backend component written in Python to process TFL Open Data APIs.


Currently stores data in MongoDB.

Install the requirements in requirements.txt, and enter your tfl app ID and app Key in tfl_auth_template.ini and rename to tfl_auth.ini (API credentials not required), enter mongodb url.

Works hand in hand with the Front-End-TFL-Data project.

## TODO
- ~~Implement Station Markers~~
- ~~Get train locations (can only get prediction data from TFL API once every 30 seconds)~~
- ~~Extraploate prediction data to ensure movement during the 30 seconds until data refresh~~
- Code cleanup and proper error handling
- Tests

