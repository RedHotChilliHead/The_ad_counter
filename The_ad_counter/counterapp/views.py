from django.utils import timezone

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response

from counterapp.models import Bundle, Counter, Ad
from counterapp.serializers import CounterSerializer, AdSerializer
from .tasks import counting_ads, get_url

import requests


class AddApiView(APIView):
    """
    API метод создает связку поискового запроса и присваивает ему уникальный идентификатор.
    Принимает количество комнат в квартире и наименование региона, регистирует связку в системе
    и вовзвращает ID.
    Наименование региона или города необходимо вводить на английском языке
    В поле 'phrase' указывается количество комнат, возможные варианты: 1,2,3,4,5,6,studio,free,
    или оставить пустое поле для 1 или 2х-комнатной квартиры.
    Пример POST запроса: /counter/add/
    {"phrase":"1", "region":"Nizhniy Novgorod"}
    """
    PHRASE_URL = ["1", "2", "3", "4", "5", "6", "studio", "free", ""]

    def post(self, request: Request) -> Response:
        try:
            phrase = request.data['phrase']
            region = request.data['region'].lower()
        except KeyError:
            return Response({'error': 'The phrase and region fields are required'},
                            status=status.HTTP_400_BAD_REQUEST)
        if phrase not in self.PHRASE_URL:
            return Response({'error': f'The phrase must take one of these meanings:{self.PHRASE_URL}'},
                            status=status.HTTP_400_BAD_REQUEST)
        if " " in region:
            region = region.replace(" ", "-")

        bundle = Bundle.objects.create(phrase=phrase, region=region)

        # валидация региона по доступу к url
        url = get_url(bundle)
        response = requests.get(url)
        if response.status_code != 200:
            bundle.delete()
            return Response({'error': 'The region is specified incorrectly'}, status=status.HTTP_400_BAD_REQUEST)

        if bundle:
            counting_ads.delay(bundle.pk)  # Вызов функции для постановки задач в очередь
            return Response({"id": bundle.pk}, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': 'An error occurred when creating a bundle'}, status=status.HTTP_400_BAD_REQUEST)


class StatApiView(APIView):
    """
    API метод отображает количество объявлений по заданному запросу.
    Принимает на вход id связки (поисковая фраза + регион и интервал), за который нужно вывести счётчики.
    Возвращает количество объявлений и соответствующие им временные метки (timestamp).
    Частота опроса = 1 раз в час  для каждого id
    URL: /counter/stat/?id=<id>&start_time=<start_time>&end_time=<end_time>
    Пример GET запроса: /counter/stat/?id=1&start_time=2024-01-01&end_time=2024-01-01
    """
    def get(self, request: Request) -> Response:
        pk = request.query_params.get('id')

        if not pk:
            return Response({'error': 'ID field is required'}, status=status.HTTP_400_BAD_REQUEST)

        start_time = request.query_params.get('start_time')
        end_time = request.query_params.get('end_time')

        if not start_time:
            return Response({'error': 'Start time field is required'}, status=status.HTTP_400_BAD_REQUEST)

        if not end_time:
            end_time = timezone.now()

        try:
            start_time = timezone.datetime.fromisoformat(start_time)
        except ValueError:
            return Response({'error': 'Invalid start_time format. Expected format: YYYY-MM-DD'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            end_time = timezone.datetime.fromisoformat(str(end_time))
        except ValueError:
            return Response({'error': 'Invalid end_time format. Expected format: YYYY-MM-DD'},
                            status=status.HTTP_400_BAD_REQUEST)

        queryset = Counter.objects.filter(bundle=pk, date__range=(start_time, end_time))
        serializer = CounterSerializer(queryset, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class TopApiView(APIView):
    """
    API метод отображает топ-5 объявлений о продаже квартиры в регионе.
    Принимает на вход id связки (поисковая фраза + регион).
    Возвращает оп-5 объявлений.
    Частота опроса = 1 раз в час  для каждого id
    URL: /counter/top/?id=<id>
    Пример GET запроса: /counter/top/?id=1
    """
    def get(self, request: Request) -> Response:
        pk = request.query_params.get('id')

        if not pk:
            return Response({'error': 'ID field is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not Bundle.objects.filter(id=pk).exists():
            return Response({'error': f'Bundle {pk} does not exist'}, status=status.HTTP_400_BAD_REQUEST)

        queryset = Ad.objects.filter(bundle=pk)
        serializer = AdSerializer(queryset, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
