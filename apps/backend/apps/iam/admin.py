from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.iam.models import Organization, User


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "stir_inn", "role", "kyb_status", "region", "is_active", "created_at")
    list_filter = ("role", "kyb_status", "region", "is_active")
    search_fields = ("name", "legal_name", "stir_inn")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "phone", "organization", "role", "is_2fa_enabled", "is_active")
    list_filter = ("role", "is_2fa_enabled", "is_active")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("DBazar Profile", {"fields": ("organization", "phone", "role", "is_2fa_enabled", "two_fa_secret")}),
    )
