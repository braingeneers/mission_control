FROM continuumio/anaconda3:latest

# Apt packages
RUN apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
        wget \
        curl \
        nano \
        zip \
        git \
        awscli \
#        glances \
        screen \
        fonts-freefont-ttf \
        sqlite3


# Pip installs
COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r ./requirements.txt && \
    python -m pip install --force-reinstall git+https://github.com/braingeneers/braingeneerspy.git@self-hosted-mqtt#egg=braingeneerspy[iot]

# PRP environment variables
ENV ENDPOINT_URL="https://s3.nautilus.optiputer.net"
# Tensorflow environment variables
ENV S3_ENDPOINT="s3.nautilus.optiputer.net"
ENV AWS_LOG_LEVEL=3
ENV TF_CPP_MIN_LOG_LEVEL=3
# Environment setup
#ENV PYTHONPATH="/console:/console/apps/dash-extensions"
#ENV PATH=".:${PATH}"
RUN echo 'alias aws3="aws --endpoint https://s3.nautilus.optiputer.net s3"' >> ~/.bashrc && \
    echo 'alias awsn="aws --endpoint https://s3.nautilus.optiputer.net"' >> ~/.bashrc && \
    echo 'alias ll="ls -alh --color"' >> ~/.bashrc && \
    echo 'alias lsw="watch -n 0.25 ls -alh"' >> ~/.bashrc && \
    printf 'shell "/bin/bash"\ntermcapinfo xterm* ti@:te@\nterm xterm-color;' >> ~/.screenrc && \
    mkdir -p /console


#this pip install breaks the build when done earlier
RUN pip install PyGithub

COPY . /console
WORKDIR /console
ENTRYPOINT ["python", "app.py"]
EXPOSE 8050:8050
