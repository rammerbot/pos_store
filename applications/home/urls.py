from django.urls import path

from .views import *

app_name = 'home'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('login/', NewLoginView.as_view(), name='login'),
    path('logout/', NewLogoutView.as_view(), name='logout'),

]