FROM ubuntu:14.04

RUN apt-get update --fix-missing
RUN apt-get upgrade -y
RUN apt-get install -y --no-install-recommends \
    build-essential \
    net-tools \
    ifupdown \
    iputils-ping \
    wget \
    unzip \
    git

RUN apt-get install -y python-dev
RUN apt-get install -y python-pip

WORKDIR /
# Install ExaBGP
RUN pip install exabgp

# Install YaBGP
RUN rm -r /yabgp &2>/dev/null
RUN git clone https://github.com/trungdtbk/yabgp
RUN \
    cd yabgp \
    && pip install -r requirements.txt \
    && python setup.py install 

COPY ./ /bgp-update-gen/
RUN \
    cd /bgp-update-gen \
    && pip install -r requirements.txt

VOLUME ["/var/log/bgp-gen/"]
CMD ["/bgp-update-gen/boot.sh"]
