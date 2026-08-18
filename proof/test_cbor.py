"""Reading a reply, against the bytes the interactors actually write.

The vectors below are not invented: they are what `weft/cbor.h` and `seethrough/cbor.py` emit
for the replies this transport layer exists to print. A reader tested only against its own
writer proves the two agree with each other and nothing about the wire.

SPDX-License-Identifier: Apache-2.0
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from buscli.cbor import Malformed, loads  # noqa: E402

FAILURES = []


def check(ok, what):
    print(f"{'ok  ' if ok else 'FAIL'} {what}")
    if not ok:
        FAILURES.append(what)


def refuses(raw, what):
    try:
        loads(raw)
        check(False, what)
    except Malformed:
        check(True, what)


def main():
    # Captured from the live RunPod endpoint: the interactor's gate refusing a 512px run.
    live = bytes.fromhex(
        "a165" + "6572726f72" + "784d" +
        "2d2d726573203531322069732062656c6f77207468652070726f64756374696f6e2073657474696e6720"
        "313238303b206120736d616c6c65722072756e206973206e6f742065766964656e6365"
    )
    got = loads(live)
    check(got == {"error": "--res 512 is below the production setting 1280; "
                           "a smaller run is not evidence"},
          "the refusal this endpoint really returned decodes whole")

    # A success reply's shape, as seethrough/command.py writes it.
    check(loads(bytes.fromhex("a2666c617965727307626d731a00057a58")) == {"layers": 7, "ms": 359000},
          "a two-key map of small and large integers decodes")

    check(loads(bytes.fromhex("a1626d73181e")) == {"ms": 30}, "a one-byte integer argument decodes")
    check(loads(bytes.fromhex("a1626d7319012c")) == {"ms": 300}, "a two-byte argument decodes")
    check(loads(bytes.fromhex("a1626d731b0000000100000000")) == {"ms": 4294967296},
          "an eight-byte argument decodes")
    check(loads(bytes.fromhex("29")) == -10, "a negative integer decodes")
    check(loads(bytes.fromhex("824161623132")) == [b"a", "12"], "an array of bytes and text decodes")

    # Malformed. Each of these is a writer and reader disagreeing about a length, which is the
    # failure that must not be silently absorbed: a truncated reply read as a short one would
    # be a wrong answer rather than an error.
    refuses(bytes.fromhex("a166"), "a map header with nothing after it is refused")
    refuses(bytes.fromhex("64616263"), "a string whose length runs past the end is refused")
    refuses(bytes.fromhex("a1626d73181e00"), "trailing bytes after a complete item are refused")
    refuses(bytes.fromhex("bf626d73181eff"), "an indefinite-length map is refused, not guessed at")
    refuses(bytes.fromhex("fb3ff0000000000000"), "a float is refused; no reply here carries one")
    refuses(b"", "an empty reply is refused")

    print("cbor: FAILED" if FAILURES else "cbor: all checks passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
