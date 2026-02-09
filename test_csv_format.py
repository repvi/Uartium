#!/usr/bin/env python3
from uartium.serial_backend import SerialBackend

# Test cases with increasing number of variables
test_cases = [
    '[INFO] :m"Temperature reading" temp:f=23.5 :t=1234',
    '[INFO] :m"Voltage check" voltage:f=4.78 current:f=1.13 :t=5903',
    '[INFO] :m"Sensor readings" temp:f=25.3 humidity:f=65.2 pressure:f=1013.2 altitude:f=152.5 :t=7890',
]

print("CSV Format Examples:\n")
print("timestamp,event,message,key,value")
print("=" * 80)

for line in test_cases:
    msg = SerialBackend._parse_line(line)
    
    # Simulate CSV row construction
    ts = msg.get('device_timestamp', int(msg['timestamp']))
    level = msg['level']
    message = msg.get('text', '')
    
    if 'data_fields' in msg and msg['data_fields']:
        for var_name, var_info in msg['data_fields'].items():
            print(f"{ts},{level},{message},{var_name},{var_info['value']}")
    else:
        print(f"{ts},{level},{message},,")

