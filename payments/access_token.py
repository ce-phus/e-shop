import logging
import time 
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
from my_app.settings import env
import environ
import base64
import math
from account.models import TransactionModel
from account.serializers import TransactionListSerializer
from phonenumber_field.phonenumber import PhoneNumber
from rest_framework.response import Response

env = environ.Env()
logging = logging.getLogger("default")

# The token received will expire after about 3599 seconds. So we’ll need to renew it every time it’s about to expire. We’ll write a decorator class that would allow us to do just that. Then we’ll just add the decorator to methods that need to use the access_token.

class MpesaGateway:
    shortcode =None
    consumer_key= None
    consumer_secret=None
    access_token_url=None
    access_token= None
    access_token_expiration= None

    def __init__(self):
        now= datetime.now()
        self.shortcode=env("shortcode")
        self.consumer_key=env("consumer_key")
        self.consumer_secret=env("consumer_secret")
        self.access_token_url=env("access_token_url")


        try:
            self.access_token=self.getAccessToken()
            if self.access_token is None:
                raise Exception("Request for access token failed")
            
        except Exception as e:
            logging.error("Error {}".format(e))

        else:
            self.access_token_expiration = time.time() + 3400

    def getAccessToken(self):
        try:
            res =  requests.get(
                self.access_token_url,
                auth=HTTPBasicAuth(self.consumer_key, self.consumer_secret),
            )
        except Exception as err:
            logging.error("Error {}".format(err))
            raise err
        else:
            token=res.json()["access_token"]
            self.headers = {"Authorization": "Bearer %s" % token}
            return token
        
    class  Decorators:
        @staticmethod
        def refreshToken(decorated):
            def wrapper(gateway, *args, **kwargs):
                if(
                    gateway.access_token_expiration
                    and time.time() > gateway.access_token_expiration
                ):
                    token = gateway.getAccessToken()
                    gateway.access_token = token
                return decorated(gateway, *args, **kwargs)
            
            return wrapper
        

# Now that we have the token, we can initiate the payment request. We'll call the mrthod stk_push_request.
# For that request, we'll need to generate a password and then make a post request 
        
    def generate_password(shortcode, passkey, timestamp):
        """Generate mpesa api password using the provided shortcode and passkey"""
        password_str= shortcode + passkey + timestamp
        password_bytes= password_str.encode("ascii")
        return base64.b64encode(password_bytes).decode("utf-8")
    
    @Decorators.refreshToken
    def stk_push_request(self, payload):
        request=payload["request"]
        data = payload["data"]
        amount= payload["amount"]
        phone_number = data["phone_number"] #A valid phone number with the format 254000000
        desc = data["description"] #THis can be anything but not blank
        reference = data["reference"] #anything but not blank

        # The shortcode and passkey values below are the test credentials availed by safaricom
        shortcode = ["174379"]
        passkey = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
        timestamp = datetime.now.strftime("%Y%m%d%H%M%S")
        req_data = {
            "BusinessShortCode": self.shortcode,
            "Password": self.password,
            "Timestamp": self.timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": math.ceil(float(amount)),
            "PartyA": phone_number,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": self.c2b_callback,
            "AccountReference": "Test",
            "TransactionDesc": "Test",
        }

        res = requests.post(
            self.checkout_url, json=req_data, headers=self.headers, timeout=30
        )
        res_data = res.json()
        logging.info("Mpesa request data{}".format(req_data))
        logging.info("MPesa response info {}".format(res_data))

        if res.ok:
            data["ip"] = request.META.get("REMOTE_ADDR")
            data["checkout_request_id"] = res_data["CheckoutRequestID"]

            TransactionModel.objects.create(**data)
        return res_data
    
    # Now lets handle the callback. We are going to keep it simple. We won’t do error handling for the different types of failures such as invalid phone number (number that is not an mpesa number), or if the users phone is off etc. We simply generally handle failure and success.

    def check_status(self, data):
        try:
            status = data["Body"]["stkCallback"]["ResultCode"]
        except Exception as e:
            logging.error(f"Error: {e}")
            status =1

        return status
    
    def get_transaction_object(data):
        checkout_request_id= data["Body"]["stkCallback"]["ResultCode"]
        transaction, _ = TransactionModel.objects.get_or_create(
            checkout_request_id=checkout_request_id
        )
        return transaction
    
    def handle_successful_pay(self, data, transaction):
        items= data["Body"]["stkCallback"]["CallbackMetadata"]["Item"]
        for item in items:
            if item["Name"]== "Amount":
                amount = item["Value"]
            elif item["Name"] == "MpesaReceiptNumber":
                receipt_no = item["Value"]
            elif item["Name"] == "PhoneNumber":
                phone_number = item["Value"]

        transaction.amount = amount
        transaction.phone_number = PhoneNumber(raw_input=phone_number)
        transaction.receipt_no = receipt_no
        transaction.confirmed = True

        return transaction
    
    def callback_handler(self, data):
        status = self.check_status(data)
        transaction = self.get_transaction_object(data)
        if status ==0:
            self.handle_successful_pay(data, transaction)
        else:
            transaction.status =1
        
        transaction.status = status
        transaction.save()
        
        transaction_data = TransactionListSerializer(transaction).data

        logging.info("Transaction completed {}".format(transaction_data))

        return Response ({"status": "ok", "code": 0}, status=200)
