import json
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# * configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# * environment variables
GMAIL_ADDRESS = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]  # not login password

SMTP_SERVER = "smtp.gmail.com"  # change if using different email provider
SMTP_PORT = 587


def lambda_handler(event: dict = {}, context: dict = {}) -> dict:
    """
    Lambda function triggered by SNS to send email using Gmail SMTP when order is created.
    """

    logger.info(f"Received event: {json.dumps(event)}")

    try:
        for record in event['Records']:
            sns_message = record['Sns']['Message']
            logger.info(f"Processing SNS message: {sns_message}")

            order_data = json.loads(sns_message)

            user_email = order_data.get("user_email")
            order_id = order_data.get("order_id")
            total = order_data.get("total")
            items = order_data.get("items", [])

            if not user_email:
                logger.error("No user_email found in order data")
                continue

            email_subject = f"Your Order {order_id} Confirmation"
            email_body = build_email_body(order_id, total, items)

            send_email(user_email, email_subject, email_body)

    except Exception as e:
        logger.exception("Error processing SNS event")
        raise e

    return {"statusCode": 200, "body": "Emails sent successfully."}


def send_email(to_email: str, subject: str, body: str) -> None:
    """
    Send an email via Gmail SMTP.
    """
    try:
        # * Setup the MIME
        message = MIMEMultipart()
        message["From"] = GMAIL_ADDRESS
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        # * Connect to Gmail SMTP server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # * Secure the connection
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, to_email, message.as_string())
        server.quit()

        logger.info(f"Email sent successfully to {to_email}")

    except Exception as e:
        logger.exception("Failed to send email via Gmail SMTP")
        raise e


def build_email_body(order_id: str, total: float, items: list) -> str:
    """
    Build a simple text email body.
    """
    item_list = "\n".join(f"- {item}" for item in items)
    body = (
        f"Thank you for your order!\n\n"
        f"Order ID: {order_id}\n"
        f"Total: ${total:.2f}\n"
        f"Items:\n{item_list}\n\n"
        f"We appreciate your business!"
    )
    return body
