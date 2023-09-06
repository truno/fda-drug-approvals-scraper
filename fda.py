from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient
from email.message import EmailMessage
from datetime import datetime
import natsort
import glob
import os
import csv
import smtplib
import ssl
import time
import logging
import argparse
import chromedriver_binary #adds the chrome driver executable to PATH so it will be found

def main(download_file):
    port = os.getenv('FDA_MAIL_SMTP_PORT')
    smtp_server = os.getenv('FDA_MAIL_SMTP_SERVER')
    sender_email = os.environ.get('FDA_SENDER_EMAIL')
    password = os.environ.get('FDA_MAIL_PASSWORD')
    receiver_email = os.environ.get('FDA_RECEIVER_EMAIL')
    temp_folder = os.environ.get('FDA_TEMP_SUBDIR')
    log_file = os.environ.get('FDA_LOG_FILE')

    logFormatter = logging.Formatter("%(asctime)s [%(threadName)s] [%(levelname)s] %(message)s")
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.INFO)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)

    if log_file:
        fileHandler = logging.FileHandler(os.path.join(os.getcwd(), log_file))
        fileHandler.setFormatter(logFormatter)
        rootLogger.addHandler(fileHandler)
    
    logging.info("Starting new drug approval check at Drugs@FDA: FDA-Approved Drugs")
    filenames = natsort.natsorted(glob.glob(temp_folder+'/*'))
    [os.remove(file) for file in filenames]

    if not download_file:
        options = Options()
        options.headless = True
        prefs = {'download.default_directory': os.path.join(os.getcwd(), temp_folder)}
        options.add_experimental_option('prefs', prefs)
        driver = webdriver.Chrome(options=options)
    
        driver.get("https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm")
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, '//*[@id="main-content"]/div/div[5]/div[1]/h4/a'))).click()
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, '//*[@id="collapseReports"]/div/form/div[7]/div/button[1]'))).click()
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, '//*[@id="example_1_wrapper"]/div[1]/a[1]/span'))).click()
        time.sleep(2) # delayed needed to complete download before closing driver
        driver.close()

        filenames = natsort.natsorted(glob.glob(temp_folder+'/*'))
        if len(filenames) != 1:
            logging.error("Incorrect number of download files, should be one file")
            return
        elif not filenames[0].endswith('.csv'):
            logging.error("Download file was not a .csv file")
            return
        else:
            download_file = filenames[0]

    client = MongoClient()
    db = client.fda
    new_drugs = []
    with open(download_file, 'r', newline='') as in_file:
        reader = csv.reader(in_file)        
        next(reader) # skip header
        for in_row in reader:
            drug_app = in_row[1].split('  #')
            app_num = drug_app[1]
            drug = drug_app[0].rstrip(' ')
            if drug.endswith('ANDA'):
                drug = drug[:len(drug)-len('ANDA')]
                app_type = "ANDA"
            elif drug.endswith('NDA'):
                drug = drug[:len(drug)-len('NDA')]
                app_type = "NDA"
            elif drug.endswith('BLA'):
                drug = drug[:len(drug)-len('BLA')]
                app_type = "BLA"
            else:
                app_type = "Unknown"
        
            row = {'Approval Date': in_row[0],
                'Drug Name': drug,
                'Application Type': app_type,
                'Application Number': app_num,
                'Submission': in_row[2], 
                'Active Ingredients': in_row[3],
                'Company': in_row[4],
                'Submission Classification': in_row[5],
                'Submission Status': in_row[6]}
            if not db.fda.count_documents( 
                {'Approval Date': row['Approval Date'],
                'Drug Name': row['Drug Name'],
                'Application Number': row['Application Number'],
                'Submission': row['Submission']} 
            ):
                logging.info('\tNew Drug Approval:', drug, 'for', in_row[4])
                new_drugs.append(row)

    drug_count = len(new_drugs)
    if drug_count:
        if db.fda.insert_many(new_drugs):
            logging.info('\t'+str(drug_count)+' New Drugs Approval(s)')
        else:
            logging.error('\tError: '+str(drug_count)+' inserts failed.')
        if sender_email and smtp_server and password and receiver_email:
            html = "<!DOCTYPE html><html><h3>"+str(drug_count)+" New Drug Approval(s)</h3><body><table>"
            for row in new_drugs:
                for k in row.keys():
                    html = html + '<tr><td>' + k + '</td><td>' + row[k] + '</td></tr>'
                row['Last Modified'] = datetime.utcnow()
                html = html + "<tr><td>-------------------------</td></tr>"    
            html = html + "</table></body></html>"

            msg = EmailMessage()
            msg.set_content("New FDA Drug Approvals")
            msg.add_alternative(html, subtype='html')
            msg['Subject'] = "FDA New Drug Approval(s)"
            msg['From'] = sender_email
            msg['To'] = receiver_email
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
                server.login(sender_email, password)
                server.send_message(msg, from_addr=sender_email, to_addrs=receiver_email)
        else:
            logging.info('Email disabled')
    else:
        logging.info('No new drug approvals found')

def is_valid_filename(parser, arg):
    if not os.path.exists(arg):
        parser.error("The file %s does not exist!" % arg)
    elif not arg.endswith(".csv"):
        parser.error("The file %s is not a .csv file" % arg)
    else:
        return arg
  
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", 
                        dest="download_file", 
                        help="csv input file for FDA-Approved Drugs website",
                        type=lambda x: is_valid_filename(parser, x))
    args = parser.parse_args()

    main(args.download_file)