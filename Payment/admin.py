from django.contrib import admin
from Payment.models import PaymentProfile, PaymentItem, PaymentLog, PaymentSlot, PaymentGroups

# Register your models here.
admin.site.register(PaymentProfile)
admin.site.register(PaymentItem)
admin.site.register(PaymentLog)
admin.site.register(PaymentSlot)
admin.site.register(PaymentGroups)

