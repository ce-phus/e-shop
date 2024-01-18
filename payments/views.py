import logging, json

from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from account.serializers import MpesaCheckoutSerializer
from .access_token import MpesaGateway

gateway = MpesaGateway()

@authentication_classes([])
@permission_classes((AllowAny,))
class MPesaCheckout(APIView):
    serializer = MpesaCheckoutSerializer

    def post(self, request, *args, **kwargs):
        serializer= self.serializer(data=request)

        if serializer.is_valid(raise_exception=True):
            payload= {"data": serializer.validated_data, "request": request}
            res = gateway.stk_push_request(payload)

@authentication_classes([])
@permission_classes((AllowAny,))
class MpesaCallBack(APIView):
    def get(self, request):
        return Response({"status": "OK"}, status=200)
    
    def post(self, request, *args, **kwargs):
        logging.info("{}".format("Callback fro MPESA"))
        data = request.body
        return gateway.callback(json.loads(data))