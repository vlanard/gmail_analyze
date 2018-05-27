This is a project to identify the most heavy email senders in your gmail account.
This is intended to help you clean up your email manually or via filters.

I wrote this to identify emails to delete, so there are settings to ignore specific emails that come from senders I like.

# 1. Setup Gmail API Access
Follow steps in "Step 1" of these instructions:
https://developers.google.com/gmail/api/quickstart/python#step_1_turn_on_the_api_name

You should have downloaded a `client_secret.json` file to the same directory as this README.


# 2. Setup your python project
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

# 3. Run the script

    python analyze.py

# Reference Guides

* Pipenv: https://docs.pipenv.org/
* Gmail APIs: https://developers.google.com/gmail/api/v1/reference/users/messages
* Gmail API Python Client: https://developers.google.com/api-client-library/python/
* Gmail API Debugger Tool: https://developers.google.com/apis-explorer/#p/gmail/v1/gmail.users.messages.list?userId=me&fields=messages(id%252ClabelIds%252CthreadId)%252CnextPageToken&_h=9&
* Gmail Filter Syntax: https://support.google.com/mail/answer/7190?hl=en

