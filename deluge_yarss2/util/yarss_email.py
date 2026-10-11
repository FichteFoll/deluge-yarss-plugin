#
# Copyright (C) 2012-2015 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

import html
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from twisted.internet import threads

from deluge_yarss2.util import logging

log = logging.getLogger(__name__)

# send_email runs in a Twisted reactor thread pool thread (see send_torrent_email's
# deferToThread call), so blocking on a stuck SMTP server there is harmless to the
# reactor, but we still want to give up eventually.
SMTP_TIMEOUT = 30


def send_email(email_conf, server_conf):
    """sends email notification of finished torrent"""
    # Send multipart message with text and html
    if "message" in email_conf:
        # Send Multipart email
        if "message_html" in email_conf:
            mime_message = MIMEMultipart("alternative")
            msg_plain = MIMEText(email_conf["message"].encode("utf-8"), "plain", _charset="utf-8")
            msg_html = MIMEText(email_conf["message_html"].encode("utf-8"), "html", _charset="utf-8")
            mime_message.attach(msg_plain)
            mime_message.attach(msg_html)
        else:
            # Send plain message
            mime_message = MIMEText(email_conf["message"].encode("utf-8"), "plain", _charset="utf-8")
    elif "message_html" in email_conf:
        # Send html message
        mime_message = MIMEText(email_conf["message_html"].encode("utf-8"), "html", _charset="utf-8")
    else:
        log.warning("Email config must contain either 'message' or 'message_html'")
        return False

    mime_message["Subject"] = email_conf["subject"]
    mime_message["From"] = server_conf["from_address"]
    mime_message["To"] = email_conf["to_address"]

    port = smtplib.SMTP_PORT
    if len(server_conf["smtp_port"].strip()) > 0:
        try:
            port = int(server_conf["smtp_port"])
        except ValueError:
            pass
    try:
        mail_server = smtplib.SMTP(server_conf["smtp_server"], port, timeout=SMTP_TIMEOUT)
    except Exception as e:
        log.error(f"There was an error sending the notification email: {e}")
        return False

    try:
        with mail_server:
            log.info(
                f"Sending email message:\nTo: {mime_message['To']}\nFrom: {mime_message['From']}\n"
                f"Subject: {mime_message['Subject']}\n"
            )
            log.info(
                "Server: {}, port: {}, authentication: {}".format(
                    server_conf["smtp_server"], server_conf["smtp_port"], server_conf["smtp_authentication"]
                )
            )
            if server_conf["smtp_authentication"]:
                mail_server.ehlo()
                mail_server.starttls()
                mail_server.ehlo()
                try:
                    mail_server.login(server_conf["smtp_username"], server_conf["smtp_password"])
                except smtplib.SMTPHeloError:
                    log.warning("The server didn't reply properly to the helo greeting")
                except smtplib.SMTPAuthenticationError:
                    log.warning("The server didn't accept the username/password combination")
            try:
                mail_server.sendmail(server_conf["from_address"], email_conf["to_address"], mime_message.as_string())
                mail_server.quit()
            except Exception as e:
                log.error(f"Sending email notification failed: {e}")
                return False
            else:
                log.info("Sending email notification of finished torrent was successful")
    except smtplib.SMTPResponseException as e:
        # __exit__ re-raises if the server answers the closing QUIT with an error;
        # the connection is already closed at that point, so just log it.
        log.warning(f"The server responded with an error while closing the connection: {e}")
        return False
    return True


def send_torrent_email(
    email_configurations,
    email_msg,
    subscription_data=None,
    torrent_name_list=None,
    deferred=False,
    callback_func=None,
):
    """Send email with optional list of torrents
    Arguments:
    email_configurations - the main email configuration of YARSS2
    email_msg - a dictionary with the email data (as saved in the YARSS config)
    torrents - a tuple containing the subscription data and a list of torrent names.
    """
    log.info("Sending email '{}'".format(email_msg["name"]))
    email_data = {
        "to_address": email_msg["to_address"],
        "subject": email_msg["subject"],
        "message": email_msg["message"],
    }
    # The template is user-configured and trusted, so it is used as is;
    # only feed-provided torrent names and the subscription name are escaped below.
    message_html = email_msg["message"]

    if subscription_data:
        subscription_title = subscription_data["name"]
        email_data["message"] = email_data["message"].replace("$subscription_title", subscription_title)
        email_data["subject"] = email_data["subject"].replace("$subscription_title", subscription_title)
        message_html = message_html.replace("$subscription_title", html.escape(subscription_title))

    if email_data["message"].find("$torrentlist") != -1 and torrent_name_list:
        torrentlist_plain = " * {}\n".format("\n * ".join(torrent_name_list))
        torrentlist_html = "<ul><li>{} </li></ul>".format(
            "</li> \n <li> ".join(html.escape(name) for name in torrent_name_list)
        )
        email_data["message"] = email_data["message"].replace("$torrentlist", torrentlist_plain)
        message_html = message_html.replace("\n", "<br/>")
        # A function replacement inserts the names literally; a string would expand backslash escapes in them.
        email_data["message_html"] = re.sub(r"\$torrentlist(<br/>){1}?", lambda _: torrentlist_html, message_html)

    # Send email with twisted to avoid waiting
    if deferred:
        d = threads.deferToThread(send_email, email_data, email_configurations)
        if callback_func is not None:
            d.addCallback(callback_func)
        return d
    else:
        return send_email(email_data, email_configurations)
