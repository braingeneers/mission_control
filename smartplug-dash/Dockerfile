FROM braingeneers/braingeneers:latest

# Install dash and related packages
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir streamlit

COPY smartplug-dashboard.py /app/smartplug-dashboard.py

COPY run.sh /app/run.sh

# braingeneers/braingeneers:latest defaults to jovyan, and you need to be root to read our ssl key file
USER root

ENTRYPOINT ["/app/run.sh"]
