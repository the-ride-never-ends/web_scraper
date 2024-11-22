from abc import ABC, ABCMeta, abstractmethod
from typing import Any, List, Dict
import asyncio


import pandas as pd
pd.DataFrame

from typing import TypeVar

import playwright.sync_api
import playwright.async_api


from typing import overload
from playwright.async_api import Browser as AsyncBrowser, Page as AsyncPage
from playwright.sync_api import Browser as SyncBrowser, Page as SyncPage


SeleniumWebDriver = TypeVar('SeleniumWebDriver')
SyncPlaywrightBrowser = TypeVar('SyncPlaywrightBrowser')
AyncPlaywrightBrowser = TypeVar('AyncPlaywrightBrowser')


class AsyncAbstractBrowserController(ABC):

    @abstractmethod
    async def navigate(self, *args, **kwargs) -> None:
        pass

    @abstractmethod
    async def click(self, *args, **kwargs) -> None: 
        pass

    @abstractmethod
    async def find_element(self, *args, **kwargs) -> Any:
        pass

    @abstractmethod
    async def find_elements(self, *args, **kwargs)  -> list[Any]:
        pass

    @abstractmethod
    async def send_keys(self, *args, **kwargs)  -> None:
        pass

    @abstractmethod
    async def get_text(self, *args, **kwargs)  -> str:
        pass

    @abstractmethod
    async def get_attribute(self, *args, **kwargs)  -> str:
        pass


class SyncAbstractBrowserController(ABC):

    @abstractmethod
    def navigate(self, *args, **kwargs) -> None:
        pass

    @abstractmethod
    def click(self, *args, **kwargs) -> None: 
        pass

    @abstractmethod
    def find_element(self, *args, **kwargs) -> Any:
        pass

    @abstractmethod
    def find_elements(self, *args, **kwargs)  -> list[Any]:
        pass

    @abstractmethod
    def send_keys(self, *args, **kwargs)  -> None:
        pass

    @abstractmethod
    def get_text(self, *args, **kwargs)  -> str:
        pass

    @abstractmethod
    def get_attribute(self, *args, **kwargs)  -> str:
        pass









class SyncAbstractBrowserController(ABC):

    @abstractmethod
    def navigate(self, url: str) -> None:
        pass

    @abstractmethod
    def find_element(self, selector: str) -> Any:
        pass

    @abstractmethod
    def find_elements(self, selector: str) -> list[Any]:
        pass

    @abstractmethod
    def click(self, element: Any) -> None:
        pass

    @abstractmethod
    def send_keys(self, element: Any, text: str) -> None:
        pass

    @abstractmethod
    def get_text(self, element: Any) -> str:
        pass

    @abstractmethod
    def get_attribute(self, element: Any, attribute: str) -> str:
        pass



class AbstractScraper(ABC):
    def __init__(self, browser_controller):
        super(AbstractScraper, self).__init__(browser_controller=browser_controller)
        self.browser = browser_controller

    @abstractmethod
    async def setup(self) -> None:
        """Perform any necessary setup before scraping."""
        pass

    @abstractmethod
    async def navigate_to_target(self) -> None:
        """Navigate to the target page or section."""
        pass

    @abstractmethod
    async def extract_data(self) -> Dict[str, Any]:
        """Extract the required data from the page."""
        pass

    @abstractmethod
    async def process_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and clean the extracted data."""
        pass

    @abstractmethod
    async def save_data(self, processed_data: Dict[str, Any]) -> None:
        """Save the processed data."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Perform any necessary cleanup after scraping."""
        pass

    async def run(self) -> Dict[str, Any]:
        """Main method to run the scraping process."""
        try:
            await self.setup()
            await self.navigate_to_target()
            raw_data = await self.extract_data()
            processed_data = await self.process_data(raw_data)
            await self.save_data(processed_data)
            return processed_data
        finally:
            await self.cleanup()

