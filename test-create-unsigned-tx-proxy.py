import requests
import threading, pprint, sys, os
data_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(data_dir, 'lib'))
import bitcoin as btc

address1, sk1 = 'n1aUo5P6mij5fJSGaefmdCTgjM7xxWhbVs', 'L5cFx7NvWSWidwNtKnBQw5VrguTax2dGYajuz12S81UhX2ewRehH'
authUtxo = 'cb2caca7500d2d943b4cd03db20ee67fcabc6afa9548e930e81632d164f6bfa1:0'

auth_pkey = '76ab32de1b1dad851316cd51c7d9f1797b7159ac3ff24319f899c230ac452436'

address2, sk2 = 'mzGNyEEJNYtRi7fGnMAKTV5EZDFN8J9jTX', 'L2xY5nTN3tjEXsmcns8CRc2RiLQqWhBNF9BiRiMRsCKC8U3exN9J'
utxos = [authUtxo]

naclKeySig = btc.ecdsa_sign(auth_pkey, btc.b58check_to_bin(sk1)).encode('hex')

data = {'testnet': True,
        'authUtxo': authUtxo,
        'naclKeySig': naclKeySig,
        'makerCount': 1,
        'utxos': utxos,
        'change': 'mtrxCNUMYXRy2hQh2bBPeLjtRHWFKZcRkU',
        'recipient': 'mzGNyEEJNYtRi7fGnMAKTV5EZDFN8J9jTX',
        'amount': 102419}
print(data)

r = requests.post('http://127.0.0.1:5000/joinmarket/v1/getUnsignedTransaction', json=data)
