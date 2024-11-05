import asyncio
import os
import subprocess
import time
from typing import Any, Coroutine, TypeVar, NamedTuple


import requests
from requests import (
    HTTPError,
    RequestException
)
import aiohttp

import pandas as pd
from playwright.sync_api import (
    Playwright,
    Browser as PlaywrightBrowser,
    Page as PlaywrightPage,
    TimeoutError as PlaywrightTimeoutError,
)
from playwright.async_api import Browser as AsyncPlaywrightBrowser
from selenium import webdriver

from abc import ABC, abstractmethod



from utils.manual.scrape_legal_websites_utils.fetch_robots_txt import fetch_robots_txt
from utils.manual.scrape_legal_websites_utils.parse_robots_txt import parse_robots_txt 
from utils.manual.scrape_legal_websites_utils.extract_urls_using_javascript import extract_urls_using_javascript
from utils.manual.scrape_legal_websites_utils.can_fetch import can_fetch
from utils.shared.decorators.try_except import try_except

from config.config import LEGAL_WEBSITE_DICT, OUTPUT_FOLDER

from utils.shared.safe_format import safe_format
from utils.shared.sanitize_filename import sanitize_filename

from logger.logger import Logger
logger = Logger(logger_name=__name__)

pd.DataFrame

AbstractPage = TypeVar('AbstracPage')
AbstractBrowser= TypeVar('AbstractBrowser')
AbstractScraper = TypeVar('AbstractScraper')
AbstractDriver = TypeVar('AbstractDriver')
AbstractInstance = TypeVar('AbstractInstance')


from urllib.robotparser import RobotFileParser
from urllib.error import URLError
from urllib.parse import urljoin

from .AbstractBrowserController import AsyncAbstractBrowserController, SyncAbstractBrowserController

from playwright.async_api import (
    async_playwright,
    Playwright as AsyncPlaywright,
    Page as AsyncPlaywrightPage,
    Browser as AsyncPlaywrightBrowser,
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeoutError,
)

class PlaywrightScrapper:

    def __init__(self, 
                 domain: str,
                 user_agent: str="*", 
                 **launch_kwargs):
        self.launch_kwargs = launch_kwargs
        self.domain: str = domain
        self.user_agent: str = user_agent
        self.rp: RobotFileParser = RobotFileParser()
        self.browser: AsyncPlaywrightBrowser = None
        self.crawl_delay: int = None
        self.rrate: NamedTuple = None
        self.page: AsyncPlaywrightPage = None


    # Define class enter and exit methods.
    @try_except(exception=[URLError], retries=2, raise_exception=True)
    def _get_robot_rules(self):
        """
        Get the site's robots.txt file and assign it to the class' applicable attributes
        See: https://docs.python.org/3/library/urllib.robotparser.html
        """
        # Construct the URL to the robots.txt file
        robots_url = urljoin(self.domain, 'robots.txt')
        self.rp.set_url(robots_url)

        # Read the robots.txt file from the server
        self.rp.read()

        # Set the request rate.
        self.rrate = self.rp.request_rate(self.user_agent)

        # Set the crawl delay
        self.crawl_delay = int(self.rp.crawl_delay(self.user_agent))
        return


    async def _load_browser(self, pw_instance: AsyncPlaywright):
        """
        Launch a chromium instance and load a page
        """
        self._browser = await pw_instance.chromium.launch(**self.launch_kwargs)


    @try_except(exception=[PlaywrightTimeoutError, PlaywrightError], raise_exception=True)
    # Define the context manager methods
    @classmethod
    async def start(cls, pw_instance: AsyncPlaywright) -> 'PlaywrightScrapper':
        instance = cls()
        instance._get_robot_rules()
        instance.browser = await instance._load_browser(pw_instance)
        return instance


    @try_except(exception=[PlaywrightTimeoutError, PlaywrightError], raise_exception=True)
    async def exit(self) -> None:
        """
        Close page and browser instances and reset internal attributes
        """
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        return


    async def __aenter__(self, pw_instance):
        self._get_robot_rules()
        self.browser = await self._load_browser(pw_instance)
        return self


    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return await self.exit()


    async def open_new_page(self):
        """
        Create a new brower page instance.
        """
        return await self.browser.new_page()


    def _can_fetch(self, url: str) -> tuple[bool, int]:
        """
        Check if a given URL can be fetched based on the rules in the robots.txt file.
        """
        return True if self.rp.can_fetch(self.user_agent, url) else False


    async def navigate_to(self, url: str, **kwargs) -> Coroutine:
        """
        Open a specified webpage and wait for any dynamic elements to load.
        """
        # See if we're allowed to get the URL, as well as get the specified delay from robots.txt
        if not self._can_fetch(self.user_agent, url):
            logger.warning(f"Cannot scrape URL '{url}' as it's disallowed in robots.txt")
            return

        # Wait per the robots.txt crawl delay.
        if self.crawl_delay > 0:
            logger.info(f"Sleeping for {self.crawl_delay} seconds to respect robots.txt crawl delay")
            await asyncio.sleep(self.crawl_delay)
        return await self.page.goto(url, **kwargs)

    @try_except(exception=[PlaywrightTimeoutError, PlaywrightError], raise_exception=True)
    async def wait_till_idle(self) -> Coroutine[Any, Any, None]:
        """
        Wait for a page to fully finish loading.
        """
        return await self.page.wait_for_load_state("networkidle")

    @try_except(exception=[PlaywrightTimeoutError, PlaywrightError], raise_exception=True)
    async def move_mouse_cursor_to_element(self, selector: str, *args, **kwargs) -> Coroutine[Any, Any, None]:
        """
        Move a "mouse" cursor over a specified element.
        """
        await self.page.locator(selector, *args, **kwargs).hover()

    @try_except(exception=[PlaywrightTimeoutError, PlaywrightError], raise_exception=True)
    async def click_on(self, selector: str, *args, **kwargs) -> Coroutine[Any, Any, None]:
        """
        Click on a specified element.
        """
        return await self.page.locator(selector, *args, **kwargs).click()

    @try_except(exception=[PlaywrightTimeoutError, PlaywrightError])
    async def take_screenshot(self,
                              filename: str,
                              full_page: bool=False,
                              element: str=None,
                              open_image_after_save: bool=False,
                              locator_kwargs: dict=None,
                              **kwargs) -> Coroutine[Any, Any, None]:
        """
        Take a screenshot of the current page or a specific element.

        The filename will be automatically corrected to .jpg if an unsupported image type is provided.\n
        The screenshot will be saved in a subdirectory of OUTPUT_FOLDER, named after the sanitized domain.\n
        If the specified directory doesn't exist, it will be created.\n
        NOTE: Opening the image after saving only works in Windows Subsystem for Linux (WSL).

        Args:
            filename (str): The name of the file to save the screenshot as.
            full_page (bool, optional): Whether to capture the full page or just the visible area. Defaults to False.
            element (str, optional): CSS selector of a specific element to capture. If None, captures the entire page. Defaults to None.
            open_image_after_save (bool, optional): Whether to open the image after saving (only works in WSL). Defaults to False.
            locator_kwargs (dict, optional): Additional keyword arguments for the locator if an element is specified.
            **kwargs: Additional keyword arguments to pass to the screenshot method.

        Returns:
            Coroutine[Any, Any, None]: A coroutine that performs the screenshot operation.

        Raises:
            PlaywrightTimeoutError: If the specified element cannot be found within the default timeout.
            PlaywrightError: Any unknown Playwright error occurs.
        """
        # Coerce the filename to jpg if it's an unsupported image type.
        if not filename.endswith('.png'|'.jpg'|'.jpeg'):
            filename = f"{os.path.splitext(filename)[0]}.jpg"
            logger.warning(f"'take_screenshot' method was given an invalid picture type. Filename is now '{filename}'")

        filepath = os.path.join(OUTPUT_FOLDER, sanitize_filename(self.domain), )
        # Create the output folder if it doesn't exist.
        if not os.path.exists(filepath):
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
        filepath = os.path.join(filepath, filename)

        # Take the screenshot.
        if element:
            await self.page.locator(element, **locator_kwargs).screenshot(path=filepath, full_page=full_page, **kwargs)
        else:
            await self.page.screenshot(path=filepath, full_page=full_page, **kwargs)

        # Open the image after it's saved.
        if not open_image_after_save: # Normal usage: explorer.exe image.png NOTE This will only work for WSL.
            subprocess.call(["mnt/c/Windows/explorer.exe", filepath], shell=True)
        return

    @try_except(exception=[PlaywrightTimeoutError, PlaywrightError], raise_exception=True)
    async def evaluate_js(self, javascript: str, **js_args) -> Coroutine[Any]:
        """
        Evaluate a JavaScript code in the context of a page.
        Example:
        >>> javascript = '''
        >>>     () => {
        >>>         const results = [];
        >>>         const elements = document.querySelectorAll('a.result-link');
        >>>         elements.forEach(element => {
        >>>             results.push({
        >>>                 href: element.href,
        >>>                 text: element.textContent.trim()
        >>>             });
        >>>         });
        >>>         return results;
        >>>     }
        >>> '''
        >>> search_results = await evaluate_js(javascript)
        >>> for result in search_results:
        >>>     logger.debug(f"Link: {result['href']}, Text: {result['text']}")
        """
        return await self.page.evaluate(safe_format(javascript, **js_args))












class AbstractScraper(ABC):
    """
    Abstract class for a JS-friendly webscraper.
    Designed for 5 child classes: Sync Playwright, Async Playwright, Selenium, Requests, and Aiohttp.

    Parameters:
        instance_or_driver: An instance or driver
        robot_txt_url: URL path to a website's robots.txt page.
        user_agent: The chosen user agent in robots.txt. Defaults to '*'
        **launch_kwargs:
            Keyword arguments to be passed to an instance or driver
            For example, you can pass ``headless=False, slow_mo=50`` 
            for a visualization of a search engine search to `playwright.chromium.launch`.
    """
    def __init__(self, 
                 domain: str,
                 browser_controller: AsyncAbstractBrowserController | SyncAbstractBrowserController,
                 user_agent: str="*", 
                 **launch_kwargs):
        self.launch_kwargs = launch_kwargs
        self.browser_controller: AbstractDriver | AbstractInstance = browser_controller
        self.domain: str = domain
        self.user_agent: str = user_agent
        self.rp: RobotFileParser = RobotFileParser()
        self.browser: AbstractBrowser = None
        self.crawl_delay: int = None
        self.rrate: NamedTuple = None

        if not browser_controller:
            raise ValueError("Driver or Instance missing from scraper keyword arguments")

    #### START CLASS STARTUP AND EXIT METHODS ####

    @try_except(exception=[URLError], retries=2, raise_exception=True)
    def get_robot_rules(self):
        """
        Get the site's robots.txt file and assign it to the class' applicable attributes
        See: https://docs.python.org/3/library/urllib.robotparser.html
        """
        # Construct the URL to the robots.txt file
        robots_url = urljoin(self.domain, 'robots.txt')
        self.rp.set_url(robots_url)

        # Read the robots.txt file from the server
        self.rp.read()

        # Set the request rate.
        self.rrate = self.rp.request_rate(self.user_agent)

        # Set the crawl delay
        self.crawl_delay = int(self.rp.crawl_delay(self.user_agent))
        return

    def can_fetch(self, url: str) -> tuple[bool, int]:
        fetch = True if self.rp.can_fetch(self.user_agent, url) else False
        return fetch, self.crawl_delay

    @abstractmethod
    def __enter__(self) -> AbstractScraper:
        self.get_robot_rules()

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass


    @classmethod
    def start(cls, domain, instance_or_driver, user_agent, **launch_kwargs) -> AbstractScraper:
        instance = cls(domain, instance_or_driver=instance_or_driver, user_agent=user_agent, **launch_kwargs)
        instance.get_robot_rules()
        return instance

    def close(self) -> None:
        self._close_browser()

    def _load_browser(self) -> None:
        """
        Launch a browser.
        """
        pass

    @abstractmethod
    def _close_browser(self) -> None:
        """
        Close browser controller and reset internal attributes
        """
        pass

    #### END CLASS STARTUP AND EXIT METHODS ####


    #### START PAGE PROCESSING METHODS ####
    @abstractmethod
    def create_page(self) -> AbstractPage:
        pass

    @abstractmethod
    async def async_create_page(self) -> AbstractPage:
        pass

    # def get_robot_rules(self):
    #     """
    #     Get the site's robots.txt file and assign it to the self.robot_urls attribute
    #     """
    #     robots_txt = fetch_robots_txt(self.robot_txt_url)
    #     rules = parse_robots_txt(robots_txt)
    #     self.robot_rules = rules

    @abstractmethod
    def _async_open_webpage(self, url: str) -> None:
        """
        Open a specified webpage and wait for any dynamic elements to load.
        """
        # See if we're allowed to get the URL, as well get the specified delay from robots.txt
        fetch, delay = can_fetch(url, self.robot_rules)
        if not fetch:
            logger.warning(f"Cannot scrape URL '{url}' as it's disallowed in robots.txt")
            return

    @abstractmethod
    def _open_webpage(self, url: str, Abstract: SyncAbstractBrowserController) -> None:
        """
        Open a specified webpage and wait for any dynamic elements to load.
        """
        # See if we're allowed to get the URL, as well get the specified delay from robots.txt
        fetch, delay = can_fetch(url, self.robot_rules)
        if not fetch:
            logger.warning(f"Cannot scrape URL '{url}' as it's disallowed in robots.txt")
            return

    @abstractmethod
    def _fetch_urls_from_page(self, url: str) -> dict[str]|dict[None]:
        pass

    @abstractmethod
    async def _async_fetch_urls_from_page(self, url: str) -> dict[str]|dict[None]:
        pass

    @abstractmethod
    async def _async_fetch_urls_from_page(self, url: str) -> dict[str]|dict[None]:
        fetch, delay = can_fetch(url)
        if not fetch:
            logger.warning(f"Cannot scrape URL '{url}' as it's disallowed in robots.txt")
            return None

    def _respectful_fetch(self, url: str) -> dict[str]|dict[None]:
        """
        Limit getting URLs based on a semaphore and the delay specified in robots.txt
        """
        fetch, delay = can_fetch(url)
        if not fetch:
            logger.warning(f"Cannot scrape URL '{url}' as it's disallowed in robots.txt")
            return None
        else:
            time.sleep(delay)
            return self._fetch_urls_from_page(url)
