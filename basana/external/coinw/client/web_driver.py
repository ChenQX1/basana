import os
from time import sleep
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Optional
import sys
import traceback
import json

from basana.external.coinw.client.web_entry import Button


class BrowserAutomator:
    def __init__(
        self,
        browser: str = "chrome",
        base_url: str = None,
        cookies_path: Optional[str] = None,
        driver_path: Optional[str] = None,
        headless: bool = False,
        implicitly_wait_time: int = 10,
    ) -> None:
        """
        Initializes the BrowserAutomator with given browser settings.

        :param browser: The browser to use ('chrome' or 'firefox').
        :param base_url: The entry URL of this session.
        :param driver_path: Path to the WebDriver executable. If None, assumes it's in PATH.
        :param headless: Whether to run the browser in headless mode.
        :param implicitly_wait_time: Implicit wait time for element searches.
        """
        self.browser = browser.lower()
        self.base_url = base_url
        self.driver: Optional[WebDriver] = None
        self.wait: Optional[WebDriverWait] = None

        try:
            if self.browser == "chrome":
                options = Options()
                if headless:
                    options.add_argument("--headless")
                if driver_path:
                    options.binary_location = driver_path
                self.driver = webdriver.Chrome(options=options)
            else:
                raise ValueError("Unsupported browser specified. Use 'chrome' or 'firefox'.")

            self.driver.implicitly_wait(implicitly_wait_time)
            self.wait = WebDriverWait(self.driver, implicitly_wait_time)
        except WebDriverException as e:
            print("Error initializing WebDriver:", e)
            sys.exit(1)

        try:
            if cookies_path:
                self.driver.get(self.base_url)
                with open(cookies_path, 'r') as cookies_file:
                    cookies = json.load(cookies_file)
                    for cookie in cookies:
                        # Adjust the cookie if necessary (e.g., remove 'sameSite' attribute if it's not accepted)
                        cookie.pop('sameSite', None)
                        self.driver.add_cookie(cookie)
                self.driver.refresh()
        except Exception as e:
            print(f'Error loading cookes: {e}')
            sys.exit(1)

    def navigate_to(self, url: str) -> None:
        """
        Navigates the browser to a specified URL.

        :param url: The URL to navigate to.
        :raises WebDriverException: If navigation fails.
        """
        try:
            self.driver.get(url)
        except WebDriverException as e:
            print(f"Error navigating to {url}: {e}")
            raise

    def click_button(self, button: Button) -> None:
        """
        Clicks a button identified by its enum value.

        :param button: The Button enum member to click.
        """
        try:
            xpath = button.value
            element = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            element.click()
        except TimeoutException:
            print(f"Timed out waiting for button '{button.name}' to be clickable.")
            raise
        except Exception as e:
            print(f"Error clicking button '{button.name}': {e}")
            traceback.print_exc()
            raise

    def send_keys_to_element(self, xpath: str, keys: str) -> None:
        """
        Sends keys to an input element specified by its XPath.

        :param xpath: The XPath of the input element.
        :param keys: The string to send to the input element.
        :raises TimeoutException: If the element is not found within the wait time.
        :raises Exception: For other exceptions.
        """
        try:
            element = self.wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            element.clear()
            element.send_keys(keys)
        except TimeoutException:
            print(f"Timed out waiting for element with XPath '{xpath}' to be present.")
            raise
        except Exception as e:
            print(f"Error sending keys to element '{xpath}': {e}")
            traceback.print_exc()
            raise

    def quit(self) -> None:
        """
        Closes the browser and quits the WebDriver session.

        :raises WebDriverException: If quitting fails.
        """
        try:
            if self.driver:
                self.driver.quit()
        except WebDriverException as e:
            print("Error quitting WebDriver:", e)
            raise


if __name__ == "__main__":
    url_ethusdt = 'https://www.coinw.com/futures/usdt/ethusdt'
    automator = BrowserAutomator(
        browser="chrome",
        base_url='https://www.coinw.com',
        cookies_path=os.environ.get('COINW_COOKIES'),
        driver_path=None,  # Assuming chromedriver is in your PATH
        headless=False
    )

    try:
        # Navigate to different endpoints
        automator.navigate_to(url_ethusdt)

        # # Interact with buttons using static mappings
        automator.click_button(Button.MARKETS)
        sleep(5)
        automator.click_button(Button.FUTURES)
        sleep(5)

        # # Send keys to an input field (example XPath)
        # input_xpath = "//input[@name='search']"
        # automator.send_keys_to_element(input_xpath, "Search Query")

        # Add more interactions as needed...

    except Exception as e:
        print(f"An error occurred during automation: {e}")

    finally:
        automator.quit()
