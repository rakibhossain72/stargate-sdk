import pytest
import asyncio
from unittest.mock import patch, Mock, AsyncMock
from stargate_bridge import StargateClient, Tokens


@pytest.mark.integration
class TestIntegration:
    """Integration test cases."""

    @pytest.mark.asyncio
    async def test_full_transfer_flow_mock(self):
        """Test full transfer flow with mocked dependencies."""
        private_key = "0x1234567890123456789012345678901234567890123456789012345678901234"
        
        # Mock API response
        mock_api_response = {
            "quotes": [
                {
                    "steps": [
                        {
                            "transaction": {
                                "to": "0x1234567890123456789012345678901234567890",
                                "data": "0x1234567890abcdef",
                                "value": "0"
                            }
                        }
                    ]
                }
            ]
        }
        
        with patch.dict('os.environ', {'EVM_PRIVATE_KEY': private_key}):
            with patch('stargate_bridge.client.Web3') as mock_web3:
                with patch('stargate_bridge.client.Account') as mock_account:
                    with patch('httpx.AsyncClient') as mock_httpx:
                        
                        # Setup mocks
                        mock_w3_instance = Mock()
                        mock_web3.return_value = mock_w3_instance
                        
                        mock_account_instance = Mock()
                        mock_account_instance.address = "0x1234567890123456789012345678901234567890"
                        mock_account.from_key.return_value = mock_account_instance
                        
                        mock_http_client = Mock()
                        mock_httpx.return_value = mock_http_client
                        
                        # Mock HTTP response
                        mock_response = Mock()
                        mock_response.json.return_value = mock_api_response
                        mock_http_client.get = AsyncMock(return_value=mock_response)
                        mock_http_client.aclose = AsyncMock()
                        
                        # Mock Web3 methods
                        mock_w3_instance.eth.get_transaction_count.return_value = 42
                        mock_w3_instance.eth.gas_price = 20000000000
                        mock_w3_instance.eth.estimate_gas.return_value = 150000
                        mock_tx_hash = Mock()
                        mock_tx_hash.hex.return_value = "0xabcdef1234567890"
                        mock_w3_instance.eth.send_raw_transaction.return_value = mock_tx_hash
                        mock_w3_instance.eth.wait_for_transaction_receipt.return_value = {'status': 1}
                        
                        # Mock signing
                        mock_signed_txn = Mock()
                        mock_signed_txn.rawTransaction = b"signed_data"
                        mock_w3_instance.eth.account.sign_transaction.return_value = mock_signed_txn
                        
                        # Execute transfer
                        async with StargateClient() as client:
                            result = await client.transfer(
                                src_token=Tokens.ETHEREUM['USDC'],
                                dst_token=Tokens.POLYGON['USDC'],
                                src_chain_key='ethereum',
                                dst_chain_key='polygon',
                                amount='1000000'
                            )
                        
                        # Verify result
                        assert len(result) == 1
                        assert result[0] == "0xabcdef1234567890"
                        
                        # Verify API call was made
                        mock_http_client.get.assert_called()
                        
                        # Verify transaction was executed
                        mock_w3_instance.eth.send_raw_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling in integration scenario."""
        private_key = "0x1234567890123456789012345678901234567890123456789012345678901234"
        
        with patch.dict('os.environ', {'EVM_PRIVATE_KEY': private_key}):
            with patch('stargate_bridge.client.Web3'):
                with patch('stargate_bridge.client.Account'):
                    with patch('httpx.AsyncClient') as mock_httpx:
                        
                        # Mock HTTP client that raises an error
                        mock_http_client = Mock()
                        mock_httpx.return_value = mock_http_client
                        mock_http_client.get = AsyncMock(side_effect=Exception("Network error"))
                        mock_http_client.aclose = AsyncMock()
                        
                        # Test that error is properly handled
                        async with StargateClient() as client:
                            with pytest.raises(Exception):
                                await client.get_quotes(Mock())

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_rate_limiting_simulation(self):
        """Test rate limiting behavior simulation."""
        private_key = "0x1234567890123456789012345678901234567890123456789012345678901234"
        
        with patch.dict('os.environ', {'EVM_PRIVATE_KEY': private_key}):
            with patch('stargate_bridge.client.Web3'):
                with patch('stargate_bridge.client.Account'):
                    with patch('httpx.AsyncClient') as mock_httpx:
                        
                        mock_http_client = Mock()
                        mock_httpx.return_value = mock_http_client
                        mock_http_client.aclose = AsyncMock()
                        
                        # Simulate rate limiting
                        call_count = 0
                        async def mock_get(*args, **kwargs):
                            nonlocal call_count
                            call_count += 1
                            if call_count <= 2:
                                # First two calls succeed
                                mock_response = Mock()
                                mock_response.json.return_value = {"chains": {}}
                                return mock_response
                            else:
                                # Third call fails (rate limited)
                                import httpx
                                raise httpx.HTTPStatusError(
                                    "Rate limited", 
                                    request=Mock(), 
                                    response=Mock(status_code=429)
                                )
                        
                        mock_http_client.get = mock_get
                        
                        async with StargateClient() as client:
                            # First two calls should succeed
                            await client.get_supported_chains()
                            await client.get_supported_chains()
                            
                            # Third call should fail
                            with pytest.raises(Exception):
                                await client.get_supported_chains()

