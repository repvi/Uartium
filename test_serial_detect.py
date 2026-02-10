#!/usr/bin/env python3
"""
Simple serial detection and listener.

This script enumerates serial ports using pyserial and can optionally
open a port and print incoming data in a loop.
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Iterable, Optional

from serial.tools import list_ports
import serial


def _matches_vid_pid(port_info, vid: Optional[int], pid: Optional[int]) -> bool:
    if vid is None and pid is None:
        return True
    if port_info.vid is None or port_info.pid is None:
        return False
    if vid is not None and port_info.vid != vid:
        return False
    if pid is not None and port_info.pid != pid:
        return False
    return True


def _iter_matching_ports(vid: Optional[int], pid: Optional[int]) -> Iterable:
    for port in list_ports.comports():
        if _matches_vid_pid(port, vid, pid):
            yield port


def _open_and_probe(port: str, baud: int, timeout: float, probe_seconds: float) -> bool:
    try:
        with serial.Serial(port, baudrate=baud, timeout=timeout) as ser:
            end_time = time.time() + probe_seconds
            while time.time() < end_time:
                data = ser.readline()
                if data:
                    return True
        return False
    except serial.SerialException as exc:
        print(f"[ERROR] Could not open {port}: {exc}")
        return False


def _listen(port: str, baud: int, timeout: float, retry_seconds: float) -> int:
    try:
        while True:
            try:
                with serial.Serial(port, baudrate=baud, timeout=timeout) as ser:
                    print(f"[INFO] Listening on {port} @ {baud}. Press Ctrl+C to stop.")
                    while True:
                        data = ser.readline()
                        if not data:
                            continue
                        text = data.decode("utf-8", errors="replace").rstrip("\r\n")
                        if text:
                            print(text)
            except serial.SerialException as exc:
                print(f"[ERROR] Could not open {port}: {exc}")
                print(f"[INFO] Retrying in {retry_seconds:.1f}s...")
                time.sleep(retry_seconds)
    except KeyboardInterrupt:
        print("\n[INFO] Stopped.")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="test_serial_detect",
        description="Detect serial devices and optionally probe or listen for data.",
    )
    parser.add_argument("--vid", type=lambda v: int(v, 16), default=None, help="USB VID in hex, e.g. 0x2341")
    parser.add_argument("--pid", type=lambda v: int(v, 16), default=None, help="USB PID in hex, e.g. 0x0043")
    parser.add_argument("--port", default=None, help="Specific port to open (e.g. COM3)")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate for probe/listen")
    parser.add_argument("--timeout", type=float, default=0.2, help="Read timeout in seconds")
    parser.add_argument("--probe", action="store_true", help="Open port and wait for data")
    parser.add_argument("--probe-seconds", type=float, default=3.0, help="How long to wait for data")
    parser.add_argument("--listen", action="store_true", help="Open port and print incoming data")
    parser.add_argument("--retry-seconds", type=float, default=2.0, help="Retry delay if port is busy")
    args = parser.parse_args()

    if args.port:
        ports = [args.port]
        print(f"[INFO] Using explicit port: {args.port}")
    else:
        ports = [p.device for p in _iter_matching_ports(args.vid, args.pid)]
        if args.vid is not None or args.pid is not None:
            print(f"[INFO] Filtering by VID/PID: {args.vid!s}/{args.pid!s}")

    if not ports:
        print("[WARN] No serial ports detected.")
        return 1

    print("[INFO] Detected ports:")
    for port in ports:
        print(f"  - {port}")

    if args.listen or not args.probe:
        return _listen(ports[0], args.baud, args.timeout, args.retry_seconds)

    ok = False
    for port in ports:
        print(f"[INFO] Probing {port} @ {args.baud}...")
        if _open_and_probe(port, args.baud, args.timeout, args.probe_seconds):
            print(f"[PASS] Data detected on {port}.")
            ok = True
            break
        print(f"[WARN] No data detected on {port}.")
    return 0 if ok else 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
