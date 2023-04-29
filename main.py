import time
import json
import requests

from bs4 import BeautifulSoup
from selenium import webdriver
from typing import Optional

from static.country_info import COUNTRY_INFO
from static.fake_user import USER_AGENT_GENERATOR
from static.variables import COUNTRY, CITY, DATASET, PARSE_SIZE

def url_from_location(country: str, city: str) -> str:
    # Check if country exists in the location dictionary
    if country in COUNTRY_INFO:
        # Get the domain and cities for the given country
        domain, cities = COUNTRY_INFO[country].values()
        if city in cities:
            return f"https://{city}.hh.{domain}"
        # Check if the given city and county exists for the given country
        raise ValueError(f"There is not city as: {city.title()}")
    raise ValueError(f"There is not country as: {country.title()}")


def parse_categories(url: str):
    """
    Extracts job categories and their corresponding URLs from a category page URL.
    """
    categories_dict = {}
    response = requests.get(url, headers={'user-agent': USER_AGENT_GENERATOR.random})
    soup = BeautifulSoup(response.text, 'lxml')
    category_list = soup.select('ul.multiple-column-list li.multiple-column-list-item')
    for category in category_list:
        link = category.find('a', attrs={'class': 'bloko-link'}).get('href')
        categories_dict[category.text] = f'{url}/{link}'
    return categories_dict



def ID(url):
    try:
        return url.split('/vacancy/')[1][:8]
    except:
        return None


def job_title(soup):
    try:
        return soup.find('div', attrs={'class': 'vacancy-title'}) \
            .find('h1', attrs={'class': 'bloko-header-section-1'}).text
    except:
        return None


def company_name(soup):
    try:
        company_name = soup.find('span', attrs={
            'class': 'bloko-header-section-2 bloko-header-section-2_lite',
            'data-qa': 'bloko-header-2'}).text
        return company_name.replace('\xa0', ' ')
    except:
        return None


def job_location(soup) -> Optional[str]:
    try:
        return soup.find('span', attrs={'data-qa': 'vacancy-view-raw-address'}).text
    except:
        return None

def required_experience(soup):
    try:
        return soup.find('span', attrs = {'data-qa' : 'vacancy-experience'}).text
    except:
        return None

def job_description(soup):
    try:
        return soup.find('div', attrs = {'class' : 'g-user-content'}).text
    except:
        return None


def required_skills(soup):
    try:
        skills = []
        skills_list = soup.find_all('div', attrs = {'class' : 'bloko-tag bloko-tag_inline'})
        for skill in skills_list:
            skills.append(skill.text.replace('\xa0', ' ').capitalize())
        return ', '.join(skills)
    except:
        return None


def get_max_page(category_url: str) -> int:
    """Maximum pages of subpages"""
    try:
        response = requests.get(category_url, headers= {'user-agent': USER_AGENT_GENERATOR.random})
        soup = BeautifulSoup(response.text, 'lxml')
        max_page = soup.find_all('a', attrs={'class': 'bloko-button', 'data-qa': 'pager-page'})[-1].text
        return int(max_page)
    except:
        return 1


def page_links_generator(url: str, page: int = 0) -> str:
    """Generates link for each subpage"""

    pages_url = url + f'&page={page}&disableBrowserCache=true&hhtmFrom=vacancy_search_list'
    return pages_url

def page_links_parser(pages_url: str):
    """Page link parser from each category"""

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    driver.get(pages_url)
    # Wait for the page to load
    driver.implicitly_wait(5)
    soup_page = BeautifulSoup(driver.page_source, 'html.parser')
    # Close the browser
    driver.quit()
    return soup_page.find_all('a', attrs={'class' : "serp-item__title", 'data-qa' : 'serp-item__title'})


def parser(page_link, category_name):
    """From final page parser"""

    try:
        url = page_link.get('href')
        time.sleep(2)

        response = requests.get(url, headers={'user-agent': USER_AGENT_GENERATOR.random})
        soup = BeautifulSoup(response.text, 'lxml')

        dict = {'id': ID(url),
                'job_title': job_title(soup),
                'company_name': company_name(soup),
                'location': job_location(soup),
                'required_experience': required_experience(soup),
                'job_market': category_name,
                'description': job_description(soup),
                'required_skills': required_skills(soup)}

        DATASET['data'].append(dict)
        return DATASET
    except:
        return


def parse_job_listings(country: str, city: str):
    """
    Scrapes job listings from HeadHunter for a given country and city.

    """
    # Get the URL to search for jobs in the given country and city
    url = url_from_location(country, city)
    print(f"Scraping job listings for {city}, {country} from: {url}")

    counter = 0
    L = 0

    # Get the different job categories available for the given location
    categories = parse_categories(url)

    # Scrape job listings for each category
    for category_name, search_by_category_url in categories.items():
        print(f"\nScraping job listings for category '{category_name}'")
        max_page = get_max_page(search_by_category_url)
        print(f"Total pages in category: {max_page}")

        # Scrape job listings on each page for the current category
        for page in range(max_page):
            print(f"Scraping job listings on page {page+1} of {max_page}")
            # Generate the URL for the current page of job listings
            pages_url = page_links_generator(search_by_category_url, page)
            # Get the links to the individual job listings on the current page
            page_links = page_links_parser(pages_url)

            # Scrape data from each individual job listing
            for page_link in page_links:
                parser(page_link, category_name)

                if counter == L:
                    print(f"Job listing {counter + 1} scraped")
                    L += 50
                counter += 1

                if counter == PARSE_SIZE:
                    break
            if counter == PARSE_SIZE:
                break
        if counter == PARSE_SIZE:
            break
    print("Job listings scraped successfully!")


parse_job_listings(COUNTRY,CITY)

with open('dataset.json', 'w') as f:
    json.dump(DATASET, f)

