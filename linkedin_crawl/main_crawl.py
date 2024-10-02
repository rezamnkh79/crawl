import re
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By

driver = webdriver.Chrome('')  # Optional argument, if not specified will search path.
driver.get("https://linkedin.com/uas/login")

# Waiting for the page to load
time.sleep(2)

# Entering usernameselenium
username = driver.find_element(By.ID, "username")

# Enter Your Email Address
username.send_keys("your email address")

# Entering password
pword = driver.find_element(By.ID, "password")

# Enter Your Password
pword.send_keys("your password")

# Clicking on the log in button
driver.find_element(By.XPATH, "//button[@type='submit']").click()

# Wait for the page to load after login
time.sleep(2)

# Optionally, you can navigate to a profile or other pages and scrape data
driver.get("https://www.linkedin.com/feed/")
time.sleep(2)

# Scrape data using BeautifulSoup
soup = BeautifulSoup(driver.page_source, 'html.parser')

# Parse the page content with BeautifulSoup
# Find the div with the specific data-id containing "urn:li:activity:sth"
for data in soup.find('div', {'data-id': lambda x: x and x.startswith("urn:li:activity:")}):
    text = data.text
    text = text.replace("\n", "").replace("         ", "")
    # regex for arabic text
    reg = re.compile('([\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)*)\s*')
    result = list(filter(None, reg.split(text)))
    print(result)
# Close the driver
driver.quit()
