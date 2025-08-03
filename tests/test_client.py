import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import httpx
from stargate_bridge import StargateClient, QuoteParams, Tokens
from stargate_bridge.exceptions import StargateAPIError, StargateTransactionError


class TestStargateClient:
    """Test cases for StargateClient class."""

    def test_client_initialization_with_private_key(self):
        """Test client initialization with private key."""
        private_key = "0x1234567890123456789012345678901234567890123456789012345678901234"
        
        with patch('stargate_bridge.client.Web3'):
            with patch('stargate_bridge.client.Account') as mock_account:
                client = StargateClient(private_key=private_key)
                assert client.private_key == private_key
                mock_account.from_key.assert_called_once_with(private_key)

    def test_client_initialization_with_env_var(self):
        """Test client initialization with environment variable."""
        private_key = "1234567890123456789012345678901234567890123456789012345678901234"
        expected_key = "0x" + private_key
        
        with patch.dict('os.environ', {'EVM_PRIVATE_KEY': private_key}):
            with patch('stargate_bridge.client.Web3'):
                with patch('stargate_bridge.client.Account') as mock_account:
                    client = StargateClient()
                    assert client.private_key == expected_key
                    mock_account.from_key.assert_called_once_with(expected_key)

    def test_client_initialization_no_private_key(self):
        """Test client initialization without private key raises error."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="Private key must be provided"):
                StargateClient()

    @pytest.mark.asyncio
    async def test_get_supported_chains_success(self, mock_client):
        """Test successful get_supported_chains call."""
        expected_response = {"ethereum": {"chainId": 1}, "polygon": {"chainId": 137}}
        
        with patch.object(mock_client, 'http_client') as mock_http:
            mock_response = Mock()
            mock_response.json.return_value = expected_response
            mock_http.get = AsyncMock(return_value=mock_response)
            
            result = await mock_client.get_supported_chains()
            
            assert result == expected_response
            mock_http.get.assert_called_once_with(f"{mock_client.api_base_url}/chains")

    @pytest.mark.asyncio
    async def test_get_supported_chains_http_error(self, mock_client):
        """Test get_supported_chains with HTTP error."""
        with patch.object(mock_client, 'http_client') as mock_http:
            mock_http.get = AsyncMock(side_effect=httpx.HTTPError("Network error"))
            
            with pytest.raises(StargateAPIError, match="Failed to fetch supported chains"):
                await mock_client.get_supported_chains()

    @pytest.mark.asyncio
    async def test_get_quotes_success(self, mock_client, sample_quote_params, sample_api_response):
        """Test successful get_quotes call."""
        with patch.object(mock_client, 'http_client') as mock_http:
            mock_response = Mock()
            mock_response.json.return_value = sample_api_response
            mock_http.get = AsyncMock(return_value=mock_response)
            
            result = await mock_client.get_quotes(sample_quote_params)
            
            assert result == sample_api_response
            mock_http.get.assert_called_once()
            
            # Check the call arguments
            call_args = mock_http.get.call_args
            assert call_args[0][0] == f"{mock_client.api_base_url}/quotes"
            
            expected_params = {
                'srcToken': sample_quote_params.src_token,
                'dstToken': sample_quote_params.dst_token,
                'srcAddress': sample_quote_params.src_address,
                'dstAddress': sample_quote_params.dst_address,
                'srcChainKey': sample_quote_params.src_chain_key,
                'dstChainKey': sample_quote_params.dst_chain_key,
                'srcAmount': sample_quote_params.src_amount,
                'dstAmountMin': sample_quote_params.dst_amount_min
            }
            assert call_args[1]['params'] == expected_params

    @pytest.mark.asyncio
    async def test_get_quotes_http_error(self, mock_client, sample_quote_params):
        """Test get_quotes with HTTP error."""
        with patch.object(mock_client, 'http_client') as mock_http:
            mock_http.get = AsyncMock(side_effect=httpx.HTTPError("API error"))
            
            with pytest.raises(StargateAPIError, match="Failed to fetch quotes"):
                await mock_client.get_quotes(sample_quote_params)

    def test_prepare_transaction(self, mock_client, sample_transaction_data):
        """Test transaction preparation."""
        nonce = 42
        
        with patch.object(mock_client, 'w3') as mock_w3:
            mock_w3.eth.gas_price = 20000000000  # 20 Gwei
            
            result = mock_client._prepare_transaction(sample_transaction_data, nonce)
            
            expected = {
                'to': sample_transaction_data.to,
                'data': sample_transaction_data.data,
                'nonce': nonce,
                'gas': 300000,
                'gasPrice': 20000000000,
            }
            assert result == expected

    def test_prepare_transaction_with_value(self, mock_client):
        """Test transaction preparation with value."""
        tx_data = TransactionData(
            to="0x1234567890123456789012345678901234567890",
            data="0x1234567890abcdef",
            value="1000000000000000000"  # 1 ETH in wei
        )
        nonce = 42
        
        with patch.object(mock_client, 'w3') as mock_w3:
            mock_w3.eth.gas_price = 20000000000
            
            result = mock_client._prepare_transaction(tx_data, nonce)
            
            assert result['value'] == 1000000000000000000

    @pytest.mark.asyncio
    async def test_execute_transaction_success(self, mock_client, sample_transaction_data):
        """Test successful transaction execution."""
        expected_hash = "0xabcdef1234567890"
        
        with patch.object(mock_client, 'w3') as mock_w3:
            with patch.object(mock_client, 'account') as mock_account:
                # Mock Web3 methods
                mock_w3.eth.get_transaction_count.return_value = 42
                mock_w3.eth.gas_price = 20000000000
                mock_w3.eth.estimate_gas.return_value = 150000
                mock_w3.eth.send_raw_transaction.return_value.hex.return_value = expected_hash
                
                # Mock account methods
                mock_account.address = "0x1234567890123456789012345678901234567890"
                mock_signed_txn = Mock()
                mock_signed_txn.rawTransaction = b"signed_transaction_data"
                mock_w3.eth.account.sign_transaction.return_value = mock_signed_txn
                
                result = await mock_client.execute_transaction(sample_transaction_data)
                
                assert result == expected_hash
                mock_w3.eth.get_transaction_count.assert_called_once()
                mock_w3.eth.estimate_gas.assert_called_once()
                mock_w3.eth.send_raw_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_transaction_failure(self, mock_client, sample_transaction_data):
        """Test transaction execution failure."""
        with patch.object(mock_client, 'w3') as mock_w3:
            mock_w3.eth.get_transaction_count.side_effect = Exception("Network error")
            
            with pytest.raises(StargateTransactionError, match="Failed to execute transaction"):
                await mock_client.execute_transaction(sample_transaction_data)

    @pytest.mark.asyncio
    async def test_wait_for_transaction_success(self, mock_client):
        """Test successful transaction waiting."""
        tx_hash = "0xabcdef1234567890"
        expected_receipt = {'status': 1, 'blockNumber': 12345}
        
        with patch.object(mock_client, 'w3') as mock_w3:
            mock_w3.eth.wait_for_transaction_receipt.return_value = expected_receipt
            
            result = await mock_client.wait_for_transaction(tx_hash)
            
            assert result == expected_receipt
            mock_w3.eth.wait_for_transaction_receipt.assert_called_once_with(tx_hash, timeout=300)

    @pytest.mark.asyncio
    async def test_wait_for_transaction_timeout(self, mock_client):
        """Test transaction waiting timeout."""
        tx_hash = "0xabcdef1234567890"
        
        with patch.object(mock_client, 'w3') as mock_w3:
            mock_w3.eth.wait_for_transaction_receipt.side_effect = Exception("Timeout")
            
            with pytest.raises(StargateTransactionError, match="Transaction failed or timed out"):
                await mock_client.wait_for_transaction(tx_hash)

    @pytest.mark.asyncio
    async def test_execute_route_success(self, mock_client, sample_api_response):
        """Test successful route execution."""
        expected_hashes = ["0xhash1", "0xhash2"]
        
        with patch.object(mock_client, 'execute_transaction') as mock_execute:
            with patch.object(mock_client, 'wait_for_transaction') as mock_wait:
                mock_execute.side_effect = expected_hashes
                mock_wait.return_value = {'status': 1}
                
                route = sample_api_response['quotes'][0]
                result = await mock_client.execute_route(route)
                
                assert result == expected_hashes[:1]  # Only one step in sample
                assert mock_execute.call_count == 1
                assert mock_wait.call_count == 1

    @pytest.mark.asyncio
    async def test_execute_route_no_steps(self, mock_client):
        """Test route execution with no steps."""
        route_data = {'steps': []}
        
        with pytest.raises(StargateTransactionError, match="No steps found in route data"):
            await mock_client.execute_route(route_data)

    @pytest.mark.asyncio
    async def test_transfer_success(self, mock_client, sample_api_response):
        """Test successful high-level transfer."""
        expected_hashes = ["0xhash1"]
        
        with patch.object(mock_client, 'get_quotes') as mock_quotes:
            with patch.object(mock_client, 'execute_route') as mock_execute:
                with patch.object(mock_client, 'account') as mock_account:
                    mock_account.address = "0x1234567890123456789012345678901234567890"
                    mock_quotes.return_value = sample_api_response
                    mock_execute.return_value = expected_hashes
                    
                    result = await mock_client.transfer(
                        src_token=Tokens.ETHEREUM['USDC'],
                        dst_token=Tokens.POLYGON['USDC'],
                        src_chain_key='ethereum',
                        dst_chain_key='polygon',
                        amount='1000000'
                    )
                    
                    assert result == expected_hashes
                    mock_quotes.assert_called_once()
                    mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_transfer_no_quotes(self, mock_client):
        """Test transfer with no available quotes."""
        with patch.object(mock_client, 'get_quotes') as mock_quotes:
            with patch.object(mock_client, 'account') as mock_account:
                mock_account.address = "0x1234567890123456789012345678901234567890"
                mock_quotes.return_value = {'quotes': []}
                
                with pytest.raises(StargateAPIError, match="No quotes available"):
                    await mock_client.transfer(
                        src_token=Tokens.ETHEREUM['USDC'],
                        dst_token=Tokens.POLYGON['USDC'],
                        src_chain_key='ethereum',
                        dst_chain_key='polygon',
                        amount='1000000'
                    )

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_private_key):
        """Test async context manager functionality."""
        with patch.dict('os.environ', {'EVM_PRIVATE_KEY': mock_private_key}):
            with patch('stargate_bridge.client.Web3'):
                with patch('stargate_bridge.client.Account'):
                    with patch('httpx.AsyncClient') as mock_httpx:
                        mock_client_instance = Mock()
                        mock_client_instance.aclose = AsyncMock()
                        mock_httpx.return_value = mock_client_instance
                        
                        async with StargateClient() as client:
                            assert client is not None
                        
                        mock_client_instance.aclose.assert_called_once()
