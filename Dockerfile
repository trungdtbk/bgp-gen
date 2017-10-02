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
RUN pip install --upgrade pip

WORKDIR /
# Install ExaBGP
RUN pip install -I -U exabgp

# Install YaBGP
RUN rm -r /yabgp &2>/dev/null
RUN git clone https://github.com/trungdtbk/yabgp
RUN \
    cd yabgp \
    && pip install -I -U -r requirements.txt \
    && python setup.py install 

# Install BGPStream (from CAIDA)
RUN apt-get update -y \
    && apt-get install -y \
    libbz2-dev \
    zlib1g-dev \
    libcurl4-gnutls-dev

RUN mkdir /src/
WORKDIR /src/
RUN wget https://research.wand.net.nz/software/wandio/wandio-1.0.4.tar.gz
RUN tar xzf wandio-1.0.4.tar.gz
RUN cd wandio-1.0.4
RUN ./configure
RUN make && make install

RUN cd /src/
RUN wget https://bgpstream.caida.org/bundles/caidabgpstreamwebhomepage/dists/bgpstream-1.1.0.tar.gz
RUN tar xzf bgpstream-1.1.0.tar.gz
RUN cd bgpstream-1.1.0
RUN ldconfig && ./configure && make && make install
RUN pip install pybgpstream
RUN ldconfig

COPY ./ /bgp-update-gen/
RUN \
    cd /bgp-update-gen \
    && pip install -I -U -r requirements.txt

VOLUME ["/var/log/bgp-gen/"]
CMD ["/bgp-update-gen/boot.sh"]
