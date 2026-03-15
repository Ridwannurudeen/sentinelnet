class TrustGraph:
    def __init__(self, db):
        self.db = db

    async def get_neighborhood(self, agent_id: int) -> dict:
        """Get an agent's trust neighborhood from stored graph edges."""
        edges = await self.db.get_edges(agent_id)
        return {
            "agent_id": agent_id,
            "neighbors": [
                {
                    "counterparty": e["counterparty"],
                    "interaction_count": e["interaction_count"],
                    "is_flagged": bool(e["is_flagged"]),
                }
                for e in edges
            ],
            "total_neighbors": len(edges),
        }
