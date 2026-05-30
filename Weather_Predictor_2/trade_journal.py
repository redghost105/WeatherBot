import csv
from datetime import datetime
import os

class TradeJournal:
    def __init__(self, mode="paper"):
        self.mode = mode
        self.filename = f"{mode}_trades.csv"
        self._init_csv()

    def _init_csv(self):
        """Create CSV if it doesn't exist."""
        if not os.path.exists(self.filename):
            with open(self.filename, "w", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "date", "city", "target_date", "bin_range",
                        "yes_price", "stake_usdc", "order_id", "status", "pnl"
                    ]
                )
                writer.writeheader()

    def log_trade(self, city, target_date, bin_low, bin_high, yes_price, stake_usdc, order_id=None):
        """Log a new trade. Dedup on (city, target_date, bin_range)."""
        bin_range = f"{int(bin_low)}-{int(bin_high)}"
        dedup_key = (city, target_date.isoformat(), bin_range)

        # Check if already logged
        existing = self._find_trade(dedup_key)
        if existing:
            print(f"Skipping duplicate: {city} {target_date} {bin_range}")
            return False

        with open(self.filename, "a", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "date", "city", "target_date", "bin_range",
                    "yes_price", "stake_usdc", "order_id", "status", "pnl"
                ]
            )
            writer.writerow({
                "date": datetime.now().isoformat(),
                "city": city,
                "target_date": target_date.isoformat(),
                "bin_range": bin_range,
                "yes_price": f"{yes_price:.2f}",
                "stake_usdc": f"{stake_usdc:.2f}",
                "order_id": order_id or "",
                "status": "open",
                "pnl": "",
            })
        return True

    def _find_trade(self, dedup_key):
        """Find trade by (city, target_date, bin_range)."""
        city, target_date, bin_range = dedup_key
        try:
            with open(self.filename, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if (row["city"] == city and
                        row["target_date"] == target_date and
                        row["bin_range"] == bin_range):
                        return row
        except FileNotFoundError:
            pass
        return None

    def mark_resolved(self, city, target_date, bin_low, bin_high, won, pnl):
        """Mark trade as resolved and update PnL."""
        bin_range = f"{int(bin_low)}-{int(bin_high)}"
        dedup_key = (city, target_date.isoformat(), bin_range)

        rows = []
        with open(self.filename, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (row["city"] == city and
                    row["target_date"] == target_date.isoformat() and
                    row["bin_range"] == bin_range):
                    row["status"] = "won" if won else "lost"
                    row["pnl"] = f"{pnl:.2f}"
                rows.append(row)

        with open(self.filename, "w", newline="") as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

    def get_roi_summary(self):
        """Print ROI summary."""
        wins, losses, total_stake, total_pnl = 0, 0, 0, 0

        try:
            with open(self.filename, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["status"] in ("won", "lost"):
                        stake = float(row["stake_usdc"])
                        pnl = float(row["pnl"]) if row["pnl"] else 0

                        total_stake += stake
                        total_pnl += pnl

                        if row["status"] == "won":
                            wins += 1
                        else:
                            losses += 1
        except FileNotFoundError:
            pass

        roi = (total_pnl / total_stake * 100) if total_stake > 0 else 0

        print(f"\n=== {self.mode.upper()} TRADE SUMMARY ===")
        print(f"Wins: {wins}, Losses: {losses}, Win Rate: {wins/(wins+losses)*100:.1f}%" if wins + losses > 0 else "No resolved trades")
        print(f"Total Stake: ${total_stake:.2f}")
        print(f"Total PnL: ${total_pnl:.2f}")
        print(f"ROI: {roi:.1f}%")


if __name__ == "__main__":
    journal = TradeJournal("paper")
    from datetime import date, timedelta

    tomorrow = date.today() + timedelta(days=1)
    journal.log_trade("NYC", tomorrow, 56, 57, 0.30, 2.0, order_id="order_1")
    journal.log_trade("NYC", tomorrow, 57, 58, 0.25, 2.0, order_id="order_2")

    journal.mark_resolved("NYC", tomorrow, 56, 57, won=True, pnl=14.0)
    journal.mark_resolved("NYC", tomorrow, 57, 58, won=False, pnl=-2.0)

    journal.get_roi_summary()
