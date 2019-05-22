FROM ubuntu:bionic

RUN adduser --disabled-password --gecos '' app

ADD requirements.txt /home/app

RUN apt-get -y update \
 && apt-get -y install \
      build-essential \
      python3-minimal \
      python3-pip \
      python3-psycopg2 \
      nginx \
      supervisor \
      ledger \
 && apt-get -y clean \
 && pip3 install -r /home/app/requirements.txt \
 && pip3 install gunicorn

ADD . /home/app/ledger-web/

WORKDIR /home/app/ledger-web/

ADD docker/configs/etc/ /etc/

RUN chown -R app:app /home/app/ledger-web/ \
 && install -d -o app -g app /var/www/ledger-web/
USER app
RUN make prod && make use_postgres
USER root

ENV LC_ALL C.UTF-8

EXPOSE 5000

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
