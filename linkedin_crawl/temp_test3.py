import time
from playwright.sync_api import sync_playwright


def type_with_delay(element, text, delay=0.1):
    """Simulate typing text with a delay between each character."""
    for char in text:
        element.type(char)
        time.sleep(delay)


def login_linkedin(username, password):
    with sync_playwright() as p:
        # Launch browser (headless=False for debugging, True for no UI)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Go to LinkedIn login page
        page.goto("https://www.linkedin.com/login")

        # Find the username and password input fields
        username_input = page.locator("input#username")
        password_input = page.locator("input#password")

        # Type the username and password with a delay
        type_with_delay(username_input, username, delay=0.2)  # Adjust delay as needed
        type_with_delay(password_input, password, delay=0.2)

        # Find and click the login button
        login_button = page.locator("button[type='submit']")
        login_button.click()

        # Wait for some time to ensure login process is complete (you can add explicit wait conditions as needed)
        page.wait_for_url("https://www.linkedin.com/feed/")

        print("Login successful!")

        # Close the browser
        browser.close()


# Use your LinkedIn credentials here
username = "your_email_or_phone"
password = "your_password"

login_linkedin(username, password)
