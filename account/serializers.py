from .models import TransactionModel, BillingAddress, OrderModel
from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

class UserSerializer(serializers.ModelSerializer):
    admin = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model=User
        fields=["id", "username", "email", "admin"]

        def get_admin(self, obj):
            return obj.is_staff

# creating tokens manually *with user regsitration we will also create tokens
class UserRegisterTokenSerializer(UserSerializer):
    token = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "admin", "token"]

    def get_token(self,obj):
        token= RefreshToken.for_user(obj)
        return str(token.access_token)
    
# List of transactions
class TransactionListSerializer(serializers.ModelSerializer):

    class Meta:
        model= TransactionModel
        fields= "__all__"

# billing address details
class BillingAddressSerializer(serializers.ModelSerializer):
    
    class Meta:
        model= BillingAddress
        fields= "__all__"

# all order list
class ALLOrderListSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderModel
        fields = "__all__"

