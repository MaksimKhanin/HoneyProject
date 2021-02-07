FROM postgres:13.1
ENV POSTGRES_USER khanin
ENV POSTGRES_PASSWORD Zx129132Aa

COPY initdb.sql /docker-entrypoint-initdb.d/
COPY ./manual_sectors.csv ./manual_sectors.csv