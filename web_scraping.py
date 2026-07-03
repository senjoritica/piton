"""
LABs 11 & 12
"""

from sys import stderr
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import ChromeOptions
import pandas as pd


ORIGINS_CSV_FILE = "athletes_origin.csv"
NAMES_CSV_FILE = "athletes_names.csv"

def from_csv(fpath):
    """
    Reads data from a csv file

    :param fpath: path to the csv file with the data
    :return: the content of the csv file as a list; None if, for any reason, reading from file was unsuccessful
    """
    try:
        names_df = pd.read_csv(fpath)
        # Option 1
        # return list(names_df.to_records(index=False))
        # Option 2
        return [tuple(row) for _, row in names_df.iterrows()]
    except OSError as err:
        stderr.write(f"Greska pri upisivanju podataka u csv fajl {fpath}.\nOriginalna poruka greske: {err}\n")
        return None

def to_csv(fpath, header, data):
    """
    Auxiliary function for storing the collected data in a csv file

    :param fpath: path to the file where data will be stored
    :param header: header (variable names) of the csv file; expected as a list, tuple, or an iterable
    :param data: data to store; expected as a list or a tuple
    :return: nothing
    """
    try:
        names_df = pd.DataFrame(data=data, columns=header)
        names_df.to_csv(fpath, index=False)
    except OSError as err:
        stderr.write(f'Greska pri upisivanju podataka u csv fajl {fpath}.\nOriginalna poruka greske: {err}\n')

def get_chrome_web_driver():
    """
    Creates and returns a Selenium web driver for Chrome web-browser

    :return: Selenium web driver for Chrome browser
    """
    options = ChromeOptions()
    options.add_argument('headless')
    return webdriver.Chrome(options=options)

def scrape_athletes_names(url):
    """
    Retrieves the web page with a list of top athletes,
    extracts athletes' names and returns a list of those names

    :param url: url of the page to scrape data from
    :return: a list of athletes' names
    """
    names = []

    web_driver = get_chrome_web_driver()
    web_driver.get(url)
    page_content = web_driver.page_source
    # print(page_content)

    page_soup = BeautifulSoup(page_content, 'html.parser')
    ol = page_soup.find(name='ol')
    for li in ol.find_all(name='li'):
        strong = li.find_next('strong')
        if strong and strong.text:
            names.append(strong.text.strip())

    print(f"Scraping imena sportista zavrsen, pronadjeno {len(names)} (od 100 mogucih).")

    web_driver.quit()

    return names
def get_athletes_names(url):
    """
    The function, first, tries to load the data (athletes' names) from a local file (NAMES_CSV_FILE);
    if the file does not exist (= data was not collected yet), it collects the
    data by calling the scrape_athletes_names() f. and stores the collected data
    for potential later use; the data is also returned as a list of athletes' names

    :param url: url of the page to scrape data from
    :return: a list of athletes' names
    """
    names = from_csv(Path.cwd() / NAMES_CSV_FILE)
    if not names:
        print(f"Imena sportista nisu raspoloziva => bice skrejpovana sa stranice {url}")
        names = scrape_athletes_names(url)
        to_csv(Path.cwd() / NAMES_CSV_FILE, ('name',), names)
    else:
        print(f"Imena sportista uspesno ucitana iz fajla {NAMES_CSV_FILE} file")
        names = [name[0] for name in names]

    return names



def collect_athletes_data(athletes_names):
    """
    The function puts several parts together:
    - iterates over the list of athletes' names to retrieve the country for each
    athlete by 'consulting' their Wikipedia page
    - stores the collected data in a csv file
    - prints names of athletes whose birthplace data could not have been collected

    :param athletes_names: list with athlete names
    :return: list of athlete name and origin pairs
    """
    names_and_origins = []
    no_country = []

    wd = get_chrome_web_driver()

    for name in athletes_names:
        print(f"Pokrece se prikupljanje podataka za {name}")
        country = retrieve_country_of_origin(name, wd)
        if country:
            names_and_origins.append((name, country))
        else:
            no_country.append(name)

    wd.quit()

    to_csv(Path.cwd() / ORIGINS_CSV_FILE, ('name', 'country'), names_and_origins)

    print(f"Zemlja porekla nije pronadjena za {len(no_country)} sportista, konkretno: ", ', '.join(no_country))

    return names_and_origins


def retrieve_country_of_origin(name, web_driver):
    """
    Receives the full name of an athlete.
    Returns the country of birth of the athlete extracted from their
    Wikipedia page or None if the information is not available.

    :param name: name of an athlete
    :param web_driver: Selenium web driver to be used for scraping
    :return: country of birth (string) or None
    """

    wiki_url = f'https://en.wikipedia.org/wiki/{name.replace(" ", "_")}'
    web_driver.get(wiki_url)
    page_content = web_driver.page_source

    wiki_soup = BeautifulSoup(page_content, 'html.parser')
    info_box = wiki_soup.find(lambda elem: elem.name=='table' and
                                           elem.has_attr('class') and
                                           all(val in elem.attrs['class'] for val in ['infobox', 'vcard']))
                                           # 'infobox' in elem.attrs['class'] and 'vcard' in elem.attrs['class'])
    if not info_box:
        disambig_page= wiki_soup.find(lambda elem: elem.name=='div' and elem.has_attr('id') and elem.attrs['id']=='disambigbox')
        if disambig_page:
            print(f"Nema jedinstvene wikipedia stranice za URL {wiki_url} => ne mozemo pristupiti podatku o drzavi rodjenja")
        else:
            print(f"Wikipedia stranica za {name} ne sadrzi infobox => ne mozemo pristupiti podatku o drzavi rodjenja")
        return None

    th = info_box.find_next(lambda elem: elem.name=='th' and elem.text and elem.text.lower() in ['born', 'place of birth'])
    if th:
        td = th.find_next_sibling(lambda elem: elem.name=='td' and elem.text)
        if td:
            return extract_country(td.text)
    else:
        td = info_box.find_next(lambda elem: elem.name=='td' and elem.text and elem.text.lower().startswith('born'))
        if td:
            return extract_country(td.text)

    return None

def extract_country(born_text):
    _, country = born_text.rsplit(',', maxsplit=1)
    if '[' in country:
        country, _ = country.rsplit('[', maxsplit=1)
    return country.strip()


def create_country_labels_mapping():
    """
    Creates a mapping between a country and different ways it was referred to
    in the collected data

    :return: a dictionary with countries as the keys and lists of different terms
    used to refer to them as values
    """

    country_lbls_dict = dict()

    country_lbls_dict['USA'] = ['California', 'New York', 'United States', 'Florida', 'Oklahoma', 'US', 'U.S.',
                                'Pennsylvania', 'Ohio', 'Mississippi', 'Alabama', 'Indian Territory', 'Maryland']
    country_lbls_dict['Germany'] = ['West Germany']
    country_lbls_dict['Australia'] = ['Victoria', 'Western Australia', 'New South Wales']
    country_lbls_dict['UK'] = ['England', 'UK', 'British Leeward Islands', 'United Kingdom', 'Northern Ireland']

    return country_lbls_dict



def most_represented_countries(athletes_list):
    """
    Creates and prints a list of countries based on how well they
    are represented in the collected athletes data

    :param athletes_list: list of athlete name and origin pairs
    :return: nothing
    """

    mapping_dict = create_country_labels_mapping()

    final_list = []

    for name, origin in athletes_list:
        main_lbl_found = False
        for main_lbl, alternatives in mapping_dict.items():
            if origin in alternatives:
                final_list.append((name, main_lbl))
                main_lbl_found = True
                break
        if not main_lbl_found:
            final_list.append((name, origin))

    from collections import Counter
    country_counts = Counter([country for _, country in final_list])

    print("Broj top sportista po zemljama porekla:")
    for country, count in sorted(country_counts.items(), key=lambda item: item[1], reverse=True):
        print(f"{country}: {count}")


if __name__ == '__main__':

    top_athletes_url = 'https://ivansmith.co.uk/?page_id=475'
    try:
        athletes_names = get_athletes_names(top_athletes_url)
        # if athletes_names:
        #     for i, name in enumerate(athletes_names):
        #         print(f"{i+1}. {name}")
        # athletes_data = collect_athletes_data(athletes_names)
        athletes_data = from_csv(Path.cwd() / ORIGINS_CSV_FILE)
        most_represented_countries(athletes_data)
    except RuntimeError as err:
        stderr.write(f"Terminating the program due to the following runtime error:\n{err}")
