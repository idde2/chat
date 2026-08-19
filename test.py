import unittest
import json
from main import app

class ChatApiTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_api_index(self):
        response = self.app.get('/api/')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("name"), "eddi.chat API")

    def test_unauthorized_access(self):
        response = self.app.get('/api/me')
        self.assertEqual(response.status_code, 401)

    def test_login_validation(self):
        response = self.app.post('/api/auth/login', 
                                 data=json.dumps({"username": "", "password": ""}),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 400)

if __name__ == '__main__':
    unittest.main()
