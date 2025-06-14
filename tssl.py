#! /usr/bin/env python3


""" tssl.py
A wrapper around testssl.sh and aha to assess TLS/SSL implementations and 
provide useful output files
"""


import argparse
import atexit
from datetime import datetime, timedelta
from getpass import getpass
from glob import glob
from libnmap.parser import NmapParser
import os
from password_strength import PasswordPolicy
from pathlib import PosixPath
import pexpect
import pyzipper
import re
from shutil import rmtree
import subprocess
import sys
import webbrowser
import xml.etree.ElementTree as ET
import zipfile


def genParser() -> argparse.ArgumentParser:
    """Generates a CLI argument parser
    @return: argument parser object
    """
    parser = argparse.ArgumentParser(add_help=False)
    helpOptions = parser.add_argument_group("help options")
    scanOptions = parser.add_argument_group("scan options")
    inputOptions = parser.add_argument_group("input options")
    outputOptions = parser.add_argument_group("output options")
    existOptions = outputOptions.add_mutually_exclusive_group()
    zipOptions = outputOptions.add_mutually_exclusive_group()
    scanOptions.add_argument('-b', '--batch', action="store_true",
                             help="do not prompt the user during execution")
    outputOptions.add_argument('-c', '--command-only', action="store_true",
                               help="output the manual command(s) to the "+
                               "console only; do not scan", dest="cmdOnly")
    outputOptions.add_argument('-d', '--directory', type=PosixPath, default='.',
                               help="directory to save output to instead of " +
                               "the current working directory", action="store")
    zipOptions.add_argument('-e', '--encrypt', action="store_true",
                            help="compress output directory into an AES256 " +
                            "encrypted zip archive (includes existing files)")
    inputOptions.add_argument('-fL', '--file-list', nargs=1, action="extend",
                              help="newline delimited file containing URLs to" +
                              " scan (can be specified multiple times per " +
                              "command)", type=PosixPath, dest="files",
                              metavar="FILE")
    inputOptions.add_argument('-fN', '--file-nessus', nargs=1, action="extend",
                              help="nessus output file to determine targets " +
                              "from (can be specified multiple times per " +
                              "command)", dest="filesNessus", metavar="FILE",
                              type=PosixPath)
    inputOptions.add_argument('-fX', '--file-xml', nargs=1, action="extend",
                              help="nmap XML output file to determine targets" +
                              " from (can be specified multiple times per " +
                              "command)", dest="filesXml", metavar="FILE",
                              type=PosixPath)
    helpOptions.add_argument('-h', '--help', action="help",
                             help="show this help message and exit")
    scanOptions.add_argument('-H', '--header', action="extend", nargs=1,
                             help="HTTP header to add to all requests in the " +
                             "form '<name>: <value>' (can be specified " +
                             "multiple times per command)", dest="headers",
                             metavar="HEADER")
    outputOptions.add_argument('-l', '--label', action="store",
                               help="add a label to output files")
    existOptions.add_argument('-o', '--overwrite', action="store_true",
                              help="overwrite existing results")
    scanOptions.add_argument('-p', '--proxy', action="store",
                             metavar="<host:port|auto>",
                             help="proxy to connect via in the form " +
                             "<host:port> or 'auto' to use value from $env " +
                             "($http(s)_proxy)")
    scanOptions.add_argument('-pA', '--aha-path', action="store",
                             dest="ahaPath", help="path of aha executable " +
                             "(default: 'aha')", metavar="PATH", type=PosixPath,
                             default="aha")
    scanOptions.add_argument('-pT', '--testssl-path', action="store",
                             dest="testsslPath", default="testssl",
                             metavar="PATH", help="path of testssl executable" +
                             " (default: 'testssl')", type=PosixPath)
    existOptions.add_argument('-s', '--skip', action="store_true",
                              help="skip targets for which matching output " +
                              "files already exist")
    scanOptions.add_argument('-t', '--timeout', action="store", type=int,
                             help="number of seconds a scan has to hang for " +
                             "in order to time out (default: 60)", default=60)
    inputOptions.add_argument('-u', '--url', nargs=1, action="extend",
                              help="URL to scan (can be specified multiple " +
                              "times per command)", dest="urls", metavar="URL")
    scanOptions.add_argument('-v', '--verbose', action="store_true",
                             help="display verbose output")
    zipOptions.add_argument('-z', '--zip', action="store_true",
                            help="compress output directory into an " +
                            "unencrypted zip archive (includes existing files)")
    return parser

def parseNessus(nessus: PosixPath) -> list:
    """Parses a nessus output file and returns a list of targets
    @param nessus: path to nessus output file to parse
    @return list of SSL/TLS endpoints
    """
    targets = []
    try:
        results = ET.parse(nessus)
    except:
        sys.exit(f"Error parsing nessus output file '{nessus}'")
    for host in results.findall("./Report/ReportHost"):
        for item in host.findall("ReportItem[@pluginID='10863']"):
            ip = host.find("HostProperties/tag[@name='host-ip']").text
            targets.append(f"{ip}:{item.attrib['port']}")
    return targets

def parseNmap(nmap: PosixPath) -> list:
    """Parses an nmap XML output file and returns a list of targets
    @param nmap: path to nmap XML output file to parse
    @return list of SSL/TLS endpoints
    """
    targets = []
    try:
        results = NmapParser.parse_fromfile(nmap)
    except:
        sys.exit(f"Error parsing nmap XML output file '{nmap}'")
    for host in results.hosts:
        for port in host.get_open_ports():
            svc = host.get_service(*port)
            if svc is not None:
                if svc.tunnel == "ssl":
                    targets.append(f"{host.address}:{svc.port}")
    return targets

def parseArgs() -> argparse.Namespace:
    """Parses CLI arguments
    @return: parsed arguments object
    """
    parser = genParser()
    args = parser.parse_args()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()
    toCheck = []
    for i in [args.files, args.filesNessus, args.filesXml, args.urls,
              args.label, args.headers, str(args.directory)]:
        if i is not None:
            toCheck.extend(i)
    for string in toCheck:
        if "'" in str(string):
            sys.exit("Arguments cannot contain single quotes (')")
    if not args.urls and not args.files and not args.filesNessus and not \
                                                                  args.filesXml:
        sys.exit("Please specify at least one target using one or more of " +
                 "-u/--url, -f/--file, -fN/--file-nessus, -fX/--file-xml")
    args.directory = args.directory.resolve()
    if args.directory.suffix == ".zip" and (args.zip or args.encrypt):
        args.directory = PosixPath(str(args.directory)[:-4])
    if args.cmdOnly:
        pass
    elif not args.directory.exists():
        if args.batch or yesNo(f"Output directory '{args.directory}' does not" +
                               " exist, create it?"):
            mkdirs(args.directory)
        else:
            sys.exit()
    elif not args.directory.is_dir():
        sys.exit(f"Specified output directory '{args.directory}' is not a " +
                 "directory")
    elif args.zip or args.encrypt:
        if not args.batch and not yesNo(f"Output directory '{args.directory}'" +
                                        " exists, all contents will be " +
                                        "compressed, continue?"):
            sys.exit()
    if args.zip or args.encrypt:
        if args.directory.with_suffix(".zip").exists() and not \
            args.overwrite:
                if args.batch:
                    sys.exit(f"Zip archive '{args.directory}.zip' exists, " +
                             "rerun using -o/--overwrite to overwrite it")
                elif not yesNo(f"Zip archive '{args.directory}.zip' exists, " +
                              "overwrite it?"):
                    sys.exit()
        if args.directory.samefile(os.getcwd()):
            sys.exit("Cannot zip the current directory, retry using " + 
                     "-d/--directory")
    if args.proxy is not None:
        proxyStrip = args.proxy.strip()
        if proxyStrip:
            args.proxy = proxyStrip
        else:
            sys.exit("Please specify a value for proxy")
    if args.headers:
        for header in args.headers:
            if not re.match(r'^.+?: .+?$', header):
                sys.exit(f"'{header}' is not a valid header")
    if args.encrypt:
        passPolicy = PasswordPolicy.from_names(length=12, uppercase=1,
                                               numbers=1, special=1)
        while True:
            passw = getpass("Password for zip archive: ")
            if not passPolicy.test(passw):
                if getpass("Confirm password: ") == passw:
                    args.passw = passw
                    break
                else:
                    print("Passwords did not match, try again")
            else:
                print("Passwords must be at least 12 characters long and " +
                      "contain at least 1 uppercase letter, 1 digit, and 1 " +
                      "special character")
    targets = []
    if args.urls:
        for target in args.urls:
            targets.append(target)
    if args.files:
        for target in args.files:
            target = target.resolve()
            if not target.exists():
                sys.exit(f"Input file '{target}' does not exist")
            with target.open() as f:
                for i in f.read().splitlines():
                    if i.startswith("<"):
                        sys.exit(f"Input file '{target}' contains invalid " +
                                 "targets. Did you mean to use -fN or -fX " +
                                 "instead of -f?")
    if args.filesNessus:
        for target in args.filesNessus:
            target = target.resolve()
            if not target.exists():
                sys.exit(f"Input file '{target}' does not exist")
            targets += parseNessus(target)
    if args.filesXml:
        for target in args.filesXml:
            target = target.resolve()
            if not target.exists():
                sys.exit(f"Input file '{target}' does not exist")
            targets += parseNmap(target)
    args.targets = set(filter(None, map(str.strip, targets)))
    if not args.targets:
        sys.exit("No targets detected")
    return args

def yesNo(prompt: str) -> bool:
        """Prompts the user for a yes/no response
        @param prompt: Prompt to display to the user
        @return: True if yes, False if no
        """
        yn = input(f"{prompt} (y/n): ")
        if yn.lower() == 'y':
            return True
        elif yn.lower() == 'n':
            return False
        else:
            return yesNo(prompt)
        
def mkdirs(path: PosixPath) -> None:
    """Makes the directories in a given path"""
    try:
        os.makedirs(path, exist_ok=True)
    except PermissionError:
        sys.exit(f"You do not have permission to write to '{path}'")

def runTestssl(args: argparse.Namespace) -> list[str]:
    """Runs testssl.sh and saves output files
    @param args: parsed CLI arguments object
    @return list of output filenames (without file extensions)
    """
    outDir = args.directory / "testssl"
    if not args.cmdOnly:
        mkdirs(outDir)
    outFiles = []
    testsslTimeout = 0 if args.timeout <= 10 else args.timeout - 10
    for target in args.targets:
        if target.strip() is None:
            continue
        try:
            targetStrip = re.match(r'^(.+?://)?(.+?)$', target.rstrip('/')
                                   ).group(2)
        except:
            targetStrip = target
        fileName = f"{outDir}/testssl_" + targetStrip.replace('/', '_').replace(' ', 
                                                           '').replace(':', '_')
        fileName = f"{fileName}_{args.label}" if args.label else fileName
        existingOutput = glob(f"{fileName}*")
        if existingOutput and not args.cmdOnly:
            if args.overwrite:
                for f in existingOutput:
                    try:
                        os.remove(f)
                    except:
                        sys.exit(f"Could not delete file '{f}'")
            elif args.skip:
                continue
            else:
                sys.exit(f"Output files for '{target}' already exist, " + 
                         "rerun with -o/--overwrite to overwrite them or " +
                         "-s/--skip to skip previously scanned hosts")
        testsslCmd = [str(args.testsslPath), '--warnings', 'batch', '--wide',
                      '--sneaky', '--color', '3', '-oJ', f"{fileName}.json",
                      '-oL', f"{fileName}.log", '-oC', f"{fileName}.csv", '-9',
                      '-E', target]
        if args.verbose:
            testsslCmd.insert(4, '--show-each')
        if args.proxy is not None:
            testsslCmd.insert(4, '--proxy')
            testsslCmd.insert(5, args.proxy)
        if testsslTimeout:
            testsslCmd.insert(4, '--connect-timeout')
            testsslCmd.insert(5, str(testsslTimeout))
            testsslCmd.insert(6, '--openssl-timeout')
            testsslCmd.insert(7, str(testsslTimeout))
        if args.headers:
            for header in args.headers:
                testsslCmd.insert(-9, '--reqheader')
                testsslCmd.insert(-9, header)
        htmlTitle = f"TestSSL - {target}"
        htmlTitle = f"{htmlTitle} - {args.label}" if args.label else htmlTitle
        ahaCmd = [str(args.ahaPath), '--black', '-t', htmlTitle]
        cmd = '/usr/bin/env bash -c "'
        toQuote = [' ', '/', '\\', ':']
        for i, arg in enumerate(testsslCmd):
            if i == 0:
                newArg = ""
                for char in arg:
                    if char in toQuote and char != "/":
                        char = f"\{char}"
                    newArg += char
                arg = newArg
            else:
                for char in toQuote:
                    if char in arg:
                        arg = f"'{arg}'"
                        break
            cmd += f"{arg} "
        cmd += "| tee >("
        for i, arg in enumerate(ahaCmd):
            if i == 0:
                newArg = ""
                for char in arg:
                    if char in toQuote and char != "/":
                        char = f"\{char}"
                    newArg += char
                arg = newArg
            else:
                for char in toQuote:
                    if char in arg:
                        arg = f"'{arg}'"
                        break
            cmd += f"{arg}"
            cmd += " "
        cmd += f'> {fileName}.html)"'
        if args.cmdOnly:
            print(f"{cmd}")
            continue
        cmdOutFile = f"{fileName}.sh"
        with open(cmdOutFile, 'w') as f:
            f.write(cmd)
        os.chmod(cmdOutFile, 0o755)
        testsslOut = b''
        run = True
        while run:
            testsslProc = pexpect.spawn(testsslCmd[0], testsslCmd[1:])
            testsslProc.logfile = sys.stdout.buffer
            while True:
                try:
                    testsslOut += testsslProc.read_nonblocking(
                                                           timeout=args.timeout)
                except pexpect.exceptions.TIMEOUT:
                    testsslProc.close()
                    if not args.batch and yesNo("\nCurrent scan timed out " +
                                                "(process hung for " +
                                                f"{args.timeout} seconds), " +
                                                "retry?"):
                        for dudOutFile in glob(f"{fileName}.*"):
                            os.remove(dudOutFile)
                    else:
                        run = False
                    break
                except pexpect.exceptions.EOF:
                    testsslProc.close()
                    run = False
                    break
        htmlFile = f"{fileName}.html"
        with open(htmlFile, 'w') as f:
            aha = subprocess.run(ahaCmd, input=testsslOut, stdout=f,
                                 stderr=sys.stderr)
        outFiles.append(fileName)
    return outFiles

def zipDir(path: PosixPath, passw: str = "") -> None:
    """Zips a directory
    @param path: path to the directory to zip
    @param encrypt: password to use to encrypt the zip (not encrypted if empty)
    """
    print("Creating zip archive...")
    path = path.resolve()
    passw = bytes(passw, "utf-8")
    zipName = f"{path}.zip"
    try:
        if passw:
            zip = pyzipper.AESZipFile(zipName, 'w',
                                      compression=pyzipper.ZIP_LZMA,
                                      encryption=pyzipper.WZ_AES)
            zip.setpassword(passw)
        else:
            zip = zipfile.ZipFile(zipName, 'w', compression=zipfile.ZIP_LZMA)
        atexit.register(zip.close)
        for root, dirs, files in os.walk(path):
            for file in files:
                zip.write(os.path.join(root, file),
                        os.path.relpath(os.path.join(root, file), 
                                        os.path.join(path, '..')))
    except:
        sys.exit(f"Could not create zip archive '{zipName}'")
    print("Verifying zip archive...")
    if passw:
        zip.close()
        atexit.unregister(zip.close)
        zip = pyzipper.AESZipFile(zipName, 'r')
        atexit.register(zip.close)
        zip.setpassword(passw)
    if zip.testzip() is None:
        zip.close()
        atexit.unregister(zip.close)
        print("Removing output directory...")
        try:
            rmtree(path)
        except:
            sys.exit(f"Could not remove directory '{path}'")
    else:
        sys.exit(f"Zip archive '{zipName}' corrupted")
    print(f"Output directory compressed to '{zipName}'")

def main() -> None:
    """Main method"""
    try:
        docker = True if os.getenv("TSSL_DOCKER") else False
        args = parseArgs()
        if not args.cmdOnly:
            pathTargets = PosixPath(args.directory, "targets_testssl.txt")
            if pathTargets.exists() and not args.overwrite:
                sys.exit(f"Target list '{pathTargets}' already exists, " + 
                         "rerun with -o/--overwrite to overwrite it")
            startTime = datetime.now()
            print("Starting scan at " +
                  f"{startTime.strftime('%d/%m/%Y - %H:%M:%S')}")
            print(f"Scanning {len(args.targets)} target(s)")
            if args.proxy:
                print(f"Using proxy '{args.proxy}'")
            with open(pathTargets, 'w') as f:
                f.write("\n".join(args.targets))
        outFiles = runTestssl(args)
        if not args.cmdOnly:
            endTime = datetime.now()
            dur = endTime - startTime
            dur -= timedelta(microseconds=dur.microseconds)
            print("Scanning completed at " + 
                f"{endTime.strftime('%d/%m/%Y - %H:%M:%S')} " +
                f"(Duration: {str(dur)})")
            if args.zip:
                zipDir(args.directory)
            elif args.encrypt:
                zipDir(args.directory, args.passw)
            else:
                print(f"Output files written to '{args.directory}'")
                if outFiles and not docker and not args.cmdOnly and not \
                    args.batch and yesNo("Would you like to view the HTML " +
                                         "output files now?"):
                    for url in outFiles:
                        webbrowser.open_new_tab(f"{url}.html")
    except KeyboardInterrupt:
        sys.exit("\nTerminated by user")


if __name__ == "__main__":
    main()
