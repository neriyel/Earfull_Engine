from django.shortcuts import render
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from . models import User
from . serilalizers import UserSerializer, RegisterSerializer

# Create your views here.

# POST /api/auth/register
class RegisterUser(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny] # Anyone allowed to access this View
    
# GET /api/auth/me
class MeView(generics.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
        