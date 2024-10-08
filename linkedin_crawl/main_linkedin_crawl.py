import csv
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def type_with_delay(element, text, delay=0.1):
    """Simulate typing with a delay."""
    for character in text:
        element.send_keys(character)
        time.sleep(delay)  # Delay in seconds


# LinkedIn credentials
username_str = "alinoradi92@gmail.com"
password_str = "42184433"
search_url = "https://www.linkedin.com/search/results/people/?facetGeoRegion=%5B%22us%3A0%22%5D&facetIndustry=%5B%22106%22%2C%2243%22%2C%2241%22%2C%2242%22%2C%2246%22%2C%2245%22%2C%22129%22%5D&keywords=ali&origin=FACETED_SEARCH"
# search_url = "https://www.linkedin.com/search/results/all/?facetGeoRegion=%5B%22us%3A0%22%5D&facetIndustry=%5B%22106%22%2C%2243%22%2C%2241%22%2C%2242%22%2C%2246%22%2C%2245%22%2C%22129%22%5D' '&keywords=ali +&origin=FACETED_SEARCH"

# Set up the Firefox options and driver
options = Options()
options.headless = False  # Set to True to run in headless mode

# Initialize the Firefox driver
driver = webdriver.Chrome('')  # Optional argument, if not specified will search path.
driver.get("https://linkedin.com/uas/login")
try:
    # Open LinkedIn login page
    driver.get("https://www.linkedin.com/login")

    # Wait for the username input to load and enter the username
    # Wait for the username input to load and enter the username
    username_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "username"))
    )
    type_with_delay(username_input, username_str, delay=0.25)  # Adjust delay as needed

    time.sleep(1)

    # Enter the password
    password_input = driver.find_element(By.ID, "password")
    type_with_delay(password_input, password_str, delay=0.25)  # Adjust delay as needed

    time.sleep(1)

    # Click the login button
    login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
    login_button.click()

    # Wait for the home page to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "global-nav-search"))
    )
    time.sleep(2)
    # Navigate to the LinkedIn search results page
    driver.get(search_url)

    # Wait for the page to load completely
    time.sleep(5)  # Adjust the sleep time if necessary

    # Scroll to the bottom to load all profiles (if necessary)
    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
    time.sleep(3)  # Adjust the sleep time if necessary

    # Parse the page content with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Find all profile containers (adjust the selector if necessary)
    profile_containers = soup.find_all('div', {'class': 'search-results-container'})

    # Extract profile information
    profiles = []
    profile_containers_tag = profile_containers[0]
    profile_containers = profile_containers_tag.find('ul',
                                                     "reusable-search__entity-result-list list-style-none").contents
    for container in profile_containers:
        try:
            if container.find('span', {'class': 'entity-result__title-text'}) is not None:
                name = container.find('span', {'class': 'entity-result__title-text'}).get_text(strip=True)
                headline = container.find('div', {'class': 'entity-result__primary-subtitle'}).get_text(strip=True)
                location = container.find('div', {'class': 'entity-result__secondary-subtitle'}).get_text(strip=True)
                profile_link = container.find('a', {'class': 'app-aware-link'})['href']
                profiles.append({
                    'name': name,
                    'headline': headline,
                    'location': location,
                    'profile_link': profile_link
                })
        except Exception as e:
            continue

    # Write profiles to a CSV file
    with open('profiles.csv', mode='w', newline='', encoding='utf-8') as csv_file:
        fieldnames = ['name', 'headline', 'location', 'profile_link']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

        writer.writeheader()  # Write header row
        for profile in profiles:
            writer.writerow(profile)  # Write profile data

    print("Profile data has been written to profiles.csv")
finally:
    # Close the browser
    driver.quit()
