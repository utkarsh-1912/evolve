"""Test-only TCP forwarder (stdlib): localhost:8010 -> localhost:8000.

Why: the citizen live build has NEXT_PUBLIC_API=http://localhost:8010 baked in at build time, while the counselor
and eval builds use :8000. The cross-app smoke needs all three apps on ONE backend, and qa-redteam may not rebuild
apps/. Usage: python tests/e2e/port_forward.py [listen_port] [target_port]
"""
import asyncio
import sys

LISTEN, TARGET = (int(sys.argv[1]) if len(sys.argv) > 1 else 8010), (int(sys.argv[2]) if len(sys.argv) > 2 else 8000)


async def pipe(r, w):
    try:
        while data := await r.read(65536):
            w.write(data)
            await w.drain()
    except (ConnectionError, OSError):
        pass
    finally:
        w.close()


async def handle(cr, cw):
    try:
        tr, tw = await asyncio.open_connection("127.0.0.1", TARGET)
    except OSError:
        cw.close()
        return
    await asyncio.gather(pipe(cr, tw), pipe(tr, cw))


async def main():
    srv = await asyncio.start_server(handle, "127.0.0.1", LISTEN)
    async with srv:
        await srv.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
