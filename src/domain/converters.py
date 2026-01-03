from typing import List

from domain.models import Resource, Record
from domain.resource_info import ResourceInfoDTO


def convert_resource_to_dto(resource: Resource, take_record: Record) -> ResourceInfoDTO:
    return ResourceInfoDTO(
        id=resource.id,
        name=resource.name,
        category_name=resource.category_name,
        vendor_code=resource.vendor_code,
        reg_date=resource.reg_date,
        firmware=resource.firmware,
        comment=resource.comment,
        user_email=take_record.user_email if take_record else None,
        address=take_record.address if take_record else None,
        take_date=take_record.take_date if take_record else None,
        return_date=take_record.return_date if take_record else None
    )


def convert_resources_to_resource_info(resources_with_records: List[Resource]) -> List[ResourceInfoDTO]:
    return [convert_resource_to_dto(resource, resource.take_record) for resource in resources_with_records]
