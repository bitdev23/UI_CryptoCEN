"""
Simple integration test for admin soft-delete flow using Flask test client.

Run locally:
  python3 scripts/test_soft_delete_flow.py

This uses a small in-memory FakeSupabase to avoid calling the real service.
"""
import uuid
from datetime import datetime

import app as app_module


class FakeAdmin:
    def __init__(self, parent):
        self.parent = parent

    def create_user(self, payload):
        uid = str(uuid.uuid4())
        user = {
            'id': uid,
            'email': payload.get('email'),
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'user_metadata': payload.get('user_metadata', {}) or {}
        }
        self.parent.users[uid] = user
        return {'user': user}

    def get_user_by_id(self, uid):
        u = self.parent.users.get(uid)
        if not u:
            raise Exception('user not found')
        return {'user': u}

    def update_user_by_id(self, uid, attrs):
        u = self.parent.users.get(uid)
        if not u:
            raise Exception('user not found')
        um = attrs.get('user_metadata')
        if um is not None:
            u['user_metadata'] = um
        return {'user': u}

    def delete_user(self, uid):
        self.parent.users.pop(uid, None)
        return {'success': True}

    def list_users(self, page=1, per_page=1000):
        # Simulate a list_users response that omits user_metadata (the problematic case)
        class U:
            def __init__(self, d):
                self.id = d.get('id')
                self.email = d.get('email')
                self.created_at = d.get('created_at')

        return [U(u) for u in self.parent.users.values()]


class FakeAuthSupabase:
    def __init__(self):
        self.users = {}
        self.auth = type('A', (), {'admin': FakeAdmin(self)})()

    def table(self, name):
        class T:
            def delete(self):
                return self

            def eq(self, a, b):
                return self

            def execute(self):
                return type('R', (), {'data': []})()

            def select(self, *args, **kwargs):
                return self

            def order(self, *args, **kwargs):
                return self

            def limit(self, *args, **kwargs):
                return self

        return T()


def run_test():
    app = app_module.app

    fake = FakeAuthSupabase()
    app_module.auth_supabase = fake

    with app.test_client() as c:
        # set admin session
        with c.session_transaction() as sess:
            sess['is_admin'] = True
            sess['admin_email'] = 'admin@test.local'

        # 1) create a user
        resp = c.post('/api/admin/users/create', json={'email': 'user1@test.local', 'password': 'Password123'})
        assert resp.status_code == 200, resp.get_data(as_text=True)

        data = c.get('/api/admin/users').get_json()
        assert data.get('success') is True
        users = data.get('users') or []
        assert len(users) == 1
        user_id = users[0]['id']

        # 2) soft-delete the user (type email as confirmation)
        resp = c.delete(f'/api/admin/users/{user_id}', json={'confirm': 'user1@test.local'})
        j = resp.get_json() or {}
        if not (resp.status_code == 200 and j.get('success') is True):
            print('DEBUG delete status:', resp.status_code)
            print('DEBUG delete body:', resp.get_data(as_text=True))
            print('DEBUG parsed json:', j)
            raise AssertionError(f'delete failed: status={resp.status_code} body={resp.get_data(as_text=True)}')

        # 3) the user should be excluded from the main admin list
        data_active = c.get('/api/admin/users').get_json()
        active_ids = [u['id'] for u in (data_active.get('users') or [])]
        assert user_id not in active_ids, f'user {user_id} still in active list'

        # 4) the user should appear in the soft-deleted list
        data_soft = c.get('/api/admin/users/soft_deleted').get_json()
        soft_ids = [u['id'] for u in (data_soft.get('users') or [])]
        assert user_id in soft_ids, f'user {user_id} not found in soft-deleted list'

        print('PASS soft-delete flow')


if __name__ == '__main__':
    run_test()
