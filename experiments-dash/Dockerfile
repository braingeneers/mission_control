FROM braingeneers/braingeneers:latest

# Install dash and related packages
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir dash

COPY experiment-plotly-app.py /app/experiment-plotly-app.py
COPY dashboard_helpers.py /app/dashboard_helpers.py
COPY metadata.json /app/metadata.json
COPY assets/style.css /app/assets/style.css

COPY run.sh /app/run.sh

# braingeneers/braingeneers:latest defaults to jovyan, and you need to be root to read our ssl key file
USER root

ENTRYPOINT ["/app/run.sh"]
