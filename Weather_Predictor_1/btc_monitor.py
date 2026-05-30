#!/usr/bin/env python3
"""
BTC 15m Kalshi Monitor — System tray app for watching Bitcoin UP/DOWN markets.
Plays bell notification when new markets appear, logs predictions, shows outcomes.
"""

import sys
import json
import subprocess
import base64
import time
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from PIL import Image, ImageDraw
import io

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSystemTrayIcon, QMenu, QDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt5.QtGui import QIcon, QColor, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QRect
from PyQt5.QtWidgets import QApplication


# === Credentials ===
KALSHI_API_KEY = "fd9fe5c2-7d6d-48fa-b4d3-2e2c6db923fb"
KALSHI_API_SECRET_RAW = """MIIEpAIBAAKCAQEA4PjnWxjQmtbhKBDxCscOhtrLoyVgAWMvNIsIX9GceCnveJAA
n2zNTdQpHP4lYzDEZXA1tdXsXfH9t8AHvDgvTwnaVu1SMjLqFqxH1MB9MoQe3DKf
z2WsP4pwQmkaQRIygzej66AeJl7lISi/wX+kEHRU7ObKZohnLTxXyLf5pWW99IZ/
Qu4LQUbi6c4Ny2wpH+e+oq8cV1yUCkbyVv5BiltP4PuToWlugsQagju58dkH2kvv
9zdCfgH6tFXAAtDhPckg/9SUWYd8MipFw0NJHEjIPowxR6MAnk8JZJ1g1xfiBVTn
MllUKiQtkChkwXFmO+yFGOqpRKQUD4zJiXEFkQIDAQABAoIBABW7JUnw5zGVwREI
NehnGvmex93d/dyUcppeNbRfwIAA+P9J1a2QqnIypLgGuqDOtKHhyWZjoB3hArON
qpGdUcCOQJd1/CMaNO90u8mKwG0xQvPdNf+oIA/RNQ/NLDqN4fA33y8i+9aUAwkF
cSRlSnlGa2+oyXNHCMRfWFFsqAI4V9iClX/FBKDQ3WhD6h33iwrHUP84lZIIelCQ
zhSt3q8MciZ2Q6SsknI02/zB1aysA0WXbxJQf1QDXw+DTyfP0Oddh9FBrehmmpyt
C6rFLbJsdtk3eQ5RwMlA45vyLlDGCyFhEDu0xwSnlJ4YYVNbb7svWBjjCvCvlADL
sSYxESMCgYEA7/jeC17EUBTcumxty/fvh6bnfveaNQiqw075ZJWT1BkA5WAz82xP
bCyTeqCIF/Wqe16faMm8hast6s9q1QBs2JVNfahop2utEkaio5bFRBkyVIqAjxJB
dEa/wnLmnX7BeerSksTKkG7XTu6w3OliJf8GT+1WKVpNegAPRMRvEaMCgYEA7/+Q
MFf1tdedNBxZd9ZfK6PkdLPk4/dnnZ1kswAouC14iP91eCzX4uJMmcAanSHStrey
kS0iB0/g26v24ZUGNM9y4CZ9h7TqFVm4WUopHnGz1IHeIOmqnhMHSSzN0rGNToI6
SG1GL/1vO17spUYqLgkNn9wNA+tzGo+dJO75hzsCgYEAnVF1n9actDM5ES4MPO9p
pHCSyvXfrmzkJe4cKQi2RRGvOLB83lRfLPd8J6QeFDcFcKNzteqrIKY8D/eyfbkt
oj8e8gX5tegtKhIMhVpOMHqkODAkX6cEKgpHpF5XOWDjzd1X9sf0VAOWOzTX1bta
kLZDmRpqpemBaT2oxNhSSCkCgYBLwpDxsdKOpJGrcYeMnM9OJ15muKL4k5DR4G15
VAOGoFP8ayfZ184OgQFNR6cfEx5BL5ve2DB1vnFs5sv4SeK7qQDKYVwfCq0aMEhR
Z2ezhJEP9C76lMiXPcp+/vW6HPJOZi2fz17op0gFpeFuCsgl4BW88Onq4thi+hLR
Jd7/IQKBgQCPQCum/nE4c6GgDg6hNgXkXRPw+XtTfbDgUbUKlOiDijQVT9fgF7ob
EN6cVxzE0kAcia5Tqfx0f2kffCqDdp0+IlEe9U+hR2mKzh9aTh/7UvCIRSFQVvt8
Kv/Kycj0xdMwvCIYzBoUL6fN51l5kqWkxwewWK8OTvegPZJfkUWsOg==""".replace("\n", "")


def build_pem_key(secret_raw: str) -> str:
    """Wrap base64 RSA key body in PEM headers and re-chunk to 64-char lines."""
    cleaned = secret_raw.strip().replace(" ", "")
    chunks = [cleaned[i:i+64] for i in range(0, len(cleaned), 64)]
    return "-----BEGIN RSA PRIVATE KEY-----\n" + "\n".join(chunks) + "\n-----END RSA PRIVATE KEY-----"


PEM_KEY = build_pem_key(KALSHI_API_SECRET_RAW)


class KalshiClient:
    """Minimal Kalshi API client for BTC 15m markets."""

    BASE_URL = "https://external-api.kalshi.com/trade-api/v2"

    def __init__(self, api_key: str, pem_key: str):
        self.api_key = api_key
        self.private_key = serialization.load_pem_private_key(
            pem_key.encode(), password=None, backend=default_backend()
        )

    def _sign(self, method: str, path: str, ts_ms: int) -> str:
        """RSA-PSS-SHA256 signature (Kalshi format)."""
        sig_string = f"{ts_ms}{method}{path}"
        signature = self.private_key.sign(
            sig_string.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode()

    def _get(self, endpoint: str) -> Dict:
        """Signed GET request."""
        url = f"{self.BASE_URL}{endpoint}"
        ts_ms = int(time.time() * 1000)
        path_for_sig = f"/trade-api/v2{endpoint.split('?')[0]}"
        signature = self._sign("GET", path_for_sig, ts_ms)

        headers = {
            "Content-Type": "application/json",
            "KALSHI-ACCESS-KEY": self.api_key,
            "KALSHI-ACCESS-TIMESTAMP": str(ts_ms),
            "KALSHI-ACCESS-SIGNATURE": signature,
        }

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"API error: {e}")
            return {}

    def get_open_btc_markets(self) -> List[Dict]:
        """GET /markets?status=open&series_ticker=kxbtc15m"""
        result = self._get("/markets?status=open&series_ticker=kxbtc15m&limit=10")
        return result.get("markets", [])

    def get_market(self, ticker: str) -> Dict:
        """GET /markets/{ticker}"""
        return self._get(f"/markets/{ticker}")


class PredictionStore:
    """Reads/writes btc_predictions.json."""

    def __init__(self, path: Path):
        self.path = path
        if not path.exists():
            path.write_text(json.dumps([]))

    def _load(self) -> List[Dict]:
        """Load all predictions."""
        try:
            return json.loads(self.path.read_text())
        except:
            return []

    def _save(self, preds: List[Dict]):
        """Save all predictions."""
        self.path.write_text(json.dumps(preds, indent=2))

    def add(self, ticker: str, direction: str, title: str) -> Dict:
        """Add a new prediction. Returns the record."""
        preds = self._load()
        record = {
            "id": str(uuid.uuid4()),
            "ticker": ticker,
            "direction": direction.lower(),
            "market_title": title,
            "predicted_at": datetime.utcnow().isoformat() + "Z",
            "outcome": None,
            "result_raw": None,
        }
        preds.append(record)
        self._save(preds)
        return record

    def resolve(self, ticker: str, result_raw: str, outcome: str):
        """Mark a prediction as resolved (correct/wrong/unknown)."""
        preds = self._load()
        for p in preds:
            if p["ticker"] == ticker:
                p["result_raw"] = result_raw
                p["outcome"] = outcome
        self._save(preds)

    def all(self) -> List[Dict]:
        """All predictions, newest first."""
        preds = self._load()
        return sorted(preds, key=lambda x: x["predicted_at"], reverse=True)

    def pending(self) -> List[Dict]:
        """Predictions without an outcome."""
        return [p for p in self._load() if p["outcome"] is None]


def play_bell():
    """Play soft bell notification."""
    sound = "/usr/share/sounds/freedesktop/stereo/bell.oga"
    try:
        # Try aplay first (available on Linux systems)
        subprocess.Popen(
            ["aplay", sound],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except:
        try:
            # Fallback to paplay
            subprocess.Popen(
                ["paplay", sound],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except:
            pass


def market_title_has_up(title: str) -> bool:
    """Parse market title to determine if YES = price up."""
    return "up" in title.lower()


class MarketPoller(QThread):
    """Background thread polling Kalshi API."""

    new_market_signal = pyqtSignal(dict)
    resolution_signal = pyqtSignal(str, str)  # (ticker, "correct"/"wrong")

    def __init__(self, client: KalshiClient, store: PredictionStore):
        super().__init__()
        self.client = client
        self.store = store
        self.seen_tickers = set()
        self.running = True

    def run(self):
        """Poll loop."""
        timer = QTimer()
        timer.timeout.connect(self._poll)
        timer.start(30000)  # 30s
        self.exec_()

    def stop(self):
        """Stop polling."""
        self.running = False
        self.quit()

    def _poll(self):
        """Check for new markets and resolution."""
        if not self.running:
            return

        # Check for new markets
        markets = self.client.get_open_btc_markets()
        for m in markets:
            ticker = m.get("ticker")
            if ticker and ticker not in self.seen_tickers:
                self.seen_tickers.add(ticker)
                self.new_market_signal.emit(m)

        # Check for resolutions
        for pred in self.store.pending():
            market = self.client.get_market(pred["ticker"])
            result = market.get("result")
            if result:
                # Determine outcome
                title = market.get("title", pred["market_title"])
                yes_means_up = market_title_has_up(title)
                predicted_up = pred["direction"] == "up"

                if (result == "yes" and yes_means_up and predicted_up) or \
                   (result == "no" and not yes_means_up and predicted_up) or \
                   (result == "yes" and not yes_means_up and not predicted_up) or \
                   (result == "no" and yes_means_up and not predicted_up):
                    outcome = "correct"
                else:
                    outcome = "wrong"

                self.store.resolve(pred["ticker"], result, outcome)
                self.resolution_signal.emit(pred["ticker"], outcome)


class HistoryDialog(QDialog):
    """Show all predictions in a table."""

    def __init__(self, store: PredictionStore, parent=None):
        super().__init__(parent)
        self.store = store
        self.setWindowTitle("Prediction History")
        self.setGeometry(100, 100, 700, 400)

        layout = QVBoxLayout()

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Time", "Market", "Prediction", "Outcome"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setColumnWidth(0, 200)
        table.setColumnWidth(3, 120)

        for pred in store.all():
            row = table.rowCount()
            table.insertRow(row)

            time_str = pred["predicted_at"].replace("Z", "")
            table.setItem(row, 0, QTableWidgetItem(time_str))
            table.setItem(row, 1, QTableWidgetItem(pred["ticker"]))

            pred_text = "↑ UP" if pred["direction"] == "up" else "↓ DOWN"
            table.setItem(row, 2, QTableWidgetItem(pred_text))

            outcome = pred["outcome"] or "Pending"
            item = QTableWidgetItem()
            if outcome == "correct":
                item.setText("✓ Correct")
                item.setForeground(QColor("green"))
            elif outcome == "wrong":
                item.setText("✗ Wrong")
                item.setForeground(QColor("red"))
            else:
                item.setText("Pending")
                item.setForeground(QColor("gray"))
            table.setItem(row, 3, item)

        layout.addWidget(table)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)


class BTCMonitorWindow(QMainWindow):
    """Main window."""

    def __init__(self, client: KalshiClient, store: PredictionStore, poller: MarketPoller):
        super().__init__()
        self.client = client
        self.store = store
        self.poller = poller
        self.notifications_on = True
        self.current_market = None

        self.setWindowTitle("₿ BTC 15m Monitor")
        self.setGeometry(100, 100, 400, 300)

        central = QWidget()
        layout = QVBoxLayout()

        # ON/OFF toggle
        toggle_layout = QHBoxLayout()
        toggle_label = QLabel("Notifications:")
        self.toggle_btn = QPushButton("ON")
        self.toggle_btn.setStyleSheet("background-color: green; color: white;")
        self.toggle_btn.clicked.connect(self._toggle_notifications)
        self.toggle_btn.setMaximumWidth(80)
        toggle_layout.addWidget(toggle_label)
        toggle_layout.addWidget(self.toggle_btn)
        toggle_layout.addStretch()
        layout.addLayout(toggle_layout)

        # Current market
        market_label = QLabel("Current Market:")
        layout.addWidget(market_label)
        self.market_display = QLabel("(waiting for new market...)")
        font = self.market_display.font()
        font.setPointSize(11)
        font.setBold(True)
        self.market_display.setFont(font)
        layout.addWidget(self.market_display)

        # UP/DOWN buttons
        button_layout = QHBoxLayout()
        self.up_btn = QPushButton("↑ UP")
        self.up_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; font-size: 14px;")
        self.up_btn.clicked.connect(lambda: self._predict("up"))
        self.up_btn.setEnabled(False)

        self.down_btn = QPushButton("↓ DOWN")
        self.down_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; font-size: 14px;")
        self.down_btn.clicked.connect(lambda: self._predict("down"))
        self.down_btn.setEnabled(False)

        button_layout.addWidget(self.up_btn)
        button_layout.addWidget(self.down_btn)
        layout.addLayout(button_layout)

        # History button
        history_btn = QPushButton("📋 History")
        history_btn.clicked.connect(self._show_history)
        layout.addWidget(history_btn)

        layout.addStretch()

        central.setLayout(layout)
        self.setCentralWidget(central)

        # Connect poller signals
        self.poller.new_market_signal.connect(self._on_new_market)
        self.poller.resolution_signal.connect(self._on_resolution)

    def _toggle_notifications(self):
        """Toggle notifications ON/OFF."""
        self.notifications_on = not self.notifications_on
        if self.notifications_on:
            self.toggle_btn.setText("ON")
            self.toggle_btn.setStyleSheet("background-color: green; color: white;")
        else:
            self.toggle_btn.setText("OFF")
            self.toggle_btn.setStyleSheet("background-color: gray; color: white;")

    def _on_new_market(self, market: Dict):
        """New market detected."""
        self.current_market = market
        ticker = market.get("ticker", "?")
        title = market.get("title", "?")
        self.market_display.setText(f"{ticker}\n{title}")
        self.up_btn.setEnabled(True)
        self.down_btn.setEnabled(True)

        if self.notifications_on:
            play_bell()

    def _predict(self, direction: str):
        """User clicked UP or DOWN."""
        if not self.current_market:
            return

        ticker = self.current_market.get("ticker")
        title = self.current_market.get("title", "")
        self.store.add(ticker, direction, title)

        # Disable buttons until next market
        self.up_btn.setEnabled(False)
        self.down_btn.setEnabled(False)

        msg = f"Predicted {direction.upper()} on {ticker}"
        print(msg)

    def _on_resolution(self, ticker: str, outcome: str):
        """Market resolved."""
        if self.notifications_on:
            title = "Correct!" if outcome == "correct" else "Wrong"
            QMessageBox.information(self, "Market Resolved", f"{ticker}: {title}")

    def _show_history(self):
        """Open history dialog."""
        dlg = HistoryDialog(self.store, self)
        dlg.exec_()

    def closeEvent(self, event):
        """Hide to tray instead of quitting."""
        self.hide()
        event.ignore()


class BTCMonitorApp:
    """Main app."""

    def __init__(self):
        self.app = QApplication(sys.argv)

        # Paths
        project_root = Path(__file__).parent
        self.store_path = project_root / "btc_predictions.json"

        # Components
        self.client = KalshiClient(KALSHI_API_KEY, PEM_KEY)
        self.store = PredictionStore(self.store_path)
        self.poller = MarketPoller(self.client, self.store)
        self.window = BTCMonitorWindow(self.client, self.store, self.poller)

        # Tray icon
        self.tray = QSystemTrayIcon(self.window)
        self.tray.setIcon(self._create_tray_icon())

        # Tray menu
        menu = QMenu()
        show_action = menu.addAction("Show")
        show_action.triggered.connect(self.window.showNormal)
        toggle_action = menu.addAction("Toggle ON/OFF")
        toggle_action.triggered.connect(self.window._toggle_notifications)
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self._quit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

        # Start poller
        self.poller.start()

    def _create_tray_icon(self) -> QIcon:
        """Generate orange BTC icon."""
        from PyQt5.QtGui import QPixmap, QColor

        img = Image.new("RGBA", (64, 64), (255, 165, 0, 255))
        draw = ImageDraw.Draw(img)
        draw.text((18, 12), "₿", fill="white", font=None)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue(), "PNG")
        return QIcon(pixmap)

    def _tray_activated(self, reason):
        """Tray icon double-click."""
        if reason == QSystemTrayIcon.DoubleClick:
            if self.window.isVisible():
                self.window.hide()
            else:
                self.window.showNormal()

    def _quit(self):
        """Quit app."""
        self.poller.stop()
        self.app.quit()

    def run(self):
        """Run app."""
        self.window.show()
        sys.exit(self.app.exec_())


if __name__ == "__main__":
    app = BTCMonitorApp()
    app.run()
