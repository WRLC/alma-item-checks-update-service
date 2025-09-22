"""Configuration file for alma_item_checks_processor_service."""

import os

STORAGE_CONNECTION_SETTING_NAME = "AzureWebJobsStorage"
STORAGE_CONNECTION_STRING = os.getenv(STORAGE_CONNECTION_SETTING_NAME)

INSTITUTION_API_ENDPOINT = os.getenv("INSTITUTION_API_ENDPOINT")
INSTITUTION_API_KEY = os.getenv("INSTITUTION_API_KEY")

UPDATE_QUEUE = os.getenv(
    "UPDATE_QUEUE", "update-queue"
)  # For items that need Alma updates
NOTIFICATION_QUEUE = os.getenv(
    "NOTIFICATION_QUEUE", "notification-queue"
)  # For notifications about updates

UPDATED_ITEMS_CONTAINER = os.getenv(
    "UPDATED_ITEMS_CONTAINER", "updated-items-container"
)  # All updated item data

REPORT_CONTAINER = os.getenv("REPORT_CONTAINER", "reports-container")

API_CLIENT_TIMEOUT = int(os.getenv("API_CLIENT_TIMEOUT", 90))
