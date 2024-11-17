# EVDS Scraper
A tool for scraping data from the TCMB (Central Bank of the Republic of Turkey) Electronic Data Delivery System (EVDS).

## Installation

```bash
pip install git+https://github.com/ozanoztrk/evds-scraper.git
```

## Requirements
- Python 3.7+
- Selenium
- Pandas

## Quick Start

```python
from selenium import webdriver
from evds_scraper import EVDSScraper, ScraperConfig, Variable

# Initialize webdriver
driver = webdriver.Chrome()

# Create scraper instance
scraper = EVDSScraper(driver)

# Interactive mode
data = scraper.scrape()

# Close the browser
driver.quit()
```

## Google Colab Example

Try out our example in Google Colab: [Open in Colab](https://colab.research.google.com/drive/1SUUHLqAkWntR-q8up0GMAaeK0xY0YazK?usp=sharing)

## Features

- Interactive and automatic modes
- Multiple output formats (Excel, DataFrame, Dictionary)
- Configurable date ranges and frequencies
- Support for multiple variables
- Language support (English/Turkish)

## License
