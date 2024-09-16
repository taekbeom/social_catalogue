"""
URL configuration for social_catalogue project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_view
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
# from users_app.forms import CustomPasswordResetForm

from users_app import views as users_views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('signup/', users_views.signup, name='signup'),
    path('login/', users_views.login, name='login'),
    path('logout/', users_views.logout, name='logout'),
    path('activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/',
         users_views.activate_account, name='activate'),
    path('delete-user/', users_views.delete_user_view, name='delete_user'),
    # path('password-reset/', auth_view.PasswordResetView.as_view(template_name='users/passwordreset.html',
    #     form_class=CustomPasswordResetForm),
    #      name='password_reset'),
    path('password-reset/', auth_view.PasswordResetView.as_view(template_name='users/passwordreset.html'),
         name='password_reset'),
    path('password-reset/done/', auth_view.PasswordResetDoneView.as_view(template_name='users/passwordresetdone.html'),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_view.PasswordResetConfirmView.as_view(
        template_name='users/passwordresetconfirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_view.PasswordResetCompleteView.as_view(
        template_name='users/passwordresetcomplete.html'), name='password_reset_complete'),
    path('', include('catalogue_app.urls')),
    path('profile/<str:profile_id>/', include('profile_app.urls')),

    path('signup', RedirectView.as_view(pattern_name='signup', permanent=True)),
    path('login', RedirectView.as_view(pattern_name='login', permanent=True)),
    path('logout', RedirectView.as_view(pattern_name='logout', permanent=True)),
    path('profile/<str:profile_id>', RedirectView.as_view(pattern_name='app_profile', permanent=True)),
]

handler400 = 'catalogue_app.views.handle_400'
handler403 = 'catalogue_app.views.handle_403'
handler404 = 'catalogue_app.views.handle_404'
handler500 = 'catalogue_app.views.handle_500'
handler503 = 'catalogue_app.views.handle_503'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
