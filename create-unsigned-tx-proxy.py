""" create-unsigned-tx-proxy is desigend to do the joinmarket heavy-lifting on
    behalf of a client. The client allows this proxy to do so by signing a nacl
    key pair with one of the used UTXO's addresses private keys.
    The client can create its own nacl key pair and share the private key with
    the proxy or for convenience call get_auth_key()
"""

from flask import Flask, abort, jsonify, make_response, request
from optparse import OptionParser
import threading, pprint, sys, os
data_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(data_dir, 'lib'))

from common import *
import common
import taker as takermodule
from irc import IRCMessageChannel, random_nick
import bitcoin as btc
import sendpayment
import libnacl.public
import enc_wrapper
app = Flask(__name__)

@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad Request'}), 400)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.route('/joinmarket/v1/ping')
def ping():
    return jsonify({'ping': 'pong'})

kp = enc_wrapper.init_keypair()
@app.route('/joinmarket/v1/getAuthKey', methods = ['GET'])
def get_auth_key():
    """returns a libnacl public key for the client to sign in order to approve
       this proxy.
    """
    # TODO: with one more node there is one more edge for a MITM to attack. We could/should? use pk for encryption with the client, too, at least optionally.
    return jsonify({'pk': kp.pk.encode('hex')})

@app.route('/joinmarket/v1/getUnsignedTransaction', methods = ['POST'])
def get_unsigned_transaction():
    print(request.json)
    if (not request.json or
        not 'authUtxo' in request.json or
        not 'naclKeySig' in request.json or
        not 'utxos' in request.json or
        not 'change' in request.json or
        not 'recipient' in request.json or
        not 'amount' in request.json):
        abort(400)
    auth_utxo = request.json['authUtxo']
    naclKeySig = request.json['naclKeySig']
    if not btc.ecdsa_verify(kp.pk.encode('hex'), naclKeySig, binascii.unhexlify(cj_pub)):
        pass
    makerCount = request.json['makerCount']
    cold_utxos = request.json['utxos']
    changeaddr = request.json['change']
    destaddr = request.json['recipient']
    cjamount = request.json['amount']
    options = type('Options', (object,), {
        'testnet': request.json['testnet'],
        'txfee': 10000,         # total miner fee in satoshis
        'waittime': 5,          # wait time in seconds to allow orders to arrive
        'makercount': 1,        # how many makers to coinjoin with
        'choosecheapest': True, # override weightened offers picking and choose cheapest
        'pickorders': False,    # manually pick which orders to take
        'answeryes': True       # answer yes to everything
    })
    kp = libnacl.public.SecretKey(naclKey)
    tx = main(auth_utxo, naclKeySig, cjamount, destaddr, changeaddr, cold_utxos, options, kp)
    return jsonify({'result': tx})

#thread which does the buy-side algorithm
# chooses which coinjoins to initiate and when
class PaymentThread(threading.Thread):
    def __init__(self, taker):
        threading.Thread.__init__(self)
        self.daemon = True
        self.taker = taker
        self.ignored_makers = []

    def create_tx(self):
        crow = self.taker.db.execute('SELECT COUNT(DISTINCT counterparty) FROM orderbook;').fetchone()
        counterparty_count = crow['COUNT(DISTINCT counterparty)']
        counterparty_count -= len(self.ignored_makers)
        if counterparty_count < self.taker.options.makercount:
            print 'not enough counterparties to fill order, ending'
            self.taker.msgchan.shutdown()
            return

        utxos = self.taker.utxo_data
        orders = None
        cjamount = 0
        change_addr = None
        choose_orders_recover = None
        if self.taker.cjamount == 0:
            total_value = sum([va['value'] for va in utxos.values()])
            orders, cjamount = choose_sweep_orders(self.taker.db, total_value,
                self.taker.options.txfee, self.taker.options.makercount,
                self.taker.chooseOrdersFunc, self.ignored_makers)
            if not self.taker.options.answeryes:
                total_cj_fee = total_value - cjamount - self.taker.options.txfee
                debug('total cj fee = ' + str(total_cj_fee))
                total_fee_pc = 1.0*total_cj_fee / cjamount
                debug('total coinjoin fee = ' + str(float('%.3g' % (100.0 * total_fee_pc))) + '%')
                sendpayment.check_high_fee(total_fee_pc)
                if raw_input('send with these orders? (y/n):')[0] != 'y':
                    self.finishcallback(None)
                    return
        else:
            orders, total_cj_fee = self.sendpayment_choose_orders(
                self.taker.cjamount, self.taker.options.makercount)
            if not orders:
                debug('ERROR not enough liquidity in the orderbook, exiting')
                return
            total_amount = self.taker.cjamount + total_cj_fee + self.taker.options.txfee
            print 'total amount spent = ' + str(total_amount)
            cjamount = self.taker.cjamount
            change_addr = self.taker.changeaddr
            choose_orders_recover = self.sendpayment_choose_orders

        auth_addr = self.taker.utxo_data[self.taker.auth_utxo]['address']
        kp = self.taker.kp
        my_btc_sig = self.taker.naclKeySig
        self.taker.start_cj(self.taker.wallet, cjamount, orders, utxos,
            self.taker.destaddr, change_addr, self.taker.options.txfee,
            self.finishcallback, choose_orders_recover, auth_addr, kp, my_btc_sig)

    def finishcallback(self, coinjointx):
        if coinjointx.all_responded:
            #now sign it ourselves
            tx = btc.serialize(coinjointx.latest_tx)
            # for index, ins in enumerate(coinjointx.latest_tx['ins']):
            #     utxo = ins['outpoint']['hash'] + ':' + str(ins['outpoint']['index'])
            #     if utxo != self.taker.auth_utxo:
            #         continue
            #     addr = coinjointx.input_utxos[utxo]['address']
            #     tx = btc.sign(tx, index, coinjointx.wallet.get_key_from_addr(addr))
            print 'unsigned tx = \n\n' + tx + '\n'
            debug('created unsigned tx, ending')
            self.taker.msgchan.shutdown()
            self.taker.tx = tx
        self.ignored_makers += coinjointx.nonrespondants
        debug('recreating the tx, ignored_makers=' + str(self.ignored_makers))
        self.create_tx()

    def sendpayment_choose_orders(self, cj_amount, makercount, nonrespondants=[], active_nicks=[]):
        self.ignored_makers += nonrespondants
        orders, total_cj_fee = choose_orders(self.taker.db, cj_amount, makercount,
            self.taker.chooseOrdersFunc, self.ignored_makers + active_nicks)
        if not orders:
            return None, 0
        print 'chosen orders to fill ' + str(orders) + ' totalcjfee=' + str(total_cj_fee)
        if not self.taker.options.answeryes:
            if len(self.ignored_makers) > 0:
                noun = 'total'
            else:
                noun = 'additional'
            total_fee_pc = 1.0*total_cj_fee / cj_amount
            debug(noun + ' coinjoin fee = ' + str(float('%.3g' % (100.0 * total_fee_pc))) + '%')
            sendpayment.check_high_fee(total_fee_pc)
            if raw_input('send with these orders? (y/n):')[0] != 'y':
                debug('ending')
                self.taker.msgchan.shutdown()
                return None, -1
        return orders, total_cj_fee

    def run(self):
        print 'waiting for all orders to certainly arrive'
        debug_dump_object(self.taker)
        time.sleep(self.taker.options.waittime)
        self.create_tx()

class CreateUnsignedTx(takermodule.Taker):
    def __init__(self, msgchan, auth_utxo, naclKeySig, cjamount, destaddr, changeaddr,
            utxo_data, options, chooseOrdersFunc, kp):
        super(CreateUnsignedTx, self).__init__(msgchan)
        self.auth_utxo = auth_utxo
        self.naclKeySig = naclKeySig
        self.cjamount = cjamount
        self.destaddr = destaddr
        self.changeaddr = changeaddr
        self.utxo_data = utxo_data
        self.options = options
        self.chooseOrdersFunc = chooseOrdersFunc
        self.kp = kp
        self.tx = None

    def on_welcome(self):
        takermodule.Taker.on_welcome(self)
        PaymentThread(self).start()

def main(auth_utxo, naclKeySig, cjamount, destaddr, changeaddr, cold_utxos, options, kp):
    common.load_program_config()
    addr_valid1, errormsg1 = validate_address(destaddr)
    #if amount = 0 dont bother checking changeaddr so user can write any junk
    if cjamount != 0:
        addr_valid2, errormsg2 = validate_address(changeaddr)
    else:
        addr_valid2 = True
    if not addr_valid1 or not addr_valid2:
        if not addr_valid1:
            print 'ERROR: Address invalid. ' + errormsg1
        else:
            print 'ERROR: Address invalid. ' + errormsg2
        return

    all_utxos = [auth_utxo] + cold_utxos
    query_result = common.bc_interface.query_utxo_set(all_utxos)
    if None in query_result:
        print query_result
    utxo_data = {}
    for utxo, data in zip(all_utxos, query_result):
        utxo_data[utxo] = {'address': data['address'], 'value': data['value']}

    chooseOrdersFunc = cheapest_order_choose
    
    common.nickname = random_nick()
    debug('starting sendpayment')

    irc = IRCMessageChannel(common.nickname)
    taker = CreateUnsignedTx(irc, auth_utxo, naclKeySig, cjamount, destaddr,
        changeaddr, utxo_data, options, chooseOrdersFunc, kp)
    try:
        debug('starting irc')
        irc.run()
        debug('done irc')
        return taker.tx
    except:
        debug('CRASHING, DUMPING EVERYTHING')
        debug_dump_object(taker)
        import traceback
        debug(traceback.format_exc())

if __name__ == "__main__":
    #main()
    app.run(debug=True)
    print('done')
