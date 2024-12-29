import json
import random
import time
from time import sleep

import redis
from playwright.sync_api import sync_playwright

"""
change user agent
store all cookie in redis and use for second time instead store just jwt token.

"""


class WebBot:
    def __init__(self, username, password, login_url, home_url, login_selectors, redis_host='localhost',
                 redis_port=6379, redis_db=0, redis_timeout=60 * 60 * 24 * 20, user_agent=None):
        """Initialize the bot with user credentials and Redis configuration."""
        self.username = username
        self.password = password
        self.login_url = login_url
        self.timeout = 1000000
        self.home_url = home_url
        self.login_selectors = login_selectors  # Dictionary with keys: 'username', 'password', 'submit_button'
        self.redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
        self.redis_timeout = redis_timeout  # Session expiration time in Redis (default 20 days)
        self.base_redis_key = "linkedin_web_session"
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"  # Default user agent
        self.base_linkedin_url = "https://www.linkedin.com"
        self.groups_link = "https://www.linkedin.com/groups/"
    def type_with_delay(self, element, text, delay=0.1):
        """Simulate typing text with a delay between each character."""
        for char in text:
            element.type(char)
            time.sleep(delay)

    def store_session_in_redis(self, session_cookies):
        """Store session cookies in Redis."""
        session_key = f"{self.base_redis_key}:{self.username}"
        self.redis_client.set(session_key, json.dumps(session_cookies), self.redis_timeout)  # Store for 20 days
        print("Session cookies stored in Redis.")

    def safe_wait_for_page_load(self, page, retries=3, timeout=100000):
        """Wait for a page to load with retries."""
        attempt = 0
        while attempt < retries:
            try:
                # Wait for the page to be fully loaded
                page.wait_for_load_state("load", timeout=timeout)
                return True
            except Exception as e:
                print(f"Attempt {attempt + 1}/{retries} failed: {e}")
                attempt += 1
                time.sleep(2)  # Wait before retrying
        return False  # Return False if all attempts failed

    def login(self):
        """Login to the site using the provided credentials."""
        with sync_playwright() as p:
            # Launch browser (headless=False for debugging, True for no UI)
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(user_agent=self.user_agent)  # Set custom user agent here
            page = context.new_page()

            # Try to load session from Redis
            session_key = f"{self.base_redis_key}:{self.username}"
            session_cookies = self.redis_client.get(session_key)

            if session_cookies:
                print("Session found in Redis, using saved session cookies.")
                # Set cookies in the browser session
                cookies = json.loads(session_cookies)
                context.add_cookies(cookies)
                # Wait for the home page to load
                page.goto(self.home_url, timeout=100000)
                page.wait_for_load_state("load", timeout=self.timeout)
            else:
                print("No session found in Redis, logging in.")
                # Go to login page
                page.goto(self.login_url, timeout=self.timeout)

                # Wait for the username input field to be visible
                page.locator(self.login_selectors['username']).wait_for(state="visible")

                # Find the username and password input fields
                username_input = page.locator(self.login_selectors['username'])
                password_input = page.locator(self.login_selectors['password'])

                # Type the username and password with a delay
                self.type_with_delay(username_input, self.username, delay=random.randint(1, 2) / 10)
                self.type_with_delay(password_input, self.password, delay=random.randint(1, 2) / 10)

                # Find and click the login button
                login_button = page.locator(self.login_selectors['submit_button'])
                login_button.click()

                # Wait for the home page to load
                if not self.safe_wait_for_page_load(page, retries=5, timeout=self.timeout):
                    print("Failed to load the home page after retries.")
                    browser.close()
                    return

                print("Login successful!")

                # Store session cookies in Redis
                session_cookies = page.context.cookies()
                self.store_session_in_redis(session_cookies)

            # Perform any further actions after logging in or restoring session
            # Example: visit a specific page
            page.goto(self.home_url, timeout=self.timeout)
            page.wait_for_load_state("load", timeout=self.timeout)
            time.sleep(random.randint(3, 10))
            self.view_user_profiles_in_group(page)
            page.wait_for_timeout(3000)
            self.search_and_join_group(page)


    def search_and_join_group(self, page):
        """Search for the word 'AI' and join the first group/channel."""
        print("Searching for 'AI' on LinkedIn...")

        # Go to the search bar and type 'AI'
        search_bar = page.locator('input[aria-label="Search"]')  # LinkedIn's search input
        search_bar.fill('AI')  # Fill the search bar with the word 'AI'
        search_bar.press('Enter')  # Simulate pressing Enter to perform the search

        # Wait for search results to load
        page.wait_for_load_state("load", timeout=self.timeout)

        # Filter the search results for groups (click the "Groups" button)
        groups_button = page.locator('button.search-reusables__filter-pill-button:has-text("Groups")')
        groups_button.click()  # Click the "Groups" tab to filter by groups
        page.wait_for_load_state("load", timeout=self.timeout)

        # Join the first group/channel in the search results
        # Locate all group links by targeting the <a> tags within the <span> element
        # that contains the group information (using class selectors you provided)
        page.wait_for_selector('ul.nOhuboXfCHtpjqEpIIFFSBhLSVJcFieOnKE')
        # Find all <li> elements with the specific class
        group_items = page.query_selector_all('li.hfrnpHqiFIFjzRKUPdWXOHmVUInUMZAcTFUI')
        for group_item in group_items:
            # Check if the "Join" button exists inside the group
            join_button = group_item.query_selector('button.artdeco-button--secondary')
            if join_button:
                print("Join button found. Clicking to join the group.")
                join_button.click()  # Click the join button
                page.wait_for_timeout(2000)  # Wait for 2 seconds to simulate human-like interaction

    def view_user_profiles_in_group(self, page):
        page.goto(self.groups_link, timeout=self.timeout)
        page.wait_for_selector("ul.artdeco-list")

        # Find all the groups on the page
        groups = page.query_selector_all("li.artdeco-list__item")

        # Loop through the groups and extract relevant details
        group_details = []
        groups_links = []
        for group in groups:
            group_info = {}

            # Extract group name and link
            group_name = group.query_selector("div.artdeco-entity-lockup__title")
            if group_name:
                group_info['name'] = group_name.inner_text().strip()
                if group_name.query_selector("a") is not None:
                    group_info['link'] = group_name.query_selector("a").get_attribute("href")
                    groups_links.append(str(group_name.query_selector("a").get_attribute("href")))

            # Extract the number of members
            group_metadata = group.query_selector("div.artdeco-entity-lockup__metadata")
            if group_metadata:
                group_info['members'] = group_metadata.inner_text().strip()

            # Extract the image URL
            group_image = group.query_selector("img")
            if group_image:
                group_info['image_url'] = group_image.get_attribute("src")

            if group_info:
                group_details.append(group_info)
        for link in groups_links:
            page.goto(self.base_linkedin_url+link+'members/', timeout=self.timeout)
            # Find user profile links in the group (you may need to adjust this locator)
            user_links = page.locator('a[href*="/in/"]')  # This will select profile links in the group

            # Get all the user profile URLs (up to a limit of 10)
            user_profiles = user_links.all_inner_texts()[:10]
            page.wait_for_selector("ul.artdeco-list")

            # Find all the groups on the page
            users_list = page.query_selector_all("a.ember-view")
            for profile in users_list:
                print(f"Visiting user profile: {profile.get_attribute('href')}")
                #should change.
                # profile_link = page.locator(f'a[href*="{profile}"]')
                # profile_link.click()

                # Wait for the profile page to load
                page.wait_for_load_state("load", timeout=self.timeout)
                print(f"Visited profile: {profile}")
                page.go_back()  # Go back to the group after viewing the profile

# Example usage
if __name__ == "__main__":
    # Define your bot configuration for the site you're working with
    username = "mammad200095@gmail.com"
    password = "42184433"
    login_url = "https://www.linkedin.com/login"  # URL of the login page
    home_url = "https://www.linkedin.com/feed/"  # URL of the home page after login

    # Selectors for the login page (these will vary for each website)
    login_selectors = {
        'username': 'input#username',  # Selector for the username field
        'password': 'input#password',  # Selector for the password field
        'submit_button': 'button[type="submit"]',  # Selector for the login button
    }

    # Optional: Define a custom user agent (optional, you can leave it as None to use the default one)
    custom_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

    web_bot = WebBot(username, password, login_url, home_url, login_selectors, user_agent=custom_user_agent)
    web_bot.login()
