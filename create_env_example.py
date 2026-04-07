with open('.env', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('.env.example', 'w', encoding='utf-8') as f:
    for line in lines:
        if '=' in line and not line.strip().startswith('#'):
            key = line.split('=')[0]
            f.write(f"{key}=\n")
        else:
            f.write(line)

print('Generated .env.example')
