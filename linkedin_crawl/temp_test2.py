import csv
import time
import imaplib
import email
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def get_verification_code(email_user, email_pass):
    """Retrieve the verification code from the email."""
    # Connect to the email server
    mail = imaplib.IMAP4_SSL('imap.gmail.com')  # Change according to your email provider
    mail.login(email_user, email_pass)
    mail.select('inbox')

    # Search for the latest email from LinkedIn
    result, data = mail.search(None, '(FROM "no-reply@linkedin.com")')
    email_ids = data[0].split()

    if email_ids:
        latest_email_id = email_ids[-1]  # Get the latest email
        result, msg_data = mail.fetch(latest_email_id, '(RFC822)')
        raw_email = msg_data[0][1]

        # Parse the email content
        msg = email.message_from_bytes(raw_email)
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()

        # Extract the verification code using regex or string operations
        # Assuming the code is in a specific format in the email body
        code = body.split("is ")[1][:6]  # Example of extracting the code
        return code
    return None


def scrape_linkedin(username, password, email_user, email_pass, search_url):
    """Function to scrape LinkedIn profiles."""
    # Set up the Firefox options and driver
    options = Options()
    options.headless = False  # Set to True to run in headless mode

    # Initialize the WebDriver
    driver = webdriver.Chrome()  # Ensure you have the ChromeDriver installed and in your PATH
    driver.get("https://www.linkedin.com/login")

    try:
        # Wait for the username input to load and enter the username
        username_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        type_with_delay(username_input, username, delay=0.25)

        time.sleep(1)

        # Enter the password
        password_input = driver.find_element(By.ID, "password")
        type_with_delay(password_input, password, delay=0.25)

        time.sleep(1)

        # Click the login button
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()

        # Wait for the verification code input
        verification_code = get_verification_code(email_user, email_pass)
        if verification_code:
            # Input the verification code if received
            code_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "input__password"))
            )
            type_with_delay(code_input, verification_code, delay=0.25)
            time.sleep(1)

            # Click the verify button
            verify_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            verify_button.click()

        # Wait for the home page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "global-nav-search"))
        )
        time.sleep(2)

        # Navigate to the LinkedIn search results page
        driver.get(search_url)

        # Wait for the page to load completely
        time.sleep(5)

        # Scroll to the bottom to load all profiles (if necessary)
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
        time.sleep(3)

        # Parse the page content with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Find all profile containers (adjust the selector if necessary)
        profile_containers = soup.find_all('div', {'class': 'search-results-container'})

        # Extract profile information
        profiles = []
        if profile_containers:
            profile_containers_tag = profile_containers[0]
            profile_containers = profile_containers_tag.find('ul',
                                                             "reusable-search__entity-result-list list-style-none").contents
            for container in profile_containers:
                try:
                    if container.find('span', {'class': 'entity-result__title-text'}) is not None:
                        name = container.find('span', {'class': 'entity-result__title-text'}).get_text(strip=True)
                        headline = container.find('div', {'class': 'entity-result__primary-subtitle'}).get_text(
                            strip=True)
                        location = container.find('div', {'class': 'entity-result__secondary-subtitle'}).get_text(
                            strip=True)
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
        filename = 'profiles.csv'
        with open(filename, mode='w', newline='', encoding='utf-8') as csv_file:
            fieldnames = ['name', 'headline', 'location', 'profile_link']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()  # Write header row
            for profile in profiles:
                writer.writerow(profile)  # Write profile data

        print(f"Profile data has been written to {filename}")
    finally:
        # Close the browser
        driver.quit()


if __name__ == '__main__':
    # LinkedIn credentials and search URL
    username_str = "alinoradi92@gmail.com"
    password_str = "42184433"
    email_user = "alinoradi92@gmail.com"  # Your email to read the verification code
    email_pass = "42184433"  # Your email password
    search_url = "https://www.linkedin.com/search/results/people/?facetGeoRegion=%5B%22us%3A0%22%5D&facetIndustry=%5B%22106%22%2C%2243%22%2C%2241%22%2C%2242%22%2C%2246%22%2C%2245%22%2C%22129%22%5D&keywords=ali&origin=FACETED_SEARCH"

    # Number of threads
    num_threads = 1

    # Create a ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for i in range(num_threads):
            futures.append(
                executor.submit(scrape_linkedin, username_str, password_str, email_user, email_pass, search_url))

        # Wait for all threads to complete
        for future in as_completed(futures):
            try:
                future.result()  # Get result from the future, if needed
            except Exception as e:
                print(f"An error occurred: {e}")
