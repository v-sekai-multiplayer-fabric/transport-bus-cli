# transport-bus-cli

The command line as a transport layer. It sends one command over the harness command bus and
prints the interactor's reply.

## Why it exists

`transport-runpod` terminates a RunPod queue; this terminates a terminal. Everything below the
input is the same — the same services, the same 8-byte request-id envelope, the same interactor
on the other side — so a command that works here works there, and one that does not is the
interactor's fault rather than the queue's.

That is the whole argument for it. Reaching an interactor through RunPod costs a container
build, a registry push and a cold start; reaching it through this costs a shell prompt. Which
interactor answers is decided by whichever one is running, so it is also how
`interactor-see-through-cpp` and `interactor-see-through-python` are compared without an
endpoint each.

```sh
python -m buscli decompose /in.png --res 1280 --steps 30
```

An interactor's error is still a reply, and still exits non-zero, so this is usable as a check
rather than only as a viewer. `--repeat` summarises the interactor's own reported milliseconds;
it never reports a clock this process kept, because a duration measured outside the program
that did the work has been wrong here before.

## Reading a reply

`buscli/cbor.py` decodes only the four kinds a reply is made of: maps, text, byte strings and
integers. A decoder handling everything RFC 8949 allows would be a library, and a reply needing
one is a reply whose shape nobody agreed on. Anything else is refused rather than guessed at —
a truncated reply read as a short one would be a wrong answer instead of an error.

`proof/test_cbor.py` checks it against bytes the interactors really write, including a refusal
captured from a live RunPod endpoint. A reader tested only against its own writer proves the
two agree with each other and nothing about the wire.
