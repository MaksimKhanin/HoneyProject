FROM python:3.8

ENV DASH_DEBUG_MODE True
COPY ./app /app
WORKDIR /app
RUN set -ex && \
    pip install -r requirements.txt
EXPOSE 8050
CMD ["python", "index.py"]