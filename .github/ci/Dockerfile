FROM rockylinux:9

RUN dnf -y update && \
    dnf -y install epel-release && \
    dnf -y install \
      git \
      gcc \
      make \
      python3.12 \
      python3.12-pip \
      python3.12-devel \
      pkgconfig \
      mariadb-connector-c-devel && \
    dnf clean all

RUN ln -sf /usr/bin/python3.12 /usr/local/bin/python && \
    ln -sf /usr/bin/python3.12 /usr/local/bin/python3 && \
    ln -sf /usr/bin/pip3.12 /usr/local/bin/pip && \
    ln -sf /usr/bin/pip3.12 /usr/local/bin/pip3

RUN python3 -m pip install --upgrade pip setuptools wheel
