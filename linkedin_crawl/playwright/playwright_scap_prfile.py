import random
import time
import redis
from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup


class LinkedInBot:
    def __init__(self, username, password, redis_host='localhost', redis_port=6379, redis_db=0,
                 redis_timeout=60 * 60 * 24 * 20):
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
                page.goto("https://www.linkedin.com/login", timeout=1000000000)

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
            self.scrape_profiles(page)

        return page

    def connect_to_new_people(self, page):
        """Send connection requests to new people."""
        try:
            # Navigate to the "My Network" Grow page
            page.goto("https://www.linkedin.com/mynetwork/grow/?skipRedirect=true")
            page.wait_for_load_state("load")
            time.sleep(3)

            # Locate connect buttons for the first 50 people
            connect_buttons = page.locator(
                "//button[contains(@aria-label, 'Invite') and contains(@class, 'mn-person-card__person-btn')]")

            # Loop over the first 50 buttons and send connection requests
            for idx in range(min(50, len(connect_buttons.all()))):
                try:
                    connect_buttons.nth(idx).click()  # Click the 'Connect' button for each person
                    time.sleep(1)

                    # Wait for the 'Send now' button to become clickable and click it
                    send_button = page.locator("//button[contains(@aria-label, 'Send now')]")
                    send_button.wait_for(state="visible", timeout=10000)  # Wait for button to be clickable
                    send_button.click()
                    print("Connection request sent.")

                    # Random sleep to simulate human interaction
                    time.sleep(random.uniform(5, 15))
                except Exception as e:
                    print(f"Could not send connection request to person {idx + 1}: {e}")
        except Exception as e:
            print(f"Error in connect_to_new_people: {e}")

    def scrape_profiles(self, page):
        """Navigate to My Network page and scrape profiles."""
        time.sleep(5)
        page.goto(
            "https://www.linkedin.com/search/results/people/?keywords=data scientist&origin=SWITCH_SEARCH_VERTICAL&searchId=faf8d963-0e13-4129-b722-41f5f9ffae8c&sid=4Co",
            timeout=1000000000)
        page.wait_for_load_state("load")  # Wait for the page to load
        time.sleep(5)

        # Find profile links
        profile_links = page.locator("a.app-aware-link")

        # Collect the first 10 profile URLs
        profiles = [link.get_attribute('href') for link in profile_links.all()[:10]]  # Adjust based on required range

        # Scrape profiles concurrently
        with ThreadPoolExecutor(max_workers=1) as executor:
            futures = [executor.submit(self.scrape_profile, page, url) for url in profiles]
            for future in as_completed(futures):
                try:
                    profile_data = future.result()
                    if profile_data:
                        self.write_profile_to_csv(profile_data)
                except Exception as e:
                    print(f"Error scraping profile: {e}")

    def scrape_profile(self, page, profile_url):
        """Scrape individual profile data."""
        # Open the profile URL in a new tab
        page.evaluate(f"window.open('{profile_url}', '_blank');")
        page.context.pages[-1].wait_for_load_state("load")
        profile_page = page.context.pages[-1]

        # Wait for the profile to load
        time.sleep(3)

        # Try to click "Show all posts" if it exists
        try:
            show_all_posts_button = profile_page.locator("button:has-text('Show all posts')")
            if show_all_posts_button.is_visible():
                show_all_posts_button.click()
                time.sleep(3)  # Wait for posts to load
        except Exception as e:
            print(f"Error clicking 'Show all posts' button: {e}")

        # Parse profile data
        soup = BeautifulSoup(profile_page.content(), 'html.parser')
        try:
            name = soup.find('h1').get_text(strip=True) if soup.find('h1') else "N/A"
            headline = soup.find('h2').get_text(strip=True) if soup.find('h2') else "N/A"
            location = soup.find('span', class_='top-card__flavor').get_text(strip=True) if soup.find('span',
                                                                                                      class_='top-card__flavor') else "N/A"

            # Fetch posts
            posts = soup.find_all('li', class_="profile-creator-shared-feed-update__container")
            post_data = []
            for post in posts:
                post_text = post.find('span', class_='break-words').get_text(strip=True) if post.find('span',
                                                                                                      class_='break-words') else "No text"
                post_data.append(post_text)

            profile_data = {
                'name': name,
                'headline': headline,
                'location': location if location else "",
                'profile_link': profile_url,
                'posts': post_data
            }

            self.write_profile_to_csv(profile_data)

        except Exception as e:
            print(f"Error scraping profile: {e}")
        finally:
            # Close the profile tab and switch back to the main tab
            # profile_page.close()
            pass

    def write_profile_to_csv(self, profile_data):
        """Write scraped profile data to a CSV file (implement this method)."""
        # This is where you would implement writing to a CSV file
        pass


def main():
    # Define your LinkedIn credentials
    username = "alimardan200095@gmail.com"
    password = "42184433"

    # Initialize the bot
    bot = LinkedInBot(username, password)

    # Login and start scraping profiles
    page = bot.login_linkedin()
    bot.scrape_profiles(page=page)


if __name__ == "__main__":
    main()
