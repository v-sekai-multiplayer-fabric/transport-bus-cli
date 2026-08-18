"""Reading a reply.

The interactors write CBOR and say so; decoding it is the caller's, which is what this is.
Only the four kinds a reply is made of are here -- maps, text, byte strings and integers --
because a decoder that handles everything RFC 8949 allows would be a library, and a reply that
needs one is a reply whose shape nobody agreed on.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations


class Malformed(Exception):
    """The reply is not the CBOR this transport layer knows how to read."""


def _argument(buf: bytes, at: int) -> tuple[int, int]:
    """The low five bits, or the bytes that follow. Returns (value, next offset)."""
    minor = buf[at] & 0x1F
    at += 1
    if minor < 24:
        return minor, at
    width = {24: 1, 25: 2, 26: 4, 27: 8}.get(minor)
    if width is None:
        raise Malformed(f"indefinite or reserved length at byte {at - 1}")
    if at + width > len(buf):
        raise Malformed("length runs past the end of the reply")
    return int.from_bytes(buf[at : at + width], "big"), at + width


def _item(buf: bytes, at: int):
    if at >= len(buf):
        raise Malformed("reply ends mid-item")
    major = buf[at] >> 5
    value, at = _argument(buf, at)

    if major == 0:
        return value, at
    if major == 1:
        return -1 - value, at
    if major in (2, 3):
        end = at + value
        if end > len(buf):
            raise Malformed("string runs past the end of the reply")
        raw = buf[at:end]
        return (raw if major == 2 else raw.decode("utf-8", "replace")), end
    if major == 4:
        out = []
        for _ in range(value):
            item, at = _item(buf, at)
            out.append(item)
        return out, at
    if major == 5:
        out = {}
        for _ in range(value):
            key, at = _item(buf, at)
            val, at = _item(buf, at)
            out[key] = val
        return out, at
    raise Malformed(f"major type {major} is not one a reply is made of")


def loads(buf: bytes):
    """One item, and nothing after it. Trailing bytes are a malformed reply rather than
    something to ignore: they mean the writer and this reader disagree about a length."""
    item, at = _item(buf, 0)
    if at != len(buf):
        raise Malformed(f"{len(buf) - at} bytes left over after the reply")
    return item
