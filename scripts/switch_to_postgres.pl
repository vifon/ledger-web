#!/usr/bin/perl -ni

use warnings;
use strict;
use 5.010;

use autodie;


if (/\Q'ENGINE': 'django.db.backends.sqlite3'\E/) {
    s/sqlite3/postgresql/;
    print;
} elsif (/\Q'NAME': os.path.join(BASE_DIR, 'db.sqlite3')\E/) {
    say ' ' x 8, q('NAME': os.environ.get('POSTGRES_DB', 'postgres'),);
    say ' ' x 8, q('USER': os.environ.get('POSTGRES_USER', 'postgres'),);
    say ' ' x 8, q('PASSWORD': os.environ['POSTGRES_PASSWORD'],);
    say ' ' x 8, q('HOST': 'db',);
    say ' ' x 8, q('PORT': '5432',);
} else {
    print;
}
