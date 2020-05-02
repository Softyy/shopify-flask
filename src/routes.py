import os
import uuid
import shopify

from flask import render_template, request, redirect, abort, jsonify

from .server import app

SHOPIFY_API_VERSION = os.getenv('SHOPIFY_API_VERSION', '2020-01')

# setup up the shopify python api, it'll keep our key and secret
shopify.Session.setup(
    api_key=os.getenv('SHOPIFY_API_KEY'),
    secret=os.getenv('SHOPIFY_API_SECRET')
)


@app.route("/")
def template_test():
    return "testing"

# admin panel view
@app.route("/shopify")
def request_access():
    hmac = request.args.get('hmac')
    validRequest = shopify.Session.validate_params(request.args)
    if not validRequest:
        return abort(401, "hmac isn't valid or this is a replay attack")

    shop = request.args.get('shop')
    locale = request.args.get('locale')
    session = request.args.get('session')
    timestamp = request.args.get('timestamp')

    allowed_shops = []
    with open('.allowed_shops', 'r+') as f:
        for shop_info in f:
            allowed_shops.append({key: value for key, value in [
                                 info.split('=') for info in shop_info.split(',')]})

    for allowed_shop in allowed_shops:
        if shop == allowed_shop['shop']:
            with shopify.Session.temp(shop, SHOPIFY_API_VERSION, allowed_shop['token']):
                # temporarily sets ShopifyResource
                shop = shopify.Shop.current()
                product = shopify.Product.find()
                print(shop, product)
            return render_template('template.html', shop=shop, locale=locale, session=session, timestamp=timestamp, hmac=hmac)

    # shop isn't known, we need to ask them for permission...

    # here we specify the shop name, shopify API version, but no token since we don't have one
    session = shopify.Session(shop, SHOPIFY_API_VERSION, None)

    # we define the scope of what our shopify app needs to use here
    # https://shopify.dev/docs/admin-api/access-scopes
    scope = ["write_products", "read_products"]

    # create a UUID for safety, on shopify routing the customer back to us after the approval form
    state = uuid.uuid4()

    # give shopify the scopes we need, where to send the customer after approval, and a state check
    permission_url = session.create_permission_url(
        scope,
        redirect_uri=os.getenv('SHOPIFY_REDIRECT_URL'),
        state=state
    )

    # leave a record of the request on our side to valid the approval (via the state)
    with open('.requested_shops', 'a+') as f:
        f.write(f'shop={shop},state={state},timestamp={timestamp}\n')

    return redirect(permission_url, code=303)


@app.route("/shopify/auth/callback")
def template_test2():
    hmac = request.args.get('hmac')
    validRequest = shopify.Session.validate_params(request.args)
    if not validRequest:
        return abort(401, "hmac isn't valid or this is a replay attack")

    code = request.args.get('code')
    shop = request.args.get('shop')
    state = request.args.get('state')
    timestamp = request.args.get('timestamp')

    request_shops = []
    shop_auth_valid = False
    with open('.requested_shops', 'r') as f:
        for shop_info in f:
            info = {key: value for key, value in [
                info.split('=') for info in shop_info.split(',')]}
            if info['shop'] == shop and info['state'] == state:
                shop_auth_valid = True
            else:
                request_shops.append(info)

    if not shop_auth_valid:
        return abort(401, "You don`t seem to be in our request records? Try installing the app again. Sorry for any inconvenience.")

    session = shopify.Session(shop, SHOPIFY_API_VERSION, None)

    # permanent access token, be sure to keep this safe
    token = session.request_token(request.args)

    # remove requested shop from requests.
    with open('.requested_shops', 'w') as f:
        for info in request_shops:
            f.write(
                f'shop={info["shop"]},state={info["state"]},timestamp={info["timestamp"]}\n'
            )

    with open('.allowed_shops', 'a+') as f:
        f.write(f'shop={shop},token={token},timestamp={timestamp}\n')

    return "Thank you for installing, we can do whatever with the page", 200


@app.route('/shopify/customers/redact', methods=['POST'])
def delete_customer_data():
    # TODO
    # payload = {
    #     "shop_id": 954889,
    #     "shop_domain": "snowdevil.myshopify.com",
    #     "customer": {
    #         "id": 191167,
    #         "email": "john@email.com",
    #         "phone": "555-625-1199"
    #     },
    #     "orders_to_redact": [299938, 280263, 220458]
    # }
    return 200


@app.route('/shopify/shop/redact', methods=['POST'])
def delete_shop_data():
    # TODO
    # payload = {
    #     "shop_id": 954889,
    #     "shop_domain": "snowdevil.myshopify.com"
    # }
    return 200


@app.route('/shopify/customers/data_request', methods=['POST'])
def get_customer_data():
    # TODO
    # {
    #     "shop_id": 954889,
    #     "shop_domain": "snowdevil.myshopify.com",
    #     "customer": {
    #         "id": 191167,
    #         "email": "john@email.com",
    #         "phone":  "555-625-1199"
    #     },
    #     "orders_requested": [299938, 280263, 220458]
    # }
    return 200
