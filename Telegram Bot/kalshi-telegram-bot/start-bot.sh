#!/bin/bash
cd "/home/carter/claude_programs/Polymarket/Telegram Bot/kalshi-telegram-bot"

# Kill any existing bot processes
pkill -f "python.*main.py" 2>/dev/null

# Wait a moment for process to terminate
sleep 1

# Activate venv and start bot
source venv/bin/activate
python main.py
