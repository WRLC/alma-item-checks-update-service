"""Unit tests for UpdateService"""
import json
from unittest.mock import Mock, patch, MagicMock
import pytest
import azure.functions as func
import azure.core.exceptions
import requests
from wrlc_alma_api_client.exceptions import NotFoundError, InvalidInputError, AlmaApiError
from wrlc_alma_api_client.models import Item

from alma_item_checks_update_service.services.update_service import UpdateService


class TestUpdateService:
    """Test class for UpdateService"""

    @pytest.fixture
    def mock_queue_message(self):
        """Mock queue message fixture"""
        mock_msg = Mock(spec=func.QueueMessage)
        test_data = {"job_id": "test-job-123", "institution_id": "12345"}
        mock_msg.get_body.return_value = Mock()
        mock_msg.get_body.return_value.decode.return_value = json.dumps(test_data)
        return mock_msg

    @pytest.fixture
    def update_service(self, mock_queue_message):
        """UpdateService fixture"""
        return UpdateService(mock_queue_message)

    @pytest.fixture
    def mock_item_data(self):
        """Mock item data fixture"""
        return {
            "bib_data": {"title": "Test Book", "mms_id": "test-mms-123"},
            "holding_data": {"holding_id": "test-holding-123", "library": {"value": "MAIN", "desc": "Test Library"}},
            "item_data": {"pid": "test-pid-123", "barcode": "123456789"},
            "link": "https://api.example.com/item/123"
        }

    def test_init(self, mock_queue_message):
        """Test UpdateService initialization"""
        service = UpdateService(mock_queue_message)
        assert service.itemmsg == mock_queue_message

    @patch('alma_item_checks_update_service.services.update_service.Item')
    @patch('alma_item_checks_update_service.services.update_service.AlmaApiClient')
    @patch('alma_item_checks_update_service.services.update_service.logging')
    def test_update_item_success(self, mock_logging, mock_alma_client, mock_item_class, update_service, mock_item_data):
        """Test successful item update"""
        with patch.object(update_service, 'get_item_data') as mock_get_item, \
             patch.object(update_service, 'get_api_key') as mock_get_api_key, \
             patch.object(update_service, 'send_notification') as mock_send_notification:

            mock_get_item.return_value = mock_item_data
            mock_get_api_key.return_value = "test-api-key"

            # Mock the Item class
            mock_item_instance = Mock()
            mock_item_class.return_value = mock_item_instance

            mock_client_instance = Mock()
            mock_alma_client.return_value = mock_client_instance

            update_service.update_item()

            mock_get_item.assert_called_once_with("test-job-123")
            mock_get_api_key.assert_called_once_with(12345)
            mock_alma_client.assert_called_once_with(
                api_key="test-api-key",
                region='NA',
                timeout=90
            )

            # Verify Item was created with correct data
            mock_item_class.assert_called_once_with(
                bib_data=mock_item_data["bib_data"],
                holding_data=mock_item_data["holding_data"],
                item_data=mock_item_data["item_data"],
                link=mock_item_data["link"]
            )

            # Verify update_item was called with the Item instance
            mock_client_instance.items.update_item.assert_called_once_with(
                mms_id="test-mms-123",
                holding_id="test-holding-123",
                item_pid="test-pid-123",
                item_record_data=mock_item_instance
            )
            mock_send_notification.assert_called_once()

    @patch('alma_item_checks_update_service.services.update_service.logging')
    def test_update_item_no_job_id(self, mock_logging, update_service):
        """Test update_item with no job_id"""
        mock_queue_message = Mock(spec=func.QueueMessage)
        test_data = {"job_id": None}
        mock_queue_message.get_body.return_value = Mock()
        mock_queue_message.get_body.return_value.decode.return_value = json.dumps(test_data)

        service = UpdateService(mock_queue_message)
        service.update_item()

        mock_logging.error.assert_called_with("UpdateService.update_item: No job id provided")

    @patch('alma_item_checks_update_service.services.update_service.logging')
    def test_update_item_no_item_found(self, mock_logging, update_service):
        """Test update_item when item is not found"""
        with patch.object(update_service, 'get_item_data') as mock_get_item:
            mock_get_item.return_value = None

            update_service.update_item()

            mock_logging.error.assert_called_with("UpdateService.update_item: Item not found")

    @patch('alma_item_checks_update_service.services.update_service.Item')
    @patch('alma_item_checks_update_service.services.update_service.logging')
    def test_update_item_no_institution_id(self, mock_logging, mock_item_class, update_service, mock_item_data):
        """Test update_item when institution_id is None"""
        # Create a queue message without institution_id
        mock_queue_message = Mock(spec=func.QueueMessage)
        test_data = {"job_id": "test-job-123", "institution_id": None}
        mock_queue_message.get_body.return_value = Mock()
        mock_queue_message.get_body.return_value.decode.return_value = json.dumps(test_data)

        service = UpdateService(mock_queue_message)

        # Mock the Item class
        mock_item_instance = Mock()
        mock_item_class.return_value = mock_item_instance

        with patch.object(service, 'get_item_data') as mock_get_item:
            mock_get_item.return_value = mock_item_data
            service.update_item()

        mock_logging.error.assert_called_with("UpdateService.update_item: No institution id provided")

    @patch('alma_item_checks_update_service.services.update_service.Item')
    @patch('alma_item_checks_update_service.services.update_service.AlmaApiClient')
    @patch('alma_item_checks_update_service.services.update_service.logging')
    def test_update_item_api_error(self, mock_logging, mock_alma_client, mock_item_class, update_service, mock_item_data):
        """Test update_item with API error"""
        with patch.object(update_service, 'get_item_data') as mock_get_item, \
             patch.object(update_service, 'get_api_key') as mock_get_api_key:

            mock_get_item.return_value = mock_item_data
            mock_get_api_key.return_value = "test-api-key"

            # Mock the Item class
            mock_item_instance = Mock()
            mock_item_class.return_value = mock_item_instance

            mock_client_instance = Mock()
            mock_client_instance.items.update_item.side_effect = AlmaApiError("API Error")
            mock_alma_client.return_value = mock_client_instance

            update_service.update_item()

            # Check that the error was logged with correct message format
            calls = mock_logging.error.call_args_list
            assert len(calls) >= 1
            call_message = calls[-1][0][0]
            assert "UpdateService.update_item: Failed to update item:" in call_message
            assert "API Error" in call_message

    @patch('alma_item_checks_update_service.services.update_service.StorageService')
    def test_get_item_data_success(self, mock_storage_service, update_service, mock_item_data):
        """Test successful get_item_data"""
        mock_storage_instance = Mock()
        mock_storage_instance.download_blob_as_json.return_value = mock_item_data
        mock_storage_service.return_value = mock_storage_instance

        result = update_service.get_item_data("test-job-123")

        assert result == mock_item_data
        mock_storage_instance.download_blob_as_json.assert_called_once_with(
            container_name="updated-items-container",
            blob_name="test-job-123.json"
        )

    @patch('alma_item_checks_update_service.services.update_service.StorageService')
    @patch('alma_item_checks_update_service.services.update_service.logging')
    def test_get_item_data_storage_error(self, mock_logging, mock_storage_service, update_service):
        """Test get_item_data with storage error"""
        mock_storage_instance = Mock()
        mock_storage_instance.download_blob_as_json.side_effect = azure.core.exceptions.ResourceNotFoundError("Not found")
        mock_storage_service.return_value = mock_storage_instance

        result = update_service.get_item_data("test-job-123")

        assert result is None
        mock_logging.warning.assert_called_with("UpdateService.update_item: Failed to download item from storage service: Not found")

    @patch('alma_item_checks_update_service.services.update_service.StorageService')
    @patch('alma_item_checks_update_service.services.update_service.logging')
    def test_get_item_data_none_item(self, mock_logging, mock_storage_service, update_service):
        """Test get_item_data when item is None"""
        mock_storage_instance = Mock()
        mock_storage_instance.download_blob_as_json.return_value = None
        mock_storage_service.return_value = mock_storage_instance

        result = update_service.get_item_data("test-job-123")

        assert result is None
        mock_logging.warning.assert_called_with("UpdateService.update_item: No item provided")

    @patch('alma_item_checks_update_service.services.update_service.requests')
    def test_get_api_key_success(self, mock_requests, update_service):
        """Test successful get_api_key"""
        mock_response = Mock()
        mock_response.json.return_value = {"api_key": "test-api-key-123"}
        mock_requests.get.return_value = mock_response

        result = update_service.get_api_key(12345)

        assert result == "test-api-key-123"
        mock_requests.get.assert_called_once()
        mock_response.raise_for_status.assert_called_once()

    @patch('alma_item_checks_update_service.services.update_service.requests')
    @patch('alma_item_checks_update_service.services.update_service.logging')
    def test_get_api_key_http_error(self, mock_logging, mock_requests, update_service):
        """Test get_api_key with HTTP error"""
        mock_response = Mock()
        # Use the real HTTPError class
        from requests.exceptions import HTTPError
        mock_response.raise_for_status.side_effect = HTTPError("HTTP Error")
        mock_requests.get.return_value = mock_response
        mock_requests.exceptions = requests.exceptions  # Ensure exceptions module is available

        result = update_service.get_api_key(12345)

        assert result is None
        mock_logging.warning.assert_called_with("UpdateService.update_item: Failed to get API key: HTTP Error")

    @patch('alma_item_checks_update_service.services.update_service.requests')
    @patch('alma_item_checks_update_service.services.update_service.logging')
    def test_get_api_key_none_response(self, mock_logging, mock_requests, update_service):
        """Test get_api_key when API key is None in response"""
        mock_response = Mock()
        mock_response.json.return_value = {"api_key": None}
        mock_requests.get.return_value = mock_response

        result = update_service.get_api_key(12345)

        assert result is None
        mock_logging.warning.assert_called_with("UpdateService.update_item: No institution api key provided")

    @patch('alma_item_checks_update_service.services.update_service.StorageService')
    def test_send_notification_success(self, mock_storage_service, update_service):
        """Test successful send_notification"""
        mock_storage_instance = Mock()
        mock_storage_service.return_value = mock_storage_instance

        message_data = {"job_id": "test-job-123", "status": "updated"}
        update_service.send_notification(message_data)

        mock_storage_instance.send_queue_message.assert_called_once_with(
            queue_name="notification-queue",
            message_content=message_data
        )

    @pytest.mark.parametrize("exception_type,error_message", [
        (NotFoundError, "Not found error"),
        (InvalidInputError, "Invalid input error"),
        (AlmaApiError, "Alma API error"),
        (ValueError, "Value error"),
        (Exception, "Generic exception")
    ])
    @patch('alma_item_checks_update_service.services.update_service.Item')
    @patch('alma_item_checks_update_service.services.update_service.AlmaApiClient')
    @patch('alma_item_checks_update_service.services.update_service.logging')
    def test_update_item_various_exceptions(self, mock_logging, mock_alma_client, mock_item_class,
                                          exception_type, error_message, update_service, mock_item_data):
        """Test update_item with various exception types"""
        with patch.object(update_service, 'get_item_data') as mock_get_item, \
             patch.object(update_service, 'get_api_key') as mock_get_api_key:

            mock_get_item.return_value = mock_item_data
            mock_get_api_key.return_value = "test-api-key"

            # Mock the Item class
            mock_item_instance = Mock()
            mock_item_class.return_value = mock_item_instance

            mock_client_instance = Mock()
            mock_client_instance.items.update_item.side_effect = exception_type(error_message)
            mock_alma_client.return_value = mock_client_instance

            update_service.update_item()

            # Some exceptions may have different string representations
            calls = mock_logging.error.call_args_list
            assert len(calls) >= 1
            call_message = calls[-1][0][0]
            assert "UpdateService.update_item: Failed to update item:" in call_message
            assert error_message in call_message

    @pytest.mark.parametrize("exception_type", [
        ValueError,
        json.JSONDecodeError,
        azure.core.exceptions.ResourceNotFoundError,
        azure.core.exceptions.ServiceRequestError,
        Exception
    ])
    @patch('alma_item_checks_update_service.services.update_service.StorageService')
    @patch('alma_item_checks_update_service.services.update_service.logging')
    def test_get_item_data_various_exceptions(self, mock_logging, mock_storage_service,
                                            exception_type, update_service):
        """Test get_item_data with various exception types"""
        mock_storage_instance = Mock()
        if exception_type == json.JSONDecodeError:
            mock_storage_instance.download_blob_as_json.side_effect = exception_type("msg", "doc", 0)
        else:
            mock_storage_instance.download_blob_as_json.side_effect = exception_type("Test error")
        mock_storage_service.return_value = mock_storage_instance

        result = update_service.get_item_data("test-job-123")

        assert result is None
        mock_logging.warning.assert_called()
