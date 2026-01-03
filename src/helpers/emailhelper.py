import os
import smtplib
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_USER = "vecheren@gmail.com"
OUTER_USER = "mnoskov@skbkontur.ru"
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


def send_email_report_dashboard(username: str) -> dict[str, tuple[int, bytes]]:
    email = get_email_template_dashboard(username)
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(SMTP_USER, SMTP_PASSWORD)
        return server.send_message(email)


def get_email_template_dashboard(username: str) -> EmailMessage:
    email = EmailMessage()
    email['Subject'] = 'Тестовое сообщение'
    email['From'] = SMTP_USER
    email['To'] = OUTER_USER

    email.set_content(
        '<div>'
        f'<h1 style="color: red;">Здравствуйте, {username}, а вот и ваш отчет. Зацените 😊</h1>'
        '<img src="https://static.vecteezy.com/system/resources/previews/008/295/031/original/custom-relationship'
        '-management-dashboard-ui-design-template-suitable-designing-application-for-android-and-ios-clean-style-app'
        '-mobile-free-vector.jpg" width="600">'
        '</div>',
        subtype='html'
    )
    return email
