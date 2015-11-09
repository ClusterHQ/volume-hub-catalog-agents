FROM        ubuntu:14.04

# Last build date - this can be updated whenever there are security updates so
# that everything is rebuilt
ENV         security_updates_as_of 2015-11-02

# Install security updates and required packages
RUN         apt-get -qy update && \
            apt-get -qy upgrade && \
            apt-get -qy install python-pip && \
            apt-get -qy install python-dev && \
            apt-get -qy install libyaml-dev && \
            apt-get -qy install libffi-dev && \
            apt-get -qy install libssl-dev && \
            apt-get -qy install python-virtualenv

RUN         virtualenv /app/

ADD         . /source
WORKDIR     /source

# Install requirements from the project's setup.py
RUN         /app/bin/pip install .

WORKDIR     /app
