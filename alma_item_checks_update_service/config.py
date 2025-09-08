"""Configuration file for alma_item_checks_processor_service."""
import os

STORAGE_CONNECTION_SETTING_NAME = "AzureWebJobsStorage"
STORAGE_CONNECTION_STRING = os.getenv(STORAGE_CONNECTION_SETTING_NAME)

SQLALCHEMY_CONNECTION_STRING = os.getenv("SQLALCHEMY_CONNECTION_STRING")

INSTITUTION_API_ENDPOINT = os.getenv("INSTITUTION_API_ENDPOINT")
INSTITUTION_API_KEY = os.getenv("INSTITUTION_API_KEY")

UPDATE_QUEUE = os.getenv("UPDATE_QUEUE", "update-queue")  # For items that need Alma updates

UPDATED_ITEMS_CONTAINER = os.getenv("UPDATED_ITEMS_CONTAINER", "updated-items-container")  # All updated item data

API_CLIENT_TIMEOUT = int(os.getenv("API_CLIENT_TIMEOUT", 90))
