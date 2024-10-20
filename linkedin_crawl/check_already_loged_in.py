import csv
import random
import time
import redis
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class LinkedInScraper:
    def __init__(self, username, password, redis_client):
        self.username = username
        self.password = password
        self.driver = self.setup_driver()
        self.redis_client = redis_client
        self.is_logged_in = False
        self.session_cookie = None

    def setup_driver(self):
        """Set up the Chrome options and WebDriver."""
        options = Options()
        options.headless = False  # Set to True to run in headless mode
        driver = webdriver.Chrome(options=options)  # Ensure you have the ChromeDriver installed and in your PATH
        return driver

    def load_session(self):
        """Load session from Redis."""
        session_key = f"linkedin_session:{self.username}"
        self.session_cookie = self.redis_client.get(session_key)

        if self.session_cookie:
            self.driver.get("https://www.linkedin.com")
            # Set the session cookie in the browser
            self.driver.add_cookie({
                'name': 'li_at',
                'value': self.session_cookie.decode('utf-8'),
                'domain': '.linkedin.com'
            })
            self.driver.refresh()  # Refresh to apply the cookie
            self.check_login()  # Check if login was successful
        else:
            print("No session found in Redis. Proceeding to login.")

    def check_login(self):
        """Check if already logged in by looking for a specific element on the home page."""
        try:
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "global-nav-search"))
            )
            self.is_logged_in = True
            print("Already logged in.")
        except Exception:
            print("Not logged in. Proceeding to login.")

    def login(self):
        """Log in to LinkedIn."""
        if self.is_logged_in:
            return  # Skip login if already logged in

        self.driver.get("https://www.linkedin.com/login")

        # Wait for the username input to load and enter the username
        username_input = WebDriverWait(self.driver, 500).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        username_input.send_keys(self.username)

        time.sleep(1)

        # Enter the password
        password_input = self.driver.find_element(By.ID, "password")
        password_input.send_keys(self.password)

        time.sleep(1)

        # Click the login button
        login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()

        # Wait for the home page to load
        WebDriverWait(self.driver, 500).until(
            EC.presence_of_element_located((By.ID, "global-nav-search"))
        )
        time.sleep(2)

        # Get the session cookie and store it in Redis
        for cookie in self.driver.get_cookies():
            if cookie['name'] == 'li_at':
                self.session_cookie = cookie['value']
                session_key = f"linkedin_session:{self.username}"
                self.redis_client.set(session_key, self.session_cookie)  # Store in Redis
                print("Session cookie stored in Redis.")

    def scrape_linkedin(self, search_url):
        """Scrape LinkedIn profiles."""
        self.driver.get(search_url)

        time.sleep(5)

        # Scroll to the bottom to load all profiles (if necessary)
        self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
        time.sleep(3)

        # Parse the page content with BeautifulSoup
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')

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

    def connect_to_new_people(self):
        """Send connection requests to new people."""
        try:
            # Navigate to the My Network grow page
            self.driver.get("https://www.linkedin.com/mynetwork/grow/?skipRedirect=true")

            time.sleep(3)  # Wait for the page to load

            # Find all connect buttons on the page
            connect_buttons = self.driver.find_elements(By.XPATH,
                                                        "//button[contains(@aria-label, 'Invite') and contains(@class, 'cnutht1hc')]")

            # Request to 10 people
            for button in connect_buttons[:50]:
                try:
                    button.click()  # Click the connect button
                    time.sleep(1)  # Wait for the modal to appear

                    # Click the send button in the modal
                    send_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Send now')]"))
                    )
                    send_button.click()  # Send the connection request
                    print("Connection request sent.")
                    time.sleep(random.uniform(5, 15))  # Random delay between requests
                except Exception as e:
                    print(f"Could not send connection request: {e}")
        finally:
            # Close the browser
            self.driver.quit()


def run_scraper(username, password, redis_client, search_url):
    """Function to create and run a LinkedIn scraper."""
    scraper = LinkedInScraper(username, password, redis_client)
    scraper.load_session()  # Load session from Redis
    if not scraper.is_logged_in:
        scraper.login()  # Log in if not already logged in
    scraper.scrape_linkedin(search_url)
    scraper.connect_to_new_people()


if __name__ == '__main__':
    # LinkedIn credentials and search URL
    username_str = "alizade200095@gmail.com"
    password_str = "42184433"
    search_url = "https://www.linkedin.com/search/results/people/?facetGeoRegion=%5B%22us%3A0%22%5D&facetIndustry=%5B%22106%22%2C%2243%22%2C%2241%22%2C%2242%22%2C%2246%22%2C%2245%22%2C%22129%22%5D&keywords=ali&origin=FACETED_SEARCH"

    # Create a Redis client
    redis_client = redis.Redis(host='localhost', port=6379, db=0)

    # Number of threads
    num_threads = 1

    # Create a ThreadPoolExecutor to run multiple scrapers
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for i in range(num_threads):
            futures.append(executor.submit(run_scraper, username_str, password_str, redis_client, search_url))

        # Wait for all threads to complete
        for future in as_completed(futures):
            try:
                future.result()  # Get result from the future, if needed
            except Exception as e:
                print(f"An error occurred: {e}")
