from domain.models import Visitor, ActionType
from domain.resource_info import ResourceInfoDTO


def format_note(resource_info: ResourceInfoDTO, visitor: Visitor, available_action: ActionType) -> str:
    """Выводит информацию про ресурс + доступные действия"""
    command = available_action.value
    note = f"{resource_info.description()}\r\n{command}{resource_info.id}\r\n"
    if available_action == ActionType.RETURN:
        note += f"{ActionType.CHANGE.value}{resource_info.id}\r\n"
    if visitor.is_admin:
        note += f"{ActionType.EDIT.value}{resource_info.id}\r\n"
        note += f"{ActionType.HISTORY.value}{resource_info.id}\r\n"
    note += "\r\n"
    return note
