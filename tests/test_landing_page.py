import pytest
from app import create_app


@pytest.fixture()
def client():
    app = create_app('development')
    app.config['TESTING'] = True
    with app.test_client() as test_client:
        yield test_client


def test_index_page_renders_landing_view(client):
    response = client.get('/')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'SAHANANETH' in html
    assert 'Citizen Login' in html
    assert 'Staff Login' in html
