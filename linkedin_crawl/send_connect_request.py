import time
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def send_connect_request(driver):
    """Function to send a connection request to LinkedIn profiles in the My Network page."""
    time.sleep(3)  # Wait for the page to load

    # Find all connect buttons on the page
    connect_buttons = driver.find_elements(By.XPATH,
                                           "//button[contains(@aria-label, 'Invite') and contains(@class, 'cnutht1hc')]")

    # Limit to 10 connection requests
    for button in connect_buttons[:10]:
        try:
            button.click()  # Click the connect button
            time.sleep(1)  # Wait for the modal to appear

            # Click the send button in the modal
            send_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Send now')]"))
            )
            send_button.click()  # Send the connection request
            print("Connection request sent.")
            time.sleep(random.uniform(5, 15))  # Random delay between requests
        except Exception as e:
            print(f"Could not send connection request: {e}")


def scrape_linkedin(username, password):
    """Function to scrape LinkedIn profiles and send connection requests."""
    # Set up the Chrome options and driver
    options = uc.ChromeOptions()
    options.headless = False  # Set to True to run in headless mode
    options.add_argument("--incognito")  # Enable incognito mode

    # Initialize the WebDriver using undetected-chromedriver
    driver = uc.Chrome(options=options)
    driver.get("https://www.linkedin.com/login")

    try:
        # Wait for the username input to load and enter the username
        username_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        username_input.send_keys(username)

        time.sleep(1)

        # Enter the password
        password_input = driver.find_element(By.ID, "password")
        password_input.send_keys(password)

        time.sleep(1)

        # Click the login button
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()

        # Wait for the home page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "global-nav-search"))
        )
        time.sleep(2)

        # Navigate to the My Network grow page
        driver.get("https://www.linkedin.com/mynetwork/grow/?skipRedirect=true")

        # Call the function to send connection requests
        send_connect_request(driver)

    finally:
        # Close the browser
        driver.quit()


if __name__ == '__main__':
    # LinkedIn credentials
    username_str = "your_username"  # Replace with your LinkedIn username
    password_str = "your_password"  # Replace with your LinkedIn password

    # Run the function
    scrape_linkedin(username_str, password_str)
