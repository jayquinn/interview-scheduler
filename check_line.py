#!/usr/bin/env python3

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    
print("=== 1450-1490번째 줄 ===")
for i in range(1449, 1490):
    stripped = lines[i].rstrip()
    if stripped:  # 빈 줄이 아닌 경우만 출력
        print(f"{i+1:4d}: {stripped}") 