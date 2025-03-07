FROM braingeneers/braingeneers:latest

RUN python -m pip install --no-cache-dir --upgrade pip flask slack_sdk

COPY slack_bridge.py /app/slack_bridge.py
COPY run.sh /app/run.sh

ENTRYPOINT ["/app/run.sh"]
