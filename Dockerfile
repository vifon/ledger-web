FROM ubuntu:bionic

RUN adduser app

ADD requirements.txt /home/app

RUN apt-get -y update \
 && apt-get -y install \
      build-essential \
      python3-minimal \
      python3-pip \
      nginx \
      supervisor \
      ledger \
 && apt-get -y clean \
 && pip3 install -r /home/app/requirements.txt \
 && pip3 install gunicorn

ADD . /home/app/ledger-web/
RUN chown -R app:app /home/app/ledger-web/ \
 && install -d -o app -g app /var/www/ledger-web/

ADD configs/ /etc/

USER app
WORKDIR /home/app/ledger-web/
RUN make prod
USER root

EXPOSE 5000

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
