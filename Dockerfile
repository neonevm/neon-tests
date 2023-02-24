FROM ubuntu:20.04

RUN apt-get update && apt-get install -y python3-pip

COPY ./deploy/requirements/* /opt/
RUN pip3 install -r /opt/prod.txt -r /opt/ui.txt -r /opt/nodeps.txt

WORKDIR /opt/neon-tests
ADD ./ /opt/neon-tests
RUN python3 ./clickfile.py contracts