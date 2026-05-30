import os
from dotenv import load_dotenv

load_dotenv()

class PolymarketClient:
    def __init__(self):
        self.private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
        self.safe_address = os.getenv("POLYMARKET_SAFE_ADDRESS")
        self.clob_client = None

        # Only initialize clob_client if credentials are available
        if self.private_key and self.safe_address:
            try:
                from py_clob_client.client import ClobClient
                from py_clob_client.clob_types import ChainID

                self.clob_client = ClobClient(
                    chain_id=ChainID.POLYGON,
                    host="https://clob.polymarket.com",
                    key=self.private_key,
                    signature_type="EOA",
                )
            except Exception as e:
                print(f"Warning: Could not initialize Polymarket client: {e}")
                print("Continuing in paper mode only.")

    def is_live_mode(self):
        return self.clob_client is not None

    def get_orderbook_price(self, token_id):
        """Get current best ask for YES token (simulated)."""
        if not self.is_live_mode():
            return 0.5  # Dummy price for paper mode

        try:
            orderbook = self.clob_client.get_orderbook(token_id)
            asks = orderbook.get("asks", [])
            if asks:
                return float(asks[0]["price"])
        except Exception as e:
            print(f"Error fetching orderbook: {e}")

        return 0.5

    def place_limit_order(self, token_id, price, amount_usdc):
        """
        Place a limit buy order for YES token.
        Returns order_id on success, None on failure or paper mode.
        """
        if not self.is_live_mode():
            return None

        try:
            order = {
                "tokenId": token_id,
                "price": price,
                "size": amount_usdc,
                "side": "BUY",
            }

            result = self.clob_client.create_and_sign_order(order)
            self.clob_client.post_order(result)
            return result.get("id")
        except Exception as e:
            print(f"Error placing order: {e}")
            return None

    def get_open_orders(self):
        """Get list of open orders."""
        if not self.is_live_mode():
            return []

        try:
            return self.clob_client.get_orders()
        except Exception as e:
            print(f"Error fetching open orders: {e}")
            return []

    def cancel_order(self, order_id):
        """Cancel an order."""
        if not self.is_live_mode():
            return False

        try:
            self.clob_client.cancel_order(order_id)
            return True
        except Exception as e:
            print(f"Error cancelling order: {e}")
            return False


if __name__ == "__main__":
    client = PolymarketClient()
    print(f"Live mode: {client.is_live_mode()}")
    print(f"Sample price (dummy): ${client.get_orderbook_price('dummy_token'):.2f}")
