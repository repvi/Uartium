#!/usr/bin/env python3
import sys
import time
sys.path.insert(0, 'C:\\Users\\alexr\\Uartium')

from uartium.serial_backend import SerialBackend
import json

test_cases = [
    '[INFO] :m="Sample 1" a:u=42 b:i=-7 c:f=? s:s="hello"',
]

for line in test_cases:
    msg = SerialBackend._parse_line(line)
    print(f"Input: {line}")
    print(f"Output:")
    print(f"  level: {msg.get('level')}")
    print(f"  text: '{msg.get('text')}'")
    print(f"  data_fields: {msg.get('data_fields', {})}")
    print()
