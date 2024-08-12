import imaplib
import os
import email
import json
import re
from email.header import decode_header
from dotenv import load_dotenv


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


# Connect to the server
mail = imaplib.IMAP4_SSL("mail.grupoapolo.com")

load_dotenv()

# Login to your account
email_account = os.getenv("EMAIL_ACCOUNT")
password = os.getenv("EMAIL_PASSWORD")
print(email_account, password)
mail.login(email_account, password)

# Select the mailbox you want to check (e.g., "inbox")
mail.select("inbox")

# Search for emails from a specific sender
sender_email = ""
# Search for emails with a specific subject
subject = ""
status, messages = mail.search(
    None, f'(FROM "{sender_email}" SUBJECT "{subject}")'
)

# Convert messages to a list of email IDs
messages = messages[0].split(b" ")

# If there are any messages from this sender
if messages:
    msg_id = messages[-1]

    # Fetch the email by ID
    res, msg = mail.fetch(msg_id, "(RFC822)")

    for msg_id in messages:

        for response_part in msg:
            if isinstance(response_part, tuple):
                # Parse the email content
                msg = email.message_from_bytes(response_part[1])

                print("\n---Raw Message---")
                # print(response_part[1].decode(errors="ignore"))
                # print(msg)

                match = re.match(r"([^<]+)\s*<([^>]+)>", msg.get("From"))

                if match:
                    name = match.group(1).strip()
                    email_address = match.group(2).strip()
                else:
                    name = ""
                    email_adress = msg.get("From").strip()

                output = {
                    "Date": msg.get("Date"),
                    "size": len(response_part[1]),
                    "Subject": msg.get("Subject"),
                    "Sender": {
                        "Email address": email_address,
                        "Sender name": name,
                    },
                }
                output_json = json.dumps(output, indent=4)
                print(output_json)

else:
    print(f"No emails found from {sender_email}")

mail.close()
mail.logout()
