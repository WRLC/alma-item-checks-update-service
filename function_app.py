"""Azure Function App"""
import azure.functions as func

from alma_item_checks_update_service.blueprints.bp_update import bp as bp_update

app = func.FunctionApp()

app.register_blueprint(bp_update)
