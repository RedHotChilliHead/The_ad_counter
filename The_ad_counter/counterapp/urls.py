from django.urls import path

from .views import AddApiView, StatApiView, TopApiView

app_name = "counterapp"

urlpatterns = [
    path('add/', AddApiView.as_view(), name='add'),
    path('stat/', StatApiView.as_view(), name='statistics'),
    path('top/', TopApiView.as_view(), name='top'),
]