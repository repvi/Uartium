#!/usr/bin/env python3
from uartium.serial_backend import SerialBackend
import json

test_cases = [
    '[INFO] :t=232 :m"this is a message" var:i=123',
    '[WARNING] :m"Low battery" voltage:f=3.2 :t=500',
    '[ERROR] :t=9999 :m"Connection failed" error:i=-1 code:s=TIMEOUT',
    '[DEBUG] :m"Memory check" heap:u=45328 fragmented:f=12.5 :t=2000',
]

for line in test_cases:
    msg = SerialBackend._parse_line(line)
    print(f"Input: {line}")
    print(f"Output: {json.dumps(msg, indent=2, default=str)}")
    print()
