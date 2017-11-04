# Bitfinex API Client

A python client for Bitfinex API

## Goal

- Implement all API calls that Bitfinex make available.

## Usage

```
>>> import bitfinex.client

>>> public = bitfinex.client.Public()
>>> print(public.ticker()['last_trade'])
620.23

>>> private_client = bitfinex.client.Private(key='xxx', secret='xxx')
>>> print(private_client.new_order(amount=10.0, price=610.00))
<order_id>
```
## Contributing

1. Create an issue and discuss.
1. Fork it.
1. Create a feature branch containing only your fix or feature.
1. Features or fixes that don't have good tests won't be accepted.
1. Create a pull request.

## References

- [https://www.bitfinex.com/pages/api](https://www.bitfinex.com/pages/api)
- [https://github.com/streblo/bitfinex-python-client](https://github.com/streblo/bitfinex-python-client)
- [https://gist.github.com/jordanbaucke/5812039](https://gist.github.com/jordanbaucke/5812039)

## Licence

The MIT License (MIT)

See [LICENSE.md](LICENSE.md)
