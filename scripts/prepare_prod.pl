#!/usr/bin/perl -ni

use warnings;
use strict;
use 5.010;

use autodie;

state $static_root_set = 0;

if (/^SECRET_KEY\b/) {
    my @chars = split //, "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)";
    my @out;
    push @out, $chars[rand @chars] for 1..50;
    say "SECRET_KEY = '", @out, "'";
} elsif (/^DEBUG\b/) {
    say 'DEBUG = False';
} elsif (/^\QALLOWED_HOSTS = []\E$/) {
    if (exists $ENV{ALLOWED_HOSTS}) {
        my @allowed_hosts = split /\s/, $ENV{ALLOWED_HOSTS};
        say 'ALLOWED_HOSTS = [', (join ",", map "'$_'", @allowed_hosts), ']';
    } else {
        warn "  * Please set the ALLOWED_HOSTS environmental variable\n";
        print;
    }
} elsif (/^STATIC_ROOT\b/) {
    $static_root_set = 1;
    print;
} else {
    print;
}

END {
    unless ($static_root_set) {
        open(my $f, '>>', $ARGV);
        my $static_root = $ENV{STATIC_ROOT} // '/var/www/ledger-web/static/';
        $static_root =~ s,/*$,/,;
        say $f "\nSTATIC_ROOT = '$static_root'";
    }
}
