from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path('', views.home, name='app_home'),
    path('news/<str:news_id>/', views.display_news, name='app_news'),
    path('add/', views.add_news, name='app_add_news'),
    path('news/<str:news_id>/edit/', views.edit_news, name='app_edit_news'),
    path('catalogue/', views.catalogue, name='app_catalogue'),
    path('catalogue/<str:entry_id>/', views.display_entry, name='app_entry'),
    path('catalogue/<str:entry_id>/update-mark/', views.update_mark, name='app_update_mark'),
    path('catalogue/<str:entry_id>/update-rate/', views.update_rate, name='app_update_rate'),
    path('catalogue/<str:entry_id>/update-additional/', views.update_additional_mark, name='app_update_additional_mark'),
    path('add-entry/', views.add_entry, name='app_add_entry'),
    path('catalogue/<str:entry_id>/edit-entry/', views.edit_entry, name='app_edit_entry'),
    path('hide-recs/', views.hide_recs, name='app_hide_recs'),
    path('catalogue/<str:entry_id>/delete-review/', views.delete_review, name='app_delete_review'),

    path('news/<str:news_id>', RedirectView.as_view(pattern_name='app_news', permanent=True)),
    path('catalogue', RedirectView.as_view(pattern_name='app_catalogue', permanent=True)),
    path('catalogue/<str:entry_id>', RedirectView.as_view(pattern_name='app_entry', permanent=True)),
    path('add', RedirectView.as_view(pattern_name='app_add_news', permanent=True)),
    path('add-entry', RedirectView.as_view(pattern_name='app_add_entry', permanent=True)),
    path('news/<str:news_id>/edit', RedirectView.as_view(pattern_name='app_edit_news', permanent=True)),
]
