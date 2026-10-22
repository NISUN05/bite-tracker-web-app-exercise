"""Offline Add → stored document → Edit integration and failure checks."""
import os
import unittest
from unittest.mock import patch

import mongomock
from bson import ObjectId
from pymongo.errors import ServerSelectionTimeoutError

with patch.dict(os.environ, MONGO_URI='mongodb://localhost:27017', MONGO_DBNAME='test'):
    with patch('pymongo.MongoClient'):
        import app as food_app


class EditFoodEntryTests(unittest.TestCase):
    def setUp(self):
        food_app.app.config.update(TESTING=True, SECRET_KEY='test-only')
        self.browser = food_app.app.test_client()
        self.collection = mongomock.MongoClient().db.food_entries
        patcher = patch.object(food_app, 'food_entries', self.collection)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.form = dict(date='2026-10-19', food_name='Oatmeal', meal='breakfast',
                         calories='320', protein='12', carbs='48', fat='9')
        self.assertEqual(self.browser.post('/meals/new', data=self.form).status_code, 303)
        self.id = self.collection.find_one()['_id']
        self.url = f'/meals/{self.id}/edit'
        self.browser.get(self.url)
        with self.browser.session_transaction() as sess:
            self.token = sess['edit_csrf']

    def post(self, **changes):
        return self.browser.post(self.url, data=dict(self.form, csrf_token=self.token, **changes))

    def test_add_list_edit_save_reload(self):
        page = self.browser.get('/entries').text
        self.assertIn(self.url, page)
        page = self.browser.get(self.url).text
        self.assertIn('value="Oatmeal"', page)
        self.assertIn('data-preview="false"', page)
        self.collection.update_one({'_id': self.id}, {'$set': {'owner': 'keep'}})
        response = self.post(food_name='Updated oats', calories='400', meal='lunch')
        self.assertEqual(response.status_code, 303)
        saved = self.collection.find_one({'_id': self.id})
        self.assertEqual(saved['food_name'], 'Updated oats')
        self.assertEqual(saved['calories'], 400.0)
        self.assertEqual(saved['meal'], 'lunch')
        self.assertEqual(saved['owner'], 'keep')
        self.assertEqual(self.collection.count_documents({}), 1)
        page = self.browser.get(response.location).text
        self.assertIn('Changes saved successfully.', page)
        self.assertIn('value="400.0"', page)
        self.assertNotIn('Changes saved successfully.', self.browser.get(self.url).text)

    def test_unchanged_save_is_success(self):
        self.assertEqual(self.post().status_code, 303)

    def test_invalid_values_preserve_database_and_form(self):
        for field, value in [('date', '2026-02-30'), ('meal', 'brunch'),
                             ('food_name', '  '), ('calories', '-1'),
                             ('protein', 'nan'), ('carbs', 'inf'), ('fat', '')]:
            with self.subTest(field=field):
                response = self.post(**{field: value})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(self.collection.find_one() ['food_name'], 'Oatmeal')
                self.assertEqual(self.collection.find_one()['calories'], 320)

    def test_csrf_missing_wrong_and_other_session(self):
        for token in ['', 'wrong', '无效']:
            response = self.browser.post(self.url, data=dict(self.form, csrf_token=token))
            self.assertEqual(response.status_code, 400)
        other = food_app.app.test_client()
        self.assertEqual(other.post(self.url, data=dict(self.form, csrf_token=self.token)).status_code, 400)

    def test_invalid_and_missing_ids(self):
        for ident in ['not-an-id', str(ObjectId())]:
            self.assertEqual(self.browser.get(f'/meals/{ident}/edit').status_code, 404)
        self.collection.delete_one({'_id': self.id})
        self.assertEqual(self.post().status_code, 404)
        self.assertEqual(self.collection.count_documents({}), 0)

    def test_concurrently_removed_entry_not_recreated(self):
        with patch.object(self.collection, 'update_one') as update:
            update.return_value.matched_count = 0
            self.assertEqual(self.post().status_code, 404)
            self.assertNotIn('upsert', update.call_args.kwargs)

    def test_database_failure_is_not_success_or_secret_leak(self):
        for operation in ['find_one', 'update_one']:
            with patch.object(self.collection, operation, side_effect=ServerSelectionTimeoutError('secret URI')):
                response = self.post(food_name='Retain my input')
                self.assertEqual(response.status_code, 503)
                self.assertIn('Retain my input', response.text)
                self.assertNotIn('secret URI', response.text)
                self.assertNotIn('Changes saved successfully.', response.text)

    def test_extra_fields_and_html(self):
        response = self.post(food_name='<script>alert(1)</script>', _id=str(ObjectId()), owner='bad')
        self.assertEqual(response.status_code, 303)
        record = self.collection.find_one({'_id': self.id})
        self.assertNotIn('owner', record)
        self.assertNotIn('<script>alert(1)</script>', self.browser.get(self.url).text)

    def test_list_empty_failure_and_pagination(self):
        self.collection.delete_many({})
        self.assertIn('No saved entries', self.browser.get('/entries').text)
        for i in range(51):
            self.collection.insert_one(dict(self.form, food_name=f'Meal {i}'))
        self.assertIn('Next', self.browser.get('/entries').text)
        page = self.browser.get('/entries?page=2').text
        self.assertNotIn('>Next<', page)
        self.assertEqual(page.count('class="meal-row"'), 1)
        with patch.object(self.collection, 'find', side_effect=ServerSelectionTimeoutError('private')):
            response = self.browser.get('/entries')
            self.assertEqual(response.status_code, 503)
            self.assertNotIn('private', response.text)

    def test_teammate_edit_route_maps_fields_and_returns_to_history(self):
        url = f'/edit/{self.id}'
        page = self.browser.get(url)
        self.assertEqual(page.status_code, 200)
        self.assertIn(f'action="{url}"', page.text)
        payload = dict(self.form, csrf_token=self.token)
        payload['item_name'] = 'Updated yogurt'
        payload['meal_category'] = 'lunch'
        del payload['food_name']
        del payload['meal']
        response = self.browser.post(url, data=payload)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.location, '/history')
        record = self.collection.find_one({'_id': self.id})
        self.assertEqual(record['food_name'], 'Updated yogurt')
        self.assertEqual(record['meal'], 'lunch')
        self.assertEqual(record['date'], self.form['date'])
        self.assertNotIn('item_name', record)
        self.assertIn('Updated yogurt', self.browser.get('/history').text)

    def test_teammate_route_still_validates_and_protects_posts(self):
        url = f'/edit/{self.id}'
        self.assertEqual(self.browser.post(url, data=self.form).status_code, 400)
        payload = dict(self.form, csrf_token=self.token, calories='-1')
        self.assertEqual(self.browser.post(url, data=payload).status_code, 400)
        self.assertEqual(self.collection.find_one() ['calories'], 320)

    def test_unfinished_delete_fails_explicitly_without_deleting(self):
        self.assertEqual(self.browser.post(f'/meals/{self.id}/delete').status_code, 501)
        self.assertIsNotNone(self.collection.find_one({'_id': self.id}))
