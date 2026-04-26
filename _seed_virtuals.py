"""One-shot: seed top-N Virtuals by mcap into the SentinelNet DB by calling the live API."""
import asyncio
import time

import httpx

LIMIT = 25


async def main():
    from agent.virtuals import VirtualsClient
    client = VirtualsClient()
    top = await client.fetch_top_by_mcap(limit=LIMIT)
    print(f"seeding {len(top)} virtuals")
    async with httpx.AsyncClient(timeout=180) as h:
        for v in top:
            t0 = time.time()
            try:
                r = await h.get(f"http://localhost:8004/api/virtual/{v.virtual_id}?fresh=true")
                if r.status_code == 200:
                    d = r.json()
                    name = v.name[:20]
                    print(f"  #{v.virtual_id:>5d} {name:20s} -> {d.get('trust_score'):3d} {d.get('verdict'):8s} ({time.time()-t0:.1f}s)")
                else:
                    print(f"  #{v.virtual_id} {v.name[:20]} -> HTTP {r.status_code}: {r.text[:100]}")
            except Exception as e:
                print(f"  #{v.virtual_id} {v.name[:20]} -> ERROR {type(e).__name__}: {e}")
            await asyncio.sleep(1)
    print("done")


asyncio.run(main())
