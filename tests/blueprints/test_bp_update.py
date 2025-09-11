"""Integration tests for bp_update blueprint"""
import json
from unittest.mock import Mock, patch
import pytest
import azure.functions as func

from alma_item_checks_update_service.blueprints.bp_update import alma_item_update


class TestBpUpdate:
    """Integration test class for bp_update blueprint"""

    @pytest.fixture
    def mock_queue_message(self):
        """Mock Azure Functions queue message fixture"""
        mock_msg = Mock(spec=func.QueueMessage)
        test_data = {"job_id": "integration-test-123", "institution_id": "67890"}
        mock_msg.get_body.return_value = Mock()
        mock_msg.get_body.return_value.decode.return_value = json.dumps(test_data)
        return mock_msg

    @patch('alma_item_checks_update_service.blueprints.bp_update.UpdateService')
    def test_alma_item_update_integration(self, mock_update_service_class, mock_queue_message):
        """Test the Azure Function entry point integration

        This is an integration test that verifies:
        1. The Azure Function entry point can be called
        2. UpdateService is properly instantiated with the queue message
        3. update_item method is called on the service instance
        """
        # Setup mock UpdateService instance
        mock_update_service_instance = Mock()
        mock_update_service_class.return_value = mock_update_service_instance

        # Call the Azure Function entry point
        alma_item_update(mock_queue_message)

        # Verify UpdateService was instantiated with the correct queue message
        mock_update_service_class.assert_called_once_with(mock_queue_message)

        # Verify update_item was called on the service instance
        mock_update_service_instance.update_item.assert_called_once()

    @patch('alma_item_checks_update_service.blueprints.bp_update.UpdateService')
    def test_alma_item_update_with_different_message(self, mock_update_service_class):
        """Test alma_item_update with a different queue message structure"""
        # Create a different mock message
        mock_msg = Mock(spec=func.QueueMessage)
        test_data = {"job_id": "different-test-456", "institution_id": "11111"}
        mock_msg.get_body.return_value = Mock()
        mock_msg.get_body.return_value.decode.return_value = json.dumps(test_data)

        # Setup mock UpdateService instance
        mock_update_service_instance = Mock()
        mock_update_service_class.return_value = mock_update_service_instance

        # Call the Azure Function entry point
        alma_item_update(mock_msg)

        # Verify the correct message was passed through
        mock_update_service_class.assert_called_once_with(mock_msg)
        mock_update_service_instance.update_item.assert_called_once()

    @patch('alma_item_checks_update_service.blueprints.bp_update.UpdateService')
    def test_alma_item_update_service_exception_propagates(self, mock_update_service_class):
        """Test that exceptions from UpdateService are properly propagated"""
        mock_msg = Mock(spec=func.QueueMessage)

        # Setup UpdateService to raise an exception
        mock_update_service_instance = Mock()
        mock_update_service_instance.update_item.side_effect = Exception("Service error")
        mock_update_service_class.return_value = mock_update_service_instance

        # Verify that the exception propagates (Azure Functions will handle it)
        with pytest.raises(Exception, match="Service error"):
            alma_item_update(mock_msg)

        # Verify the service was still properly instantiated and called
        mock_update_service_class.assert_called_once_with(mock_msg)
        mock_update_service_instance.update_item.assert_called_once()
