#!/usr/bin/python3
"""
:Module: daemon.py

:Author:
    Peter Hyl

:Description:
    This is the executable module (daemon) for the Unix system
"""

import argparse
import atexit
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from subprocess import call

LOG_PATH = "/var/log/example/daemon"


class Daemon:
    """
    Daemon class.
    """
    def __init__(self, pid_file, stdout=os.path.join(LOG_PATH, 'stdout.log'),
                 stderr=os.path.join(LOG_PATH, 'stderr.log')):
        self.stdout = stdout
        self.stderr = stderr
        self.pid_file = pid_file

    def daemonize(self):
        """
        Do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment"
        """
        # fork 1 to spin off the child that will spawn the deamon.
        if os.fork():
            # exit first parent
            sys.exit()

        # This is the child.
        # 1. cd to root for a guarenteed working dir.
        # 2. clear the session id to clear the controlling TTY.
        # 3. set the umask so we have access to all files created by the daemon.
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # fork 2 ensures we can't get a controlling ttd.
        if os.fork():
            sys.exit()

        # This is a child that can't ever have a controlling TTY.
        # Now we shut down stdin and point stdout/stderr at log files.

        # stdin
        with open(os.devnull, 'r') as dev_null:
            os.dup2(dev_null.fileno(), sys.stdin.fileno())

        # stderr - do this before stdout so that errors about setting stdout write to the log file.
        #
        # Exceptions raised after this point will be written to the log file.
        sys.stderr.flush()
        with open(self.stderr, 'a+') as stderr:
            os.dup2(stderr.fileno(), sys.stderr.fileno())

        # stdout
        #
        # Print statements after this step will not work. Use sys.stdout
        # instead.
        sys.stdout.flush()
        with open(self.stdout, 'a+') as stdout:
            os.dup2(stdout.fileno(), sys.stdout.fileno())

    def create_pid_file(self):
        """
        Write pid file
        """
        # Before file creation, make sure we'll delete the pid file on exit!
        atexit.register(self.del_pid)
        pid = os.getpid()
        pid_dir = os.path.dirname(self.pid_file)

        if not os.path.exists(pid_dir):
            call(["sudo", "mkdir", pid_dir])
            call(["sudo", "chown", "user:group", pid_dir])
        with open(self.pid_file, 'w+') as pid_file:
            pid_file.write('{}'.format(pid))

    def del_pid(self):
        """
        Delete the pid file.
        """
        os.remove(self.pid_file)

    def get_pid_by_file(self):
        """
        Return the pid read from the pid file.
        """
        try:
            with open(self.pid_file, 'r') as pid_file:
                pid = int(pid_file.read().strip())
            return pid
        except IOError:
            return

    def start(self, args):
        """
        Start the daemon.
        """
        print("Starting daemon...")
        if self.get_pid_by_file():
            print("PID file {} exists. Is the deamon already running?".format(self.pid_file))
            sys.exit(1)

        if args.daemon:
            self.daemonize()
        self.create_pid_file()
        self.run()

    def stop(self, _):
        """
        Stop the daemon.
        """
        print("Stopping daemon...")
        pid = self.get_pid_by_file()
        if not pid:
            print("PID file {} doesn't exist. Is the daemon not running?".format(self.pid_file))
            return

        stopping_time = datetime.now()
        # Time to kill.
        try:
            while 1:
                if datetime.now() - timedelta(minutes=10) > stopping_time:
                    os.kill(pid, signal.SIGKILL)
                else:
                    os.kill(pid, signal.SIGTERM)
                time.sleep(1)
        except OSError as err:
            if "No such process" in err.strerror:
                if os.path.exists(self.pid_file):
                    os.remove(self.pid_file)
            else:
                print(err)
                sys.exit(1)

    def run(self):
        """
        You should override this method when you subclass Daemon.
        It will be called after the process has been
        daemonized by start() or restart().
        """
        raise NotImplementedError


def main():
    """
    This method parses arguments supplied to the script
    """
    daemon = Daemon("/run/autoclave/autoclave.pid")

    # parse arguments
    parser = argparse.ArgumentParser(description="Daemon used for your application")

    parsers = parser.add_subparsers(help="Daemon commands")
    stop = parsers.add_parser(
        "stop",
        help="Stop daemon"
    )
    stop.set_defaults(handler=daemon.stop)

    start = parsers.add_parser(
        "start",
        help="Start daemon"
    )
    start.add_argument(
        "-d", "--daemon",
        help="Daemonize this application",
        action="store_true"
    )
    start.set_defaults(handler=daemon.start)

    if not len(sys.argv) > 1:
        parser.print_help()
        sys.exit()

    return parser.parse_args()


if __name__ == '__main__':
    args = main()
    args.handler(args)
