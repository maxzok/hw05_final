from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django import forms
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile

from posts.models import Post, Group, Follow
from ..utils import POSTS_PER_PAGE

User = get_user_model()

TEST_POSTS_CREATED = 13


class ViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='testuser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='1',
            description='Тестовое описание',
        )
        for post in range(TEST_POSTS_CREATED):
            cls.post = Post.objects.create(
                author=cls.user,
                text='Тестовый пост',
                group=cls.group,
                image=cls.uploaded
            )
        cls.index = 'posts:main'
        cls.group_posts = 'posts:group_posts'
        cls.post_detail = 'posts:post_detail'
        cls.post_edit = 'posts:post_edit'
        cls.post_create = 'posts:post_create'
        cls.profile = 'posts:profile'
        cls.follow = 'posts:follow_index'
        cache.clear()

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def check(self, first_object):
        self.assertEqual(self.post.text, first_object.text)
        self.assertEqual(first_object.group, self.post.group)
        self.assertEqual(first_object.author, self.post.author)
        self.assertEqual(first_object.id, self.post.id)
        self.assertEqual(first_object.image, self.post.image)

    def test_pages_uses_correct_template(self):
        """Проверяем работу кэша главной страницы"""
        response = self.client.get(reverse(self.index))
        cached_response_content = response.content
        Post.objects.create(text='Второй пост', author=self.user)
        response = self.client.get(reverse(self.index))
        self.assertEqual(cached_response_content, response.content)
        cache.clear()
        response = self.client.get(reverse(self.index))
        self.assertNotEqual(cached_response_content, response.content)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse(self.index): 'posts/index.html',
            reverse(
                self.group_posts, kwargs={'slug': '1'}
            ): 'posts/group_list.html',
            reverse(
                self.post_detail, kwargs={'post_id': self.post.id}
            ): 'posts/post_detail.html',
            reverse(
                self.post_edit, kwargs={'post_id': self.post.id}
            ): 'posts/create_post.html',
            reverse(self.post_create): 'posts/create_post.html',
            reverse(
                self.profile, kwargs={'username': self.user.username}
            ): 'posts/profile.html'
        }

        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)


    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(self.index))
        first_object = response.context['page_obj'][0]

        self.check(first_object)

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(self.group_posts, kwargs={'slug': '1'})
        )
        page_obj = response.context.get('page_obj').object_list
        expected = list(Post.objects.filter(group=self.group)[:POSTS_PER_PAGE])
        first_object = response.context['page_obj'][0]

        self.check(first_object)
        self.assertEqual(page_obj, expected)

    def assert_post_create_form(self, response):
        """Поля формы имеют правильный тип"""
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)

                self.assertIsInstance(form_field, expected)

    def test_post_create_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(self.post_create))

        self.assert_post_create_form(response)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        response = self.authorized_client.get(
            reverse(self.post_edit, kwargs={'post_id': self.post.pk}))
        is_edit = response.context.get('is_edit')

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        self.assert_post_create_form(response)
        self.assertTrue(is_edit)

    def test_post_in_correct_profile_page(self):
        """Тестовый пост попадает в нужный профиль"""
        response = self.authorized_client.get(
            reverse(self.profile, kwargs={'username': self.user.username})
        )
        first_object = response.context['page_obj'][0]

        self.check(first_object)

    def test_post_in_correct_group_page(self):
        """Тестовый пост попадает в нужную группу"""
        response = self.authorized_client.get(
            reverse(self.group_posts, kwargs={'slug': 1})
        )
        first_object = response.context['page_obj'][0]

        self.check(first_object)

    def test_post_not_in_wrong_group_page(self):
        """Тестовый пост не попадает в ненужную группу"""
        test_post = Post.objects.create(
            author=self.user,
            text='Тестовый пост',
            group=self.group
        )
        group2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='2',
            description='Тестовое описание',
        )

        response = self.authorized_client.get(
            reverse(self.group_posts, kwargs={'slug': group2.slug})
        )
        first_object = response.context['page_obj']

        self.assertNotIn(test_post, first_object)

    def test_post_not_in_wrong_profile_page(self):
        """Тестовый пост не попадает в ненужнкю страницу профиль"""
        testuser = User.objects.create_user(username='testuser2')
        test_post = Post.objects.create(
            author=self.user,
            text='Тестовый пост',
            group=self.group
        )

        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': testuser.username})
        )
        first_object = response.context['page_obj']

        self.assertNotIn(test_post, first_object)

    def test_created_post_appears_on_pages(self):
        pages_names = [
            reverse(self.index),
            reverse(self.group_posts, kwargs={'slug': '1'}),
            reverse(self.profile, kwargs={'username': self.user.username})
        ]
        Post.objects.create(
            author=self.user,
            text='Тестовый пост',
            group=self.group
        )

        for reverse_name in pages_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(
                    reverse_name
                ).context['page_obj']
                self.assertIn(self.post, response)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='NoName')
        cls.group = Group.objects.create(
            title='test_title',
            description='test_description',
            slug='test-slug'
        )
        cache.clear()

    def setUp(self):
        for post_temp in range(TEST_POSTS_CREATED):
            Post.objects.create(
                text=f'text{post_temp}', author=self.author, group=self.group
            )
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)
        cache.clear()

    def test_first_page_contains_ten_records(self):
        """Paginator работает на первой странице (10 постов)"""
        pages = [
            reverse('posts:main'),
            reverse('posts:group_posts', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.author}),
        ]
        for reverse_name in pages:
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name)
                self.assertEqual(
                    len(response.context['page_obj']), POSTS_PER_PAGE
                )

    def test_second_page_contains_three_records(self):
        """Paginator работает на второй странице ((всего постов - 3) поста)"""
        pages = [
            reverse('posts:main') + '?page=2',
            reverse(
                'posts:group_posts', kwargs={'slug': self.group.slug}
            ) + '?page=2',
            reverse(
                'posts:profile', kwargs={'username': self.author}
            ) + '?page=2',
        ]
        for reverse_name in pages:
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name)
                self.assertEqual(len(
                    response.context['page_obj']), (
                        TEST_POSTS_CREATED - POSTS_PER_PAGE
                )
                )


class FollowViewsTest(TestCase):
    def setUp(self):
        self.follower = User.objects.create_user(username='Follower')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.follower)
        self.author = User.objects.create_user(username='author')
        self.post_author = Post.objects.create(
            text='Текст автора',
            author=self.author,
        )

    def test_follow_author(self):
        follow_count = Follow.objects.count()
        response = self.authorized_client.get(
            reverse('posts:profile_follow', args={self.author}))
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        last_follow = Follow.objects.latest('id')
        self.assertEqual(last_follow.author, self.author)
        self.assertEqual(last_follow.user, self.follower)
        self.assertRedirects(response, reverse(
            'posts:profile', args={self.author}))

    def test_unfollow_author(self):
        follow_count = Follow.objects.count()
        self.authorized_client.get(
            reverse('posts:profile_follow', args={self.author}))
        response = self.authorized_client.get(
            reverse('posts:profile_unfollow', args={self.author}))
        self.assertRedirects(response, reverse(
            'posts:profile', args={self.author}))
        self.assertEqual(Follow.objects.count(), follow_count)

    def test_new_post_follow(self):
        self.authorized_client.get(
            reverse('posts:profile_follow', args={self.author}))
        response = self.authorized_client.get(
            reverse('posts:follow_index'))
        post_follow = response.context['page_obj'][0]
        self.assertEqual(post_follow, self.post_author)

    def test_new_post_unfollow(self):
        new_author = User.objects.create_user(username='new_author')
        self.authorized_client.force_login(new_author)
        Post.objects.create(
            text='Новый текст автора',
            author=new_author,
        )
        response = self.authorized_client.get(
            reverse('posts:follow_index'))
        self.assertEqual(len(response.context['page_obj']), 0)
