from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path('', views.profile, name='app_profile'),
    path('edit/', views.edit_profile, name='app_edit_profile'),
    path('chat/', views.chat, name='app_chat'),
    path('feed/', views.feed, name='app_feed'),
    path('friend-list/', views.friend_list, name='app_friend_list'),
    path('history/', views.history, name='app_history'),
    path('notifications/', views.notifications, name='app_notifications'),
    path('catalogue_lists/', views.catalogue_lists, name='app_lists'),
    path('check_friends/<int:user1>/<int:user2>/', views.check_friends, name='app_check_friends'),
    path('check_star/<int:user1>/<int:user2>/', views.check_star, name='app_check_star'),
    path('check_block/<int:user1>/<int:user2>/', views.check_block, name='app_check_block'),
    path('delete-post/', views.delete_post, name='app_delete_post'),
    path('edit-post/', views.upload_post, name='app_edit_post'),
    path('add-mark/', views.add_mark, name='app_add_mark'),
    path('delete-mark/', views.delete_mark, name='app_delete_mark'),
    path('mark_notifications_as_read/', views.mark_notifications_as_read, name='app_notification_read'),

    path('edit', RedirectView.as_view(pattern_name='app_edit_profile', permanent=True)),
    path('chat', RedirectView.as_view(pattern_name='app_chat', permanent=True)),
    path('feed', RedirectView.as_view(pattern_name='app_feed', permanent=True)),
    path('friend-list', RedirectView.as_view(pattern_name='app_friend_list', permanent=True)),
    path('history', RedirectView.as_view(pattern_name='app_history', permanent=True)),
    path('notifications', RedirectView.as_view(pattern_name='app_notifications', permanent=True)),
    path('catalogue_lists', RedirectView.as_view(pattern_name='app_lists', permanent=True)),
    path('check_friends/<int:user1>/<int:user2>',
         RedirectView.as_view(pattern_name='app_check_friends', permanent=True)),
    path('check_star/<int:user1>/<int:user2>',
         RedirectView.as_view(pattern_name='app_check_star', permanent=True)),
    path('check_block/<int:user1>/<int:user2>',
         RedirectView.as_view(pattern_name='app_check_block', permanent=True)),
]
