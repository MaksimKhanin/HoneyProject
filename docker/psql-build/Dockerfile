FROM postgres:13

COPY initdb.sql /docker-entrypoint-initdb.d/
# Копируем конфиг памяти
COPY postgres.conf /etc/postgresql/postgresql.conf

# Команда запуска с нашим конфигом
CMD ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]