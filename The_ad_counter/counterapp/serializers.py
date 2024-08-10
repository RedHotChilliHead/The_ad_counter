from rest_framework import serializers
from counterapp.models import Counter, Ad


class CounterSerializer(serializers.ModelSerializer):
    """
    Сериализатор счетчиков объявлений
    """

    class Meta:
        model = Counter
        fields = ['id', 'count', 'date']


class AdSerializer(serializers.ModelSerializer):
    """
    Сериализатор топ-5 объявлений
    """

    class Meta:
        model = Ad
        fields = ['top', 'link']
