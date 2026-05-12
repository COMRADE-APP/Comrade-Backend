
import os

file_path = r'C:\Users\Imani\Documents\Comrade\Comrade-Backend\Payment\serializers.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "def get_member_count(self, obj):" in line:
        new_lines.append("    def get_creator_name(self, obj):\n")
        new_lines.append("        if obj.creator and obj.creator.user and obj.creator.user.user:\n")
        new_lines.append("            return f\"{obj.creator.user.user.first_name} {obj.creator.user.user.last_name}\"\n")
        new_lines.append("        return \"Unknown\"\n\n")
    new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Serializer fixed successfully!")
