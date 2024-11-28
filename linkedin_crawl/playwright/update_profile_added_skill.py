import json
import random
import time
import redis
from playwright.sync_api import sync_playwright


class LinkedInBot:
    def __init__(self, username, password, login_url, home_url, profile_url, login_selectors, redis_host='localhost',
                 redis_port=6379, redis_db=0, redis_timeout=60 * 60 * 24 * 20, user_agent=None):
        """Initialize the bot with user credentials and Redis configuration."""
        self.username = username
        self.password = password
        self.login_url = login_url
        self.timeout = 1000000
        self.home_url = home_url
        self.profile_url = profile_url
        self.login_selectors = login_selectors  # Dictionary with keys: 'username', 'password', 'submit_button'
        self.redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
        self.redis_timeout = redis_timeout  # Session expiration time in Redis (default 20 days)
        self.base_redis_key = "linkedin_web_session"
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"  # Default user agent

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
            page.goto(self.profile_url, timeout=self.timeout)
            page.wait_for_load_state("load", timeout=self.timeout)

    def add_skill(self, skill_name="Django"):
        """Add a new skill (e.g., Django) to the LinkedIn profile."""
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(user_agent=self.user_agent)  # Set custom user agent
            page = context.new_page()

            # Try to load session from Redis
            session_key = f"{self.base_redis_key}:{self.username}"
            session_cookies = self.redis_client.get(session_key)

            if session_cookies:
                print("Session found in Redis, using saved session cookies.")
                cookies = json.loads(session_cookies)
                context.add_cookies(cookies)
                page.goto(self.profile_url, timeout=100000)
                page.wait_for_load_state("load", timeout=self.timeout)

                # Locate and click the "Add skills" button
                add_skill_button = page.locator("span.pvs-navigation__text:has-text('Add skills')")
                add_skill_button.click()

                # Wait for the skill input popup to appear
                skill_input = page.locator("input[id^='single-typeahead-entity-form-component-profileEditFormElement-SKILL-AND-ASSOCIATION-skill']")
                skill_input.wait_for(state="visible", timeout=5000)

                # Fill in the skill (e.g., Django)
                self.type_with_delay(skill_input, skill_name)

                # Save the skill by clicking the save button
                save_button = page.locator("span.artdeco-button__text:has-text('Save')")
                save_button.click()

                # Wait for the changes to be saved and the page to reload
                page.wait_for_load_state("load", timeout=self.timeout)
                print(f"Skill '{skill_name}' added successfully!")

            else:
                print("No session found in Redis. Please log in first.")


# Example usage
if __name__ == "__main__":
    # Define your bot configuration for LinkedIn
    username = "alimardan200095@gmail.com"
    password = "42184433"
    login_url = "https://www.linkedin.com/login"  # URL of the login page
    home_url = "https://www.linkedin.com/feed/"  # URL of the home page after login
    profile_url = "https://www.linkedin.com/in/ali-mardan-9b6477334/"  # Your specific profile URL

    # Selectors for the login page (these will vary for each website)
    login_selectors = {
        'username': 'alimardan200095@gmail.com',  # Selector for the username field
        'password': '42184433',  # Selector for the password field
        'submit_button': 'button[type="submit"]',  # Selector for the login button
    }

    # Optional: Define a custom user agent
    custom_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

    # Initialize the LinkedIn bot
    linked_in_bot = LinkedInBot(username, password, login_url, home_url, profile_url, login_selectors, user_agent=custom_user_agent)

    # Log in
    # linked_in_bot.login()

    # Add a skill (Django in this case)
    linked_in_bot.add_skill("Django")
