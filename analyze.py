"""
Shows basic usage of the Gmail API.

Lists the user's Gmail labels.
"""
from __future__ import print_function
from apiclient.discovery import build
from apiclient import errors
from httplib2 import Http
from oauth2client import file, client, tools
import operator
import sys
import time
from typing import Optional
import config

# THE PURPOSE OF THIS SCRIPT IS TO IDENTIFY THE MOST HEAVY EMAIL SENDERS (whose email i don't want to keep)

SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'
MIN_FREQ_TO_DISPLAY = 15  # TODO could be a threshold based on the overall count
HOUR_SECONDS = 60 * 60

_service = None
_emailSenders = {}

def init():
    # Setup the Gmail API oauth token
    # NOTE: TO CHANGE SCOPES, DELETE credentials.json file & RERUN
    global _service
    store = file.Storage('credentials.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
        creds = tools.run_flow(flow, store)
    _service = build('gmail', 'v1', http=creds.authorize(Http()))
    return _service


def fetch_and_count_messages(*, service, user_id:str, query:str, token:Optional[str]):
    count = 0
    page_token = None
    response = service.users().messages().list(userId=user_id,q=query, pageToken=token).execute()
    ids = []
    if 'messages' in response:
        count += len(response['messages']) #1170 158 71/51
        for message_info in response['messages']:
            ids.append(message_info['id'])
    if not ids:
        return count,page_token

    batch = service.new_batch_http_request(callback=parseEmailHeader)
    for id in ids:
        batch.add(service.users().messages().get(userId='me', id=id, format="metadata", fields="labelIds,payload/headers"))
    batch.execute()#http=http
    page_token = response.get('nextPageToken')
    return count,page_token


def parseEmailHeader(request_id, response, exception):
    global _emailSenders
    sender = _parseEmailHeader(response)
    if sender:
        _emailSenders[sender] = _emailSenders.get(sender, 0) + 1


def _parseEmailHeader(response)-> Optional[str]:
    headers = response['payload']['headers']
    for h in headers:
        if h['name'].lower() == "from":  #From, FROM
            return h['value']
    # payload['headers']['Date']  #{'name': 'Date', 'value': 'Wed, 18 Apr 2018 03:43:58 +0000 (UTC)'}
    # payload['headers']['To']
    print("Error parsing Sender", headers, id)
    return None


def CountMessageSendersForQuery(service, user_id, query=''):
    """Count senders among all Messages in the user's mailbox matching the query.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me" = authenticated user.
      query: String used to filter messages returned.
      Eg.- 'from:user@some_domain.com' for Messages from a particular sender.
    """
    global _emailSenders  # this sucks.
    show_status_every_n = 500
    try:
        count = 0
        sum,page_token = fetch_and_count_messages(service=service, user_id=user_id,query=query, token=None)
        count += sum
        if count % show_status_every_n == 0:
            print(count, end=".")
        sys.stdout.flush()
        while page_token:
            sum, page_token = fetch_and_count_messages(service=service, user_id=user_id, query=query, token=page_token)
            count += sum
            if count % show_status_every_n == 0:
                print(count, end=".")
                sys.stdout.flush()

    except errors.HttpError as error:
        print('An error occurred: %s' % error)

    if _emailSenders:
        print()
        normalizeSenders(_emailSenders, query)
    else:
        print("None for %s" % query)


def sort_by_value(map, reverse=True):
    # rsort dict by value
    return sorted(map.items(), key=operator.itemgetter(1), reverse=reverse)


def find_dominant_field(senderc,emailc,namec,domainc,sender,email,name,domain):
    vals = []
    for x in senderc,emailc,namec,domainc:
        if x != None:
            vals.append(x)
        else:
            vals.append(0) #replace Nones, just in case they occur
    dominant = max(vals)
    if dominant == senderc: # use most to least specificity
        return sender
    elif dominant == emailc:
        return email
    elif dominant == namec:
        return name if name else email
    else:
        return domain


def normalizeSenders(senderMap, query):
    # this function creates a score associated with the overall sender identity -
    #   score increases with raw number of messages received per email address,
    #   per domain, and per sender name ; so the highest volume senders as well
    #   as senders who mask the same email with unique names will rise to the top

    # MANY NAMES ASSOCIATED WITH SAME EMAIL
    # ('"Bob Barker (LinkedIn Invitations)" <invitations@linkedin.com>', 1)
    #('Jane Doe via LinkedIn <member@linkedin.com>', 1)
    # 'John Doe <notification+tc=28f6@facebookmail.com>'

    # MANY EMAILS ASSOCIATED WITH SAME NAME AND/OR SAME SENDER DOMAIN
    # ('"AT&T Online Services" <att-services.cn.1313192153@email.att-mail.com>', 1)
    # ('"AT&T Online Services" <att-services.cn.7243330651@email.att-mail.com>', 1)
    # ('Pacific Gas and Electric Company <kc.32315077.5948.0@kc.pge.com>', 1)
    # ('Pacific Gas and Electric Company <kc.32315077.6500.0@kc.pge.com>', 1)
    # ('"Facebook" <update+tc=28f6@facebookmail.com>', 278)
    # ('Facebook <update+tc=28f6@facebookmail.com>', 253)

    email_map = {}
    name_map = {}
    domain_map = {}
    domain_sender = {}
    for sender,count in senderMap.items():
        email, name, domain = parseSender(sender)
        # count per sender email
        weight = email_map.get(email,0) + 1
        email_map[email] = weight
        # count per name
        name_map[name] = name_map.get(name,0) + 1
        # count domain if not a whitelisted one, in which case give it a lower score
        weight = 1 if domain in config.SAFE_DOMAINS else domain_map.get(domain,0) + 1
        domain_map[domain] = weight
        senderlist = domain_sender.setdefault(domain,[])
        senderlist.append(sender)

    # order the results by most frequent sender (the entire header string)
    sorted_senders = sort_by_value(senderMap)
    print (query)
    rows = []
    printed = {}
    # build an overall score per combo of sender / email / name / domain; then resort by that score descending.
    #   -> safe domains will have a lower score than all other domains
    #   this will bubble up the biggest senders & spammers (rolling up by reuse of domain or sender name or sender email)
    num_examples = 3
    for sender, count in sorted_senders:
        email, name, domain = parseSender(sender)
        email_count = email_map[email]
        name_count = name_map[name]
        domain_count = domain_map[domain]
        best_example = find_dominant_field(count,email_count,name_count,domain_count,sender,email,name,domain)
        score = count + email_count + name_count + domain_count
        if printed.get(email):  # output only highest-ranking line for this email (even if variants within sender header)
            continue
        if printed.get(domain): # output only highest-ranking line for this domain
            continue
        if len(domain_sender[domain]) > 0:
            min_index = 1 if best_example == sender else 0 # skip showing duplicate if already shown
            max_index = min_index + num_examples
            # pick up to N examples of sender strings to show for this sender (don't show a million)
            instances = domain_sender[domain][min_index:min(max_index,len(domain_sender[domain]))]
        else:
            instances = ""
        rows.append((score, best_example, count, email, email_count, name, name_count, domain, domain_count, instances))
        printed[email] = 1
        printed[domain] = 1

    # print rows (desc by score) above a certain frequency (ignore the long tail)
    sorted_rows = sorted(rows, key=operator.itemgetter(0), reverse=True)
    print()
    print("=" * 20, query, "=" * 20)
    for tup in sorted_rows:
        if tup[0] >= MIN_FREQ_TO_DISPLAY:
            print(tup)
    print("=" * 55)


def stripQuotes(thething):
    if not thething:
        return
    if thething[0] == '"' and thething[-1] == '"':
        thething = thething[1:-1]
    elif thething[0] == "'" and thething[-1] == "'":
        thething = thething[1:-1]
    return thething


def parseSender(sender):
    """
    given an email header for a sender, parse into name, email, and domain
    :param sender:
    :return:
    """
    # THIS PARSES ALL OF THESE FORMATS SEEN IN MY GMAIL HISTORY
    #   Jennifer <jennifer@acompany.com>
    #   first.last@gmail.com
    #   <company@company.com>
    #   Amazon Associates <'associates@amazon.com'>
    name = None
    email = None
    domain = None
    args = sender.split("<")
    if len(args) == 1:  # no reply-to name if no angle brackets
        email = args[0].strip()
        name = email
    elif len(args) > 1:
        name = args[0].strip()
        email = args[1].strip()
        if email[-1] == ">":
            email = email[:-1]
        #normalize by removing quotes
        name = stripQuotes(name)
    if email:
        email = stripQuotes(email).lower()
        parts = email.split("@")
        if len(parts) != 2 and parts[0]:
            print ("Warning: Invalid domain format", email)
        if len(parts) > 1:
            domain = parts[1]
    return email,name,domain


def get_ignore_labels_for_query():
    # Example:  -{label:exclude1 label:exclude2}
    if not config.IGNORE_LABELS:
        return ""
    labels = ["-{"]
    for l in config.IGNORE_LABELS:
        labels.append(f"label:{l}")
    labels.append("}")
    return " ".join(labels)


def get_ignore_senders_for_query():
    # Example:  -{from:safe1@b.com from:safe2@b.com}
    if not config.IGNORE_EMAILS:
        return ""
    labels = ["-{from:me"]   # anything from me to me is an ignore
    for l in config.IGNORE_EMAILS:
        labels.append(f"from:{l}")
    labels.append("}")
    return " ".join(labels)


def elapsed_pretty(elapsed_sec:int):
    if elapsed_sec > HOUR_SECONDS:
        hr,min = divmod(elapsed_sec,HOUR_SECONDS)
        min,sec = divmod(min,60)
        return "%d:%02d:%02d hr" % (hr, min,sec)
    elif elapsed_sec > 60:
        min,sec = divmod(elapsed_sec,60)
        return "%d:%02d min" % (min,sec)
    else:
        return "%d.02 sec" % elapsed_sec


if __name__ == '__main__':
    service = init()

    starttime = time.time()
    start = config.EARLIEST_YEAR or sys.exit("config.EARLIEST_YEAR is required")
    thisyear = int(time.strftime("%Y"))
    end = int(config.LATEST_YEAR or thisyear) + 1
    interval = config.NUM_YEARS_PER_BATCH or 50
    end = min(end, (thisyear + 1))

    ignore_labels = get_ignore_labels_for_query()
    ignore_senders = get_ignore_senders_for_query()
    while start < end:
        before = min(start + interval, end)
        # example  after:2004 before:2005  = 1 full year
        print(f"after:{start} before:{before} {ignore_senders} {ignore_labels}")
        #CountMessageSendersForQuery(service, 'me', query=f"after:{start} before:{before} {ignore_senders} {ignore_labels}")
        start += interval
    endtime = time.time()
    elapsed = endtime - starttime
    print("Elapsed time:",elapsed_pretty(elapsed_sec=elapsed))

