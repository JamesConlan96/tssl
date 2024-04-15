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
import zipfile


def genParser() -> argparse.ArgumentParser:
    """Generates a CLI argument parser
    @return: argument parser object
    """
    parser = argparse.ArgumentParser()
    existOptions = parser.add_mutually_exclusive_group()
    zipOptions = parser.add_mutually_exclusive_group()
    parser.add_argument('-d', '--directory', type=PosixPath, default='.',
                        help="directory to save output to instead of the " +
                        "current working directory")
    zipOptions.add_argument('-e', '--encrypt', action="store_true",
                            help="compress output directory into an AES256 " +
                            "encrypted zip archive (includes existing files)")
    parser.add_argument('-f', '--file', nargs=1, action="extend",
                        help="newline delimited file containing URLs to scan " +
                        "(can be specified multiple times per command)",
                        dest="files", metavar="FILE")
    parser.add_argument('-H', '--header', action="extend", nargs=1,
                        help="HTTP header to add to all requests in the form " +
                        "'<name>: <value>' (can be specified multiple times " +
                        "per command)", dest="headers", metavar="HEADER")
    parser.add_argument('-l', '--label', action="store",
                        help="add a label to output files")
    existOptions.add_argument('-o', '--overwrite', action="store_true",
                              help="overwrite existing results")
    existOptions.add_argument('-s', '--skip', action="store_true",
                              help="skip targets for which matching output " +
                              "files already exist")
    parser.add_argument('-t', '--timeout', action="store", type=int,
                        help="number of seconds a scan has to hang for in " +
                        "order to time out (default: 60)", default=60)
    parser.add_argument('-u', '--url', nargs=1, action="extend",
                        help="URL to scan (can be specified multiple times " +
                        "per command)", dest="urls", metavar="URL")
    parser.add_argument('-v', '--verbose', action="store_true",
                        help="display verbose output")
    zipOptions.add_argument('-z', '--zip', action="store_true",
                            help="compress output directory into an " +
                            "unencrypted zip archive (includes existing files)")
    return parser

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
    for i in [args.files, args.urls, args.label, args.headers,
              str(args.directory)]:
        if i is not None:
            toCheck.extend(i)
    for string in toCheck:
        if "'" in str(string):
            sys.exit("Arguments cannot contain single quotes (')")
    if not args.urls and not args.files:
        sys.exit("Please specify at least one target using -u/--url and/or " +
                 "-f/--file")
    args.directory = args.directory.resolve()
    if str(args.directory).endswith(".zip") and (args.zip or args.encrypt):
        args.directory = PosixPath(str(args.directory)[:-4])
    if not args.directory.exists():
        if yesNo(f"Output directory '{args.directory}' does not exist, create" +
                 " it?"):
            mkdirs(args.directory)
        else:
            sys.exit()
    elif not args.directory.is_dir():
        sys.exit(f"Specified output directory '{args.directory}' is not a " +
                 "directory")
    elif args.zip or args.encrypt:
        if not yesNo(f"Output directory '{args.directory}' exists, all " + 
                     "contents will be compressed, continue?"):
            sys.exit()
    if args.zip or args.encrypt:
        if PosixPath(f"{str(args.directory)}.zip").exists() and not \
            args.overwrite and not yesNo(f"Zip archive '{args.directory}.zip'" +
                                         " exists, overwrite it?"):
            sys.exit()
        if args.directory.resolve().samefile(os.getcwd()):
            sys.exit("Cannot zip the current directory, retry using " + 
                     "-d/--directory")
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
            try:
                target = PosixPath(target)
            except:
                sys.exit(f"'{target}' is not a valid file path")
            if not target.exists():
                sys.exit(f"Input file '{target}' does not exist")
            with target.open() as f:
                targets += f.read().splitlines()
    args.targets = set(targets)
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
    mkdirs(outDir)
    outFiles = []
    for target in args.targets:
        fileName = f"{outDir}/testssl_" + re.match(r'^(.+?://)?(.+?)$', 
                   target.rstrip('/')).group(2).replace('/', '_').replace(' ', 
                                                           '').replace(':', '_')
        fileName = f"{fileName}_{args.label}" if args.label else fileName
        existingOutput = glob(f"{fileName}*")
        if existingOutput:
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
        testsslCmd = ['testssl', '--warnings', 'batch', '--wide', '--sneaky', 
                      '--color', '3', '-oJ', f"{fileName}.json", '-oL', 
                      f"{fileName}.log", '-oC', f"{fileName}.csv", '-9', '-E',
                      target]
        if args.verbose:
            testsslCmd.insert(4, '--show-each')
        if args.headers:
            for header in args.headers:
                testsslCmd.insert(-9, '--reqheader')
                testsslCmd.insert(-9, header)
        htmlTitle = f"TestSSL - {target}"
        htmlTitle = f"{htmlTitle} - {args.label}" if args.label else htmlTitle
        ahaCmd = ['aha', '--black', '-t', htmlTitle]
        with open(f"{fileName}.command", 'w') as f:
            toQuote = [' ', '/', '\\', ':']
            for arg in testsslCmd:
                for char in toQuote:
                    if char in arg:
                        arg = f"'{arg}'"
                        break
                f.write(f"{arg} ")
            f.write("| ")
            for i, arg in enumerate(ahaCmd):
                for char in toQuote:
                    if char in arg:
                        arg = f"'{arg}'"
                        break
                f.write(f"{arg}")
                if i != len(ahaCmd) - 1:
                    f.write(" ")
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
                    if yesNo("\nCurrent scan timed out (process hung for " +
                             f"{args.timeout} seconds), retry?"):
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
        startTime = datetime.now()
        print(f"Starting scan at {startTime.strftime('%d/%m/%Y - %H:%M:%S')}")
        outFiles = runTestssl(args)
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
            if outFiles and not docker and \
                yesNo("Would you like to view the HTML output files now?"):
                for url in outFiles:
                    webbrowser.open_new_tab(f"{url}.html")
    except KeyboardInterrupt:
        sys.exit("\nTerminated by user")


if __name__ == "__main__":
    main()
