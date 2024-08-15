import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
import openai
from dotenv import load_dotenv
import os
import time
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
MAIL_SERVER = os.getenv("MAIL_SERVER")
EMAIL_ACCOUNT = os.getenv("EMAIL_ACCOUNT")
PASSWORD = os.getenv("EMAIL_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

# Initialize OpenAI API
openai.api_key = OPENAI_API_KEY


def decode_header_value(header_value):
    decoded = decode_header(header_value)
    return "".join(
        [
            (str(t[0], t[1] if t[1] else "utf-8")
             if isinstance(t[0], bytes)
             else t[0])
            for t in decoded
        ]
    )


def extract_plain_text(email_message):
    plain_text = ""
    for part in email_message.walk():
        content_type = part.get_content_type()
        charset = part.get_content_charset()
        if content_type == "text/plain":
            plain_text = part.get_payload(decode=True).decode(charset)
        elif content_type == "text/html":
            html_content = part.get_payload(decode=True).decode(charset)
            soup = BeautifulSoup(html_content, "lxml")
            plain_text = soup.get_text().strip()

    if plain_text:
        plain_text = " ".join(plain_text.split()).replace("\n", " ")
    return plain_text


def summarize_email(content):
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an AI assistant responsible for reviewing emails"
                    "and providing concise summaries. "
                    "When summarizing, focus on the key points, including"
                    "important requests, decisions, or actions required. "
                    "Exclude any unnecessary details or repetitive"
                    "information. Your summaries should be clear, precise"
                    "and no longer than a few sentences. Answer in the"
                    "language the mail is written."
                ),
            },
            {"role": "user", "content": content},
        ],
    )
    return response.choices[0].message.content


def process_email(email_message):
    subject = decode_header_value(email_message["Subject"])
    sender = decode_header_value(email_message["From"])
    recipient = decode_header_value(email_message["To"])
    date = email_message["Date"]
    content = extract_plain_text(email_message)
    summary = summarize_email(content)

    output = {
        "Date": date,
        "Subject": subject,
        "Sender": sender,
        "Recipient": recipient,
        "Summary": summary,
    }
    output_json = json.dumps(output, indent=4, ensure_ascii=False)
    logger.info(output_json)


def main():
    try:
        mail = imaplib.IMAP4_SSL(MAIL_SERVER)
        mail.login(EMAIL_ACCOUNT, PASSWORD)
    except imaplib.IMAP4.error as e:
        logger.error(f"Failed to connect to the mail server: {e}")
        return

    last_seen_msg_id = None

    try:
        while True:
            mail.select("inbox")
            status, messages = mail.search(None, "ALL")
            email_ids = messages[0].split()
            if not email_ids:
                logger.info("No new emails found.")
                time.sleep(10)
                continue

            latest_msg_id = email_ids[-1]
            if latest_msg_id != last_seen_msg_id:
                status, msg_data = mail.fetch(latest_msg_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        process_email(msg)
                last_seen_msg_id = latest_msg_id

            time.sleep(10)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        mail.logout()


if __name__ == "__main__":
    main()
