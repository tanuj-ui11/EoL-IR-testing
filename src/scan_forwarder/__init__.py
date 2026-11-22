"""Barcode-scanner to HTTP forwarder for line-side kiosks.

Reads one dedicated USB scanner (HID keyboard via /dev/input, or USB-COM via a tty), assembles each scan,
and POSTs it to a webhook. Scans are spooled to disk first, so nothing is lost while the network is down.
Zero runtime dependencies; Linux only for the device readers.
"""
from .core import Assembler, Debouncer, Spool, decode_key, make_payload

__all__ = ["Assembler", "Debouncer", "Spool", "decode_key", "make_payload"]
