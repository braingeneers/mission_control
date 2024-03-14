FROM nextflow/nextflow:latest

RUN yum install python3 -y
RUN python3 -m pip install awscli
RUN python3 -m pip install --force-reinstall git+https://github.com/braingeneers/braingeneerspy.git#egg=braingeneerspy[iot,analysis,data]
