# client.py

import json
import hmac
import time
import base64
import hashlib
import requests

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
		# Raises a ''requests.HTTPError'' if the response status isn't 200,
		# Raises a :class:'BitfinexError' if the response contains a json encoded error message.

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

	def ticker(self):
		# The ticker is a high level overview of the state of the market.

		# url = "v1/pubticker/" + symbol
		return self._get("v1/pubticker/btcusd", return_json=True)

	def get_last(self):
		# Shortcut for last trade
		return float(self.ticker()['last_price'])

class Private(Public):

	def __init__(self, key, secret, *args, **kwargs):
		# Stores the username, key, and secret which is used when making POST requests to Bitfinex.
		super(Private, self).__init__(
				key=key, secret=secret, *args, **kwargs)
		self.key = key
		self.secret = secret

	def _get_nonce(self):
		# Get a unique nonce for the bitfinex API. This integer must always be increasing, so use the current unix time. Every time this variable is requested, it automatically increments to allow for more than one API request per second. This isn't a thread-safe function however, so you should only rely on a single thread if you have a high level of concurrent API requests in your application.
		nonce = getattr(self, '_nonce', 0)
		if nonce:
			nonce += 1
		# If the unix time is greater though, use that instead (helps low
		# concurrency multi-threaded apps always call with the largest nonce).
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
		# Returns dictionary::
		# [{"fees":[{"pairs":"BTC","maker_fees":"0.1","taker_fees":"0.2"},
		# {"pairs":"LTC","maker_fees":"0.0","taker_fees":"0.1"},
		# {"pairs":"DRK","maker_fees":"0.0","taker_fees":"0.1"}]}]
		return self._post("/v1/account_infos", return_json=True)

	def balances(self):
		# returns a list of balances

		return self._post("/v1/balances",return_json=True)

	def new_order(self, amount=0.01, price=1.11, side='buy', order_type='limit', symbol='btcusd'):
		# Enters a new order onto the orderbook

		data = {'symbol': str(symbol),
				'amount': str(amount),
				'price': str(price),
				'exchange': 'bitfinex',
				'side':str(side),
				'type':order_type
				}
		return self._post("/v1/order/new", data=data, return_json=True)

	def orders(self):
		# Returns an array of the results of `/order/status` for all your live orders.
		return self._post("/v1/orders", return_json=True)

	def cancel_order(self, order_id):
		# cancels order with order_id

		data = {'order_id': str(order_id)}
		return self._post("/v1/order/cancel",data, return_json=True)

	def cancel_all_orders(self):
		# cancels all orders

		req = self._post('/v1/order/cancel/all', return_json=False)
		if req.content == "All orders cancelled":
			return True
		else:
			return False

	def positions(self):
		# gets positions
		return self._post("/v1/positions", return_json=True)
