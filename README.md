# Web Scraper Module

## Overview
The module sets up a web scraper based on Playwright or Selenium.
It supports various scraping methods (GET, POST, PUT, DELETE) and provides functions to extract
data from different types of web pages. The Scraper class can be instantiated with custom user agents,
proxy settings, and request timeouts.

NOTE: This module is still under development and is not yet ready for production use.

## Key Features
- Support for both synchronous and asynchronous scraping.
- Automatic parsing and saving of robots.txt for responsible scraping.
- Dynamic URL handling and request routing
- A specialized parser for handling different HTML structures.
- Configurable request headers and parameters
- Customizable data extraction patterns (CSS selectors, XPath, regex)

## Dependencies
This module requires the following external libraries:
- aiohttp
- beautifulsoup4
- multipledispatch
- pandas
- pytest-playwright
- pyyaml
- requests
- selenium

## Usage
To use this module, import it as follows:
```python
from web_scraper.playwright.async_scraper.async_playwright_scraper import AsyncPlaywrightScrapper

scraper = await AsyncPlaywrightScrapper(user_agent="My Web Scraper").start()

await scraper.navigate_to("https://example.com")
await scraper.save_page_html_content_to_output_dir("example_content.html")

await scraper.exit()