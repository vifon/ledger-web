# Ledger Web

*Ledger Web* was [initially](https://github.com/vifon/ledger-web-api)
created to bridge the gap between a smartphone and [Ledger
CLI](https://ledger-cli.org/) by exposing a HTTP API.  Since then it
evolved into a more general web UI for Ledger.

## Features

- HTTP API for submitting new payment entries.
- Rules to override the attributes of the entries submitted via the API.
- A web form for submitting new payment entries.
- Expenses & income charting.
- A web preview of the basic Ledger data.
- Support for multiple users with separate ledgers and rules.
- A responsive UI suitable for mobile devices.
- Can act as a very basic Progressive Web App (PWA).
- Almost no JavaScript (only used for charts and eyecandy), works even
  on a Kindle.

### Non-features

I consider *Ledger Web* a companion to the regular *Ledger CLI*, not a
replacement, so it tries to add things missing in Ledger (+ some
convenient goodies) while not reinventing the wheel.  These are some
features visibly missing from *Ledger Web*.

- There is only a limited support for modifying the ledger file other
  than appending new entries.  It's possible to modify or revert the
  very last added entry but that's it.
- The register view won't show any included files' contents, it only
  reads the main file.  The other views are free from this limitation.

## Screenshots

### Mobile version

[![](https://raw.githubusercontent.com/vifon/ledger-web/master/examples/Charts_mobile.png)](https://raw.githubusercontent.com/vifon/ledger-web/master/examples/Charts_mobile.png)

### Balance

[![](https://raw.githubusercontent.com/vifon/ledger-web/master/examples/Balance.png)](https://raw.githubusercontent.com/vifon/ledger-web/master/examples/Balance.png)

### Charts

[![](https://raw.githubusercontent.com/vifon/ledger-web/master/examples/Charts.png)](https://raw.githubusercontent.com/vifon/ledger-web/master/examples/Charts.png)

### Replacement rules

[![](https://raw.githubusercontent.com/vifon/ledger-web/master/examples/Rules.png)](https://raw.githubusercontent.com/vifon/ledger-web/master/examples/Rules.png)

[![](https://raw.githubusercontent.com/vifon/ledger-web/master/examples/Rules_mobile.png)](https://raw.githubusercontent.com/vifon/ledger-web/master/examples/Rules_mobile.png)

### Ledger register

[![](https://raw.githubusercontent.com/vifon/ledger-web/master/examples/Register.png)](https://raw.githubusercontent.com/vifon/ledger-web/master/examples/Register.png)

[![](https://raw.githubusercontent.com/vifon/ledger-web/master/examples/Register_mobile.png)](https://raw.githubusercontent.com/vifon/ledger-web/master/examples/Register_mobile.png)

### Ledger Web on Kindle

[![](https://raw.githubusercontent.com/vifon/ledger-web/master/examples/Submit_Kindle.png)](https://raw.githubusercontent.com/vifon/ledger-web/master/examples/Submit_Kindle.png)

## Installation

*Ledger Web* is designed to be constantly running on a server so it's
easily accessible from mobile devices.  That being said, it's possible
to run it on demand locally for example just to analyze the charts.
The instructions below assume the former case though.

### Docker

There is a **experimental** Docker image available.  To use it, run:

```
docker run --name ledger-db -e POSTGRES_PASSWORD=mysecretpassword -d postgres
docker run --name ledger-web \
  -e USERNAME=user \
  -e PASSWORD=change_me \
  -e POSTGRES_PASSWORD=mysecretpassword \
  -v /path/to/ledger.dat:/home/app/ledger.dat \
  -p 8080:5000 --link ledger-db:db -d vifon/ledger-web
```

...substituting the passwords of 

*Ledger Web* should be running on port 8080 now.

You may need to tweak the permissions of your Ledger file.  Setting
the owner UID to 1000 should do as a quick fix.

### Manual installation

1. Clone the repository and install the dependencies:

        git clone https://github.com/vifon/ledger-web
        cd ledger-web
        virtualenv .venv
        . .venv/bin/activate
        pip install -r requirements.txt

2. Set up the database.  SQLite is used by default, it can be changed
   in `ledger/settings.py`.

        ./manage.py makemigrations
        ./manage.py migrate

3. Set the access credentials:

        ./manage.py createsuperuser
        ./manage.py runserver

   Follow the instructions on screen and the enter
   http://localhost:8000/admin

   Add a new entry in the *Ledger paths* table for your user, pointing
   it to your Ledger file.

   If you want to use the HTTP API, add an access token too.  A token
   should be between 32 and 256 characters long.  You'll need to
   generate it yourself, for example with `pwgen 256 1`.

4. Customize `ledger/settings.py`, specifically you may be interested
   in the options starting with `LEDGER_` at the end of this file.

5. Check that everything works at http://localhost:8000/

6. Enable the production mode in `ledger/settings.py`.

   Either run `make prod` (see the output of `make` for the optional
   arguments) or follow these steps:

    - Set `DEBUG = False`.
    - Generate a new `SECRET_KEY`, for example with [this snippet](https://gist.github.com/sandervm/2b15775012685553f0e2).
    - Enter your domain and possibly a localhost in `ALLOWED_HOSTS`.
    - Set `STATIC_ROOT`, for example `'/var/www/ledger' + STATIC_URL`
      and run `./manage.py collectstatic`.

7. Set up a WSGI server (for example Gunicorn):

        pip install gunicorn
        gunicorn -w 4 -b 127.0.0.1:1234 ledger.wsgi

8. Set up a reverse proxy in a HTTP server, for example Nginx, a
   config file included in `examples/ledger.nginx.conf`.

## HTTP API

*Ledger Web* exposes an HTTP API that is used to add new Ledger
entries.  It is available under the following HTTP routes:

### `POST /ledger/submit/v1/`

JSON arguments:

- `account_from`
- `account_to`
- `payee`
- `amount`
- `token`
- (optional) `skip_rules`: boolean

All arguments are strings unless specified otherwise.

This is the legacy API from older *Ledger Web* versions.

The `skip_rules` argument is optional, it causes the transaction to
be submitted verbatim with no rules applied to it.

For example:

    curl -X POST 'http://localhost:8000/ledger/submit/v1/' -H "Content-Type: application/json" -d '{
        "account_from": "Assets:Bank",
        "account_to": "Expenses:Food",
        "payee": "Pizza",
        "amount": "10 USD",
        "token": "my_secure_token"
    }'

### `POST /ledger/submit/v2/`

JSON arguments:

- `payee`
- (optional) `date`: string (`YYYY-MM-DD`)
- (optional) `skip_rules`: boolean
- (optional) `comment`
- `accounts`: list of any combination of such lists:
  - [`account`, `amount`, `currency`]
  - [`account`, `amount`]
  - [`account`, `amount currency`]
  - [`account`]

All arguments are strings unless specified otherwise.

For example:

    curl -X POST 'http://localhost:8000/ledger/submit/v2/' -H "Content-Type: application/json" -d '{
        "payee": "Pizza with George",
        "accounts": [
            ["Assets:Food", "20 USD"],
            ["Assets:Loans:George", "10", "USD"],
            ["Assets:Bank"]
        ],
        "token": "my_secure_token"
    }'

### Replacement rules

If the payee submitted via the HTTP API matches one of the regexps in
the added rules, the rule overrides the data passed in the HTTP
request.

It can be used to process and/or clean up automated requests on card
payment (left as an exercise for the user).

In the v2 API the account name gets replaced only for accounts equal
to `LEDGER_DEFAULT_TO` in `settings.py`, the other accounts are left
intact.

## Copyright

Copyright (C) 2019  Wojciech Siewierski

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
