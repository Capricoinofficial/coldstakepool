#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2018-2019 The Particl Core developers
# Copyright (c) 2020 The Capricoin+ Core developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE.txt or http://www.opensource.org/licenses/mit-license.php.

"""

Minimal example of starting a CapricoinPlus stake pool.

1. Download and verify a capricoinplus-core release.

2. Create a capricoinplus.conf that:
    - Starts 2 wallets
    - Enables zmqpubhashblock
    - Enables csindex and addressindex

3. Generate and import a recovery phrase for both wallets.
4. Generate the pool_stake_address from the staking wallet.
    - The address pool participants will set their outputs to stake with.
5. Generate the pool_reward_address from the reward wallet.
    - The address that will collect the rewards for blocks staked by the pool.
6. Disable staking on the reward wallet.
7. Set the reward address of the staking wallet.
8. Create the stakepool.json configuration file.


Install dependencies:
apt-get install wget gnupg

Run the prepare script:
coldstakepool-prepare.py -datadir=~/stakepoolDemoTest -testnet

Start the daemon:
~/capricoinplus-binaries/capricoinplusd -datadir=/home/$(id -u -n)/stakepoolDemoTest

Start the pool script:
coldstakepool-run.py -datadir=~/stakepoolDemoTest/stakepool -testnet


"""

import sys
import os
import subprocess
import time
import json
import hashlib
import mmap
import urllib.request
from coldstakepool.util import (
    callrpc_cli,
)


CAPRICOINPLUS_BINDIR = os.path.expanduser(os.getenv('CAPRICOINPLUS_BINDIR', '~/capricoinplus-binaries'))
CAPRICOINPLUSD = os.getenv('CAPRICOINPLUSD', 'capricoinplusd')
CAPRICOINPLUS_CLI = os.getenv('CAPRICOINPLUS_CLI', 'capricoinplus-cli')
CAPRICOINPLUS_TX = os.getenv('CAPRICOINPLUS_CLI', 'capricoinplus-tx')

CAPRICOINPLUS_VERSION = os.getenv('CAPRICOINPLUS_VERSION', '0.18.1.7')
CAPRICOINPLUS_VERSION_TAG = os.getenv('CAPRICOINPLUS_VERSION_TAG', '')
CAPRICOINPLUS_ARCH = os.getenv('CAPRICOINPLUS_ARCH', 'x86_64-linux-gnu.tar.gz')
CAPRICOINPLUS_REPO = os.getenv('CAPRICOINPLUS_REPO', 'Capricoinofficial')


def startDaemon(nodeDir, bindir):
    command_cli = os.path.join(bindir, CAPRICOINPLUSD)

    args = [command_cli, '-daemon', '-noconnect', '-nostaking', '-nodnsseed', '-datadir=' + nodeDir]
    p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = p.communicate()

    if len(out[1]) > 0:
        raise ValueError('Daemon error ' + str(out[1]))
    return out[0]


def downloadCapricoinPlusCore():
    print('Download and verify CapricoinPlus core release.')

    if 'osx' in CAPRICOINPLUS_ARCH:
        os_dir_name = 'osx-unsigned'
        os_name = 'osx'
    elif 'win32-setup' in CAPRICOINPLUS_ARCH or 'win64-setup' in CAPRICOINPLUS_ARCH:
        os_dir_name = 'win-signed'
        os_name = 'win-signer'
    elif 'win32' in CAPRICOINPLUS_ARCH or 'win64' in CAPRICOINPLUS_ARCH:
        os_dir_name = 'win-unsigned'
        os_name = 'win'
    else:
        os_dir_name = 'linux'
        os_name = 'linux'

    signing_key_fingerprint = '8BE6C158D381E7AA68095502B48A2245CFE7C482'
    signing_key_name = 'CapricoinPlus'

    if os_dir_name == 'win-signed':
        assert_filename = 'capricoinplus-{}-build.assert'.format(os_name)
    else:
        assert_filename = 'capricoinplus-{}-{}-build.assert'.format(os_name, CAPRICOINPLUS_VERSION)

    assert_url = 'https://raw.githubusercontent.com/%s/gitian.sigs/master/%s-%s/%s/%s' % (CAPRICOINPLUS_REPO, CAPRICOINPLUS_VERSION + CAPRICOINPLUS_VERSION_TAG, os_dir_name, signing_key_name, assert_filename)
    assert_path = os.path.join(CAPRICOINPLUS_BINDIR, assert_filename)

    release_filename = 'capricoinplus-{}-{}'.format(CAPRICOINPLUS_VERSION, CAPRICOINPLUS_ARCH)
    release_url = 'https://github.com/%s/capricoinplus-core/releases/download/v%s/%s' % (CAPRICOINPLUS_REPO, CAPRICOINPLUS_VERSION + CAPRICOINPLUS_VERSION_TAG, release_filename)

    if not os.path.exists(assert_path):
        subprocess.check_call(['wget', assert_url, '-P', CAPRICOINPLUS_BINDIR])

    sig_path = os.path.join(CAPRICOINPLUS_BINDIR, 'capricoinplus-%s-%s-build.assert.sig' % (os_name, CAPRICOINPLUS_VERSION))
    if not os.path.exists(sig_path):
        subprocess.check_call(['wget', assert_url + '.sig?raw=true', '-O', sig_path])

    packed_path = os.path.join(CAPRICOINPLUS_BINDIR, release_filename)
    if not os.path.exists(packed_path):
        subprocess.check_call(['wget', release_url, '-P', CAPRICOINPLUS_BINDIR])

    hasher = hashlib.sha256()
    with open(packed_path, 'rb') as fp:
        hasher.update(fp.read())
    release_hash = hasher.digest()

    print('Release hash:', release_hash.hex())
    with open(assert_path, 'rb', 0) as fp, mmap.mmap(fp.fileno(), 0, access=mmap.ACCESS_READ) as s:
        if s.find(bytes(release_hash.hex(), 'utf-8')) == -1:
            sys.stderr.write('Error: release hash %s not found in assert file.' % (release_hash.hex()))
            exit(1)
        else:
            print('Found release hash %s in assert file.' % (release_hash.hex()))

    try:
        subprocess.check_call(['gpg', '--list-keys', signing_key_fingerprint])
    except Exception:
        print('Downloading release signing pubkey')
        keyservers = ['keyserver.ubuntu.com', 'hkp://subset.pool.sks-keyservers.net']
        for ks in keyservers:
            try:
                subprocess.check_call(['gpg', '--keyserver', ks, '--recv-keys', signing_key_fingerprint])
            except Exception:
                continue
            break
        subprocess.check_call(['gpg', '--list-keys', signing_key_fingerprint])

    try:
        subprocess.check_call(['gpg', '--verify', sig_path, assert_path])
    except Exception:
        sys.stderr.write('Error: Signature verification failed!')
        exit(1)


def extractCapricoinPlusCore():
    packed_path = os.path.join(CAPRICOINPLUS_BINDIR, 'capricoinplus-%s-%s' % (CAPRICOINPLUS_VERSION, CAPRICOINPLUS_ARCH))
    daemon_path = os.path.join(CAPRICOINPLUS_BINDIR, CAPRICOINPLUSD)
    bin_prefix = 'capricoinplus-%s/bin' % (CAPRICOINPLUS_VERSION)
    subprocess.check_call(['tar', '-xvf', packed_path, '-C', CAPRICOINPLUS_BINDIR, '--strip-components', '2',
                           os.path.join(bin_prefix, CAPRICOINPLUSD), os.path.join(bin_prefix, CAPRICOINPLUS_CLI), os.path.join(bin_prefix, CAPRICOINPLUS_TX)])

    output = subprocess.check_output([daemon_path, '--version'])
    version = output.splitlines()[0].decode('utf-8')
    print('capricoinplusd --version\n' + version)
    assert(CAPRICOINPLUS_VERSION in version)


def printVersion():
    from coldstakepool import __version__
    print('CapricoinPlus coldstakepool version:', __version__)


def printHelp():
    print('Usage: coldstakepool-prepare ')
    print('\n--help, -h                 Print help.')
    print('\n--version, -v              Print version.')
    print('\n--update_core              Download, verify and extract CapricoinPlus core release and exit.')
    print('\n--download_core            Download and verify CapricoinPlus core release and exit.')
    print('\n--datadir=PATH             Path to CapricoinPlus data directory, default:~/.capricoinplus.')
    print('\n--pooldir=PATH             Path to stakepool data directory, default:{datadir}/stakepool.')
    print('\n--mainnet                  Run CapricoinPlus in mainnet mode.')
    print('\n--testnet                  Run CapricoinPlus in testnet mode.')
    print('\n--regtest                  Run CapricoinPlus in regtest mode.')
    print('\n--stake_wallet_mnemonic=   Recovery phrase to use for the staking wallet, default is randomly generated.')
    print('\n--reward_wallet_mnemonic=  Recovery phrase to use for the reward wallet, default is randomly generated.')
    print('\n--mode=master/observer     Mode stakepool is initialised to. observer mode requires configurl to be specified, default:master.')
    print('\n--configurl=url            Url to pull the stakepool config file from when initialising for observer mode.')


def main():
    dataDir = None
    poolDir = None
    chain = 'mainnet'
    mode = 'master'
    configurl = None
    stake_wallet_mnemonic = None
    reward_wallet_mnemonic = None

    for v in sys.argv[1:]:
        if len(v) < 2 or v[0] != '-':
            print('Unknown argument', v)
            continue

        s = v.split('=')
        name = s[0].strip()

        for i in range(2):
            if name[0] == '-':
                name = name[1:]

        if name == 'v' or name == 'version':
            printVersion()
            return 0
        if name == 'h' or name == 'help':
            printHelp()
            return 0
        if name == 'update_core':
            downloadCapricoinPlusCore()
            extractCapricoinPlusCore()
            return 0
        if name == 'download_core':
            downloadCapricoinPlusCore()
            return 0
        if name == 'mainnet':
            continue
        if name == 'testnet':
            chain = 'testnet'
            continue
        if name == 'regtest':
            chain = 'regtest'
            continue

        if len(s) == 2:
            if name == 'datadir':
                dataDir = os.path.expanduser(s[1])
                continue
            if name == 'pooldir':
                poolDir = os.path.expanduser(s[1])
                continue
            if name == 'stake_wallet_mnemonic':
                stake_wallet_mnemonic = s[1]
                continue
            if name == 'reward_wallet_mnemonic':
                reward_wallet_mnemonic = s[1]
                continue
            if name == 'mode':
                mode = s[1]
                if mode != 'master' and mode != 'observer':
                    sys.stderr.write('Unknown value for mode:' + mode)
                    exit(1)
                continue
            if name == 'configurl':
                configurl = s[1]
                continue

        print('Unknown argument', v)

    if mode == 'observer' and configurl is None:
        sys.stderr.write('observer mode requires configurl set\n')
        exit(1)

    if not os.path.exists(CAPRICOINPLUS_BINDIR):
        os.makedirs(CAPRICOINPLUS_BINDIR)

    # 1. Download and verify the specified version of capricoinplus-core
    downloadCapricoinPlusCore()
    extractCapricoinPlusCore()

    dataDirWasNone = False
    if dataDir is None:
        dataDir = os.path.expanduser('~/.capricoinplus')
        dataDirWasNone = True

    if poolDir is None:
        if dataDirWasNone:
            poolDir = os.path.join(os.path.expanduser(dataDir), ('' if chain == 'mainnet' else chain), 'stakepool')
        else:
            poolDir = os.path.join(os.path.expanduser(dataDir), 'stakepool')

    print('dataDir:', dataDir)
    print('poolDir:', poolDir)
    if chain != 'mainnet':
        print('chain:', chain)

    if not os.path.exists(dataDir):
        os.makedirs(dataDir)

    if not os.path.exists(poolDir):
        os.makedirs(poolDir)

    # 2. Create a capricoinplus.conf
    daemonConfFile = os.path.join(dataDir, 'capricoinplus.conf')
    if os.path.exists(daemonConfFile):
        sys.stderr.write('Error: %s exists, exiting.' % (daemonConfFile))
        exit(1)

    zmq_port = 207922 if chain == 'mainnet' else 208922
    with open(daemonConfFile, 'w') as fp:
        if chain != 'mainnet':
            fp.write(chain + '=1\n\n')

        fp.write('zmqpubhashblock=tcp://127.0.0.1:%d\n' % (zmq_port))

        chain_id = 'test.' if chain == 'testnet' else 'regtest.' if chain == 'regtest' else ''
        fp.write(chain_id + 'wallet=pool_stake\n')
        fp.write(chain_id + 'wallet=pool_reward\n')

        fp.write('csindex=1\n')
        fp.write('addressindex=1\n')

    startDaemon(dataDir, CAPRICOINPLUS_BINDIR)

    # Delay until responding
    for k in range(10):
        try:
            callrpc_cli(CAPRICOINPLUS_BINDIR, dataDir, chain, 'getblockchaininfo')
            break
        except Exception:
            time.sleep(0.5)

    try:
        if mode == 'observer':
            print('Preparing observer config.')

            settings = json.loads(urllib.request.urlopen(configurl).read().decode('utf-8'))

            settings['mode'] = 'observer'
            settings['capricoinplusbindir'] = CAPRICOINPLUS_BINDIR
            settings['capricoinplusdatadir'] = dataDir
            pool_stake_address = settings['pooladdress']
            pool_reward_address = settings['rewardaddress']

            v = callrpc_cli(CAPRICOINPLUS_BINDIR, dataDir, chain, 'validateaddress "%s"' % (pool_stake_address))
            assert('isvalid' in v)
            assert(v['isvalid'] is True)

            callrpc_cli(CAPRICOINPLUS_BINDIR, dataDir, chain, '-rpcwallet=pool_stake importaddress "%s"' % (v['address']))
            callrpc_cli(CAPRICOINPLUS_BINDIR, dataDir, chain, '-rpcwallet=pool_reward importaddress "%s"' % (pool_reward_address))

            poolConfFile = os.path.join(poolDir, 'stakepool.json')
            if os.path.exists(poolConfFile):
                sys.stderr.write('Error: %s exists, exiting.' % (poolConfFile))
                exit(1)
            with open(poolConfFile, 'w') as fp:
                json.dump(settings, fp, indent=4)

            print('Done.')
            return 0

        # 3. Generate and import a recovery phrase for both wallets.
        if stake_wallet_mnemonic is None:
            stake_wallet_mnemonic = callrpc_cli(CAPRICOINPLUS_BINDIR, dataDir, chain, 'mnemonic new')['mnemonic']

        if reward_wallet_mnemonic is None:
            reward_wallet_mnemonic = callrpc_cli(CAPRICOINPLUS_BINDIR, dataDir, chain, 'mnemonic new')['mnemonic']

        callrpc_cli(CAPRICOINPLUS_BINDIR, dataDir, chain, '-rpcwallet=pool_stake extkeyimportmaster "%s"' % (stake_wallet_mnemonic))
        callrpc_cli(CAPRICOINPLUS_BINDIR, dataDir, chain, '-rpcwallet=pool_reward extkeyimportmaster "%s"' % (reward_wallet_mnemonic))

        # 4. Generate the pool_stake_address from the staking wallet.
        pool_stake_address = callrpc_cli(CAPRICOINPLUS_BINDIR, dataDir, chain, '-rpcwallet=pool_stake getnewaddress')
        pool_stake_address = callrpc_cli(CAPRICOINPLUS_BINDIR, dataDir, chain, '-rpcwallet=pool_stake validateaddress %s true' % (pool_stake_address))['stakeonly_address']

        # 5. Generate the pool_reward_address from the reward wallet.
        pool_reward_address = callrpc_cli(CAPRICOINPLUS_BINDIR, dataDir, chain, '-rpcwallet=pool_reward getnewaddress')

        # 6. Disable staking on the reward wallet.
        callrpc_cli(CAPRICOINPLUS_BINDIR, dataDir, chain, '-rpcwallet=pool_reward walletsettings stakingoptions "{\\"enabled\\":\\"false\\"}"')

        # 7. Set the reward address of the staking wallet.
        callrpc_cli(CAPRICOINPLUS_BINDIR, dataDir, chain, '-rpcwallet=pool_stake walletsettings stakingoptions "{\\"rewardaddress\\":\\"%s\\"}"' % (pool_reward_address))

    finally:
        callrpc_cli(CAPRICOINPLUS_BINDIR, dataDir, chain, 'stop')

    # 8. Create the stakepool.json configuration file.
    html_port = 9000 if chain == 'mainnet' else 9001
    poolsettings = {
        'mode': 'master',
        'debug': True,
        'capricoinplusbindir': CAPRICOINPLUS_BINDIR,
        'capricoinplusdatadir': dataDir,
        'startheight': 200000,  # Set to a block height before the pool begins operating
        'pooladdress': pool_stake_address,
        'rewardaddress': pool_reward_address,
        'zmqhost': 'tcp://127.0.0.1',
        'zmqport': zmq_port,
        'htmlhost': 'localhost',
        'htmlport': html_port,
        'parameters': [
            {
                'height': 0,
                'poolfeepercent': 3,
                'stakebonuspercent': 5,
                'payoutthreshold': 0.5,
                'minblocksbetweenpayments': 100,
                'minoutputvalue': 0.1,
            },
        ]
    }

    poolConfFile = os.path.join(poolDir, 'stakepool.json')
    if os.path.exists(poolConfFile):
        sys.stderr.write('Error: %s exists, exiting.' % (poolConfFile))
        exit(1)
    with open(poolConfFile, 'w') as fp:
        json.dump(poolsettings, fp, indent=4)

    print('NOTE: Save both the recovery phrases:')
    print('Stake wallet recovery phrase:', stake_wallet_mnemonic)
    print('Reward wallet recovery phrase:', reward_wallet_mnemonic)
    print('Stake address:', pool_stake_address)
    print('Reward address:', pool_reward_address)

    print('Done.')


if __name__ == '__main__':
    main()
