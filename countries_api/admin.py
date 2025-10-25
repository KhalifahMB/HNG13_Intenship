from django.contrib import admin
from .models import Country, RefreshMetadata


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    """
    Admin configuration for Country model
    """
    list_display = [
        'name',
        'capital',
        'region',
        'population',
        'currency_code',
        'exchange_rate',
        'estimated_gdp',
        'last_refreshed_at'
    ]
    list_filter = ['region', 'currency_code', 'last_refreshed_at']
    search_fields = ['name', 'capital', 'region', 'currency_code']
    ordering = ['-last_refreshed_at', 'name']
    readonly_fields = ['created_at', 'updated_at', 'last_refreshed_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'capital', 'region', 'population', 'flag_url')
        }),
        ('Currency & Economics', {
            'fields': ('currency_code', 'exchange_rate', 'estimated_gdp')
        }),
        ('Metadata', {
            'fields': ('last_refreshed_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RefreshMetadata)
class RefreshMetadataAdmin(admin.ModelAdmin):
    """
    Admin configuration for RefreshMetadata model
    """
    list_display = [
        'total_countries',
        'last_refreshed_at',
        'refresh_status',
        'created_at'
    ]
    list_filter = ['refresh_status', 'last_refreshed_at']
    ordering = ['-last_refreshed_at']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Refresh Information', {
            'fields': ('total_countries', 'last_refreshed_at', 'refresh_status')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
