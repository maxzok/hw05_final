from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from posts.models import Post, Group

User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='testuser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='1',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )
        cls.HOME_PG = '/'
        cls.GROUP_PG = f'/group/{StaticURLTests.group.slug}/'
        cls.PROFILE_PG = f'/profile/{StaticURLTests.user.username}/'
        cls.DETAIL_PG = f'/posts/{StaticURLTests.post.id}/'
        cls.CREATE_PG = '/create/'
        cls.EDIT_PG = f'/posts/{StaticURLTests.post.id}/edit/'
        cls.NOT_EXIST_PG = 'not_a_url/'

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_urls_uses_correct_template_not_a_url(self):
        """Несуществующий адрес отвечает 404"""
        response = self.client.get(self.NOT_EXIST_PG)

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            self.HOME_PG: 'posts/index.html',
            self.GROUP_PG: 'posts/group_list.html',
            self.DETAIL_PG: 'posts/post_detail.html',
            self.PROFILE_PG: 'posts/profile.html',
            self.CREATE_PG: 'posts/create_post.html',
            self.EDIT_PG: 'posts/create_post.html'
        }

        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_url_exists_at_desired_location_auth(self):
        """URL-адрес доступен авторизованному пользователю"""
        code_url_names = {
            self.HOME_PG: HTTPStatus.OK,
            self.GROUP_PG: HTTPStatus.OK,
            self.DETAIL_PG: HTTPStatus.OK,
            self.PROFILE_PG: HTTPStatus.OK,
            self.CREATE_PG: HTTPStatus.OK,
            self.EDIT_PG: HTTPStatus.OK
        }

        for adress, code in code_url_names.items():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                self.assertEqual(response.status_code, code)

    def test_url_exists_at_desired_location_not_auth(self):
        """URL-адрес доступен неавторизованному пользователю"""
        code_url_names = {
            self.HOME_PG: HTTPStatus.OK,
            self.GROUP_PG: HTTPStatus.OK,
            self.DETAIL_PG: HTTPStatus.OK,
            self.PROFILE_PG: HTTPStatus.OK,
            self.CREATE_PG: HTTPStatus.FOUND,
            self.EDIT_PG: HTTPStatus.FOUND
        }

        for adress, code in code_url_names.items():
            with self.subTest(adress=adress):
                response = self.client.get(adress)
                self.assertEqual(response.status_code, code)

    def test_task_list_url_redirect_anonymous_on_admin_login(self):
        """Страница create перенаправит неавторизованного
        пользователя на страницу логина."""
        response = self.client.get(self.CREATE_PG, follow=True)

        self.assertRedirects(
            response, '/auth/login/?next=/create/'
        )

    def test_not_author_cant_edit(self):
        user2 = User.objects.create_user(username='testuser2')
        p2 = Post.objects.create(
            author=user2,
            text='Тестовый пост',
        )

        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': p2.id}), follow=True
        )

        self.assertRedirects(
            response, reverse('posts:post_detail', kwargs={'post_id': p2.id})
        )
