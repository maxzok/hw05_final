from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post, CHARS_IN_TEXT

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост больше пятнадцати символов',
        )

    def test_post_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        post = PostModelTest.post
        expected_object_name_post = post.text[:CHARS_IN_TEXT]

        self.assertEqual(expected_object_name_post, str(post))

    def test_group_have_correct_object_names(self):
        group = PostModelTest.group
        expected_object_name_group = group.title

        self.assertEqual(expected_object_name_group, str(group))
