import sys, os
data_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(data_dir, 'lib'))
import bitcoin as btc
import binascii

btc_sk = 'L5cFx7NvWSWidwNtKnBQw5VrguTax2dGYajuz12S81UhX2ewRehH'
data = 'hello world' # something to sign
btc_sig = btc.ecdsa_sign(data, btc.b58check_to_bin(btc_sk))

# send stuff to server, without sending the btc_pk

btc_pk = '0000' # TODO: figure out btc_pk from only the btc_sig

if not btc.ecdsa_verify(
        data,
        btc_sig):
    print('failed')
else:
    print('success')
