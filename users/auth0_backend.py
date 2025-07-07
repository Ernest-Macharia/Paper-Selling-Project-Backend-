import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

DEFAULT_TIMEOUT = 10  # reduced timeout for better responsiveness


class Auth0JSONWebTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None  # Allow fallthrough to other authentication methods

        token = auth_header.split(" ")[1]

        try:
            payload = self.decode_token(token)
        except ExpiredSignatureError:
            raise AuthenticationFailed("Token has expired.")
        except JWTError as e:
            raise AuthenticationFailed(f"Invalid token: {str(e)}")

        email = payload.get("email")
        if not email:
            raise AuthenticationFailed("Token missing email claim.")

        User = get_user_model()
        user, _ = User.objects.get_or_create(email=email)
        return (user, None)

    def decode_token(self, token):
        unverified_header = jwt.get_unverified_header(token)

        jwks_url = f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json"
        try:
            jwks = requests.get(jwks_url, timeout=DEFAULT_TIMEOUT).json()
        except requests.RequestException:
            raise AuthenticationFailed("Unable to fetch JWKS keys from Auth0.")

        rsa_key = next(
            (
                {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
                for key in jwks["keys"]
                if key["kid"] == unverified_header["kid"]
            ),
            None,
        )

        if not rsa_key:
            raise AuthenticationFailed("Matching RSA key not found in JWKS.")

        return jwt.decode(
            token,
            rsa_key,
            algorithms=settings.AUTH0_ALGORITHMS,
            audience=settings.AUTH0_API_IDENTIFIER,
            issuer=f"https://{settings.AUTH0_DOMAIN}/",
        )
