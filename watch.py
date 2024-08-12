import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import re
import time

load_dotenv()

# Load environment variables
mail_server = os.getenv("MAIL_SERVER")
email_account = os.getenv("EMAIL_ACCOUNT")
password = os.getenv("EMAIL_PASSWORD")
apikey = os.getenv("OPENAI_API_KEY")


# Function to decode email subject and other headers
def decode_header_value(header_value):
    decoded = decode_header(header_value)
    return "".join(
        [
            (
                str(t[0], t[1] if t[1] else "utf-8")
                if isinstance(t[0], bytes)
                else t[0]
            )
            for t in decoded
        ]
    )


# Function to parse name and email address from a header field
def parse_name_and_email(header_value):
    match = re.match(r"([^<]+)\s*<([^>]+)>", header_value)
    if match:
        name = match.group(1).strip()
        email_address = match.group(2).strip()
    else:
        name = ""
        email_address = header_value.strip()
    return name, email_address


# Function to clean HTML tags and get plain text
def extract_plain_text(email_message):
    plain_text = ""
    for part in email_message.walk():
        content_type = part.get_content_type()
        if content_type == "text/plain":  # Check for plain text part
            plain_text = part.get_payload(decode=True).decode(
                part.get_content_charset()
            )
        elif (
            content_type == "text/html"
        ):  # If plain text is not found, use HTML part
            html_content = part.get_payload(decode=True).decode(
                part.get_content_charset()
            )
            soup = BeautifulSoup(html_content, "lxml")
            plain_text = soup.get_text().strip()

    # Clean up the plain text
    if plain_text:
        plain_text = " ".join(
            plain_text.split()
        )  # Remove all extra spaces and newlines
        plain_text = plain_text.replace(
            "\n", " "
        )  # Replace newlines with a space

    return plain_text


# Function to fetch and print the latest email
def fetch_and_print_latest_email(mail):
    # Select the mailbox you want to check
    mail.select("inbox")

    sender_email = ""
    subject = ""

    # Search for all emails
    status, messages = mail.search(
        None, f'(FROM "{sender_email}" SUBJECT "{subject}")'
    )

    # Convert messages to a list of email IDs
    messages = messages[0].split(b" ")

    # If there are any messages
    if messages:
        # Get the latest email ID
        latest_msg_id = messages[-1]

        # Fetch the latest email by ID
        res, data = mail.fetch(latest_msg_id, "(RFC822)")

        for response_part in data:
            if isinstance(response_part, tuple):
                # Parse the email content
                email_message = email.message_from_bytes(response_part[1])

                # Parse sender information
                sender_name, sender_email = parse_name_and_email(
                    email_message.get("From")
                )

                # Parse recipient information
                recipient_name, recipient_email = parse_name_and_email(
                    email_message.get("To", "")
                )

                # Parse plain text content
                plain_text_content = extract_plain_text(email_message)

                output = {
                    "Date": email_message.get("Date"),
                    "size": len(response_part[1]),
                    "Subject": email_message.get("Subject"),
                    "Sender": {
                        "Email address": sender_email,
                        "Sender name": sender_name,
                    },
                    "Recipient": {
                        "Email address": recipient_email,
                        "Recipient name": recipient_name,
                    },
                    "Text content": plain_text_content,
                }
                output_json = json.dumps(output, indent=4, ensure_ascii=False)
                with open("latest_email.json", "w") as json_file:
                    json_file.write(output_json)
                # print(plain_text_content)

                client = OpenAI(api_key=apikey)

                completion = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an AI assistant responsible for reviewing emails and providing concise summaries. When summarizing, focus on the key points, including important requests, decisions, or actions required. Exclude any unnecessary details or repetitive information. Your summaries should be clear, to the point, and no longer than a few sentences. Answer in the language the mail is written.",
                        },
                        {
                            "role": "user",
                            "content": f"""Here is the mail content: {plain_text_content}""",
                        },
                    ],
                )
                print(completion.choices[0].message)


# Connect to the server
mail = imaplib.IMAP4_SSL(mail_server)

# Login to your account
mail.login(email_account, password)

# Track the latest email ID that was processed
last_seen_msg_id = None

# Infinite loop to continuously check for new emails
while True:
    mail.select("inbox")

    # Search for all emails
    status, messages = mail.search(None, "ALL")

    # Convert messages to a list of email IDs
    messages = messages[0].split(b" ")

    # If there are any messages
    if messages:
        # Get the latest email ID
        latest_msg_id = messages[-1]

        # If the latest message ID is different
        # from the last one we saw, fetch and print it
        if latest_msg_id != last_seen_msg_id:
            fetch_and_print_latest_email(mail)
            last_seen_msg_id = latest_msg_id

    # Wait for X seconds before checking again
    time.sleep(10)

mail.close()
mail.logout()
