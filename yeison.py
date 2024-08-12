import imaplib
import email
from email.header import decode_header


def load_env_file(filepath):
    """Load environment variables from a .env file"""
    env_vars = {}
    with open(filepath) as f:
        for line in f:
            # Remove comments and extra whitespace
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Split line into key and value
            key, value = line.split("=", 1)
            env_vars[key.strip()] = value.strip()
    return env_vars


# Load environment variables
env_vars = load_env_file(".env")
email_account = env_vars.get("EMAIL_ACCOUNT")
password = env_vars.get("EMAIL_PASSWORD")


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


# Connect to the server
mail = imaplib.IMAP4_SSL("mail.grupoapolo.com")

# Login to your account
mail.login(email_account, password)

# Select the mailbox you want to check (e.g., "inbox")
mail.select("inbox")

# Search for all emails
status, messages = mail.search(None, "ALL")

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

            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    print(
                        part.get_payload(decode=True).decode(
                            part.get_content_charset()
                        )
                    )

            # print(email_message)

else:
    print("No emails found")

mail.close()
mail.logout()
