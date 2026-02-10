#!/usr/bin/env python3
import re

def _extract_message_field(text: str):
    """Extract :m\"...\" message field from text."""
    # Match :m"..." with support for escaped quotes (\")
    match = re.search(r':m"((?:[^"\\]|\\.)*)"', text)
    if match:
        message = match.group(1)
        # Unescape any escaped quotes in the message
        message = message.replace(r'\"', '"').replace(r'\\', '\\')
        remaining = text[:match.start()] + text[match.end():]
        return message, remaining.strip()
    return None, text

# Test cases
test_lines = [
    ':m"Temperature reading" temp:f=23.5 :t=1234',
    ':m"Sample 1" a:u=42 b:i=-7',
    'temp:f=23.5 :t=1234',  # no :m
]

for line in test_lines:
    msg, remaining = _extract_message_field(line)
    print(f"Input:     {line}")
    print(f"Message:   {msg}")
    print(f"Remaining: {remaining}")
    print()
