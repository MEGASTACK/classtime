#
# Yo dawg, I heard you like Docker
#
# To build dockerized-classtime: 
#   docker build -t rosshamish/classtime:latest . 
#
# To run dockerized-classtime, simply do
# 	docker run rosshamish/classtime
#
# You may need to do some network configuration to
# expose port 5000, especially under boot2docker.
# (documentation on this coming soon? :) )
#

FROM centos:7

MAINTAINER MEGASTACK

RUN yum install -y epel-release
RUN yum install -y gcc-c++
RUN yum install -y python-pip
RUN yum install -y libpqxx-devel
RUN yum install -y python-devel
RUN yum install -y openldap-devel

ADD . /opt/classtime
WORKDIR /opt/classtime

RUN pip install -r requirements.txt

EXPOSE 5000
CMD ["python", "./runserver.py"]