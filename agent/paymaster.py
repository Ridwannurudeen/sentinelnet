"""
Coinbase CDP Paymaster integration for gasless on-chain transactions.
Routes calls through an ERC-4337 Smart Account with sponsored gas.
"""
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PaymasterTransactor:
    """Sends on-chain transactions via Coinbase CDP Paymaster (zero gas cost)."""

    def __init__(self, api_key_id: str, api_secret: str,
                 smart_account_address: str, paymaster_url: str,
                 private_key: str, network: str = "base"):
        self.api_key_id = api_key_id
        self.api_secret = api_secret
        self.smart_account_address = smart_account_address
        self.paymaster_url = paymaster_url
        self.private_key = private_key
        self.network = network
        self._enabled = bool(
            api_key_id and api_secret and smart_account_address and paymaster_url
        )

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def send_calls(self, calls: list) -> list:
        """Send multiple contract calls in a single UserOperation via paymaster.

        Args:
            calls: List of dicts with keys: to, data, value (optional, default 0)

        Returns:
            List of tx hashes (one per call, all same hash since batched).
        """
        if not self._enabled or not calls:
            return [""] * len(calls)

        try:
            from cdp import CdpClient, EncodedCall
            from eth_account import Account

            local_account = Account.from_key(self.private_key)

            async with CdpClient(
                api_key_id=self.api_key_id,
                api_key_secret=self.api_secret,
            ) as client:
                smart = await client.evm.get_smart_account(
                    address=self.smart_account_address,
                    owner=local_account,
                )

                encoded_calls = [
                    EncodedCall(
                        to=c["to"],
                        value=c.get("value", 0),
                        data=c["data"],
                    )
                    for c in calls
                ]

                result = await client.evm.send_user_operation(
                    smart_account=smart,
                    calls=encoded_calls,
                    network=self.network,
                    paymaster_url=self.paymaster_url,
                )

                logger.info(
                    f"Paymaster UserOp sent: {result.user_op_hash} "
                    f"status={result.status} ({len(calls)} calls)"
                )

                # Return the UserOp hash immediately — confirmation happens async.
                # Waiting adds latency and the CDP wait API has version compat issues.
                return [result.user_op_hash] * len(calls)

        except Exception as e:
            # CDP returns 402 payment_method_required when the account has no
            # billing source. This won't fix itself — disable the paymaster for
            # the rest of the process to stop log spam. Restart fixes it once
            # the operator adds a payment method.
            msg = str(e)
            if "402" in msg or "payment_method_required" in msg:
                if self._enabled:
                    logger.error(
                        "Paymaster disabled for this run: CDP requires a payment "
                        "method. Set one at https://portal.cdp.coinbase.com and "
                        "restart the service."
                    )
                self._enabled = False
            else:
                logger.error(f"Paymaster transaction failed: {e}")
            raise

    async def send_call(self, to: str, data: str, value: int = 0) -> str:
        """Send a single contract call through the paymaster."""
        results = await self.send_calls([{"to": to, "data": data, "value": value}])
        return results[0] if results else ""
