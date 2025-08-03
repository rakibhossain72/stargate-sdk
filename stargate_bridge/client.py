import os
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import httpx
from web3 import Web3
from eth_account import Account
from .exceptions import StargateAPIError, StargateTransactionError, StargateAPIError
from .types import QuoteParams, TransactionData

class StargateClient:
    """
    Main client for interacting with Stargate Finance.
    
    This client provides methods to:
    - Fetch quotes from Stargate API
    - Execute cross-chain transactions
    - Manage Web3 connections
    """
    
    def __init__(
        self,
        private_key: Optional[str] = None,
        rpc_url: str = "https://eth.merkle.io",
        api_base_url: str = "https://stargate.finance/api/v1"
    ):
        """
        Initialize the Stargate client.
        
        Args:
            private_key: Private key for transaction signing (can also use env var EVM_PRIVATE_KEY)
            rpc_url: Ethereum RPC URL
            api_base_url: Stargate API base URL
        """
        self.api_base_url = api_base_url
        self.rpc_url = rpc_url
        
        # Initialize private key
        self.private_key = private_key or os.getenv('EVM_PRIVATE_KEY')
        if not self.private_key:
            raise ValueError("Private key must be provided or set in EVM_PRIVATE_KEY environment variable")
        
        if not self.private_key.startswith('0x'):
            self.private_key = '0x' + self.private_key
            
        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.account = Account.from_key(self.private_key)
        
        # Initialize HTTP client
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.http_client.aclose()
    
    async def get_supported_chains(self) -> Dict[str, Any]:
        """
        Get all supported chains from Stargate.
        
        Returns:
            Dict containing supported chains information
        """
        try:
            response = await self.http_client.get(f"{self.api_base_url}/chains")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise StargateAPIError(f"Failed to fetch supported chains: {e}")
    
    async def get_quotes(self, params: QuoteParams) -> Dict[str, Any]:
        """
        Fetch quotes from Stargate API.
        
        Args:
            params: Quote parameters
            
        Returns:
            Dict containing quotes data
        """
        query_params = {
            'srcToken': params.src_token,
            'dstToken': params.dst_token,
            'srcAddress': params.src_address,
            'dstAddress': params.dst_address,
            'srcChainKey': params.src_chain_key,
            'dstChainKey': params.dst_chain_key,
            'srcAmount': params.src_amount,
            'dstAmountMin': params.dst_amount_min
        }
        
        try:
            response = await self.http_client.get(
                f"{self.api_base_url}/quotes",
                params=query_params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise StargateAPIError(f"Failed to fetch quotes: {e}")
    
    def _prepare_transaction(self, tx_data: TransactionData, nonce: int) -> Dict[str, Any]:
        """
        Prepare a transaction for execution.
        
        Args:
            tx_data: Transaction data
            nonce: Transaction nonce
            
        Returns:
            Prepared transaction dictionary
        """
        transaction = {
            'to': tx_data.to,
            'data': tx_data.data,
            'nonce': nonce,
            'gas': 300000,  # Default gas limit, should be estimated
            'gasPrice': self.w3.eth.gas_price,
        }
        
        # Only add value if it exists and is not zero
        if tx_data.value and tx_data.value != '0':
            transaction['value'] = int(tx_data.value)
        
        return transaction
    
    async def execute_transaction(self, tx_data: TransactionData) -> str:
        """
        Execute a single transaction.
        
        Args:
            tx_data: Transaction data to execute
            
        Returns:
            Transaction hash
        """
        try:
            # Get current nonce
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            # Prepare transaction
            transaction = self._prepare_transaction(tx_data, nonce)
            
            # Estimate gas
            try:
                gas_estimate = self.w3.eth.estimate_gas(transaction)
                transaction['gas'] = int(gas_estimate * 1.2)  # Add 20% buffer
            except Exception as e:
                print(f"Gas estimation failed, using default: {e}")
            
            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            return tx_hash.hex()
            
        except Exception as e:
            raise StargateTransactionError(f"Failed to execute transaction: {e}")
    
    async def wait_for_transaction(self, tx_hash: str, timeout: int = 300) -> Dict[str, Any]:
        """
        Wait for a transaction to be confirmed.
        
        Args:
            tx_hash: Transaction hash to wait for
            timeout: Timeout in seconds
            
        Returns:
            Transaction receipt
        """
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
            return dict(receipt)
        except Exception as e:
            raise StargateTransactionError(f"Transaction failed or timed out: {e}")
    
    async def execute_route(self, route_data: Dict[str, Any]) -> List[str]:
        """
        Execute all steps in a Stargate route.
        
        Args:
            route_data: Route data containing steps
            
        Returns:
            List of transaction hashes
        """
        if not route_data.get('steps'):
            raise StargateTransactionError("No steps found in route data")
        
        tx_hashes = []
        
        for i, step in enumerate(route_data['steps']):
            print(f"Executing step {i + 1}/{len(route_data['steps'])}")
            
            # Extract transaction data
            tx_info = step.get('transaction', {})
            tx_data = TransactionData(
                to=tx_info.get('to', ''),
                data=tx_info.get('data', ''),
                value=tx_info.get('value', '0')
            )
            
            # Execute transaction
            tx_hash = await self.execute_transaction(tx_data)
            print(f"Step {i + 1} transaction hash: {tx_hash}")
            
            # Wait for confirmation
            receipt = await self.wait_for_transaction(tx_hash)
            print(f"Step {i + 1} confirmed: {receipt['status']}")
            
            tx_hashes.append(tx_hash)
            
            # Small delay between transactions
            await asyncio.sleep(1)
        
        return tx_hashes
    
    async def transfer(
        self,
        src_token: str,
        dst_token: str,
        src_chain_key: str,
        dst_chain_key: str,
        amount: str,
        src_address: Optional[str] = None,
        dst_address: Optional[str] = None,
        slippage_tolerance: float = 0.05
    ) -> List[str]:
        """
        High-level method to execute a cross-chain transfer.
        
        Args:
            src_token: Source token address
            dst_token: Destination token address
            src_chain_key: Source chain key
            dst_chain_key: Destination chain key
            amount: Amount to transfer (in token's smallest unit)
            src_address: Source address (defaults to wallet address)
            dst_address: Destination address (defaults to wallet address)
            slippage_tolerance: Slippage tolerance (0.05 = 5%)
            
        Returns:
            List of transaction hashes
        """
        # Use wallet address as default
        src_address = src_address or self.account.address
        dst_address = dst_address or self.account.address
        
        # Calculate minimum destination amount with slippage
        dst_amount_min = str(int(int(amount) * (1 - slippage_tolerance)))
        
        # Create quote parameters
        quote_params = QuoteParams(
            src_token=src_token,
            dst_token=dst_token,
            src_address=src_address,
            dst_address=dst_address,
            src_chain_key=src_chain_key,
            dst_chain_key=dst_chain_key,
            src_amount=amount,
            dst_amount_min=dst_amount_min
        )
        
        # Get quotes
        quotes_data = await self.get_quotes(quote_params)
        
        if not quotes_data.get('quotes'):
            raise StargateAPIError("No quotes available for this transfer")
        
        # Select the first available route
        selected_route = quotes_data['quotes'][0]
        print(f"Selected route with {len(selected_route['steps'])} steps")
        
        # Execute the route
        return await self.execute_route(selected_route)

