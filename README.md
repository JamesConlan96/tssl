# TSSL

A wrapper around testssl.sh and aha to aid in TLS/SSL testing

## Usage

~~~
usage: tssl [-b] [-c] [-d DIRECTORY] [-e] [-fL FILE] [-fN FILE] [-fX FILE] [-h] [-H HEADER] [-l LABEL] [-o] [-p <host:port|auto>] [-pA PATH] [-pT PATH] [-s] [-t TIMEOUT] [-u URL] [-v] [-z]

help options:
  -h, --help            show this help message and exit

scan options:
  -b, --batch           do not prompt the user during execution
  -H, --header HEADER   HTTP header to add to all requests in the form '<name>: <value>' (can be specified multiple times per command)
  -p, --proxy <host:port|auto>
                        proxy to connect via in the form <host:port> or 'auto' to use value from $env ($http(s)_proxy)
  -pA, --aha-path PATH  path of aha executable (default: 'aha')
  -pT, --testssl-path PATH
                        path of testssl executable (default: 'testssl')
  -t, --timeout TIMEOUT
                        number of seconds a scan has to hang for in order to time out (default: 60)
  -v, --verbose         display verbose output

input options:
  -fL, --file-list FILE
                        newline delimited file containing URLs to scan (can be specified multiple times per command)
  -fN, --file-nessus FILE
                        nessus output file to determine targets from (can be specified multiple times per command)
  -fX, --file-xml FILE  nmap XML output file to determine targets from (can be specified multiple times per command)
  -u, --url URL         URL to scan (can be specified multiple times per command)

output options:
  -c, --command-only    output the manual command(s) to the console only; do not scan
  -d, --directory DIRECTORY
                        directory to save output to instead of the current working directory
  -e, --encrypt         compress output directory into an AES256 encrypted zip archive (includes existing files)
  -l, --label LABEL     add a label to output files
  -o, --overwrite       overwrite existing results
  -s, --skip            skip targets for which matching output files already exist
  -z, --zip             compress output directory into an unencrypted zip archive (includes existing files)
~~~

## Installation

### Pipx (recommended)

~~~
pipx install 'git+https://github.com/JamesConlan96/tssl.git'
~~~

### Docker

Note that the following is a guideline only and you may need to adjust the docker commands to fit your use case:

~~~
docker build -t tssl 'https://github.com/JamesConlan96/tssl.git#main' --network=host
docker run -it -v "$(pwd)/test:/tssl_out" --network=host tssl
~~~

## Requirements

- testssl.sh
- aha
- A web browser (not supported when running with Docker)
