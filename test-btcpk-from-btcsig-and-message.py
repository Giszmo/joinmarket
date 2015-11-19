import sys, os, binascii
data_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(data_dir, 'lib'))
import bitcoin as btc

data = 'hello world' # something to sign
btc_sk = btc.b58check_to_bin('L5cFx7NvWSWidwNtKnBQw5VrguTax2dGYajuz12S81UhX2ewRehH')
btc_pk = btc.privkey_to_pubkey(btc_sk)
btc_sig = btc.ecdsa_sign(data, btc_sk)

print('the data is {0}'.format(data))
print('the sk is {0}'.format(btc_sk.encode('hex')))
print('the pk is {0}'.format(btc_pk.encode('hex')))
print('the sig is {0}'.format(btc_sig.encode('hex')))

if btc.ecdsa_verify(data, btc_sig, btc_pk):
    print('success')
else:
    print('failed')
