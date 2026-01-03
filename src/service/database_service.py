import asyncio
import logging
from io import StringIO
from typing import List

from database.uow import UnitOfWork
from domain.models import CATEGORIES, Category


class DatabaseService:
    def __init__(self, unit_of_work: UnitOfWork):
        self.unit_of_work = unit_of_work

    async def init(self) -> None:
        try:
            async with self.unit_of_work as uow:
                await uow.database.start()
            await self.prepare_data()
            logging.info("БД инициализирована")
        except Exception:
            logging.error("Не удалось инициализировать БД, работа приложения завершена", exc_info=True)
            exit()

    async def prepare_data(self) -> None:
        async with self.unit_of_work as uow:
            categories = await uow.categories.list()
            if len(categories) != 0:
                return
            for category in CATEGORIES:
                uow.categories.add(Category(name=category))
            logging.info(f"В БД добавлены категории: {' '.join(CATEGORIES)}")

    async def drop_base(self) -> None:
        async with self.unit_of_work as uow:
            await uow.database.drop()

    async def get_revisions_from_db(self) -> List[str]:
        async with self.unit_of_work as uow:
            return await uow.database.get_revisions()

    async def get_revisions_from_cli(self) -> StringIO:
        """Получает историю ревизий командой алембика в консоли"""
        shell = await asyncio.create_subprocess_shell(
            cmd="cd .. && alembic history --verbose",
            shell=True,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await shell.communicate()
        revisions = "" if stderr else stdout.decode("utf-8")
        result = StringIO()
        result.name = str("revision")
        result.write(revisions)
        result.seek(0)
        return result
