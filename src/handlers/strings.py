"""
Вспомогательный класс с текстами для роутеров
"""

from aiogram.types import Message

from database.models import Resource

from enum import StrEnum


class ResourceError(StrEnum):
    """Ошибки валидации ресурсов"""
    WRONG_ID = "Айди ресурса не является числом"
    EXISTED_ID = "Указан айди уже существующего устройства"
    EXISTED_VENDOR_CODE = "Указан артикул уже существующего устройства"
    NO_VENDOR_CODE = "Нет артикула"
    NO_NAME = "Нет названия"
    WRONG_CATEGORY = "Категория не из списка"
    WRONG_EMAIL = "Email должен быть в формате email@skbkontur.ru",
    WRONG_DATE = "Дата не соответствует формату: дд.мм.гггг"
    PASSED_DATE = "Дата из прошлого"
    WRONG_REG_DATE = "Дата регистрации должна быть в формате дд.мм.гггг"
    WRONG_RETURN_DATE = "Дата возврата должна быть в формате дд.мм.гггг и не в прошлом"


class ResourceColumn(StrEnum):
    """Названия колонок для загрузки таблицы с ресурсами"""
    id = "Айди"
    name = "Название"
    category_name = "Категория"
    vendor_code = "Артикул"
    reg_date = "Дата регистрации"
    firmware = "Прошивка"
    comment = "Комментарий"
    user_email = "Электронная почта"
    address = "Место устройства"
    return_date = "Дата возврата"

    @classmethod
    def cols(cls) -> list[str]:
        return [i.value for i in ResourceColumn]
    
    @classmethod
    def cols_str(cls) -> str:
        return ', '.join(cls.cols())


def get_table_error_msg(index: int, error: ResourceError) -> str:
    """Возвращает строку, в которой указан номер строки и ошибка"""
    return f"{table_error_prefix} {index + 2} {error.value.lower()}"


def get_username_str(message: Message) -> str:
    """Возвращает юзернейм по Message"""
    if message.from_user:
        return f" {message.from_user.username} "
    return ' '


def get_take_from_user_msg(email: str, resource: Resource) -> str:
    """Формирует сообщение о списании ресурсов - для админа"""
    return f"Вы списали {resource.short_str()} с пользователя {email}. " \
           f"Напомните ему, чтобы в следующий раз сам отмечался в боте, не зря ж мы его делали :)"


def get_pass_to_user_msg(resource: Resource) -> str:
    """Формирует сообщение о записи ресурса - для админа"""
    return f"Вы записали {resource.short_str()} на пользователя {resource.user_email}"


welcome_msg = "Добро пожаловать в бот кассового зоопарка!\r\n" \
              "Для поиска техники - введите серийный номер " \
              "или отсканируйте QR-код на устройстве и нажмите Start\r\n\r\n" \
              "Также вам помогут три команды:\r\n" \
              "/all - вся техника\r\n" \
              "/categories - по категориям\r\n" \
              "/mine - записанная на вас\r\n" \
              "/wishlist - за какими устройствами вы в очереди"

admin_welcome_msg = "Вы смотритель кассового зоопарка, поэтому вам доступны " \
                    "две дополнительных команды, скрытых из меню:\r\n" \
                    "/add - для добавления устройств\r\n" \
                    "/users - для изменения данных пользователей\r\n\r\n" \
                    "Также вы можете написать рабочую почту пользователя и увидеть, какие он взял устройства"


def auth_message(user_email: str, is_admin: bool) -> str:
    """Формирует сообщение об успешной авторизации"""
    return f"Проверка в Стаффе прошла успешно, вы авторизовались как {user_email}!\r\n\r\n" \
           f"{admin_welcome_msg if is_admin else welcome_msg}"


delete_success_msg = "Вы успешно удалили устройство"
edit_success_msg = "Вы отредактировали запись"
cancel_msg = "Вы отменили действие"

not_auth_msg = "Чтобы авторизоваться, ведите адрес своей контуровской почты в формате email@skbkontur.ru"
not_admin_error_msg = "Действие доступно только админу. Обратитесь к автору бота, @misha_voyager"
wrong_email_msg = "Укажите именно контуровскую почту, чтобы мы идентифицировали вас однозначно :)"
should_be_username_msg = "Пожалуйста, укажите юзернейм в телеграме или дайте боту доступ к нему. " \
                         "Иначе не получится подтвердить вашу личность"
not_your_email_msg = "Кажется, вы ввели чужую почту!"
no_telegram_in_staff_msg = "Ваш ник в телеграме не найден в Стаффе. Укажите на своей странице " \
                           "актуальный ник, чтобы вас опознал этот бот и не кикнул " \
                           "из рабочих чатов kontur_guard"

ask_int_msg = "Пожалуйста, введите число"
ask_id = "Укажите id, которое написано на устройстве"
ask_vendor_code_msg = "Укажите артикул устройства"
ask_name_msg = "Напишите название устройства. Например, MSPOS-N"
ask_category_msg = "Выберите категорию из списка ниже"
ask_email_msg = "Напишите email пользователя, у которого сейчас устройство, в формате email@skbkontur.ru"
ask_address_msg = "Где пользователь хранит устройство? Например, дома у Пети"
ask_return_date_msg = "Когда пользователь вернет устройство? Напишите примерную дату, например, 23.11.2024"
ask_reg_date_msg = "Введите дату регистрации устройства. Например, 28.01.2024"
ask_firmware_msg = "Укажите, какая прошивка на устройстве? Например: Прошивка 5.8.100, ДТО 10.9.0.10"
ask_comment_msg = "Введите комментарий к устройству. Например: Вернули в Атол (по договору тестирования)"

ask_way_of_adding_msg = "Выберите, добавить устройства по одному или загрузить файл в формате csv"
ask_file_msg = f"Загрузите эксель-файл или csv. В верхней строке должны быть:\r\n\r\n{ResourceColumn.cols_str()}\r\n\r\n" \
               f"Первые 4 поля обязательные. Пример строки: 49,MSPOS-N,ККТ,4894892299,18.05.2024"
file_is_processing_msg = "Идет добавление устройств из файла. Бот сообщит об успехе или возникших ошибках"
confirm_adding_msg = "Точно-точно добавить устройство?"

unexpected_action_msg = "Респект от тестировщика: возникла неожиданная ошибка. " \
                        "Попробуйте снова или свяжитесь с @misha_voyager"

pass_date_error_msg = f"{ResourceError.PASSED_DATE.value}. Пожалуйста, поделитесь маховиком времени с автором бота"
not_found_msg = "Устройство не найдено, попробуйте поискать по-другому"
user_have_no_device_msg = "На вас не записано ни одно устройство. Спите спокойно, Эдуард не держит вас на карандашике"
empty_wishlist = "Вы не стоите в очереди ни на одно устройство"
return_others_device_msg = "Нельзя вернуть устройство, которое на вас не записано!"
leaving_queue_error_msg = "Нельзя покинуть очередь, в которой вы не стоите!"
unexpected_resource_not_found_error_msg = "Устройство не найдено. " + unexpected_action_msg
adding_file_error_msg = "При обработке файла произошла неожиданная ошибка. " \
                        "Попробуйте снова и, если повторится, обратитесь к автору бота, @misha_voyager"
wrong_file_format_msg = "Файл должен быть в формате .csv! Если у вас excel, просто экспортируйте его в нужном формате"
delete_taken_error_msg = "Устройство занял пользователь. " \
                         "Нельзя удалить его сейчас, сначала спишите его с пользователя"
update_address_others_resource_msg = "Устройство записано на другого пользователя, вы не можете обновить его адрес"
take_taken_error_msg = "Устройство уже занято! Снова выполните поиск, чтобы посмотреть, на кого оно записано"
take_nonnexisted_error_msg = "Устройство не найдено, обратитесь к автору бота, @misha_voyager"
queue_second_time_error_msg = "Вы уже стоите в очереди на устройство, " \
                              "нельзя войти в одну реку дважды, как и вернуть 2007"
leave_left_error_msg = "Покинуть очередь не удалось: вас в ней не было. " \
                       "Заигрались в путешествия во времени и опять перепутали порядок событий?"

user_not_found_msg = "Нет такого пользователя. Попробуйте снова найти его в поиске"
password_required_msg = "Опасное действие. Введите пароль для продолжения"
table_error_prefix = "В строке"
id_doubles_prefix = "Есть дубли айди в строках"
vendor_code_doubles_prefix = "Есть дубли артикулов в строках"
table_errors_msg = "Исправьте ошибки и попробуйте снова"
table_upload_success_msg = "Вы успешно внесли данные!"
table_upload_cancelled_msg = "Загрузка файла отменена"
ask_cancel_table_upload_msg = "Вы ввели текст. Прервать процесс загрузки файла?"
ask_table_again_msg = "Тогда ждем файл в формате csv или excel"
incorrect_table_columns_msg = "Некорректные заголовки. Исправьте на такие:"
ask_upload_or_add_manually = "Хотите добавить устройства по одному или загрузить файл?"

file_option = "Файлом"
manually_option = "По одному"
choose_option_msg = "Выберите один из вариантов"

manually_add_success_msg = "Вы добавили устройство!"
manually_add_err_msg = "Не удалось добавить устройство"
