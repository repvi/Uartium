"""
Uartium - PySerial Backend Module
==================================

Provides a simple serial connection wrapper and a mock/demo serial source
for testing without real hardware.

USAGE WITH REAL HARDWARE
------------------------
    from uartium.serial_backend import SerialBackend

    backend = SerialBackend(port="COM3", baudrate=115200)
    backend.start()
    while True:
        msg = backend.read_message()  # blocks briefly then returns None or a dict
        if msg:
            print(msg)
    backend.stop()

USAGE WITH DEMO / MOCK DATA
----------------------------
    from uartium.serial_backend import DemoSerialBackend

    backend = DemoSerialBackend(interval=0.8)   # fake message every 0.8s
    backend.start()
    msg = backend.read_message()
    backend.stop()

Message dict format returned by read_message():
    {
        "timestamp": float,           # time.time() value
        "level":     str,             # "EVENT", "ERROR", "WARNING", "INFO", "DEBUG"
        "text":      str,             # the message text (or extracted from :m"...")
        "device_timestamp": int,      # optional: device timestamp from :t=...
        "data_fields": dict,          # optional: structured variables from varName:type=value
    }
"""

from __future__ import annotations

import random
import threading
import time
from collections import deque
from typing import Optional

import serial  # pyserial


# ---------------------------------------------------------------------------
# Real serial backend
# ---------------------------------------------------------------------------
class SerialBackend:
    DATA_TYPE = {"ERROR", "WARNING", "INFO", "DEBUG"}
    """Thin wrapper around pyserial that reads lines in a background thread."""

    def __init__(self, port: str = "COM3", baudrate: int = 115200, timeout: float = 0.1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._ser: Optional[serial.Serial] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._queue: deque[dict] = deque(maxlen=5000)

    # -- public API ----------------------------------------------------------
    def start(self) -> None:
        """Open the serial port and start the reader thread."""
        if self._running:
            return
        self._ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        self._running = True
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the reader thread and close the port."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        if self._ser and self._ser.is_open:
            self._ser.close()
            self._ser = None

    def read_message(self) -> Optional[dict]:
        """Return the oldest queued message or None."""
        try:
            return self._queue.popleft()
        except IndexError:
            return None

    @property
    def is_running(self) -> bool:
        return self._running

    # -- internals -----------------------------------------------------------
    def _reader_loop(self) -> None:
        while self._running:
            try:
                raw = self._ser.readline()
                if raw:
                    line = raw.decode("utf-8", errors="replace").strip()
                    self._queue.append(self._parse_line(line))
            except serial.SerialException:
                self._queue.append({
                    "timestamp": time.time(),
                    "level": "ERROR",
                    "text": "Serial connection lost",
                })
                self._running = False
            except Exception as exc:
                self._queue.append({
                    "timestamp": time.time(),
                    "level": "ERROR",
                    "text": f"Reader error: {exc}",
                })

    @staticmethod
    def _parse_data_fields(text: str) -> dict:
        """
        Parse structured data fields from text.

        Format:  varName=value  or  varName:type=value
        Also handles :t=value for timestamps and :m"..." for message text
        (those should be extracted before calling this).
        
        Supported type suffixes:
            :u  — unsigned int
            :i  — signed int
            :s  — string
            :f  — float
            :t  — timestamp (uint32)
            :m  — message (string)
        No suffix defaults to string.

        Returns a dict  { varName: {"value": <converted>, "type": <suffix>} }
        """
        TYPE_MAP = {
            "u": "uint",
            "i": "int",
            "s": "str",
            "f": "float",
            "t": "timestamp",
            "m": "message",
        }
        fields: dict[str, dict] = {}
        for token in text.split():
            if "=" not in token:
                continue
            name_part, _, raw_value = token.partition("=")
            # separate optional type suffix  (e.g. "varName:u")
            if ":" in name_part:
                var_name, _, type_char = name_part.rpartition(":")
                type_label = TYPE_MAP.get(type_char, "str")
            else:
                var_name = name_part
                type_char = None
                type_label = "str"

            # attempt conversion
            converted = raw_value
            try:
                if type_label in ("uint", "timestamp"):
                    converted = abs(int(raw_value)) & 0xFFFFFFFF  # uint32_t
                elif type_label == "int":
                    converted = int(raw_value)
                elif type_label == "float":
                    converted = float(raw_value)
                # else stays as string
            except (ValueError, TypeError):
                pass  # keep as raw string on conversion failure

            fields[var_name] = {"value": converted, "type": type_label}
        return fields

    @staticmethod

    @staticmethod
    def _extract_message_field(text: str):
        """
        Extract :m\"...\" message field from text.
        Returns (message_text, remaining_text) if found,
        or (None, original_text) otherwise.
        """
        import re
        # Match :m"..." (greedy to capture everything in quotes)
        match = re.search(r':m"([^"]*)"', text)
        if match:
            message = match.group(1)
            remaining = text[:match.start()] + text[match.end():]
            return message, remaining.strip()
        return None, text

    @staticmethod
    def _extract_timestamp_field(text: str):
        """
        Scan tokens in *text* for a  :t=<number>  field.
        Returns (device_timestamp_uint32, remaining_text) if found,
        or (None, original_text) otherwise.
        """
        tokens = text.split()
        remaining = []
        device_ts = None
        for token in tokens:
            if "=" in token:
                name_part, _, raw_value = token.partition("=")
                if ":" in name_part:
                    _, _, type_char = name_part.rpartition(":")
                    if type_char == "t" and device_ts is None:
                        try:
                            device_ts = abs(int(raw_value)) & 0xFFFFFFFF
                        except (ValueError, TypeError):
                            remaining.append(token)
                        continue
            remaining.append(token)
        return device_ts, " ".join(remaining)

    @staticmethod
    def _parse_line(line: str) -> dict:
        """
        Very simple parser: if the line starts with a known level tag
        (e.g.  "[ERROR] something happened") we extract it, otherwise
        default to INFO.

        Any message may contain a  :t=<number>  field which is extracted
        as a uint32 device timestamp, :m"..." for message text,
        and varName:type=value for typed variables.
        """
        level = "INFO"
        text = line
        for tag in SerialBackend.DATA_TYPE:
            prefixes = (f"[{tag}]", f"{tag}:", f"{tag} ")
            for p in prefixes:
                if line.upper().startswith(p):
                    level = tag if tag != "WARN" else "WARNING"
                    text = line[len(p):].strip()
                    break

        # extract optional message field  (:m="...")
        message_text, text = SerialBackend._extract_message_field(text)
        
        # extract optional device timestamp  (:t=<value>)
        device_ts, text = SerialBackend._extract_timestamp_field(text)

        msg = {
            "timestamp": time.time(),
            "level": level,
            "text": message_text if message_text else text,
        }

        if device_ts is not None:
            msg["device_timestamp"] = device_ts

        # Parse any remaining variables from text
        data_fields = SerialBackend._parse_data_fields(text)
        if data_fields:
            msg["data_fields"] = data_fields

        return msg


# ---------------------------------------------------------------------------
# Demo / mock backend  (no hardware required)
# ---------------------------------------------------------------------------
_DEMO_MESSAGES = [
    ("INFO",    "Reading temperature: 23.4 °C"),
    ("INFO",    "Reading humidity: 61 %"),
    ("WARNING", "Battery voltage low: 3.21 V"),
    ("DEBUG",   "ADC sample buffer flushed"),
    ("ERROR",   "CRC mismatch on packet #1042"),
    ("INFO",    "Uptime: 00:42:17"),
    ("INFO",    "RSSI: -67 dBm"),
    ("WARNING", "Temperature above threshold: 38.1 °C"),
    ("ERROR",   "I2C NACK from address 0x48"),
    ("DEBUG",   "Entering low-power mode"),
    ("INFO",    "GPS fix acquired: 40.7128 N, 74.0060 W"),
    ("WARNING", "Flash write near sector limit"),
    ("ERROR",   "Timeout waiting for ACK"),
    ("INFO",    "Packet TX count: 8571"),
    ("DEBUG",   "Heap free: 34816 bytes"),
]

_DEMO_STRUCTURED_MSG_TEMPLATES = [
    ('INFO', ':m"Temperature reading" temp:f={temp:.1f} :t={ts}'),
    ('WARNING', ':m"High temperature alert" temp:f={temp:.1f} threshold:f={thresh:.1f} :t={ts}'),
    ('ERROR', ':m"Connection lost" error:i={err} retries:u={retry} :t={ts}'),
    ('INFO', ':m"Voltage check" voltage:f={volt:.2f} current:f={cur:.2f} :t={ts}'),
    ('INFO', ':m"Sensor readings" temp:f={temp:.1f} humidity:f={hum:.1f} pressure:f={pres:.1f} altitude:f={alt:.1f} :t={ts}'),
    ('INFO', ':m"Power status" voltage:f={volt:.2f} current:f={cur:.2f} power:f={pwr:.2f} battery:u={bat} charging:u={chg} :t={ts}'),
    ('WARNING', ':m"System diagnostics" cpu:u={cpu} memory:u={mem} disk:u={disk} temp:f={temp:.1f} uptime:u={up} :t={ts}'),
    ('DEBUG', ':m"Motor telemetry" rpm:u={rpm} current:f={cur:.2f} voltage:f={volt:.1f} temp:f={temp:.1f} torque:f={torq:.2f} efficiency:f={eff:.1f} :t={ts}'),
]


class DemoSerialBackend:
    """
    Drop-in replacement for SerialBackend that generates fake UART-style
    messages so you can test the GUI without any hardware attached.
    """

    def __init__(self, interval: float = 0.6):
        self.interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._queue: deque[dict] = deque(maxlen=5000)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._producer, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def read_message(self) -> Optional[dict]:
        try:
            return self._queue.popleft()
        except IndexError:
            return None

    @property
    def is_running(self) -> bool:
        return self._running

    def _producer(self) -> None:
        while self._running:
            choice = random.random()
            # ~40% structured messages with :m and variables
            if choice < 0.4:
                level, template = random.choice(_DEMO_STRUCTURED_MSG_TEMPLATES)
                raw_data = template.format(
                    temp=random.uniform(18, 45),
                    hum=random.uniform(30, 90),
                    pres=random.uniform(990, 1030),
                    alt=random.uniform(0, 500),
                    thresh=random.uniform(35, 45),
                    err=random.randint(-10, 0),
                    retry=random.randint(1, 5),
                    btn=random.randint(1, 4),
                    cnt=random.randint(1, 20),
                    volt=random.uniform(4.0, 5.5),
                    cur=random.uniform(0.1, 2.0),
                    pwr=random.uniform(0.5, 10.0),
                    bat=random.randint(0, 100),
                    chg=random.randint(0, 1),
                    cpu=random.randint(10, 95),
                    mem=random.randint(30, 85),
                    disk=random.randint(20, 90),
                    up=random.randint(100, 99999),
                    rpm=random.randint(0, 8000),
                    torq=random.uniform(0, 5.0),
                    eff=random.uniform(75, 98),
                    ts=random.randint(1000, 9999),
                )
                line = f"[{level}] {raw_data}"
                self._queue.append(SerialBackend._parse_line(line))
            # ~60% simple messages
            else:
                level, text = random.choice(_DEMO_MESSAGES)
                self._queue.append({
                    "timestamp": time.time(),
                    "level": level,
                    "text": text,
                })
            jitter = random.uniform(self.interval * 0.3, self.interval * 1.7)
            time.sleep(jitter)
