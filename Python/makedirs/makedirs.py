"""
:Module: makedirs.py

:Author:
    Peter Hyl

:Description: This module contains the functions for Linux ACL and
              functions to create user folders with defined subfolders.
"""
import configparser
import logging
import os
import shutil
import subprocess
import time

from ldap3 import AUTH_SIMPLE, GET_ALL_INFO, SEARCH_SCOPE_WHOLE_SUBTREE, STRATEGY_SYNC
from ldap3 import Server, Connection
from subprocess import CalledProcessError

ROOT_DIRS = []
USERS = []


def set_user_acl(path, username, rights):
    """
    This method set access for user dirs using command `setfacl -m` which modifies the current ACL.

    Args:
        path:               path to the destination directory
        username:           username
        rights:             rights that will be set
    """
    try:
        subprocess.check_call(["sudo", "setfacl",
                               "-n",
                               "-m",
                               "d:u:{}:{},u:{}:{}".format(username, rights, username, rights),
                               path])
    except CalledProcessError as exp:
        logging.error("Cannot set user ACL: %s", exp)


def set_groups_acl(path, groups, rights):
    """
    This method set access for groups dirs using command `setfacl -m` which modifies the current ACL.

    Args:
        path:               path to the destination directory
        groups:             group names (list)
        rights:             rights that will be set
    """
    for group in groups:
        try:
            subprocess.check_call(["sudo", "setfacl",
                                   "-n",
                                   "-m",
                                   "d:g:{}:{},g:{}:{}".format(group, rights, group, rights),
                                   path])
        except CalledProcessError as exp:
            logging.error("Cannot set group ACL: %s", exp)


def remove_acl(path, username):
    """
    Remove the user access to the directory.

    Args:
        path:               path to the destination directory
        username:               username
    """
    try:
        subprocess.check_call(["sudo", "setfacl",
                               "-d",
                               "-Rx",
                               "{}"
                              .format(username), path])
        subprocess.check_call(["sudo", "setfacl",
                               "-Rx",
                               "{}"
                              .format(username), path])
    except CalledProcessError as exp:
        logging.error("Cannot remove ACL: %s", exp)


def _LDAP(group):
    """
    Get all members of a group.

    Args:
        group: group to find users

    Returns:
        list of users
    """
    try:
        url = ""
        server = Server(url, getInfo=GET_ALL_INFO)
        connection = Connection(server, autoBind=True, clientStrategy=STRATEGY_SYNC, user='', password='',
                                authentication=AUTH_SIMPLE)

        result = connection.search(searchBase="",
                                   searchFilter="",
                                   searchScope=SEARCH_SCOPE_WHOLE_SUBTREE,
                                   attributes=[""])
    except Exception as error:
        logging.warning("[*] Could not make query on LDAP: %s", error)
    else:
        users = []
        if result:
            for r in connection.response:
                users.append(r['attributes'][""][0])
        else:
            logging.warning("[*] LDAP result error: %s", connection.result)
    finally:
        try:
            connection.unbind()
        except Exception as error:
            logging.warning("[*] Could not unbind connection: %s", error)
        logging.info("Loaded users from %s group", group)

        return users


def _makedirs(path):
    """
    Create new directory, if exists then continue

    Args:
        path:    path to new directory
    """
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as exp:
        logging.error("Directory error: %s", exp)


def is_subdir(name, subfolder):
    """
    Method check this subfolder and user allow subfolders.

    Args:
        name:                username (root folder)
        subfolder:           subfolder name
    """

    for user in USERS:
        if (name == user.name) and (subfolder in user.subfolders):
            return True
    return False


class Section(object):
    """
    Class contains sections on settings config.

    Args:
        name:               section name
        admis:              list of domain groups which gains admin access
        groups:             list of domain groups which gains user access
        user:               list of user specific access
        path:               path to the destination directory
        group_list:         list of the all Group
    """

    def __init__(self, name, admins, groups, user, path, groups_list):
        self.groups = []
        section_groups = set(groups + admins + user)

        for group in groups_list:
            if group.name in section_groups:
                self.groups.append(group)
        self.path = os.path.join(path, name)

        _makedirs(self.path)
        set_groups_acl(self.path, groups, "rx")
        set_groups_acl(self.path, admins, "rwx")


class Group(object):
    """
    Get all users that are in specified group.

    Args:
        name:                   group name
        subfolders              list group subfolders
        user_subfolders_dir:    path to the tree structure of subfolders
    """

    def __init__(self, name, subfolders, user_subfolders_dir):
        self.name = name
        self._subfolders = []
        for sub_folder in subfolders:
            if ".*" in sub_folder:
                temp = sub_folder.split(".*")[0]
                temp = temp.rsplit('/', 1)[0]
                path = os.path.join(user_subfolders_dir, temp)
                for path, dirs, files in os.walk(path):
                    if not dirs:
                        self._subfolders.append(path.replace(user_subfolders_dir + '/', ""))
            else:
                self._subfolders.append(sub_folder)

                # if name is user it's append, else it's group then load all users
        if "group" not in name:
            self.usernames = [name]
        else:
            self.usernames = _LDAP(name)

        # Add subfolders or create class User.
        for username in self.usernames:
            exists = False
            for user in USERS:
                if user.name == username:
                    user.add_subfolders(self._subfolders)
                    exists = True
                    break
            if not exists:
                USERS.append(User(username, self._subfolders))
                ROOT_DIRS.append(username)

    def makedirs(self, path):
        """
        Create user directory and user subfolders with correct ACL.

        Args:
            path:     must already exist and must have correct ACL for all domain groups
        """
        for username in self.usernames:
            user_path = os.path.join(path, username)  # rootdir
            _makedirs(user_path)
            set_user_acl(user_path, username, "rwx")

            for subfolder in self.subfolders:
                user_subfolder = os.path.join(user_path, subfolder)  # subdir
                _makedirs(user_subfolder)


class User(object):
    """
    Contain username and all user subfolders.

    Args:
        name:           username
        subfolders:     list user subfolders
    """

    def __init__(self, name, subfolders):
        self.name = name
        self.subfolders = set()
        for subfolder in subfolders:
            self.subfolders.add(subfolder)

    def add_subfolders(self, subfolders):
        """
        Add list of subfolders to the user
        """
        for subfolder in subfolders:
            self.subfolders.add(subfolder)


def create_dirs(sections):
    """
    Create tree structure subfolders
    """
    logging.info("Creating dirs...")
    for section in sections:
        for group in section.groups:
            group.makedirs(section.path)
    logging.info("Created.")


def clean_up(sections):
    """
    Clean up obsolete subdir or user dir
    """
    logging.info("Cleaning...")
    for section in sections:
        for rootdir in os.listdir(section.path):
            if rootdir not in ROOT_DIRS:
                shutil.rmtree(os.path.join(section.path, rootdir))
                logging.info("Should be deleted path: %s", os.path.join(section.path, rootdir))
            else:
                path = os.path.join(section.path, rootdir)
                for path, dirs, files in os.walk(path):
                    if not dirs:
                        temp = path.replace(os.path.join(section.path, rootdir) + '/', "")
                        if not is_subdir(rootdir, temp):
                            shutil.rmtree(os.path.join(temp, path))
                            logging.info("Should be deleted path: %s", os.path.join(temp, path))
    logging.info("Cleaned.")


def main():
    """
    Load configs and create objects
    """
    groups = []
    sections = []
    # loading data from config
    cfg = configparser.ConfigParser(allow_no_value=True, interpolation=configparser.ExtendedInterpolation())
    config_path = os.path.join("path", "to", "setting.cfg")
    cfg.read_file(open(config_path))

    directory = cfg.get("paths", "STORAGE")
    user_config_path = cfg.get("paths", "CONFIG")
    log_file = os.path.join(cfg.get("paths", "LOG"), "debug.log")
    user_config = os.path.join(user_config_path, "user_groups.cfg")
    user_subfolders_dir = cfg.get("paths", "USER_SUBFOLDERS")

    if not os.path.isdir(directory):
        os.makedirs(directory)

        # initialize logging
    logging.basicConfig(filename=log_file, filemode='w', level=logging.DEBUG)

    logging.info("Started.")
    start_time = time.time()
    user_cfg = configparser.ConfigParser(allow_no_value=True, interpolation=configparser.ExtendedInterpolation())
    user_cfg.read_file(open(user_config))

    # loading users subfolders and groups
    for section in user_cfg.sections():
        subfolders = set()
        for pattern in user_cfg.get(section, "SUBFOLDERS").split():
            subfolders.add(pattern)
        subfolders = list(subfolders)
        groups.append(Group(section, subfolders, user_subfolders_dir))

    for section in cfg.sections():
        if "dirs" not in section:
            try:
                users = cfg.get(section, "USERS").split(', ')
            except configparser.Error:
                users = []
            sections.append(Section(section, cfg.get(section, "ADMIN_GROUPS").split(', '),
                                    cfg.get(section, "USER_GROUPS").split(', '), users, directory, groups))

    logging.info("All setting are loaded")
    create_dirs(sections)
    clean_up(sections)
    logging.info("Finished.")
    logging.info("Elapsed time: %s", str(time.time() - start_time))


if __name__ == "__main__":
    main()
