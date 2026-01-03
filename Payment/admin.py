from django.contrib import admin
from Payment.models import (
    PaymentProfile, PaymentItem, PaymentLog, PaymentGroups,
    TransactionToken, PaymentAuthorization, PaymentVerification,
    TransactionHistory, TransactionTracker, PaymentGroupMember,
    Contribution, StandingOrder, GroupInvitation, GroupTarget,
    Product, UserSubscription, IndividualShare
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

