

import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    StaleElementReferenceException, 
    WebDriverException,
    NoSuchElementException, 
    TimeoutException,
    InvalidArgumentException
)

from utils.shared.decorators.try_except import try_except
from utils.shared.decorators.get_exec_time import get_exec_time 

from config.config import LEGAL_WEBSITE_DICT, OUTPUT_FOLDER
from logger.logger import Logger
logger = Logger(logger_name=__name__)


class SeleniumScraper:

    def __init__(self, driver: webdriver.Chrome=None, wait_in_seconds: int=1, ):
        self.driver = driver
        self.wait_in_seconds = wait_in_seconds
        self.page = None

        if not self.driver:
            logger.error("Chrome webdriver not passed to Selenium.")
            raise ValueError("Chrome webdriver not passed to Selenium.")

    @try_except(exception=[WebDriverException])
    def close_webpage(self):
        return self.driver.close()

    @try_except(exception=[WebDriverException])
    def _quit_driver(self):
        return self.driver.quit()

    def __enter__(self):
        return self

    @classmethod
    def enter(cls, wait_in_seconds):
        """
        Factory method to start Selenium
        """
        instance = cls(wait_in_seconds)
        return instance

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit()
        return False
    
    def try_except_decorator_exit(self):
        """
        Function to be called by the try_except decorator to permit graceful shutdowns.
        """
        self.exit()
        return

    def exit(self):
        """
        Close the webpage and webdriver.
        """
        if self.page:
            logger.info("Trying to close webpage...")
            self.close_webpage()
            logger.info("Webpage closed successfully.")
        logger.info("Trying to quit webdriver...")
        self._quit_driver()
        logger.info("Webdriver quit successfully.")
        return

    @try_except
    def refresh_page(self) -> None:
        """
        Refresh the web page currently in the driver.
        """
        self.driver.refresh()

    @get_exec_time
    @try_except(exception=[WebDriverException, InvalidArgumentException, TimeoutException], raise_exception=True)
    def wait_to_fully_load(self, implicit_wait: int=5, page_load_timeout: int=10, class_name: str=None):
        assert class_name, "class_name must be provided."
        logger.info("Waiting for page to full load...")

        # Wait for Angular to finish loading
        angular_js_code = """
        'return (window.angular !== undefined) && 
        (angular.element(document).injector() !== undefined) && 
        (angular.element(document).injector().get("$http").pendingRequests.length === 0)'
        """
        WebDriverWait(self.driver, page_load_timeout).until(
            lambda driver: driver.execute_script(angular_js_code)
        )
        logger.info("Angular finished loading.")

        # Wait for the Table of Contents button to be clickable
        button = WebDriverWait(self.driver, page_load_timeout).until(
            EC.presence_of_element_located((By.CLASS_NAME, class_name))
        )
        logger.info(f"toc_button found on page '{button.text}'.")

        # Additional wait for any JavaScript to finish (adjust time as needed)
        #self.driver.implicitly_wait(implicit_wait)

        # Execute JavaScript to check if page is fully loaded
        logger.info("Executing JavaScript command 'return document.readtState;'")
        is_ready = self.driver.execute_script("return document.readyState;")
        logger.info(f"JavaScript command successfully executed\nPage ready state: {is_ready}")


    @try_except(exception=[WebDriverException, InvalidArgumentException, TimeoutException])
    def make_page(self, url: str) -> None:
        """
        Navigate to the specified URL using the given Chrome webdriver.

        Args:
            url (str): The URL to navigate to.
        Raises:
            WebDriverException: If there's an issue with the WebDriver while navigating.
            TimeoutException: If the page load takes too long.
            InvalidArgumentException: If the URL is not valid.
            Exception: For any other unexpected errors making the page.
        """
        logger.info(f"Getting URL {url}...")
        self.driver.get(url)
        logger.info(f"URL ok.")


    @try_except(exception=[WebDriverException, 
                           StaleElementReferenceException, 
                           TimeoutException])
    def _check_if_interactable(self, xpath: str, wait_time: int, poll_frequency: float) -> None:
        """
        Check if elements located by the given XPath are interactable (clickable).

        Args:
            xpath (str): The XPath used to locate the elements.
            wait_time (int): Maximum time to wait for the elements to become clickable, in seconds.
            poll_frequency (float): How often to check if the elements are clickable, in seconds.

        Raises:
            TimeoutException: If the elements are not clickable within the specified wait time.
            StaleElementReferenceException: If the element becomes stale during the wait.
            WebDriverException: For other WebDriver-related exceptions.
        """
        WebDriverWait(self.driver,
                    wait_time,
                    poll_frequency=poll_frequency).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        return

    @try_except(exception=[WebDriverException, 
                           StaleElementReferenceException, 
                           NoSuchElementException, 
                           TimeoutException])
    def _wait_to_load(self, xpath: str, wait_time: int, poll_frequency: float) -> list[WebElement]:
        """
        Wait for elements specified by the given XPath to be present on the page.

        Args:
            xpath (str): The XPath used to locate the elements on the page.
            wait_time (int): Maximum time to wait for the elements to be present, in seconds.
            poll_frequency (float): How often to check for the presence of the elements, in seconds.

        Returns:
            list[WebElement]: A list of WebElements that match the provided XPath.

        Raises:
            WebDriverException: If there's an issue with the WebDriver during the wait.
            StaleElementReferenceException: If the element becomes stale during the wait.
            NoSuchElementException: If no elements are found matching the XPath after the wait time.
            TimeoutException: If the wait time is exceeded before the elements are found.
        """
        # Wait for the element to load.
        elements = WebDriverWait(self.driver,
                                wait_time,
                                poll_frequency=poll_frequency).until(
            EC.presence_of_all_elements_located((By.XPATH, xpath))
        )
        return elements if elements else []


    def wait_for_and_then_return_elements(self, 
                                         xpath: str, 
                                         wait_time: int = 10, 
                                         poll_frequency: float = 0.5, 
                                         retries: int = 2
                                         ) -> list[WebElement]:
        """
        Wait for elements to be present and interactable on the page, then return them.

        Args:
            xpath (str): The XPath to locate the elements.
            wait_time (int, optional): Maximum time to wait for the elements, in seconds. Defaults to 10.
            poll_frequency (float, optional): How often to check for the elements, in seconds. Defaults to 0.5.

        Returns:
            list[WebElement]: A list of WebElements that match the XPath and are interactable. 

        Raises:
            TimeoutException: If the elements are not found or not interactable within the specified wait time.
            StaleElementReferenceException: If the element becomes stale during the wait. The method will retry in this case.
            NoSuchElementException: If no elements are found matching the XPath.
            Exception: For any other unexpected errors during the wait process.
        """
        assert retries > 0
        counter = 0
        while counter < retries:
            try:
                # Wait for the element to load.
                elements = self._wait_to_load(xpath, wait_time, poll_frequency)
                if not elements:
                    logger.warning(f"No elements found for x-path '{xpath}'.\nReturning empty list...")
                    return []

                # Check to see if the element is interactable.
                self._check_if_interactable(xpath, wait_time, poll_frequency)

                return elements
            except:
                counter += 1
        logger.exception(f"Could not locate elements after {counter + 1} retries.\nReturning empty list...")
        return []


    @try_except(exception=[WebDriverException, NoSuchElementException], raise_exception=False)
    def find_elements_by_xpath(self, 
                               url: str, 
                               xpath: str, 
                               first_elem: bool=True
                               ) -> WebElement|list[WebElement]|None:
        """
        Find an element or elements on the page using the specified XPath.

        Args:
            url (str): The URL being searched (for logging purposes).
            xpath (str): The XPath to use for finding elements.
            first_elem (bool, optional): If True, returns only the first matching element. 
                                         If False, returns all matching elements. Defaults to True.

        Returns:
            WebElement|list[WebElement]|None: 
                - If first_elem is True: Returns the first matching WebElement, or None if not found.
                - If first_elem is False: Returns a list of matching WebElements, or None if none found.

        Raises:
            NoSuchElementException: If no elements are found and first_elem is True.
            WebDriverException: For other Selenium-related errors.
        """
        logger.info(f"Searching for {'first element' if first_elem else 'all elements'} along x-path '{xpath}'")
        elements: WebElement = self.driver.find_element(by=By.XPATH, value=xpath)
        if not elements:
            logger.warning(f"No elements found for URL '{url}'.\n Check the x-path '{xpath}'.\nReturning None...")
            return None

        elements = elements if first_elem else self.driver.find_elements(by=By.XPATH, value=xpath)
        return elements

    def wait_for_aria_expanded(self, element: WebElement, state: bool='true', timeout: int=10):
        """
        Wait for an element's 'aria-expanded' attribute to become 'true' or 'false'.
        """
        WebDriverWait(self.driver, timeout).until(
            lambda driver: element.get_attribute('aria-expanded') == state
        )

    @try_except(exception=[WebDriverException])
    def press_buttons(self, 
                      xpath: str, 
                      first_button: bool = True, 
                      delay: float = 0.5,
                      target_buttons: list[str] = None,
                      ) -> None:
        """
        Press one or multiple buttons identified by the given XPath.
        TODO Add in logic to specify which buttons to press.

        Args:
            xpath (str): The XPath used to locate the button(s) on the page.
            first_button (bool, optional): If True, only the first button found will be clicked.
                                           If False, all matching buttons will be clicked. 
                                           Defaults to True.
            delay (float, optional): Wait between button clicks. Defaults to 0.5 (half a second)
            targt_buttons(list[str], optional): A list specifying which buttons to press if they are found. Defaults to None.

        Raises:
            WebDriverException: If there's an issue with the WebDriver while attempting to click.
        """
        # Find all the buttons
        buttons = self.driver.find_elements(By.XPATH, xpath)
        if not buttons:
            logger.warning(f"No buttons found for XPath: {xpath}")
            return

        # Click on all or a specified set of buttons.
        buttons_to_click = buttons[:1] if first_button else buttons
        for button in buttons_to_click:
            if target_buttons:
                if button.text in target_buttons:
                    button.click()
            else:
                button.click()
            time.sleep(delay)  # Wait between clicks
        return












