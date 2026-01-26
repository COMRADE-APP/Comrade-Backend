from django.contrib import admin
from Payment.models import (
    PaymentProfile, PaymentItem, PaymentLog, PaymentGroups,
    TransactionToken, PaymentAuthorization, PaymentVerification,
    TransactionHistory, TransactionTracker, PaymentGroupMember,
    Contribution, StandingOrder, GroupInvitation, GroupTarget,
    Product, UserSubscription, IndividualShare, Partner, PartnerApplication
)

admin.site.register(PaymentProfile)
admin.site.register(PaymentItem)
admin.site.register(PaymentLog)
admin.site.register(PaymentGroups)
admin.site.register(TransactionToken)
admin.site.register(PaymentAuthorization)
admin.site.register(PaymentVerification)
admin.site.register(TransactionHistory)
admin.site.register(TransactionTracker)
admin.site.register(PaymentGroupMember)
admin.site.register(Contribution)
admin.site.register(StandingOrder)
admin.site.register(GroupInvitation)
admin.site.register(GroupTarget)
admin.site.register(Product)
admin.site.register(UserSubscription)
admin.site.register(IndividualShare)


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'partner_type', 'status', 'verified', 'commission_rate', 'created_at']
    list_filter = ['partner_type', 'status', 'verified']
    search_fields = ['business_name', 'contact_email', 'user__user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(PartnerApplication)
class PartnerApplicationAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'partner_type', 'status', 'applicant', 'created_at']
    list_filter = ['partner_type', 'status']
    search_fields = ['business_name', 'contact_email', 'applicant__user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
