
import os

file_path = r'C:\Users\Imani\Documents\Comrade\Comrade-Backend\Payment\serializers.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix PaymentGroupMemberSerializer methods to be safe
content = content.replace(
    "    def get_user_email(self, obj):\n        if obj.is_anonymous:\n            return None\n        return obj.payment_profile.user.user.email",
    "    def get_user_email(self, obj):\n        if obj.is_anonymous or not obj.payment_profile or not obj.payment_profile.user or not obj.payment_profile.user.user:\n            return None\n        return obj.payment_profile.user.user.email"
)

content = content.replace(
    "    def get_user_name(self, obj):\n        if obj.is_anonymous:\n            return obj.anonymous_alias or 'Anonymous Member'\n        return f\"{obj.payment_profile.user.user.first_name} {obj.payment_profile.user.user.last_name}\"",
    "    def get_user_name(self, obj):\n        if obj.is_anonymous:\n            return obj.anonymous_alias or 'Anonymous Member'\n        if obj.payment_profile and obj.payment_profile.user and obj.payment_profile.user.user:\n            return f\"{obj.payment_profile.user.user.first_name} {obj.payment_profile.user.user.last_name}\"\n        return \"Unknown Member\""
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("PaymentGroupMemberSerializer methods fixed!")
