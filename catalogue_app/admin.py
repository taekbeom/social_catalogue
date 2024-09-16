from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from catalogue_app.models import User
from users_app.forms import CustomUserCreationForm


class UserAdmin(BaseUserAdmin):
    model = User
    add_form = CustomUserCreationForm
    list_display = ("username", "email", "is_staff", "is_active",)
    list_filter = ("username", "email", "is_staff", "is_active",)
    search_fields = ("email",)
    ordering = ("email",)


admin.site.register(User, UserAdmin)
