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
        "timestamp": float,      # time.time() value
        "level":     str,        # "EVENT", "ERROR", "WARNING", "INFO", "DEBUG"
        "text":      str,        # the raw line / payload
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
    DATA_TYPE = {"EVENT", "ERROR", "WARNING", "INFO", "DEBUG"}
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
    def _parse_line(line: str) -> dict:
        """
        Very simple parser: if the line starts with a known level tag
        (e.g.  "[ERROR] something happened") we extract it, otherwise
        default to INFO.
        """
        level = "INFO"
        text = line
        for tag in SerialBackend.DATA_TYPE:
            prefixes = (f"[{tag}]", f"{tag}:", f"{tag} ")
            for p in prefixes:
                if line.upper().startswith(p):
                    level = tag.replace("WARN", "WARNING")
                    text = line[len(p):].strip()
                    break
        return {
            "timestamp": time.time(),
            "level": level,
            "text": text,
        }


# ---------------------------------------------------------------------------
# Demo / mock backend  (no hardware required)
# ---------------------------------------------------------------------------
_DEMO_MESSAGES = [
    ("EVENT",   "Sensor initialized successfully"),
    ("INFO",    "Reading temperature: 23.4 °C"),
    ("INFO",    "Reading humidity: 61 %"),
    ("WARNING", "Battery voltage low: 3.21 V"),
    ("EVENT",   "Button press detected"),
    ("DEBUG",   "ADC sample buffer flushed"),
    ("ERROR",   "CRC mismatch on packet #1042"),
    ("INFO",    "Uptime: 00:42:17"),
    ("EVENT",   "Motion detected on PIR sensor"),
    ("INFO",    "RSSI: -67 dBm"),
    ("WARNING", "Temperature above threshold: 38.1 °C"),
    ("ERROR",   "I2C NACK from address 0x48"),
    ("DEBUG",   "Entering low-power mode"),
    ("EVENT",   "Wake-up from deep sleep"),
    ("INFO",    "GPS fix acquired: 40.7128 N, 74.0060 W"),
    ("WARNING", "Flash write near sector limit"),
    ("EVENT",   "OTA update started"),
    ("ERROR",   "Timeout waiting for ACK"),
    ("INFO",    "Packet TX count: 8571"),
    ("DEBUG",   "Heap free: 34816 bytes"),
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
            level, text = random.choice(_DEMO_MESSAGES)
            self._queue.append({
                "timestamp": time.time(),
                "level": level,
                "text": text,
            })
            jitter = random.uniform(self.interval * 0.3, self.interval * 1.7)
            time.sleep(jitter)
