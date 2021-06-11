=======
🐟 ryba
=======

Backs up directories on your computer to remote targets using `rsync`,
Creates a timestamped snapshot of the current state,
and rotates old backups.

Installation
============

.. code-block:: shell

    $ pip3 install --user "ryba"

Usage
=====

``ryba`` uses a configuration file to store all the backup source and target directories.
See `Configuration`_ for instructions on creating a configuration file.

To back up every configured directory, run the ``ryba`` command:

.. code-block:: shell

    $ ryba

A few commonly useful options:

``ryba -v``
    Print more information when running. Use a second time for even more verbosity.
``ryba backup --dry-run``
    Do not make any changes, only print what would happen.
``ryba backup --directory <directory>``
    Back up only this configured directory.

See ``ryba --help`` and ``ryba backup --help`` for more options.

Configuration
=============

Configuration lives in the file ``~/.config/ryba/config.toml``.
It uses the `TOML`_ file format.

Three things need to be configured:

#. Source directories that will be backed up
#. Targets where backups will be stored
#. How to rotate backups

Source directories
------------------

These are directories on the host computer that need backing up.
A directory needs a source, a target, and a backup rotation strategy.

The following is the minimal configuration to define a source directory:

.. code-block:: toml

    [[backup]]
    source = "~/Documents"
    target = "delorian:/backups/Documents/"
    rotate = "monthly"

``source``
    The path to a directory that will be backed up.
``target``
    A named target - in this case "delorian" -
    and the path on the target where backups should be created,
    separated by a colon ``:``.
``rotate``
    A rotation strategy. Optional.
    If this is not set, all backups will be kept.
    A backup rotation strategy can be defined later, and old backups will be cleaned up.

There are a number of optional fields you can also define:

``exclude_from``
    The name of an exclude file, used with the ``rsync --exclude-from`` option.
    By default, if a file named ``.rsync-exclude`` is found in the ``source`` directory,
    that file is used.
    You can name another file to use instead.
    Relative paths are resolved relative to ``source``.
``exclude_files``
    A list of patterns to use with the ``rsync --exclude`` option.
``one_file_system``
    Set ``rsync --one-file-system``. Defaults to true.

Targets
-------

Targets are where backups are stored.
Targets must have a name.
To define a target named "delorian", make a section named ``[target.delorian]``.
The options available for targets depend on the type.

Local targets
*************

Backs up one directory on your local machine to another.
Useful for backing up to a mounted external hard drive, for example.

.. code-block:: toml

    [target.tardis]
    type = "local"
    path = "/mount/tardis"

SSH targets
***********

Backs up to a remote server using SSH.
Defaults for some SSH options are pulled from ``~/.ssh/config`` if possible.

.. code-block:: toml

    [target.briefcase]
    type = "ssh"

Available options:

``hostname``
    The hostname of the server. Defaults to the target name if not set.
``username``
    The username to authenticate to the remote server with.
    Defaults to your username if not set.
``port``
    The SSH port to use.
``path``
    A base path to use for all backups. Optional, defaults to ``/``.
    This is useful if the server has an external drive mounted
    that you would like to place all backups on, for example.
    All target directories from the backup definition are taken as relative to this path.

Rotation strategies
-------------------

Every time a backup is made, a timestamped snapshot is created.
These snapshots are made using hard links,
so multiple snapshots do not take up an unreasonable amount of space.
However, backups still need rotating.
A rotation strategy define how to keep or delete old snapshots.

Rotation strategies must have a name.
To define a rotation strategy named "monthly", make a section named ``[rotate.monthly]``.
The options available for a rotation strategy depend on the strategy.

Keep all
********

The most basic strategy simply keeps all backups.

.. code-block:: toml

    [rotate.keep-all]
    strategy = "all"

Keep ``n`` most recent
**********************

This will keep a fixed number of the most recent backups.

.. code-block:: toml

    [rotate.keep-7]
    strategy = "latest"
    count = 7

Date buckets
************

This will keep some configurable number of backups per time period.

.. code-block:: toml

    [rotate.6-months]
    strategy = "date-bucket"
    # Keep one backup per day for seven days
    day = 7
    # Keep one backup per week for four weeks
    week = 4
    # Keep one backup per month for six months
    month = 6

Available buckets are ``hour``, ``day``, ``week``, ``month``, ``year``.
Backups are sorted in to buckets based on their timestamp.
A setting of ``day = 7`` will keep one backup from the seven most recent distinct days.
A setting of ``week = 4`` will keep one backup from the four most recent distinct weeks.
The value ``"all"`` for a bucket can be used to keep one backup per bucket with no limit.
A setting of ``year = "all"`` will keep one backup per year with no limit.
A backup can be kept by multiple buckets.

One backup is kept per bucket, but the buckets do not have to be contiguous in time.
If you only make one backup per week, and have ``days = 7``,
this will still keep one backup per distinct days,
but the days will be spread over seven weeks.

By default, the oldest backup in a bucket will be kept.
If you took a backup every day, and had ``month = 6``,
one backup from the first day of the last six months would be kept.
This would result in keeping backups from ``2021-01-01``, ``2021-02-01``, ``2021-03-01``, and so forth.
If you would prefer to keep the newest backup in a bucket instead, set ``prefer_newest = true``.
This would result in keeping a backup from ``2021-01-31``, ``2021-02-28``, ``2021-03-31``, and so forth.

.. _TOML: https://toml.io/
