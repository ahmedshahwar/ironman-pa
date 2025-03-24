import email
import imaplib
from email.header import decode_header
from email.utils import parsedate_to_datetime

def fetch_mail(IMAP_SERVER, EMAIL_ACCOUNT, EMAIL_PASSWORD, max_emails=5):
    try:
        # print("Connecting to IMAP server...")  
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993)

        # print("Logging into email account...")  
        mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)

        # print("Selecting Inbox...")  
        mail.select("inbox")  

        # print("Selecting Primary Inbox...")
        # Gmail-specific IMAP filter to fetch emails only from the Primary tab
        result, data = mail.search(None, 'X-GM-RAW "category:primary"')

        if result != "OK":
            # print("IMAP search failed:", result)
            return {"error": "IMAP search failed"}
        
        # print("Geting Latest Emails...")
        email_ids = data[0].split()[-max_emails:]  # Get latest emails

        if not email_ids:
            # print("No new emails found in Primary inbox.")
            return []

        saved_emails = []
        for e_id in email_ids:
            result, msg_data = mail.fetch(e_id, "(RFC822)")
            if result != "OK":
                # print(f"Failed to fetch email {e_id}: {result}")
                continue

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    # Decode subject
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes) and encoding:
                        subject = subject.decode(encoding)
                    subject = subject if subject else "No Subject"

                    # Decode sender
                    sender, encoding = decode_header(msg["From"])[0]
                    if isinstance(sender, bytes) and encoding:
                        sender = sender.decode(encoding)

                    # Extract email received timestamp
                    date_header = msg["Date"]
                    email_timestamp = parsedate_to_datetime(date_header).strftime("%Y-%m-%d %H:%M:%S")

                    # Extract email body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")

                    email_data = {
                        "email_id": e_id.decode() if isinstance(e_id, bytes) else str(e_id),
                        "subject": subject,
                        "sender": sender,
                        "body": body.strip(),
                        "received_time": email_timestamp,
                        "processed": False,
                    }
                    
                    saved_emails.append(email_data)

        mail.logout()

        # print(len(saved_emails), "new emails fetched.")  
        # for email_data in saved_emails:
        #     print(f"""
        #     =========================================
        #     Email ID: {email_data['email_id']}
        #     Sender: {email_data['sender']}
        #     Subject: {email_data['subject']}
        #     Received Time: {email_data['received_time']}
        #     =========================================
        #     """)

        # print("Emails Fetched Successfully.")
        return saved_emails

    except Exception as e:
        # print("Email Fetch Error:", str(e))  
        return {"error": str(e)}
