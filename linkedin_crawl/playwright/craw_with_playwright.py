import json
import random
import time
import redis
from playwright.sync_api import sync_playwright

class LinkedInBot:
    def __init__(self, username, password, redis_host='localhost', redis_port=6379, redis_db=0, redis_timeout=60*60*24*20):
        """Initialize the bot with user credentials and Redis configuration."""
        self.username = username
        self.password = password
        self.redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
        self.redis_timeout = redis_timeout  # Session expiration time in Redis (default 20 days)

    def type_with_delay(self, element, text, delay=0.1):
        """Simulate typing text with a delay between each character."""
        for char in text:
            element.type(char)
            time.sleep(delay)

    def store_session_in_redis(self, session_cookies):
        """Store session cookies in Redis."""
        for cookie in session_cookies:
            if cookie['name'] == 'li_at':
                session_cookie = cookie['value']
                session_key = f"linkedin_session:{self.username}"
                self.redis_client.set(session_key, session_cookie, self.redis_timeout)  # Store for 20 days
                print("Session cookie stored in Redis.")

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

    def login_linkedin(self):
        """Login to LinkedIn using the provided credentials."""
        with sync_playwright() as p:
            # Launch browser (headless=False for debugging, True for no UI)
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            # Try to load session from Redis
            session_key = f"linkedin_session:{self.username}"
            session_cookie = self.redis_client.get(session_key)

            if session_cookie:
                print("Session found in Redis, using saved session cookies.")
                # Set cookies in the browser session
                page.context.add_cookies([
                    {
                        'name': 'li_at',  # Required
                        'value': session_cookie,  # Required
                        'domain': '.linkedin.com',  # Optional, but recommended
                        'path': '/',  # Optional, '/' is a common value
                        'httpOnly': True,  # Optional, you can set it to True if required
                        'secure': True,  # Optional, set to True since LinkedIn uses HTTPS
                        'sameSite': 'None',  # Optional, depends on LinkedIn's cookie policy
                    }
                ])
                # Wait for the feed page to load
                page.goto("https://www.linkedin.com/feed/", timeout=1000000000)
                page.wait_for_load_state("load", timeout=10000000000)

            else:
                print("No session found in Redis, logging in.")
                # Go to LinkedIn login page
                page.goto("https://www.linkedin.com/login", timeout=10000000000)

                # Wait for the username input field to be visible
                page.locator("input#username").wait_for(state="visible")

                # Find the username and password input fields
                username_input = page.locator("input#username")
                password_input = page.locator("input#password")

                # Type the username and password with a delay
                self.type_with_delay(username_input, self.username, delay=random.randint(1, 2) / 10)
                self.type_with_delay(password_input, self.password, delay=random.randint(1, 2) / 10)

                # Find and click the login button
                login_button = page.locator("button[type='submit']")
                login_button.click()

                # Wait for the page to load after login
                if not self.safe_wait_for_page_load(page, retries=5):
                    print("Failed to load the feed page after retries.")
                    browser.close()
                    return

                print("Login successful!")

                # Store session cookies in Redis
                session_cookies = page.context.cookies()
                self.store_session_in_redis(session_cookies)

            # Perform any further actions after logging in or restoring session
            # For example, you could navigate to some LinkedIn pages

            # # Close the browser
            # browser.close()


# Example usage
if __name__ == "__main__":
    # Use your LinkedIn credentials here
    username = "alimardan200095@gmail.com"
    password = "42184433"

    linkedin_bot = LinkedInBot(username, password)
    linkedin_bot.login_linkedin()
