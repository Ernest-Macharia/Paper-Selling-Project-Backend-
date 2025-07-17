import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from jose import jwt
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from users.utils import send_activation_email

from .serializers import (
    CustomTokenObtainSerializer,
    PasswordResetConfirmSerializer,
    RegisterSerializer,
    RequestPasswordResetSerializer,
    UserProfileUpdateSerializer,
    UserSerializer,
)

User = get_user_model()

DEFAULT_TIMEOUT = 60


class RegisterUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user.is_active = False
        user.save()

        send_activation_email(user)

        # Generate JWT Token
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        return Response(
            {
                "user": {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                },
                "access": access_token,
            },
            status=status.HTTP_201_CREATED,
        )


class CustomLoginView(APIView):
    def post(self, request):
        serializer = CustomTokenObtainSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]


class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UpdateUserDetailsView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class RequestPasswordResetView(generics.GenericAPIView):
    serializer_class = RequestPasswordResetSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        user = User.objects.get(email=email)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        reset_link = f"{settings.BASE_URL}/reset-password-confirm/{uid}/{token}"

        html_message = render_to_string(
            "emails/password_reset_email_template.html",
            {
                "user": user,
                "reset_link": reset_link,
                "current_year": now().year,
            },
        )

        send_mail(
            subject="Password Reset Request",
            message=f"Click the link to reset your password: {reset_link}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
            html_message=html_message,
        )

        return Response(
            {"detail": "Password reset link sent."}, status=status.HTTP_200_OK
        )


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid = serializer.validated_data["uid"]
        token = serializer.validated_data["token"]
        password = serializer.validated_data["new_password"]

        try:
            uid = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {"detail": "Token is invalid or expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(password)
        user.save()

        return Response(
            {"detail": "Password reset successfully."}, status=status.HTTP_200_OK
        )


class ResendActivationEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required."}, status=400)

        try:
            user = User.objects.get(email=email)

            if user.is_active:
                return Response({"error": "Account is already active."}, status=400)

            send_activation_email(user)
            return Response({"message": "Activation email resent successfully."})
        except User.DoesNotExist:
            return Response(
                {"error": "User with this email does not exist."}, status=404
            )


@csrf_exempt
def activate_user(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)

        if user.is_active:
            return JsonResponse({"message": "Account already activated."})

        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            return JsonResponse({"message": "Account activated successfully."})
        else:
            return JsonResponse({"error": "Invalid or expired token."}, status=400)

    except (User.DoesNotExist, ValueError, TypeError):
        return JsonResponse({"error": "Invalid activation link."}, status=400)


class Auth0LoginView(APIView):
    def post(self, request):
        token = request.data.get("token")

        if not token:
            return Response(
                {"detail": "Token is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Verify the token with Auth0
            jwks_url = f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json"
            jwks = requests.get(jwks_url, timeout=DEFAULT_TIMEOUT).json()

            unverified_header = jwt.get_unverified_header(token)
            rsa_key = {}
            for key in jwks["keys"]:
                if key["kid"] == unverified_header["kid"]:
                    rsa_key = {
                        "kty": key["kty"],
                        "kid": key["kid"],
                        "use": key["use"],
                        "n": key["n"],
                        "e": key["e"],
                    }

            if not rsa_key:
                return Response(
                    {"detail": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST
                )

            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=settings.AUTH0_ALGORITHMS,
                audience=settings.AUTH0_API_IDENTIFIER,
                issuer=f"https://{settings.AUTH0_DOMAIN}/",
            )

            email = payload.get("email")
            if not email:
                return Response(
                    {"detail": "Email not found in token"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get or create user
            user, created = User.objects.get_or_create(email=email)
            if created:
                user.first_name = payload.get("given_name", "")
                user.last_name = payload.get("family_name", "")
                user.set_unusable_password()
                user.save()

            # Generate tokens
            refresh = RefreshToken.for_user(user)

            return Response(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                    },
                }
            )

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
