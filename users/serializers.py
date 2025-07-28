from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "full_name",
            "is_seller",
            "is_buyer",
            "balance",
            "avatar",
            "gender",
            "birth_year",
            "school",
            "country",
            "school_type",
            "course",
        )

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "gender",
            "birth_year",
            "school",
            "country",
            "school_type",
            "course",
            "avatar",
        ]
        extra_kwargs = {
            "email": {"required": True},
        }

    def validate_username(self, value):
        if self.instance and self.instance.username != value:
            if User.objects.filter(username=value).exists():
                raise serializers.ValidationError("This username is already taken.")
        return value

    def update(self, instance, validated_data):
        username_changed = (
            "username" in validated_data
            and instance.username != validated_data["username"]
        )

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if username_changed:
            pass

        return instance


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password",
            "is_seller",
            "is_buyer",
        )

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already in use.")
        if not value:
            raise serializers.ValidationError("Username is required.")
        if len(value) < 6:
            raise serializers.ValidationError(
                "Username must be at least 6 characters long."
            )
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError(
                "Password must be at least 8 characters long."
            )
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            password=validated_data["password"],
            is_seller=validated_data.get("is_seller", False),
            is_buyer=validated_data.get("is_buyer", False),
        )
        return user


class CustomTokenObtainSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        error_messages={
            "required": "Email is required.",
            "invalid": "Enter a valid email address.",
        },
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        error_messages={"required": "Password is required."},
    )

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if not email or not password:
            raise serializers.ValidationError(
                {"email": "Email is required.", "password": "Password is required."}
            )

        user = User.objects.filter(email=email).first()

        if not user:
            raise serializers.ValidationError(
                {"email": "User with this email does not exist."}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"email": "Account is not active. Please activate your account."}
            )

        if not user.check_password(password):
            raise serializers.ValidationError({"password": "Incorrect password."})

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "is_seller": getattr(user, "is_seller", False),
                "is_buyer": getattr(user, "is_buyer", False),
            },
        }


class RequestPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user is associated with this email.")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)

    def validate_new_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError(
                "Password must be at least 8 characters long."
            )
        return value
