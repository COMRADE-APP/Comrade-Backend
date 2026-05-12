
import os

file_path = r'C:\Users\Imani\Documents\Comrade\Comrade-Backend\Payment\views.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

header = "import math\n"
if "import math" not in content:
    content = header + content

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Math import added successfully!")
