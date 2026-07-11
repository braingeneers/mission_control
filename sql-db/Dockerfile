FROM postgres:16-alpine

COPY backup-sql-db.sh /usr/local/bin/backup-sql-db.sh
COPY docker-entrypoint-sql-db.sh /usr/local/bin/docker-entrypoint-sql-db.sh

RUN chmod +x /usr/local/bin/backup-sql-db.sh /usr/local/bin/docker-entrypoint-sql-db.sh \
    && printf '%s\n' '0 8 * * * /usr/local/bin/backup-sql-db.sh >> /proc/1/fd/1 2>> /proc/1/fd/2' > /etc/crontabs/root

ENTRYPOINT ["docker-entrypoint-sql-db.sh"]
CMD ["postgres"]
