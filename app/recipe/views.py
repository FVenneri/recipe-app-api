from rest_framework import viewsets, mixins
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from core.models import Tag, Ingredient

from recipe import serializers


class BaseRecipeAttributeViewSet(viewsets.GenericViewSet,
                                 mixins.ListModelMixin,
                                 mixins.CreateModelMixin):
    """Manage generic recipe attributes in database"""
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        """Return the objects limited to the authenticated user"""
        return self.queryset.filter(user=self.request.user).order_by('-name')

    def perform_create(self, serializer):
        """Create a new object for the authenticated user"""
        serializer.save(user=self.request.user)


class TagViewSet(BaseRecipeAttributeViewSet):
    """Manage tags in database"""
    queryset = Tag.objects.all()
    serializer_class = serializers.TagSerializer


class IngredientViewSet(BaseRecipeAttributeViewSet):
    """Manage ingredients in database"""
    queryset = Ingredient.objects.all()
    serializer_class = serializers.IngredientSerializer
