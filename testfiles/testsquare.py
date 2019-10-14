from square.client import Client

# Create an instance of the API Client
# and initialize it with the credentials
# for the Square account whose assets you want to manage

client = Client(
    access_token='EAAAEHzQywVWiysH2dLJ_MBAvkTDvkN3f5iWojFnQgnLUT-KZb-mhx6BMezxz_dA',
    environment='production',
)
api_locations = client.locations
mobile_authorization_api = client.mobile_authorization
# Call list_locations method to get all locations in this Square account
result = api_locations.list_locations()
# Call the success method to see if the call succeeded
if result.is_success():
	# The body property is a list of locations
    locations = result.body['locations']
	# Iterate over the list
    for location in locations:
        if((dict(location.items())["status"]) == "ACTIVE"):
            print(dict(location.items()))
            locationName = (dict(location.items())["name"]).replace(" ","-")
            print(locationName)
            locationId = dict(location.items())["id"]
            print(dict(location.items())["business_email"])
            print(dict(location.items()))
            print(locationId)
            addrNumber = ""
            street = ""
            for ltrAddr in range(len(dict(location.items())["address"]['address_line_1'])):
                currentLtr = dict(location.items())["address"]['address_line_1'][ltrAddr]
                try:
                    int(currentLtr)
                    addrNumber += currentLtr
                except Exception as e:
                    street = dict(location.items())["address"]['address_line_1'][ltrAddr+1:len(dict(location.items())["address"]['address_line_1'])]
                    break

            addrP = str(addrNumber+ ","+ street+","+dict(location.items())["address"]['locality'] + "," + dict(location.items())["address"]['administrative_district_level_1'] + "," + dict(location.items())["address"]['postal_code'][:5])
            timez = dict(location.items())["timezone"]




            body = {}
            body['location_id'] = locationId

            result = mobile_authorization_api.create_mobile_authorization_code(body)

            if result.is_success():
                print(result.body)
            elif result.is_error():
                print(result.errors)


            checkout_api = client.checkout
            location_id = 'B266MPEW4JSYZ'
            body = {}
            body['idempotency_key'] = '86ae1696-b1e3-4328-ade2sijiyg734f6dhdnq-fqffygyqefqe'
            body['order'] = {}
            body['order']['reference_id'] = 'reference_id'
            body['order']['line_items'] = []

            body['order']['line_items'].append({})
            body['order']['line_items'][0]['name'] = 'Your Order From '
            body['order']['line_items'][0]['quantity'] = '1'
            body['order']['line_items'][0]['base_price_money'] = {}
            body['order']['line_items'][0]['base_price_money']['amount'] = 110
            body['order']['line_items'][0]['base_price_money']['currency'] = "USD"

            body['order']['line_items'].append({})
            body['order']['line_items'][1]['name'] = 'Service Fees'
            body['order']['line_items'][1]['quantity'] = '1'
            body['order']['line_items'][1]['base_price_money'] = {}
            body['order']['line_items'][1]['base_price_money']['amount'] = 50
            body['order']['line_items'][1]['base_price_money']['currency'] = "USD"

            body['order']['taxes'] = []
            body['order']['taxes'].append({})
            body['order']['taxes'][0]['name'] = 'Sales Tax'
            body['order']['taxes'][0]['percentage'] = '10'

            body['ask_for_shipping_address'] = False
            body['redirect_url'] = 'https://cdrorder.serveo.net/ipn'

            result = checkout_api.create_checkout(location_id, body)

            if result.is_success():
                print(result.body["checkout"]["checkout_page_url"])
                print(result.body["checkout"])
            elif result.is_error():
                print(result.errors)
