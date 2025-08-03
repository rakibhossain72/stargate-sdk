import asyncio
import os
from stargate_bridge import StargateClient, Tokens


async def main():
    """Example of basic USDC transfer from Ethereum to Polygon."""
    
    # Make sure to set your private key in environment variables
    if not os.getenv('EVM_PRIVATE_KEY'):
        print("Please set EVM_PRIVATE_KEY environment variable")
        return
    
    async with StargateClient() as client:
        try:
            # Transfer 1 USDC from Ethereum to Polygon
            print("Starting USDC transfer from Ethereum to Polygon...")
            
            tx_hashes = await client.transfer(
                src_token=Tokens.ETHEREUM['USDC'],
                dst_token=Tokens.POLYGON['USDC'],
                src_chain_key='ethereum',
                dst_chain_key='polygon',
                amount='1000000',  # 1 USDC (6 decimals)
                slippage_tolerance=0.05  # 5% slippage
            )
            
            print("Transfer completed successfully!")
            print("Transaction hashes:")
            for i, tx_hash in enumerate(tx_hashes, 1):
                print(f"  Step {i}: {tx_hash}")
                
        except Exception as e:
            print(f"Transfer failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())