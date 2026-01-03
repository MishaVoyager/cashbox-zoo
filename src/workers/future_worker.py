# async def notify_user_about_take(message: Message, email: str, resource: Resource) -> None:
#     """Уведомляет пользователя, что на него записали ресурс"""
#     # TODO убрать отсюда
#     visitor = await get_visitor(email)
#     if not visitor:
#         logging.info(f"Из-за ошибки авторизации не удалось уведомить пользователя с почтой {email} "
#                      f"о записи на него ресурса {repr(resource)}")
#         return None
#     if visitor.chat_id is None:
#         logging.info(
#             f"Не уведомили {email} о записи ресурса {repr(resource)}: пользователь еще не отправлял сообщений боту")
#         return None
#     await message.bot.send_message(
#         visitor.chat_id,
#         f"На вас записали {resource.short_str()}\r\n/return{resource.id} - если уже неактуально"
#     )
#
#
# async def notify_next_user_about_take(message: Message, next_user_email: str, resource: Resource) -> None:
#     """Уведомляет пользователя, что пришла его очередь, и на него записан ресурс"""
#     # TODO убрать отсюда
#
#     visitor = await get_visitor(next_user_email)
#     if not visitor:
#         logging.error(f"Не нашли пользователя {next_user_email}, чтобы уведомить "
#                       f"о записи на него ресурса: {repr(resource)}")
#         return None
#     if visitor.chat_id is None:
#         logging.error(f"Не уведомили {next_user_email}, что пришла его очередь занять "
#                       f"{repr(resource)}: отсутствует chat_id")
#         return None
#     next_user_chat_id = visitor.chat_id
#     await message.bot.send_message(
#         next_user_chat_id,
#         f"Записали на вас устройство {resource.name} c артикулом {resource.vendor_code}. Нажмите:\r\n"
#         f"/change{resource.id} - если подтверждаете,\r\n"
#         f"/return{resource.id} - если уже неактуально"
#     )
#
#
# async def notify_user_about_return(message: Message, email: str, resource: Resource) -> None:
#     """Уведомляет пользователя, что с него списали ресурс"""
#     # TODO убрать отсюда
#     visitor = await get_visitor(email)
#     if not visitor:
#         logging.error(f"Не нашли пользователя {email}, чтобы уведомить о списании с него "
#                       f"ресурса {repr(resource)}")
#         return None
#     if visitor.chat_id is None:
#         logging.info(f"Не уведомили {email} о списании ресурса {repr(resource)}: "
#                      f"он еще не отправлял сообщений боту")
#         return None
#     await message.bot.send_message(visitor.chat_id, f"С вас списали {resource.short_str()}")
#
#
# async def get_resource_info(resource_ids: list[int]) -> List[ResourceInfoDTO]:
#     async with get_session_factory()() as session:
#         query = select(Resource).filter(Resource.id.in_(resource_ids))
#         result = await session.execute(query)
#         resources = list(result.scalars().unique().all())
#     return convert_resources_to_resource_info(resources)
