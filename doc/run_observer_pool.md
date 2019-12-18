# Running a pool in 'observer' mode

Install the python code:

```
$ git clone https://github.com/Capricoinofficial/coldstakepool capricoinplus_stakepool
$ cd capricoinplus_stakepool
$ sudo pip3 install .
```

Set configurl to that of the pool you're interested in:

```
$ POOL_PATH=${HOME}/observer_pool
$ coldstakepool-prepare --datadir=${POOL_PATH} --testnet --mode=observer --configurl=http://66.172.10.231:901/config
```

```
$ ~/capricoinplus-binaries/capricoinplusd --datadir=${POOL_PATH}
$ coldstakepool-run -datadir=${POOL_PATH}/stakepool -testnet
```
