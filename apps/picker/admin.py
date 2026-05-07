"""Picker app admin registration."""
from django.contrib import admin
from .models import PickerProfile, PickerTask, PickerTaskItem, Hub


@admin.register(PickerProfile)
class PickerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'hub_name', 'is_active', 'created_at')
    list_filter = ('is_active', 'hub_name')
    search_fields = ('user__username', 'hub_name')

admin.site.register(Hub)


class PickerTaskItemInline(admin.TabularInline):
    model = PickerTaskItem
    extra = 0
    readonly_fields = ('id',)


@admin.register(PickerTask)
class PickerTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'picker', 'status', 'priority', 'created_at')
    list_filter = ('status', 'priority')
    search_fields = ('order__tracking_id', 'picker__username')
    inlines = [PickerTaskItemInline]
    readonly_fields = ('id',)
