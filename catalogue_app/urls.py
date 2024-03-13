from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='app_home'),
    path('profile/', views.profile, name='app_profile'),
    path('catalogue/', views.catalogue, name='app_catalogue'),
    path('login/', views.login, name='app_login'),
    path('signup/', views.signup, name='app_signup'),
]
