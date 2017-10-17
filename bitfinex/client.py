# python client.py

import json
import hmac
import time
import base64
import hashlib
import requests
from datetime import datetime, timedelta

one_week_ago = datetime.today() - timedelta(days=7)

class BitfinexError(Exception):
	pass

class Base(object):
	# A base class for the API Client methods that handles interaction with the requests library.
	api_url = 'https://api.bitfinex.com/'
	exception_on_error = True

	def __init__(self, proxydict=None, *args, **kwargs):
		self.proxydict = proxydict

	def _get(self, *args, **kwargs):
		# Make a GET request.
		return self._request(requests.get, *args, **kwargs)

	def _post(self, *args, **kwargs):
		# Make a POST request.
		data = self._default_data()
		data.update(kwargs.get('data') or {})
		kwargs['data'] = data
		return self._request(requests.post, *args, **kwargs)

	def _default_data(self):
		# Default data for a POST request.
		return {}

	def _request(self, func, url, *args, **kwargs):
		# Make a generic request, adding in any proxy defined by the instance.
		# Raises a 'requests.HTTPError if the response status isn't 200,
		# Raises a 'BitfinexError' if the response contains a json encoded error message.

		return_json = kwargs.pop('return_json', False)
		url = self.api_url + url
		response = func(url, *args, **kwargs)

		if 'proxies' not in kwargs:
			kwargs['proxies'] = self.proxydict

		# Check for error, raising an exception if appropriate.
		response.raise_for_status()

		try:
			json_response = response.json()
		except ValueError:
			json_response = None
		if isinstance(json_response, dict):
			error = json_response.get('error')
			if error:
				raise BitfinexError(error)

		if return_json:
			if json_response is None:
				raise BitfinexError(
					"Could not decode json for: " + response.text)
			return json_response

		return response

class Public(Base):

	def ticker(self, symbol="btcusd"):
		# The ticker is a high level overview of the state of the market.

		url = "v1/pubticker/" + symbol
		return self._get(url, return_json=True)

	def last_trade(self, symbol="btcusd"):
		# Shortcut for last trade

		return float(self.ticker(symbol)['last_price'])

	def stats(self, symbol="btcusd"):
		# Various statistics about the requested pair.

		url = "v1/stats/" + symbol
		return self._get(url, return_json=True)

	def funding_book(self, currency="USD"):
		# Get the full margin funding book
		url = "v1/lendbook/" + currency
		return self._get(url, return_json=True)

	def order_book(self, symbol="btcusd"):
		# Get the full order book.

		url = "v1/book/" + symbol
		return self._get(url, return_json=True)

	def trades(self, symbol="btcusd"):
		# Get a list of the most recent trades for the given symbol.

		url = "v1/trades/" + symbol
		return self._get(url, return_json=True)

	def lends(self, currency="USD"):
		# Get a list of the most recent funding data for the given currency: total amount provided and Flash Return Rate (in % by 365 days) over time.

		url = "v1/lends/" + currency
		return self._get(url, return_json=True)

	def symbols(self):
		# A list of symbol names.
		return self._get("/v1/symbols", return_json=True)

	def symbols_details(self):
		# Get a list of valid symbol IDs and the pair details.
		return self._get("/v1/symbols_details", return_json=True)

class Private(Public):

	def __init__(self, key, secret, *args, **kwargs):
		# Stores the username, key, and secret which is used when making POST requests to Bitfinex.
		super(Private, self).__init__(
				key=key, secret=secret, *args, **kwargs)
		self.key = key
		self.secret = secret

	def _get_nonce(self):
		# Get a unique nonce for the bitfinex API.
		# This isn't a thread-safe function.

		nonce = getattr(self, '_nonce', 0)
		if nonce:
			nonce += 1

		self._nonce = max(int(time.time()), nonce)
		return self._nonce

	def _default_data(self, *args, **kwargs):
		# Generate a one-time signature and other data required to send a secure POST request to the Bitfinex API.
		data = {}
		nonce = self._get_nonce()
		data['nonce'] = str(nonce)
		data['request'] = args[0]
		return data

	def _post(self, *args, **kwargs):
		# Make a POST request.
		data = kwargs.pop('data', {})
		data.update(self._default_data(*args, **kwargs))

		key = self.key
		secret = self.secret
		payload_json = json.dumps(data)
		payload = base64.b64encode(payload_json)
		sig = hmac.new(secret, payload, hashlib.sha384)
		sig = sig.hexdigest()

		headers = {
			'X-BFX-APIKEY' : key,
			'X-BFX-PAYLOAD' : payload,
			'X-BFX-SIGNATURE' : sig
		}
		kwargs['headers'] = headers

		return self._request(requests.post, *args, **kwargs)

	def account_infos(self):
		# Return information about your account
		return self._post("/v1/account_infos", return_json=True)

	def account_fees(self):
		# See the fees applied to your withdrawals
		return self._post("/v1/account_fees", return_json=True)

	def summary(self):
		# Returns a 30-day summary of your trading volume and return on margin funding
		return self._post("/v1/summary", return_json=True)

	def deposit(self, method, wallet_name, renew=0):
		data = {'method': method,
				'wallet_name': wallet_name,
				'renew': renew
				}

		return self._post("/v1/deposit/new", data=data, return_json=True)

	def key_info(self):
		# Check the permissions of the key being used to generate this request.

		return self._post("/v1/key_info",return_json=True)

	def margin_infos(self):
		# See your trading wallet information for margin trading.

		return self._post("/v1/margin_infos",return_json=True)

	def balances(self):
		# See your balances

		return self._post("/v1/balances",return_json=True)

	def transfer(self, amount, currency, wallet_from, wallet_to):
		# Allow you to move available balances between your wallets.
		data = {'amount': amount,
				'currency': currency,
				'walletfrom': wallet_from,
				'walletto': wallet_to
				}

		return self._post("/v1/transfer", data=data, return_json=True)

	def withdraw(self, withdraw_type, wallet_selected, amount, address, payment_id="", account_name="", account_number, swift_code="", bank_name, bank_address, bank_city, bank_country, detail_payment="", express_wire=0, intermediary_bank_name="", intermediary_bank_address="", intermediary_bank_city="", intermediary_bank_country="", intermediary_bank_account="", intermediary_bank_swift=""):
		# Allow you to request a withdrawal from one of your wallet.

		data = {'withdraw_type': withdraw_type,
				'walletselected': wallet_selected,
				'amount': amount,
				'address': address,
				'payment_id': payment_id,
				'account_name': account_name,
				'account_number': account_number,
				'swift': swift_code,
				'bank_name': bank_name,
				'bank_address': bank_address,
				'bank_city': bank_city,
				'bank_country': bank_country,
				'detail_payment': detail_payment,
				'expressWire': express_wire,
				'intermediary_bank_name': intermediary_bank_name,
				'intermediary_bank_address': intermediary_bank_address,
				'intermediary_bank_city': intermediary_bank_city,
				'intermediary_bank_country': intermediary_bank_country,
				'intermediary_bank_account': intermediary_bank_account,
				'intermediary_bank_swift': intermediary_bank_swift
				}

		return self._post("/v1/withdraw", data=data, return_json=True)

	####### Orders #######

	def new_order(self, symbol, amount, price, side, order_type):
		# Submit a new Order

		data = {'symbol': symbol,
				'amount': amount,
				'price': price,
				'exchange': 'bitfinex',
				'side': side,
				'type': order_type
				}
		return self._post("/v1/order/new", data=data, return_json=True)

	def multiple_orders(self):
		# Submit several new orders at once.
		return

	def cancel_order(self, order_id):
		# Cancel an order.

		data = {'order_id': order_id}
		return self._post("/v1/order/cancel",data, return_json=True)

	def cancel_multiple_orders(self, order_ids):
		# Cancel multiples orders at once.

		data = {'order_ids': order_ids}
		req = self._post("/v1/order/cancel/multi",data, return_json=True)
		if req.content == "Orders cancelled":
			return True
		else:
			return False

	def cancel_all_orders(self):
		# Cancel all active orders at once.

		req = self._post('/v1/order/cancel/all', return_json=False)
		if req.content == "All orders cancelled":
			return True
		else:
			return False

	def replace_order(self, order_id, symbol, amount, price, side, order_type):
		# Replace an order with a new one.
		data = {'order_id': order_id,
				'symbol': symbol,
				'amount': amount,
				'price': price,
				'exchange': 'bitfinex',
				'side': side,
				'type': order_type
				}
		return self._post('/v1/order/cancel/replace', return_json=False)

	def order_status(self, order_id):
		# Get the status of an order.

		data = {'order_id': order_id}
		return self._post('/v1/order/status', return_json=True)

	def active_orders(self):
		# Returns an array of the results of `/order/status` for all your live orders.
		return self._post("/v1/orders", return_json=True)

	def order_history(self, limit=10):
		# View your latest inactive orders
		# Limited to last 3 days and 1 request per minute.
		data = {'limit': limit}
		return self._post("/v1/orders/hist", return_json=True)

	####### Positions #######

	def active_positions(self):
		# View your active positions.
		return self._post("/v1/positions", return_json=True)

	def claim_position(self, position_id, amount):
		'''
		A position can be claimed if:

		It is a long position: The amount in the last unit of the position pair that you have in your trading wallet AND/OR the realized profit of the position is greater or equal to the purchase amount of the position (base price position amount) and the funds which need to be returned. For example, for a long BTCUSD position, you can claim the position if the amount of USD you have in the trading wallet is greater than the base price the position amount and the funds used.

		It is a short position: The amount in the first unit of the position pair that you have in your trading wallet is greater or equal to the amount of the position and the margin funding used.
		'''
		data = {'position_id': position_id,
				'amount': amount
				}
		return self._post("/v1/position/claim", return_json=True)

	####### Historical Data #######

	def balance_history(self, currency, since=one_week_ago, until=datetime.today(), limit=100, wallet):
		# View all of your balance ledger entries.
		data = {'currency': currency,
				'since': since,
				'until': until,
				'limit': limit,
				'wallet': wallet
				}
		return self._post("/v1/history", return_json=True)

	def deposit_withdrawl_history(self, currency, method="bitcoin",since=one_week_ago, until=datetime.today(), limit=100):
		# View your past deposits/withdrawals.
		data = {'currency': currency,
				'method': method,
				'since': since,
				'until': until,
				'limit': limit
				}
		return self._post("/v1/history/movements", return_json=True)

	def past_trades(self, symbol="BTCUSD", timestamp=one_week_ago, until=datetime.today(), limit_trades=50, reverse=0):
		data = {'symbol': symbol,
				'timestamp': timestamp,
				'until': until,
				'limit_trades': limit_trades,
				'reverse': reverse
				}
		return self._post("/v1/mytrades", return_json=True)

	####### Margin Funding #######

	def new_offer(self):
		# Submit a new Offer
		return

	def cancel_offer(self):
		return

	def offer_status(self):
		return

	def active_credits(self):
		return

	def offers(self):
		return

	def offers_history(self):
		return

	def past_funding_trades(self):
		return

	def taken_funds(self):
		# Active Funding Used in a margin position
		return

	def unused_taken_funds(self):
		# Active Funding Not Used in a margin position
		# View your funding currently borrowed and not used (available for a new margin position).
		return

	def total_taken_funds(self):
		# View the total of your active funding used in your position(s).
		return

	def close_margin_funding(self):
		return

	def basket_manage(self):
		return
