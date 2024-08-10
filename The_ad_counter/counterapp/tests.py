import json

from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch, Mock
from django.urls import reverse
from django.utils import timezone
import os

from counterapp.models import Bundle, Counter, Ad

from .tasks import get_url, parser


# TEST_MODE=True docker compose up -d
# docker compose exec counterapp python manage.py test
# docker compose exec counterapp coverage report


class AddBundleTestCase(APITestCase):
    def setUp(self) -> None:
        self.bundle_moscow = Bundle.objects.create(phrase='studio', region='moscow')
        self.bundle_ufa = Bundle.objects.create(phrase='studio', region='ufa')
        self.bundle_ekb = Bundle.objects.create(phrase='studio', region='ekaterinburg')

    def tearDown(self) -> None:
        self.bundle_moscow.delete()
        self.bundle_ufa.delete()
        self.bundle_ekb.delete()

    def test_add_bundle(self):
        """
        Проверка запросов к приложению
        Добавления в базу данных связки регион+фраза
        """
        post_data = {
            "phrase": "studio",
            "region": "Nizhniy Novgorod"
        }
        post_data_json = json.dumps(post_data)
        response = self.client.post(reverse('counterapp:add'), post_data_json, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Bundle.objects.filter(phrase=post_data['phrase'], region='nizhniy-novgorod').exists())
        bundle = Bundle.objects.get(phrase=post_data['phrase'], region='nizhniy-novgorod'.lower())
        expected_data = {"id": bundle.pk}
        self.assertEqual(response.data, expected_data)
        self.assertTrue(Counter.objects.filter(bundle=bundle).exists())

        # проверка валидации полей
        # когда не передали поле phrase
        post_data = {
            "region": "Ufa"
        }
        post_data_json = json.dumps(post_data)
        response = self.client.post(reverse('counterapp:add'), post_data_json, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'The phrase and region fields are required'})

        # когда не передали поле region
        post_data = {
            "phrase": "studio",
        }
        post_data_json = json.dumps(post_data)
        response = self.client.post(reverse('counterapp:add'), post_data_json, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'The phrase and region fields are required'})

        # когда поле phrase указали некорректно
        post_data = {
            "phrase": "abrakadabra",
            "region": "Ufa"
        }
        post_data_json = json.dumps(post_data)
        response = self.client.post(reverse('counterapp:add'), post_data_json, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_data = json.loads(response.content)  # Преобразуем контент ответа в словарь
        PHRASE_URL = ["1", "2", "3", "4", "5", "6", "studio", "free", ""]
        self.assertEqual(response_data, {'error': f'The phrase must take one of these meanings:{PHRASE_URL}'})

        # когда поле region указали некорректно
        post_data = {
            "phrase": "studio",
            "region": "abrakadabra"
        }
        post_data_json = json.dumps(post_data)
        response = self.client.post(reverse('counterapp:add'), post_data_json, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'The region is specified incorrectly'})

    def test_get_url(self):
        """
        Отдельная проверка на генерацию url из связки регион+фраза
        """
        url = get_url(self.bundle_moscow)
        self.assertEqual(url, 'https://www.cian.ru/kupit-kvartiru-studiu/')
        url = get_url(self.bundle_ufa)
        self.assertEqual(url, 'https://ufa.cian.ru/kupit-kvartiru-studiu/')
        url = get_url(self.bundle_ekb)
        self.assertEqual(url, 'https://ekb.cian.ru/kupit-kvartiru-studiu/')

    @patch('counterapp.tasks.create_driver')
    def test_parse_ads_count(self, mock_create_driver):
        """
        Тестирование парсинга
        """

        # Создаем mock driver
        mock_driver = Mock()
        mock_create_driver.return_value = mock_driver

        # Получаем путь к текущему файлу (tests.py)
        current_dir = os.path.dirname(__file__)
        # Формируем путь к файлу Moscow-studio.html относительно текущего файла
        file_path = os.path.join(current_dir, '.', 'templates', 'Moscow-studio.html')
        # Загружаем HTML из файла
        with open(file_path, 'r') as f:
            mock_driver.page_source = f.read()

        # Замокируем метод get так, чтобы он не делал реальные запросы
        mock_driver.get.return_value = None

        # Вызываем парсер
        result = parser(self.bundle_moscow, 'https://www.cian.ru/kupit-kvartiru-studiu/')

        # Проверяем результат
        assert result == 15910

        # Проверяем, что get был вызван с правильным URL
        mock_driver.get.assert_called_once_with('https://www.cian.ru/kupit-kvartiru-studiu/')

        # Проверяем результат выполнения get_top_links
        links = {
            1: 'https://www.cian.ru/sale/flat/305769432/',
            2: 'https://www.cian.ru/sale/flat/303315104/',
            3: 'https://www.cian.ru/sale/flat/299093647/',
            4: 'https://www.cian.ru/sale/flat/299715415/',
            5: 'https://www.cian.ru/sale/flat/295195106/',
        }
        q = Ad.objects.all()

        self.assertTrue(Ad.objects.filter(bundle=self.bundle_moscow, link=links[1], top=1).exists())
        self.assertTrue(Ad.objects.filter(bundle=self.bundle_moscow, link=links[2], top=2).exists())
        self.assertTrue(Ad.objects.filter(bundle=self.bundle_moscow, link=links[3], top=3).exists())
        self.assertTrue(Ad.objects.filter(bundle=self.bundle_moscow, link=links[4], top=4).exists())
        self.assertTrue(Ad.objects.filter(bundle=self.bundle_moscow, link=links[5], top=5).exists())


# мб тестирование создания новых счетчиков через час


class StatisticTestCase(APITestCase):
    def setUp(self) -> None:
        self.bundle_moscow = Bundle.objects.create(phrase='studio', region='moscow')
        self.counter_1 = Counter.objects.create(bundle=self.bundle_moscow, count=1400, date=timezone.now())
        self.counter_2 = Counter.objects.create(bundle=self.bundle_moscow, count=2400, date=timezone.now())

    def tearDown(self) -> None:
        self.counter_1.delete()
        self.counter_2.delete()
        self.bundle_moscow.delete()

    def test_get_statistic(self):
        """
        Проверка получения статистики (списка счетчиков)
        """
        query_param = {'id': self.bundle_moscow.pk, 'start_time': '2024-01-01'}
        response = self.client.get(reverse('counterapp:statistics'), data=query_param)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = json.loads(response.content)  # Преобразуем контент ответа в словарь

        expected_data = [
            {'id': self.counter_1.id,
             'count': self.counter_1.count,
             'date': self.counter_1.date.isoformat().replace('+00:00', 'Z')},
            {'id': self.counter_2.id,
             'count': self.counter_2.count,
             'date': self.counter_2.date.isoformat().replace('+00:00', 'Z')}
        ]
        self.assertEqual(response_data, expected_data)

        # проверка некорректных запросов
        query_param = {'start_time': '2024-01-01'}
        response = self.client.get(reverse('counterapp:statistics'), data=query_param)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'ID field is required'})

        query_param = {'id': self.bundle_moscow.pk}
        response = self.client.get(reverse('counterapp:statistics'), data=query_param)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'Start time field is required'})

        query_param = {'id': self.bundle_moscow.pk, 'start_time': '01.01.2024'}
        response = self.client.get(reverse('counterapp:statistics'), data=query_param)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'Invalid start_time format. Expected format: YYYY-MM-DD'})

        query_param = {'id': self.bundle_moscow.pk, 'start_time': '2024-01-01', 'end_time': '01.05.2024'}
        response = self.client.get(reverse('counterapp:statistics'), data=query_param)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'Invalid end_time format. Expected format: YYYY-MM-DD'})


class TopTestCase(APITestCase):
    def setUp(self) -> None:
        self.bundle_moscow = Bundle.objects.create(phrase='studio', region='moscow')
        self.counter = Counter.objects.create(bundle=self.bundle_moscow, count=1400, date=timezone.now())
        self.add_1 = Ad.objects.create(bundle=self.bundle_moscow, top=1, link='https://www.cian.ru/sale/flat/305769432/')
        self.add_2 = Ad.objects.create(bundle=self.bundle_moscow, top=2, link='https://www.cian.ru/sale/flat/303315104/')
        self.add_3 = Ad.objects.create(bundle=self.bundle_moscow, top=3, link='https://www.cian.ru/sale/flat/299093647/')
        self.add_4 = Ad.objects.create(bundle=self.bundle_moscow, top=4, link='https://www.cian.ru/sale/flat/299715415/')
        self.add_5 = Ad.objects.create(bundle=self.bundle_moscow, top=5, link='https://www.cian.ru/sale/flat/295195106/')

    def tearDown(self) -> None:
        self.add_1.delete()
        self.add_2.delete()
        self.add_3.delete()
        self.add_4.delete()
        self.add_5.delete()
        self.counter.delete()
        self.bundle_moscow.delete()

    def test_get_top_ads(self):
        """
        Проверка получения топ-5 объявлений
        """
        query_param = {'id': self.bundle_moscow.pk}
        response = self.client.get(reverse('counterapp:top'), data=query_param)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = json.loads(response.content)  # Преобразуем контент ответа в словарь
        expected_data = []
        q = Ad.objects.filter(bundle=self.bundle_moscow)
        for x in q:
            expected_data.append({'top': x.top, 'link': x.link})
        self.assertEqual(response_data, expected_data)

        # проверка некорректных запросов
        response = self.client.get(reverse('counterapp:top'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': 'ID field is required'})

        query_param = {'id': 1000}
        response = self.client.get(reverse('counterapp:top'), data=query_param)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'error': f'Bundle 1000 does not exist'})
