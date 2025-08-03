class Tokens:
    """Common token addresses for different chains."""
    
    ETHEREUM = {
        'USDC': '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',
        'USDT': '0xdac17f958d2ee523a2206206994597c13d831ec7'
    }
    
    POLYGON = {
        'USDC': '0x3c499c542cef5e3811e1192ce70d8cc03d5c3359',
        'USDT': '0xc2132d05d31c914a87c6611c10748aeb04b58e8f'
    }
    
    ARBITRUM = {
        'USDC': '0xaf88d065e77c8cc2239327c5edb3a432268e5831',
        'USDT': '0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9'
    }

class ChainIds:
    """Chain IDs for different networks."""
    ETHEREUM = 1
    POLYGON = 137
    ARBITRUM = 42161
    OPTIMISM = 10
    BASE = 8453
    AVALANCHE = 43114