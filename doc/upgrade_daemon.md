# Upgrading capricoinplusd daemon

This guide covers upgrading Capricoin+ daemon, when a new version is available.

## 1. Preparation

Login to your machine, replace `stakepoolvps` with the IP address or url of your pool:

    $ ssh stakepooluser@stakepoolvps

Shut down the pool and daemon (second line applies if you're running testnet version as well):

    $ sudo systemctl stop stakepool_live.service capricoinplusd_live.service
    $ sudo systemctl stop stakepool_test.service capricoinplusd_test.service

## 2. Update `coldstakepool` & `capricoinplusd` to latest version

Update the coldstakepool code:

    $ cd ~/capricoinplus_stakepool
    $ git pull
    $ sudo pip3 install --upgrade .

Update Capricoin+ Core:

    $ coldstakepool-prepare --update_core

Output should end (if successful) with lines similar to:

    capricoinplusd --version
    Capricoin+ Core Daemon version v0.18.1.7

## 3. Restart the pool

Start the pool/s back up (second line applies if you're running testnet version as well):

    $ sudo systemctl start stakepool_live.service
    $ sudo systemctl start stakepool_test.service

Verify if everything is running correctly:

```
$ ~/capricoinplus-binaries/capricoinplus-cli -datadir=${HOME}/stakepoolDemoLive getnetworkinfo
{
  "version": 18001000,
  "subversion": "/Satoshi:0.18.0.10/",
(..)
```

```
$ tail -n 1000 ~/stakepoolDemoLive/stakepool/stakepool.log | grep version
19-06-25_03-27-36	coldstakepool-run, version: 0.0.10
19-06-25_03-27-51	Capricoin+ Core version 18001000
```

In your browser, open `http://stakepoolvpsip:900/json/version`, you should see this:

    {"pool": "0.0.10", "core": "18001000"}

----

## Notes

You can select specific versions of Capricoin+ Core and where to place them using the following environment variables:

    $ CAPRICOINPLUS_BINDIR=~/capricoinplus-alpha CAPRICOINPLUS_VERSION=0.18.0.1 CAPRICOINPLUS_VERSION_TAG=alpha coldstakepool-prepare --update_core
