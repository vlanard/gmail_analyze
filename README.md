This is a little utility to identify the most heavy email senders & offenders in your gmail account.
Outputs by ranked frequency the most common senders, domains, and email addresses.
Output is intended to help you manually clean up your gmail, unsubscribe, and/or create filters.

I wrote this to identify emails to delete, so there are settings to ignore specific emails that come from senders I like.

# One time setup

## 1. Setup Gmail API Access
Follow steps in "Step 1" of these instructions:
https://developers.google.com/gmail/api/quickstart/python#step_1_turn_on_the_api_name

You should have downloaded a `client_secret.json` file to the same directory as this README.

This will give *you* permission to access your own gmail. No one else.

## 2. Setup your python project
1. Install pipenv

        pip install pipenv

1. Create a python3 venv
(it will be created under ~/.virtualenvs/)

        pipenv --three

1. Activate your venv

        pipenv shell

1. Install dependencies, which includes the gmail python client.

        pipenv install

1. Copy `config.py.sample` to `config.py` and edit `config.py` as desired

        cp config.py.sample config.py

# Run the script
Edit `config.py` repeatedly as desired and rerun with:

    python3 analyze.py

To speed up testing while you figure out your desired config settings, use a small year range or 1 year batches.

# Reference Guides

* Pipenv: https://docs.pipenv.org/
* Gmail APIs: https://developers.google.com/gmail/api/v1/reference/users/messages
* Gmail API Python Client: https://developers.google.com/api-client-library/python/
* Gmail API Debugger Tool: https://developers.google.com/apis-explorer/#p/gmail/v1/gmail.users.messages.list?userId=me&fields=messages(id%252ClabelIds%252CthreadId)%252CnextPageToken&_h=9&
* Gmail Filter Syntax: https://support.google.com/mail/answer/7190?hl=en

