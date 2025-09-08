"""Alma Item Update blueprint"""
import azure.functions as func

from alma_item_checks_update_service.config import UPDATE_QUEUE, STORAGE_CONNECTION_SETTING_NAME
from alma_item_checks_update_service.services.update_service import UpdateService

bp: func.Blueprint = func.Blueprint()


@bp.function_name("alma_item_update")
@bp.queue_trigger(
    arg_name="itemmsg",
    queue_name=UPDATE_QUEUE,
    connection=STORAGE_CONNECTION_SETTING_NAME
)
def alma_item_update(itemmsg: func.QueueMessage) -> None:
    """
    Alma Item Update blueprint

    Args:
        itemmsg (func.QueueMessage): Queue message
    """
    update_service = UpdateService(itemmsg)
    update_service.update_item()
