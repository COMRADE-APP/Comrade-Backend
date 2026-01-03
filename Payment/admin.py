from django.contrib import admin
from Payment.models import (
    PaymentProfile, TransactionToken, PaymentGroups, GroupMembers,
    Contribution, StandingOrder, GroupInvitation, GroupTarget,
    Product, UserSubscription, PaymentItem, PaymentLog,
    PaymentAuthorization, PaymentVerification, TransactionHistory,
    TransactionTracker
)


@admin.register(PaymentProfile)
class PaymentProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'comrade_balance', 'total_sent', 'total_received', 'default_payment_method', 'created_at']
    list_filter = ['default_payment_method', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Balance & Totals', {
            'fields': ('comrade_balance', 'total_sent', 'total_received')
        }),
        ('Payment Methods', {
            'fields': ('payment_methods', 'default_payment_method')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(TransactionToken)
class TransactionTokenAdmin(admin.ModelAdmin):
    list_display = ['token_display', 'sender', 'receiver', 'amount', 'transaction_type', 'status', 'created_at']
    list_filter = ['status', 'transaction_type', 'payment_method', 'created_at']
    search_fields = ['token', 'sender__email', 'receiver__email', 'description']
    readonly_fields = ['token', 'created_at', 'updated_at', 'token_display']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Transaction Details', {
            'fields': ('token', 'token_display', 'sender', 'receiver', 'amount', 'transaction_type', 'description')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'external_payment_provider', 'status', 'authorization_code')
        }),
        ('Metadata', {
            'fields': ('metadata', 'verification_date'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(PaymentGroups)
class PaymentGroupsAdmin(admin.ModelAdmin):
    list_display = ['name', 'admin', 'group_type', 'current_amount', 'target_amount', 'is_active', 'created_at']
    list_filter = ['group_type', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'admin__email']
    readonly_fields = ['current_amount', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Group Information', {
            'fields': ('name', 'description', 'admin', 'group_type')
        }),
        ('Financial Details', {
            'fields': ('target_amount', 'current_amount', 'currency')
        }),
        ('Settings', {
            'fields': ('deadline', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(GroupMembers)
class GroupMembersAdmin(admin.ModelAdmin):
    list_display = ['user', 'group', 'role', 'total_contributed', 'joined_at']
    list_filter = ['role', 'joined_at']
    search_fields = ['user__email', 'group__name']
    readonly_fields = ['total_contributed', 'joined_at']
    date_hierarchy = 'joined_at'


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = ['member', 'group', 'amount', 'contribution_date']
    list_filter = ['contribution_date']
    search_fields = ['member__email', 'group__name']
    readonly_fields = ['contribution_date']
    date_hierarchy = 'contribution_date'


@admin.register(StandingOrder)
class StandingOrderAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'frequency', 'payment_method', 'next_execution', 'is_active']
    list_filter = ['frequency', 'payment_method', 'is_active', 'created_at']
    search_fields = ['user__email', 'recipient__email', 'description']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'next_execution'


@admin.register(GroupInvitation)
class GroupInvitationAdmin(admin.ModelAdmin):
    list_display = ['invitee_email', 'group', 'inviter', 'status', 'expires_at', 'created_at']
    list_filter = ['status', 'created_at', 'expires_at']
    search_fields = ['invitee_email', 'group__name', 'inviter__email']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(GroupTarget)
class GroupTargetAdmin(admin.ModelAdmin):
    list_display = ['name', 'group', 'current_amount', 'target_amount', 'progress_percentage', 'is_achieved', 'target_date']
    list_filter = ['is_achieved', 'created_at']
    search_fields = ['name', 'group__name', 'description']
    readonly_fields = ['current_amount', 'is_achieved', 'created_at', 'updated_at', 'progress_percentage']
    date_hierarchy = 'created_at'
    
    def progress_percentage(self, obj):
        return f"{obj.progress_percentage}%"
    progress_percentage.short_description = 'Progress'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'category', 'stock_quantity', 'is_available', 'created_at']
    list_filter = ['category', 'is_available', 'created_at']
    search_fields = ['name', 'description', 'category']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'description', 'category', 'image')
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'stock_quantity', 'is_available')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'subscription_type', 'status', 'start_date', 'end_date', 'auto_renew']
    list_filter = ['subscription_type', 'status', 'auto_renew', 'created_at']
    search_fields = ['user__email']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Subscription Details', {
            'fields': ('user', 'subscription_type', 'status')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date', 'auto_renew')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(PaymentItem)
class PaymentItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'currency', 'is_active']
    list_filter = ['is_active', 'currency']
    search_fields = ['name', 'description']


# Register remaining models with basic admin
admin.site.register(PaymentLog)
admin.site.register(PaymentAuthorization)
admin.site.register(PaymentVerification)
admin.site.register(TransactionHistory)
admin.site.register(TransactionTracker)
