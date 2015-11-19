import requests
import threading, pprint, sys, os
data_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(data_dir, 'lib'))
import bitcoin as btc

address1  = 'n1aUo5P6mij5fJSGaefmdCTgjM7xxWhbVs'
sk1 = btc.b58check_to_bin('L5cFx7NvWSWidwNtKnBQw5VrguTax2dGYajuz12S81UhX2ewRehH')
pk1 = btc.privkey_to_pubkey(sk1)

authUtxo = 'cb2caca7500d2d943b4cd03db20ee67fcabc6afa9548e930e81632d164f6bfa1:0'

auth_pkey = '55e37940fcf11c5fef84b5c0c980180fe0520f6f9bec89a27a157b54710f200a'

utxos = [authUtxo]

naclKeySig = btc.ecdsa_sign(auth_pkey, sk1)

data = {'testnet': True,
        'authUtxo': authUtxo,
        'authUtxoPK': pk1.encode('hex'),
        'naclKeySig': naclKeySig.encode('hex'),
        'makerCount': 1,
        'utxos': utxos,
        'change': 'mtrxCNUMYXRy2hQh2bBPeLjtRHWFKZcRkU',
        'recipient': 'mzGNyEEJNYtRi7fGnMAKTV5EZDFN8J9jTX',
        'amount': 102419}
print(data)

authPK = pk1
sigGood = btc.ecdsa_verify(auth_pkey, naclKeySig, authPK)
print('sig is good: {0}'.format(sigGood))

r = requests.post('http://127.0.0.1:5000/joinmarket/v1/getUnsignedTransaction', json=data)
