FROM python
RUN apt update && apt install -y aha testssl.sh
WORKDIR /app
COPY . .
RUN mkdir /tssl_out
VOLUME /tssl_out
ENV TSSL_DOCKER=1
ENTRYPOINT ["/app/tssl.py", "-d", "/tssl_out"]