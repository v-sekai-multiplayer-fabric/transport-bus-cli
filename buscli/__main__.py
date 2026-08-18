"""The command line as a transport layer.

`transport-runpod` terminates a RunPod queue; this terminates a terminal. Everything below the
input is the same -- the same request-id envelope, the same services, the same interactor on
the other side -- so a command that works here works there, and one that does not is the
interactor's fault rather than the queue's.

That is what makes it worth having. Reaching an interactor through RunPod costs a container
build, a registry push and a cold start; reaching it through this costs a shell prompt, and
which interactor answers is decided by whichever one is running.

    python -m buscli decompose /in.png --res 1280 --steps 30

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import argparse
import itertools
import sys
import time

from weft_harness import Bus, ask

from .cbor import Malformed, loads

_ids = itertools.count(int(time.time()) << 16)


def parse_args(argv):
    ap = argparse.ArgumentParser(
        prog="buscli",
        description="Send one command to whichever interactor is on the bus, and print its reply.",
    )
    ap.add_argument("command", nargs=argparse.REMAINDER,
                    help="the command line, sent to the interactor verbatim")
    ap.add_argument("--timeout", type=float, default=900.0,
                    help="seconds to wait for the reply (default 900, a production run's size)")
    ap.add_argument("--repeat", type=int, default=1,
                    help="send it N times and summarise the interactor's own reported ms")
    ap.add_argument("--raw", action="store_true", help="print the reply bytes as hex, undecoded")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if not args.command:
        print("buscli: no command given", file=sys.stderr)
        return 2

    line = " ".join(args.command).encode("utf-8")
    bus = Bus("client")
    reported = []
    failed = False

    for _ in range(max(1, args.repeat)):
        reply = ask(bus, next(_ids), line, timeout_s=args.timeout)
        if reply is None:
            print("buscli: no reply before the deadline", file=sys.stderr)
            return 1
        if args.raw:
            print(reply.hex())
            continue
        try:
            decoded = loads(reply)
        except Malformed as why:
            print(f"buscli: {why}", file=sys.stderr)
            return 1

        print(decoded)
        # An interactor's error is a reply, not a transport failure -- but it is still a
        # non-zero exit, so this is usable as a check rather than only as a viewer.
        if isinstance(decoded, dict) and "error" in decoded:
            failed = True
        elif isinstance(decoded, dict) and isinstance(decoded.get("ms"), int):
            reported.append(decoded["ms"])

    if len(reported) > 1:
        # The interactor's own numbers, never a clock this process kept. A duration measured
        # outside the program that did the work has been wrong here before, confidently.
        ordered = sorted(reported)
        mid = ordered[len(ordered) // 2]
        print(f"interactor-reported ms: min {ordered[0]} median {mid} max {ordered[-1]} "
              f"over {len(ordered)} runs", file=sys.stderr)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
