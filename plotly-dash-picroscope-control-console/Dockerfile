# Use official Python 3.10 slim image
FROM python:3.10-slim

# Install apt packages
RUN apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
        wget curl nano zip git awscli screen fonts-freefont-ttf sqlite3 && \
    rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /console

# Copy requirements.txt
COPY requirements.txt /tmp/requirements.txt

# Upgrade pip and install Python packages
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    # Force reinstall packages that braingeneers expects metadata for
    #pip install --no-cache-dir --force-reinstall --ignore-installed \
    #    paho-mqtt==2.1.0 redis==6.4.0 schedule && \
    #python -m pip install --force-reinstall git+https://github.com/braingeneers/braingeneerspy.git
    pip install braingeneers    
#python -m pip install --force-reinstall git+https://github.com/braingeneers/braingeneerspy.git@self-hosted-mqtt#egg=braingeneerspy[iot]
# Ensure required optional packages for braingeneers.iot are correctly installed
#RUN pip install --no-cache-dir --upgrade --force-reinstall --no-binary :all: redis paho-mqtt schedule

# Copy application code
COPY . /console

# Environment variables
ENV ENDPOINT_URL="https://s3.nautilus.optiputer.net"
ENV S3_ENDPOINT="s3.nautilus.optiputer.net"
ENV AWS_LOG_LEVEL=3
ENV TF_CPP_MIN_LOG_LEVEL=3

# Shell aliases and setup
RUN echo 'alias aws3="aws --endpoint https://s3.nautilus.optiputer.net s3"' >> ~/.bashrc && \
    echo 'alias awsn="aws --endpoint https://s3.nautilus.optiputer.net"' >> ~/.bashrc && \
    echo 'alias ll="ls -alh --color"' >> ~/.bashrc && \
    echo 'alias lsw="watch -n 0.25 ls -alh"' >> ~/.bashrc && \
    printf 'shell "/bin/bash"\ntermcapinfo xterm* ti@:te@\nterm xterm-color;' >> ~/.screenrc && \
    mkdir -p /console

# Expose Dash default port
EXPOSE 8050

# Run the app
ENTRYPOINT ["python", "app.py"]
#ENTRYPOINT ["tail", "-f", "/dev/null"]
