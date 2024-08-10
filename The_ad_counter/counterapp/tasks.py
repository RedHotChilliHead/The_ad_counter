import json
import logging

from celery import shared_task
from .models import Counter, Bundle, Ad
from bs4 import BeautifulSoup

from datetime import timedelta
from django.utils import timezone


from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CITY_URL = {
    "nizhniy-novgorod": "nn",
    "saint-petersburg": "spb",
    "ekaterinburg": "ekb",
}

PHRASE_URL = {
    "1": "kupit-1-komnatnuyu-kvartiru",
    "2": "kupit-2-komnatnuyu-kvartiru",
    "3": "kupit-3-komnatnuyu-kvartiru",
    "4": "kupit-4-komnatnuyu-kvartiru",
    "5": "kupit-5-komnatnuyu-kvartiru",
    "6": "kupit-mnogkomnatnuyu-kvartiru",
    "studio": "kupit-kvartiru-studiu",
    "free": "kupit-kvartiru-svobodnoy-planirovki",
    "": "kupit-kvartiru-1-komn-ili-2-komn",
}
# https://www.cian.ru/cat.php?deal_type=sale&engine_version=2&offer_type=flat&region=1&room1=1&room3=1/
# https://nn.cian.ru/kupit-2-komnatnuyu-kvartiru-nizhegorodskaya-oblast/


def get_url(bundle):
    """
    Метод получения полной ссылки
    Пример: запрос - Moscow, 1 или 2, готовая ссылка https://www.cian.ru/kupit-kvartiru-1-komn-ili-2-komn/
    """
    print('get_url стартовала')
    if bundle.region == "moscow":
        return f"https://www.cian.ru/{PHRASE_URL[bundle.phrase]}/"

    if bundle.region in CITY_URL:
        return f"https://{CITY_URL[bundle.region]}.cian.ru/{PHRASE_URL[bundle.phrase]}/"
    else:
        return f"https://{bundle.region}.cian.ru/{PHRASE_URL[bundle.phrase]}/"


def create_driver():
    print('create_driver стартовала')
    options = Options()
    options.binary_location = "/usr/bin/google-chrome"
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    options.add_argument("--headless")  # Запуск в фоновом режиме
    options.add_argument("--no-sandbox")  # Требуется для некоторых окружений Docker
    options.add_argument("--disable-dev-shm-usage")  # Предотвращение использования /dev/shm
    options.add_argument("start-maximized")  # Опции для запуска браузера

    # Подключение к Selenium через Docker-сеть
    driver = webdriver.Remote(
        command_executor='http://selenium:4444/wd/hub',
        options=options
    )
    return driver


def get_top_links(bundle, soup):
    print('get_top_links стартовала')
    Ad.objects.filter(bundle=bundle).delete()
    # Находим все контейнеры с атрибутом data-name="LinkArea"
    link_area_divs = soup.find_all('div', attrs={'data-name': 'LinkArea'})
    # Собираем ссылки в множество, чтобы избежать дубликатов
    unique_links = []
    seen_links = set()
    for link_area_div in link_area_divs:
        link = link_area_div.find('a')['href']
        if link not in seen_links:
            unique_links.append(link)
            seen_links.add(link)
        # # Остановимся после 5 уникальных ссылок
        if len(unique_links) == 5:
            break

    # Записываем ссылки в базу данных
    for i, link in enumerate(unique_links, start=1):
        Ad.objects.create(bundle=bundle, link=link, top=i)


def parser(bundle, url):
    print('parser стартовала')
    logger.info(f"start parsing {url}")
    driver = None

    try:
        driver = create_driver()
        driver.get(url)

        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

        # Печатаем текст HTML-страницы после нахождения элемента
        page_source = driver.page_source

        soup = BeautifulSoup(page_source, 'html.parser')
        # print('soup:')
        # print(soup.prettify())  # Печатаем отформатированный HTML-код для удобства

        script_tags = soup.find_all('script', {'type': 'application/ld+json'})
        get_top_links(bundle, soup)
        for script in script_tags:
            try:
                data = json.loads(script.string)
                if 'offers' in data and 'offerCount' in data['offers']:
                    offer_count = int(data['offers']['offerCount'])
                    return offer_count
            except json.JSONDecodeError as e:
                logger.error(f'Error decoding JSON: {e}')
                continue

        return 0  # Если элемент не найден, возвращаем 0

    except Exception as e:
        logger.error(f'Request error {url}: {e}')
        if driver:
            try:
                logger.error(f'status_code: {driver.get_log("driver")}')
            except Exception as log_e:
                logger.error(f'Failed to get driver logs: {log_e}')

    finally:
        if driver:
            driver.quit()


# задача по подсчету количества объявлений, по заданной связке поисковой запрос + регион
@shared_task()
def counting_ads(bundle_id):
    print('задача стартовала')
    logger.info("задача стартовала")
    if Bundle.objects.filter(id=bundle_id).exists():
        bundle = Bundle.objects.get(pk=bundle_id)
    else:
        logger.error(f'Bundle {bundle_id} does not exist')
    url = get_url(bundle)
    count = parser(bundle, url)

    counter = Counter.objects.create(bundle=bundle, count=count)
    if counter is None:
        logger.error(f'Create counter error')
    else:
        logger.info(f'{counter.count} ads on request {url} at {counter.date}')


@shared_task()
def adding_tasks_to_delay():
    logger.info(f'start adding tasks to delay every hour')
    bundles = Bundle.objects.all()
    # delta = timedelta(seconds=45)
    delta = timedelta(hours=1)
    for bundle in bundles:
        print('bundle.id:', bundle.id)
        counter = Counter.objects.filter(bundle=bundle.id).last()
        print(f'last counter.id {counter.id} for bundle {bundle.id}')
        if counter is None:
            counting_ads.delay(bundle.pk)
        if counter.date + delta < timezone.now():
            counting_ads.delay(bundle.pk)
