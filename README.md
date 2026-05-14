# Codex Account Pool Proxy

Multi-account proxy for OpenAI Codex CLI with web management UI, quota tracking, and automatic failover.

## Features

- **Multi-account pool** — supports 2–8+ ChatGPT Plus accounts with round-robin load balancing
- **Automatic failover** — detects rate limits (429) and switches to next available account
- **Token management** — auto-refreshes OAuth tokens on 401
- **Web dashboard** — manage accounts, view quotas, configure settings
- **Quota tracking** — monitors 5-hour and 7-day usage windows per account

## Quick Start

```bash
# Install dependencies
pip3 install -r requirements.txt

# Add your first account
python3 proxy.py &
# Open http://127.0.0.1:8800/app → Accounts → Add Account

# Configure Codex
# Add to ~/.codex/config.toml:
#   openai_base_url = "http://127.0.0.1:8800/v1"
#   chatgpt_base_url = "http://127.0.0.1:8800"
```
