"""Service class for Alma Item Updates"""

import json
import logging
from typing import Any

import azure.core.exceptions
import azure.functions as func
import requests
from wrlc_alma_api_client import AlmaApiClient  # type: ignore
from wrlc_alma_api_client.exceptions import (  # type: ignore
    NotFoundError,
    InvalidInputError,
    AlmaApiError,
)
from wrlc_alma_api_client.models import Item  # type: ignore
from wrlc_azure_storage_service import StorageService  # type: ignore

from alma_item_checks_update_service.config import (
    API_CLIENT_TIMEOUT,
    INSTITUTION_API_ENDPOINT,
    INSTITUTION_API_KEY,
    NOTIFICATION_QUEUE,
    STORAGE_CONNECTION_STRING,
    UPDATED_ITEMS_CONTAINER,
    REPORT_CONTAINER,
)


# noinspection PyMethodMayBeStatic
class UpdateService:
    """Service class for Alma Item Updates"""

    def __init__(self, itemmsg: func.QueueMessage) -> None:
        """Initialize the service

        Args:
            itemmsg (func.QueueMessage): Queue message
        """
        self.itemmsg: func.QueueMessage = itemmsg

    def update_item(self) -> None:
        """Update the item in Alma"""
        message_data: dict[str, Any] = json.loads(  # get queued message
            self.itemmsg.get_body().decode()
        )

        job_id: str | None = message_data["job_id"]  # get job_id from message data
        if job_id is None:
            logging.error("UpdateService.update_item: No job id provided")
            return

        full_item = self.get_item_data(job_id)  # get item details from blob
        if full_item is None:
            logging.error("UpdateService.update_item: Item not found")
            return

        item: Item = Item(  # Create Item object from the full item data
            bib_data=full_item.get("bib_data"),  # bib data
            holding_data=full_item.get("holding_data"),  # holding data
            item_data=full_item.get("item_data"),  # item data
            link=full_item.get("link"),  # link
        )

        bib_data = full_item.get("bib_data", {})  # Extract bib data from item
        holding_data = full_item.get(
            "holding_data", {}
        )  # Extract holding data from item
        item_data_section = full_item.get(
            "item_data", {}
        )  # Extract item data from item

        mms_id = bib_data.get("mms_id")  # Get mms_id
        holding_id = holding_data.get("holding_id")  # Get holding_id
        item_pid = item_data_section.get("pid")  # Get item_pid

        if not all([mms_id, holding_id, item_pid]):  # Handle missing data
            logging.error(
                f"UpdateService.update_item: Missing required IDs - mms_id: {mms_id}, holding_id: {holding_id}, "
                f"item_pid: {item_pid}"
            )
            return

        institution_id: str | None = message_data.get(
            "institution_id"
        )  # get institution ID
        if institution_id is None:
            logging.error("UpdateService.update_item: No institution id provided")
            return

        api_key: str | None = self.get_api_key(
            int(institution_id)
        )  # get API key for institution

        alma_api_client: AlmaApiClient = AlmaApiClient(  # intialize Alma API client
            api_key=str(api_key), region="NA", timeout=API_CLIENT_TIMEOUT
        )

        try:
            alma_api_client.items.update_item(  # Update Alma item record
                mms_id=mms_id,
                holding_id=holding_id,
                item_pid=item_pid,
                item_record_data=item,
            )
        except (
            ValueError,
            NotFoundError,
            InvalidInputError,
            AlmaApiError,
            Exception,
        ) as e:
            logging.error(f"UpdateService.update_item: Failed to update item: {e}")
            return

        self.save_report(item, job_id)  # Save report blob

        self.send_notification(message_data)  # Queue notification message

    def get_item_data(self, job_id: str) -> dict[str, Any] | None:
        """Get item details

        Args:
            job_id (str): Job ID

        Returns:
            dict[str, Any]: Item details or None
        """
        storage_service: StorageService = StorageService(  # initialize storage service
            storage_connection_string=STORAGE_CONNECTION_STRING
        )

        try:
            item: dict[str, Any] | None = (
                storage_service.download_blob_as_json(  # get item data from container
                    container_name=UPDATED_ITEMS_CONTAINER,
                    blob_name=job_id + ".json",
                )
            )
        except (
            ValueError,
            json.JSONDecodeError,
            azure.core.exceptions.ResourceNotFoundError,
            azure.core.exceptions.ServiceRequestError,
            Exception,
        ) as e:
            logging.warning(
                f"UpdateService.update_item: Failed to download item from storage service: {e}"
            )
            return None

        if item is None:
            logging.warning("UpdateService.update_item: No item provided")
            return None

        return item

    def get_api_key(self, institution_id: int) -> str | None:
        """Get institution api key

        Args:
            institution_id (str): institution id

        Returns:
            str: institution api key or None
        """
        params: dict[str, Any] = {"code": INSTITUTION_API_KEY}
        url: str = f"{INSTITUTION_API_ENDPOINT}/{institution_id}/api-key"

        try:
            response: requests.Response = (
                requests.get(  # send request to Institution API
                    url, params=params, timeout=API_CLIENT_TIMEOUT
                )
            )
            response.raise_for_status()  # raise http errors as errors
            api_key: str | None = response.json()["api_key"]  # get the API key
        except (requests.exceptions.HTTPError, Exception) as err:  # Handle HTTP error
            logging.warning(f"UpdateService.update_item: Failed to get API key: {err}")
            return None

        if api_key is None:  # Handle missing API key
            logging.warning(
                "UpdateService.update_item: No institution api key provided"
            )
            return None

        return api_key

    def save_report(self, item: Item, job_id: str) -> None:
        """Save report data

        Args:
            item (Item): Item object
            job_id (str): Job id
        """

        storage_service: StorageService = StorageService(  # Initialize storage service
            storage_connection_string=STORAGE_CONNECTION_STRING
        )

        report_data: dict[str, Any] = {  # Create report data
            "Title": item.bib_data.title,
            "Barcode": item.item_data.barcode,
            "Item Call Number": item.item_data.alternative_call_number,
        }

        if item.item_data.internal_note_1:
            report_data["Internal Note 1"] = item.item_data.internal_note_1

        if item.item_data.provenance.desc:
            report_data["Provenance Code"] = item.item_data.provenance.desc

        storage_service.upload_blob_data(  # Save report to container
            container_name=REPORT_CONTAINER,
            blob_name=job_id + ".json",
            data=json.dumps(report_data),
        )

    def send_notification(self, message_data: dict[str, Any]) -> None:
        """Send notification about update

        Args:
            message_data (dict[str, Any]): message data
        """
        storage_service: StorageService = StorageService(  # Initialize storage service
            storage_connection_string=STORAGE_CONNECTION_STRING
        )

        storage_service.send_queue_message(  # Queue notification message
            queue_name=NOTIFICATION_QUEUE, message_content=message_data
        )
