# Stargate Bridge Python SDK

A Python SDK for interacting with Stargate Finance, enabling seamless cross-chain token transfers.

## Features

- Cross-chain token transfers via Stargate Finance
- Support for multiple chains (Ethereum, Polygon, Arbitrum, Optimism, etc.)
- Automatic quote fetching and route optimization
- Secure transaction signing with private keys
- Easy-to-use async/await API
- Comprehensive error handling

## Installation

```bash
pip install stargate-bridge-sdk
```

## Quick Start

```python
import asyncio
from stargate_bridge import StargateClient, Tokens

async def transfer_usdc():
    async with StargateClient() as client:
        # Transfer 1 USDC from Ethereum to Polygon
        tx_hashes = await client.transfer(
            src_token=Tokens.ETHEREUM['USDC'],
            dst_token=Tokens.POLYGON['USDC'],
            src_chain_key='ethereum',
            dst_chain_key='polygon',
            amount='1000000',  # 1 USDC (6 decimals)
        )
        print("Transfer completed:", tx_hashes)

asyncio.run(transfer_usdc())
```

## Configuration

Set your private key as an environment variable:

```bash
export EVM_PRIVATE_KEY="your_private_key_here"
```

Or pass it directly to the client:

```python
client = StargateClient(private_key="your_private_key")
```

## Supported Chains

- Ethereum
- Polygon
- Arbitrum
- Optimism
- Base
- Avalanche

## API Reference

### StargateClient

Main client for interacting with Stargate Finance.

#### Methods

- `transfer()` - Execute a cross-chain transfer
- `get_quotes()` - Fetch transfer quotes
- `execute_route()` - Execute a specific route
- `get_supported_chains()` - Get supported chains

### Tokens

Predefined token addresses for common tokens across chains.

## Development

1. Clone the repository
2. Install development dependencies: `pip install -e .[dev]`
3. Run tests: `pytest`
4. Format code: `black stargate_bridge/`

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.
