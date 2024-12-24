import subprocess

from flask import Flask, render_template, jsonify
import os
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import pymongo
import uuid
import requests
from webdriver_manager.chrome import ChromeDriverManager


# Initialize Flask app
app = Flask(__name__)

# MongoDB Setup
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["twitter_scraping"]
collection = db["trending_topics"]

# proxymix setup for changing proxy
current_directory = os.path.dirname(os.path.abspath(__file__))
pac_file_path = f'file:///{current_directory}/us-ca.pac'

# setting up the proxy
chrome_options = Options()
chrome_options.add_argument(f'--proxy-pac-url={pac_file_path}')

def get_driver():
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get("https://twitter.com/login")
    return driver


def login(driver, username, password):
    time.sleep(3)

    username_field = driver.find_element(By.NAME, "text")
    username_field.send_keys(username)  # Replace with your Twitter username
    username_field.send_keys(Keys.RETURN)
    time.sleep(3)

    password_field = driver.find_element(By.NAME, "password")
    password_field.send_keys(password)  # Replace with your Twitter password
    password_field.send_keys(Keys.RETURN)
    time.sleep(5)


# main logic of getting the trending data
# as for now only 4 of them are listed in the page
# for getting more we have go to next page but as per instructions i did it on home page
def get_trending_topics(driver):

    res = []
    trending_topics = driver.find_elements(By.XPATH, '//div[@class="css-175oi2r r-1adg3ll r-1ny4l3l"]')[2:6]
    for i, topic in enumerate(trending_topics, 1):
        trending_title = topic.find_elements(By.XPATH, './/span')
        final_text = trending_title[0].text
        if len(trending_title) >= 2:
            final_text = trending_title[1].text

        res.append(final_text)

    return res


def store_data(trending_topics, ip_address):
    unique_id = str(uuid.uuid4())

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    data = {
        "_id": unique_id,
        "name_of_trend1": trending_topics[0] if len(trending_topics) > 0 else "",
        "name_of_trend2": trending_topics[1] if len(trending_topics) > 1 else "",
        "name_of_trend3": trending_topics[2] if len(trending_topics) > 2 else "",
        "name_of_trend4": trending_topics[3] if len(trending_topics) > 3 else "",
        "name_of_trend5": trending_topics[4] if len(trending_topics) > 4 else "",
        "date_time": timestamp,
        "ip_address": ip_address
    }


    collection.insert_one(data)


def scrap_data(username, password):
    driver = get_driver()
    login(driver, username, password)

    # wait for page loading
    time.sleep(5)

    # Get trending topics
    trending_topics = get_trending_topics(driver)

    # getting ip address
    response = requests.get('https://api.ipify.org?format=json')
    ip_address = response.json()['ip']

    #storing data
    store_data(trending_topics, ip_address)

    # Close the driver
    driver.quit()

    return trending_topics, ip_address




def get_latest_trending_data():
    latest_data = collection.find().sort("date_time", -1).limit(1)
    return latest_data[0] if latest_data else None


def run_scraping_script(username, password):
    try:
        
        trending_topics, ip_address = scrap_data(username, password)
        print("Trending Topics:", trending_topics)
        print("IP Address used:", ip_address)

    except Exception as e:
        print(f"Error running script: {str(e)}")
        return None

# root route
@app.route('/')
def index():
    return render_template('index.html')

# route to run the script
@app.route('/run_script')
def run_script():

    # change credentials sorry you can try using any test account as for now
    # I don't have any test account I apologize for that.
    username = "by_mohammad_ashfaq"
    password = "********"  # please update these

    run_scraping_script(username, password)

    # getting data from the mongodb
    latest_data = get_latest_trending_data()

    if latest_data:

        formatted_data = {
            'timestamp': latest_data['date_time'],
            'trends': [
                latest_data['name_of_trend1'],
                latest_data['name_of_trend2'],
                latest_data['name_of_trend3'],
                latest_data['name_of_trend4'],
                latest_data['name_of_trend5']
            ],
            'ip_address': latest_data['ip_address'],
            'json_extract': latest_data
        }
        return render_template('result.html', data=formatted_data)
    else:
        return "No data found in MongoDB.", 404

if __name__ == '__main__':
    app.run(debug=True)
