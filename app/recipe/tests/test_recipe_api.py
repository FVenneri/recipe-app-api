import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient

from recipe.serializers import RecipeSerializer, RecipeDetailSerializer


RECIPES_URL = reverse('recipe:recipe-list')


def upload_image_url(recipe_id):
    """Return URL for recipe image upload"""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def detail_url(recipe_id):
    """Return recipe URL"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def sample_tag(user, name='Main Course'):
    """Create a new sample tag"""
    return Tag.objects.create(user=user, name=name)


def sample_ingredient(user, name='Oil'):
    """Create a new sample ingredient"""
    return Ingredient.objects.create(user=user, name=name)


def sample_recipe(user, **params):
    """Create and return a sample recipe"""
    defaults = {
        'title': 'Sample recipe',
        'time_minutes': 10,
        'price': 5.00
    }
    defaults.update(params)
    return Recipe.objects.create(user=user, **defaults)


class PublicRecipeApiTests(TestCase):
    """Test that authentication is required on public recipe API"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication in required"""
        res = self.client.get(RECIPES_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    """Test private recipe API"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@test.com',
            password='testpass'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Test retrieving a list of recipes"""
        sample_recipe(user=self.user)
        sample_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_recipes_limited_to_user(self):
        """Test retrieve only the recipes of the given user"""
        another_user = get_user_model().objects.create_user(
            email='another@test.com',
            password='testpass'
        )
        sample_recipe(user=another_user, title='another recipe')
        sample_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data, serializer.data)

    def test_view_recipe_detail(self):
        """Test view recipe details"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        recipe.ingredients.add(sample_ingredient(user=self.user))

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """Test create a recipe"""
        payload = {
            'title': 'Bacon wrapped meatloaf',
            'time_minutes': 60,
            'price': 5.00
        }
        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))

    def test_create_recipe_with_tags(self):
        """Test create a recipe with tags"""
        tag1 = sample_tag(user=self.user, name='Meat')
        tag2 = sample_tag(user=self.user, name='Main Course')
        payload = {
            'title': 'Bacon wrapped meatloaf',
            "tags": [tag1.id, tag2.id],
            'time_minutes': 60,
            'price': 5.00
        }

        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        tags = recipe.tags.all()
        self.assertEqual(tags.count(), 2)
        self.assertIn(tag1, tags)
        self.assertIn(tag2, tags)

    def test_create_recipe_with_ingredients(self):
        """Test create a recipe with tags"""
        ingredient1 = sample_ingredient(user=self.user, name='Bacon')
        ingredient2 = sample_ingredient(user=self.user, name='Sausage')
        payload = {
            'title': 'Bacon wrapped meatloaf',
            "ingredients": [ingredient1.id, ingredient2.id],
            'time_minutes': 50,
            'price': 8.00
        }

        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        ingredients = recipe.ingredients.all()
        self.assertEqual(ingredients.count(), 2)
        self.assertIn(ingredient1, ingredients)
        self.assertIn(ingredient2, ingredients)

    def test_partial_update_recipe(self):
        """Test partial update with PATCH"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        new_tag = sample_tag(user=self.user, name='Curry')

        payload = {'title': 'Chicken Tikka', 'tags': [new_tag.id]}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        tags = recipe.tags.all()
        self.assertEqual(len(tags), 1)
        self.assertIn(new_tag, tags)

    def test_full_update_recipe(self):
        """Test full update with PUT"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))

        payload = {
            'title': 'Tiramisu',
            'time_minutes': 12,
            'price': 5.00
        }
        url = detail_url(recipe.id)
        self.client.put(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.time_minutes, payload['time_minutes'])
        self.assertEqual(recipe.price, payload['price'])
        self.assertEqual(len(recipe.tags.all()), 0)

    def test_filter_recipes_by_tags(self):
        recipe1 = sample_recipe(user=self.user, title='Burger')
        recipe2 = sample_recipe(user=self.user, title='Steak')
        tag1 = sample_tag(user=self.user, name='Fast Food')
        tag2 = sample_tag(user=self.user, name='Slow Food')
        recipe1.tags.add(tag1)
        recipe2.tags.add(tag2)
        recipe3 = sample_recipe(user=self.user, title='Fish and chips')

        res = self.client.get(
            RECIPES_URL,
            {'tags': f'{tag1.id},{tag2.id}'}
        )

        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_recipes_by_ingredients(self):
        recipe1 = sample_recipe(user=self.user, title='Chicken wings')
        recipe2 = sample_recipe(user=self.user, title='Smoked salmon')
        ingredient1 = sample_ingredient(user=self.user, name='Chicken')
        ingredient2 = sample_ingredient(user=self.user, name='Salmon')
        recipe1.ingredients.add(ingredient1)
        recipe2.ingredients.add(ingredient2)
        recipe3 = sample_recipe(user=self.user, title='Fish and chips')
        recipe3.ingredients.add(sample_ingredient(user=self.user, name='Cod'))
        recipe3.ingredients.add(
            sample_ingredient(user=self.user, name='Potato')
        )

        res = self.client.get(
            RECIPES_URL,
            {'ingredients': f'{ingredient1.id},{ingredient2.id}'}
        )

        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)


class RecipeUploadImageTests(TestCase):
    """Tests for image uploading"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user('u@u.com', 'testpass')
        self.client.force_authenticate(self.user)
        self.recipe = sample_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image_recipe(self):
        """Test uploading the image for a recipe"""
        url = upload_image_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as temporary_file:
            img = Image.new('RGB', (10, 10))
            img.save(temporary_file, format='JPEG')
            temporary_file.seek(0)
            res = self.client.post(
                url, {'image': temporary_file}, format='multipart'
            )
        self.recipe.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

        url = detail_url(self.recipe.id)
        res_recipe = self.client.get(url)
        self.assertIn('image', res_recipe.data)

    def test_upload_image_recipe_invalid(self):
        """Test uploading the invalid image for a recipe"""
        url = upload_image_url(self.recipe.id)
        res = self.client.post(url, {'image': 'str'}, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
