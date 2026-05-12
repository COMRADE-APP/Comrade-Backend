with open('Payment/serializers.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines before: {len(lines)}")

# Remove the corrupted block: lines 1372-1566 (0-indexed: 1371-1565)
# Keep lines 1-1371, skip 1372-1566, keep 1567 onwards
new_lines = lines[:1371] + lines[1566:]

with open('Payment/serializers.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Total lines after: {len(new_lines)}")
print("Removed corrupted duplicate block (lines 1372-1566)")
