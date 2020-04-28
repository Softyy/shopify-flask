import os
import uuid
import shopify

from flask import render_template, request, redirect, abort

from .server import app

# setup a new shopify session since that's what their python tool wants....?
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
    shop = request.args.get('shop')
    locale = request.args.get('locale')
    session = request.args.get('session')
    timestamp = request.args.get('timestamp')

    allowed_shops = []
    with open('.allowed_shops', 'r+') as f:
        for shop_info in f:
            allowed_shops.append({key: value for key, value in [
                                 info.split('=') for info in shop_info.split(',')]})

    if shop in [shop_info['shop'] for shop_info in allowed_shops]:
        # session valid TODO
        return render_template('template.html', shop=shop, locale=locale, session=session, timestamp=timestamp, hmac=hmac)
    # shop isn't known, we need to ask them for permission...

    # here we specify the shop name, shopify API version, and the token that shopify sent us
    session = shopify.Session(shop, '2020-01', hmac)

    # we define the scope of what our shopify app needs to use here
    scope = ["write_products"]

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

    # remove requested shop from requests.
    with open('.requested_shops', 'w') as f:
        for info in request_shops:
            f.write(
                f'shop={info["shop"]},state={info["state"]},timestamp={info["timestamp"]}\n'
            )

    with open('.allowed_shops', 'a+') as f:
        f.write(f'shop={shop},code={code},timestamp={timestamp}\n')

    return "Thank you for installing, we can do whatever with the page"
