import sys, os
data_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(data_dir, 'lib'))
import bitcoin as btc
import binascii

btc_sk = btc.b58check_to_bin('L5cFx7NvWSWidwNtKnBQw5VrguTax2dGYajuz12S81UhX2ewRehH')
data = 'hello world' # something to sign
btc_sig = btc.ecdsa_sign(data, btc_sk)

# send stuff to server, without sending the btc_pk

# TODO: figure out btc_pk from only the btc_sig
btc_pk = btc.privkey_to_pubkey(btc_sk)

print('the sk is {0}', btc_sk)
print('the pk is {0}', btc_pk)
print('the data is {0}', data)


if not btc.ecdsa_verify(
        data,
        btc_sig,
        btc_pk):
    print('failed')
else:
    print('success')
