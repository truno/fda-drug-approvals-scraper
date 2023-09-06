# fda-drugs-scraper
Python web scraper monitoring fda drugs website for approved drugs. This web scraper will check the Drugs@FDA: FDA-Approved Drugs (https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm), pull down the latest monthly list of approved drugs and process it to the MongoDB database. Optionally, email environment variables can be configured to automatically send updates.

## Usage

1. You will need python 3.10+ and MongoDB
2. Clone this repo, then navigate to the folder and install requirements via `pip -r requirements.txt`
3. Install ChromeDriver 114.0.5735.90 from [ChromeDriver](https://chromedriver.chromium.org/downloads)
4. Create a temporary download directory
5. Configure environment variables (if email env variables are not defined, no error will be thrown but emails won't be sent)
   export FDA_LOG_FILE='fda_out.log'
   export FDA_TEMP_SUBDIR='temp'
   export FDA_MAIL_SMTP_PORT=465
   export FDA_MAIL_SMTP_SERVER="smtp.gmail.com"
   export FDA_SENDER_EMAIL="youremail@gmail.com"
   export FDA_MAIL_PASSWORD="yourgmailpassword"
   export FDA_RECEIVER_EMAIL="receiver@somewhere.com"
7. If running in webscraping mode: `python fda.py`
8. Adding `-i filename.csv` will forego the web scraping and process the specified file. Note this file must be in the FDA defined format as downloaded from the the website.
