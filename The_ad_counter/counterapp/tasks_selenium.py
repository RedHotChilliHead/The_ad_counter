import logging

from celery import shared_task
from .models import Counter, Bundle
from bs4 import BeautifulSoup
import requests

from datetime import timedelta
from django.utils import timezone

import aiohttp
import asyncio

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

URL = 'https://www.avito.ru/'


def get_url(base_url, bundle):
    """
    Метод получения полной ссылки
    Пример: запрос - замиокулькас зензи, готовая ссылка https://www.avito.ru/nizhniy_novgorod?q=замиокулькас+зензи
    """
    q = ""
    count = 1
    phrase_list = bundle.phrase.split(" ")
    lenght = len(phrase_list)
    for word in phrase_list:
        if lenght == count:
            q += word
        else:
            q += word + "+"
        count += 1

    return f"{base_url}{bundle.region}?q={q}"


# def parser(url):
#     options = Options()
#     options.binary_location = "/usr/bin/google-chrome"  # Путь к бинарному файлу Chrome
#     options.add_argument(
#         "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
#
#     driver = None
#     try:
#         # Установка ChromeDriver
#         service = ChromeService(executable_path='/usr/local/bin/chromedriver')
#         driver = webdriver.Chrome(service=service, options=options)
#         driver.get(url)
#         wait = WebDriverWait(driver, 20)
#         count_span = wait.until(
#             EC.presence_of_element_located((By.CSS_SELECTOR, 'span[data-marker="page-title/count"]')))
#         page_source = driver.page_source
#         soup = BeautifulSoup(page_source, 'html.parser')
#         count_span = soup.find('span', {'data-marker': 'page-title/count'})
#
#         # response = requests.get(url)
#         # response.raise_for_status()  # проверяем статус-код ответа и выбрасывает исключение, если статус-код не 200
#         # root = BeautifulSoup(response.content, 'html.parser')
#         # # Извлекаем текст из найденного элемента span и удаляем пробелы по краям.
#         # count_span = root.find('span', {'data-marker': 'page-title/count'})
#
#         if count_span:
#             count = int(count_span.text.strip())  # Извлекаем и преобразуем текст в число
#             return count
#
#         return 0  # Если элемент не найден, возвращаем 0
#     except Exception as e:
#         logger.error(f'Request error {url}: {e}')
#         if driver:
#             try:
#                 logger.error(f'status_code: {driver.get_log("driver")}')
#             except Exception as log_e:
#                 logger.error(f'Failed to get driver logs: {log_e}')
#     finally:
#         if driver:
#             driver.quit()

def parser(url):
    print('start parser')
    url = 'https://www.avito.ru/nizhniy_novgorod?q=macbook'
    options = Options()
    options.binary_location = "/usr/bin/google-chrome"
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    options.add_argument("--headless")  # Запуск в фоновом режиме
    options.add_argument("--no-sandbox")  # Требуется для некоторых окружений Docker
    options.add_argument("--disable-dev-shm-usage")  # Предотвращение использования /dev/shm

    driver = None
    try:
        print('start try')
        service = ChromeService(executable_path='/usr/local/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        print(f'driver.get({url})')
        wait = WebDriverWait(driver, 20)
        count_span = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'span[data-marker="page-title/count"]')))
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        count_span = soup.find('span', {'data-marker': 'page-title/count'})

        title = wait.until(EC.presence_of_element_located((By.TAG_NAME, 'h1')))

        if count_span:
            count_text = count_span.text.strip()
            logger.info(f'Extracted text: "{count_text}"')
            try:
                count = int(''.join(filter(str.isdigit, count_text)))
                print(count)
                return count
            except ValueError as ve:
                logger.error(f'Error converting text to int: {ve}')
                print(0)
                return 0

        print(0)
        return 0  # Если элемент не найден, возвращаем 0

    except Exception as e:
        logger.error(f'Request error {url}: {e}')
    finally:
        if driver:
            driver.quit()

# задача по подсчету количества объявлений, по заданной связке поисковой запрос + регион
@shared_task()
def counting_ads(bundle_id):
    print("задача стартовала")
    if Bundle.objects.filter(id=bundle_id).exists():
        bundle = Bundle.objects.get(pk=bundle_id)
    else:
        logger.error(f'Bundle {bundle_id} does not exist')
    url = get_url(URL, bundle)
    print(url)
    count = parser(url)

    counter = Counter.objects.create(bundle=bundle, count=count)
    if counter is None:
        logger.error(f'Create counter error')
    else:
        logger.info(f'{counter.count} ads on request {counter.bundle.phrase} at {counter.date}')


# @shared_task()
# async def async_counting_ads(session, bundle):
#     url = get_url(URL, bundle)
#     count = parser(url)
#
#     try:
#         async with session.get(url, ssl=False) as response:  # выполняет асинхронный HTTP GET-запрос
#             response.raise_for_status()  # проверяем статус-код ответа и выбрасывает исключение, если статус-код не 200
#
#             counter = Counter.objects.create(bundle=bundle.pk, count=count)
#
#             if counter is None:
#                 logger.error(f'Create counter error')
#             else:
#                 logger.info(f'{counter.count} ads on request {counter.bundle_set.phrase} at {counter.date}')
#
#     except Exception as e:
#         logger.error(f'Failed to request {url}: {e}')


# задача по постановке в очередь всех связок, у которых последний счетчик создан более часа назад
# @shared_task()
# async def adding_tasks_to_delay():
#     # создаем асинхронную HTTP-сессию, которая будет использоваться для get-запросов
#     async with aiohttp.ClientSession() as session:
#         tasks = []  # список задач для создания счетчиков
#         bundles = Bundle.objects.all()
#         delta = timedelta(hours=1)
#         for bundle in bundles:
#             counter = Counter.objects.filter(bundle=bundle.id).last()
#             if counter.date + delta < timezone.now():
#                 tasks.append(async_counting_ads(session, bundle))
#         await asyncio.gather(*tasks)  # запускаем все задачи параллельно и ждем их завершения

@shared_task()
def adding_tasks_to_delay():
    bundles = Bundle.objects.all()
    delta = timedelta(hours=1)
    for bundle in bundles:
        print(bundle.phrase)
        print(bundle.id)
        counter = Counter.objects.filter(bundle=bundle.id).last()
        print(counter)
        if counter is None:
            counting_ads.delay(bundle.pk)
        print(counter.bundle)
        print(counter.count)
        print(counter.date)
        if counter.date + delta < timezone.now():
            counting_ads.delay(bundle.pk)
