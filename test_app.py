import pytest
import datetime
from app import app, db, User, Product, Order, OrderItem, Customer, PaymentTransaction, Supplier, PurchaseOrder, PurchaseOrderItem
 
@pytest.fixture(scope='function')
def client():
    """테스트를 위한 가상 클라이언트 및 테스트 DB를 생성합니다."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' 
    
    with app.app_context():
        db.drop_all() # Ensure a clean slate before creating tables
        db.create_all()

        # 상품 테스트를 위한 초기 데이터
        p1 = Product(id='P01', name='근위', unit='KG', price=5000, stock_quantity=100) # 초기 재고 추가
        p2 = Product(id='P02', name='닭', unit='마리', price=8000, stock_quantity=100) # 초기 재고 추가
        db.session.add_all([p1, p2])
        db.session.commit()

        with app.test_client() as client:
            yield client

        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def logged_in_client(client):
    """
    회원가입 및 로그인을 미리 수행하고, 로그인된 상태의 클라이언트를 반환합니다.
    이 Fixture를 사용하는 테스트는 인증이 필요한 API를 바로 테스트할 수 있습니다.
    """
    # GIVEN: 테스트용 사용자 생성 및 로그인
    client.post('/api/auth/register', json={'username': 'testuser', 'password': 'password'})
    client.post('/api/auth/login', json={'username': 'testuser', 'password': 'password'})
    yield client
    # 테스트 종료 후에는 client fixture에서 db.drop_all()로 정리됩니다.

# --- Phase 1: 상품 CRUD 테스트 ---
# (이전 단계에서 작성한 상품 관련 테스트들은 그대로 둡니다)
def test_product_api_unauthorized(client):
    """로그인하지 않고 상품 API 접근 시 401 에러가 발생하는지 테스트합니다."""
    # GET /api/products
    response = client.get('/api/products')
    assert response.status_code == 401

    # POST /api/products
    response = client.post('/api/products', json={'name': '새우깡', 'unit': '봉', 'price': 1500})
    assert response.status_code == 401

    # GET /api/product/<id>
    response = client.get('/api/product/P01')
    assert response.status_code == 401

def test_get_all_products_after_login(logged_in_client):
    """로그인 후 상품 목록을 성공적으로 조회하는지 테스트합니다."""
    response = logged_in_client.get('/api/products')
    assert response.status_code == 200
    assert len(response.json) == 2 # 초기 데이터 2개

def test_add_new_product_after_login(logged_in_client):
    """로그인 후 새로운 상품을 성공적으로 추가하는지 테스트합니다."""
    # [버그 수정] 'id' 필드 추가
    new_product = {'id': 'P03', 'name': '새우깡', 'unit': '봉', 'price': 1500, 'stock_quantity': 50}
    response = logged_in_client.post('/api/products', json=new_product)
    assert response.status_code == 201
    
    with app.app_context():
        assert Product.query.count() == 3
        product = Product.query.get('P03')
        assert product is not None
        assert product.name == '새우깡'
        assert product.stock_quantity == 50
        
def test_update_product_after_login(logged_in_client):
    # GIVEN: P01 상품의 초기 재고를 설정 (fixture에서 설정되지만, 명시적으로 확인)
    with app.app_context():
        product_p01 = Product.query.get('P01')
        assert product_p01.stock_quantity == 100 # fixture에서 설정된 초기 재고
    """로그인 후 상품 정보를 성공적으로 수정하는지 테스트합니다."""
    # WHEN: /api/product/P01 에 PUT 요청으로 상품 정보를 수정할 때
    updated_data = {'name': '근위(수정)', 'unit': 'g', 'price': 6000, 'stock_quantity': 50} # 재고 수량 포함
    response = logged_in_client.put('/api/product/P01', json=updated_data) # P01: 근위

    # THEN: 응답 코드는 200 (OK) 여야 한다.
    assert response.status_code == 200
    assert response.json['name'] == '근위(수정)'

    # 추가 검증: DB의 정보가 실제로 변경되었는지 확인
    with app.app_context(): # DB 접근을 위해 app_context 사용
        product = Product.query.get('P01')
    assert product.name == '근위(수정)'
    assert product.unit == 'g'
    assert product.price == 6000
    assert product.stock_quantity == 50

def test_delete_product_after_login(logged_in_client):
    """로그인 후 상품을 성공적으로 삭제하는지 테스트합니다."""
    # WHEN: /api/product/P01 에 DELETE 요청을 보낼 때
    response = logged_in_client.delete('/api/product/P01')

    # THEN: 응답 코드는 204 (No Content) 여야 한다.
    assert response.status_code == 204

    # 추가 검증: DB에서 상품이 실제로 삭제되었는지 확인
    with app.app_context(): # DB 접근을 위해 app_context 사용
        product = Product.query.get('P01')
    assert product is None
    assert Product.query.count() == 1 # 초기 데이터 2개 중 1개 삭제

def test_get_product_detail_with_stock_quantity(logged_in_client):
    """로그인 후 특정 상품의 상세 정보(재고 포함)를 성공적으로 조회하는지 테스트합니다."""
    # GIVEN: P01 상품은 fixture에서 초기 재고 100으로 설정됨
    
    # WHEN: /api/product/P01 에 GET 요청을 보낼 때
    response = logged_in_client.get('/api/product/P01')

    # THEN: 응답 코드는 200 (OK) 이고, 상품 정보와 재고 수량이 정확해야 한다.
    assert response.status_code == 200
    assert response.json['id'] == 'P01'
    assert response.json['name'] == '근위'
    assert response.json['unit'] == 'KG'
    assert response.json['price'] == 5000
    assert response.json['stock_quantity'] == 100

def test_adjust_product_stock_increase_success(logged_in_client):
    """로그인 후 상품 재고를 성공적으로 증가시키는지 테스트합니다."""
    # GIVEN: P01 상품의 초기 재고는 100
    with app.app_context():
        product_p01 = Product.query.get('P01')
        assert product_p01.stock_quantity == 100

    # WHEN: P01 상품의 재고를 50 증가시키는 요청
    response = logged_in_client.put('/api/product/P01/stock', json={'adjustment': 50})

    # THEN: 응답 코드는 200 (OK) 이고, 재고가 정확히 업데이트되어야 한다.
    assert response.status_code == 200
    assert response.json['id'] == 'P01'
    assert response.json['stock_quantity'] == 150

    # DB에서 실제 재고 확인
    with app.app_context():
        product_p01_after = Product.query.get('P01')
        assert product_p01_after.stock_quantity == 150

def test_adjust_product_stock_decrease_success(logged_in_client):
    """로그인 후 상품 재고를 성공적으로 감소시키는지 테스트합니다."""
    # GIVEN: P01 상품의 초기 재고는 100
    with app.app_context():
        product_p01 = Product.query.get('P01')
        assert product_p01.stock_quantity == 100

    # WHEN: P01 상품의 재고를 30 감소시키는 요청
    response = logged_in_client.put('/api/product/P01/stock', json={'adjustment': -30})

    # THEN: 응답 코드는 200 (OK) 이고, 재고가 정확히 업데이트되어야 한다.
    assert response.status_code == 200
    assert response.json['id'] == 'P01'
    assert response.json['stock_quantity'] == 70

    # DB에서 실제 재고 확인
    with app.app_context():
        product_p01_after = Product.query.get('P01')
        assert product_p01_after.stock_quantity == 70

def test_adjust_product_stock_below_zero_failure(logged_in_client):
    """재고를 0 미만으로 감소시키려고 할 때 실패하는지 테스트합니다."""
    # GIVEN: P01 상품의 초기 재고는 100
    with app.app_context():
        product_p01 = Product.query.get('P01')
        assert product_p01.stock_quantity == 100

    # WHEN: P01 상품의 재고를 110 감소시키는 요청 (100 - 110 = -10)
    response = logged_in_client.put('/api/product/P01/stock', json={'adjustment': -110})

    # THEN: 응답 코드는 400 (Bad Request) 이고, 에러 메시지가 반환되어야 한다.
    assert response.status_code == 400
    assert 'Stock cannot go below zero' in response.json['error']

    # DB에서 재고가 변경되지 않았는지 확인
    with app.app_context():
        product_p01_after = Product.query.get('P01')
        assert product_p01_after.stock_quantity == 100 # 재고는 그대로 100이어야 함

def test_adjust_product_stock_product_not_found(logged_in_client):
    """존재하지 않는 상품의 재고를 조정하려고 할 때 404 에러를 테스트합니다."""
    response = logged_in_client.put('/api/product/P99/stock', json={'adjustment': 10})
    assert response.status_code == 404
    assert 'Product not found' in response.json['error']

    
# --- Phase 2: 사용자 인증(Auth) 테스트 ---

def test_register_success(client):
    """성공적인 회원가입을 테스트합니다."""
    # WHEN: 새로운 사용자 정보로 /api/auth/register 에 POST 요청을 보낼 때
    response = client.post('/api/auth/register', json={
        'username': 'testuser',
        'password': 'password123'
    })

    # THEN: 응답 코드는 201 (Created) 여야 한다.
    assert response.status_code == 201
    assert response.json['message'] == 'User registered successfully'
    
    # 추가 검증: 실제로 User 테이블에 데이터가 생성되었는지 확인
    user = User.query.filter_by(username='testuser').first()
    assert user is not None
    assert user.check_password('password123') is True


def test_register_duplicate_username(client):
    """이미 존재하는 아이디로 회원가입 시도 시 에러를 테스트합니다."""
    # GIVEN: 'testuser'가 이미 가입되어 있는 상황
    client.post('/api/auth/register', json={
        'username': 'testuser',
        'password': 'password123'
    })

    # WHEN: 동일한 사용자 정보로 다시 POST 요청을 보낼 때
    response = client.post('/api/auth/register', json={
        'username': 'testuser',
        'password': 'password123'
    })

    # THEN: 응답 코드는 409 (Conflict) 여야 한다.
    assert response.status_code == 409
    assert 'already exists' in response.json['error']

def test_login_success(client):
    """성공적인 로그인을 테스트합니다."""
    # GIVEN: 사용자가 미리 회원가입 되어 있는 상황
    client.post('/api/auth/register', json={
        'username': 'loginuser',
        'password': 'loginpassword'
    })

    # WHEN: 올바른 사용자 정보로 /api/auth/login 에 POST 요청을 보낼 때
    response = client.post('/api/auth/login', json={
        'username': 'loginuser',
        'password': 'loginpassword'
    })

    # THEN: 응답 코드는 200 (OK) 여야 한다.
    assert response.status_code == 200
    assert response.json['message'] == 'Logged in successfully'

    # 추가 검증: 로그인 후 접근 가능한 API (예: /api/products)에 접근 시 401이 아닌 200을 받는지 확인
    # Flask-Login은 세션 쿠키를 사용하므로, client 객체가 세션을 유지합니다.
    product_response = client.get('/api/products')
    assert product_response.status_code == 200

def test_login_failure_wrong_password(client):
    """잘못된 비밀번호로 로그인 시도 시 실패를 테스트합니다."""
    # GIVEN: 사용자가 미리 회원가입 되어 있는 상황
    client.post('/api/auth/register', json={
        'username': 'wrongpassuser',
        'password': 'correctpassword'
    })

    # WHEN: 잘못된 비밀번호로 /api/auth/login 에 POST 요청을 보낼 때
    response = client.post('/api/auth/login', json={
        'username': 'wrongpassuser',
        'password': 'wrongpassword'
    })

    # THEN: 응답 코드는 401 (Unauthorized) 여야 한다.
    assert response.status_code == 401
    assert response.json['error'] == 'Invalid username or password'

def test_login_failure_non_existent_user(client):
    """존재하지 않는 사용자로 로그인 시도 시 실패를 테스트합니다."""
    # WHEN: 존재하지 않는 사용자 정보로 /api/auth/login 에 POST 요청을 보낼 때
    response = client.post('/api/auth/login', json={
        'username': 'nonexistentuser',
        'password': 'somepassword'
    })

    # THEN: 응답 코드는 401 (Unauthorized) 여야 한다.
    assert response.status_code == 401
    assert response.json['error'] == 'Invalid username or password'

def test_logout_success(client):
    """로그아웃 성공을 테스트합니다."""
    # 로그아웃은 로그인된 상태에서만 가능하므로, 먼저 로그인합니다.
    client.post('/api/auth/register', json={'username': 'logoutuser', 'password': 'logoutpass'})
    client.post('/api/auth/login', json={'username': 'logoutuser', 'password': 'logoutpass'})

    # WHEN: /api/auth/logout 에 POST 요청을 보낼 때
    response = client.post('/api/auth/logout')

    # THEN: 응답 코드는 200 (OK) 여야 한다.
    assert response.status_code == 200
    assert response.json['message'] == 'Logged out successfully'

    # 추가 검증: 로그아웃 후 로그인 필요 API (예: /api/products)에 접근 시 401을 받는지 확인
    product_response = client.get('/api/products')
    assert product_response.status_code == 401

def test_adjust_product_stock_unauthorized(client):
    """로그인하지 않은 상태에서 재고 조정 API 접근 시 401 에러를 테스트합니다."""
    response = client.put('/api/product/P01/stock', json={'adjustment': 10})
    assert response.status_code == 401

def test_adjust_product_stock_invalid_input(logged_in_client):
    """재고 조정 API에 잘못된 입력 시 400 에러를 테스트합니다."""
    # 'adjustment' 필드 누락
    response = logged_in_client.put('/api/product/P01/stock', json={'value': 10})
    assert response.status_code == 400
    assert 'Missing "adjustment" field' in response.json['error']

    # 'adjustment' 필드 값이 정수가 아님
    response = logged_in_client.put('/api/product/P01/stock', json={'adjustment': 'abc'})
    assert response.status_code == 400
    assert 'Adjustment must be an integer' in response.json['error']


# --- Phase 3: 주문(Order) API 테스트 ---

def test_create_order_success(logged_in_client):
    """로그인 후 주문을 성공적으로 생성하는지 테스트합니다."""
    # GIVEN: 거래처 생성
    customer_res = logged_in_client.post('/api/customers', json={'name': '테스트거래처'})
    assert customer_res.status_code == 201
    customer_id = customer_res.json['id']

    # GIVEN: 주문할 상품 데이터
    with app.app_context():
        order_items = [
            {'id': 'P01', 'quantity': 2, 'price': 5000}, # 근위 2KG
            {'id': 'P02', 'quantity': 1, 'price': 8000}  # 닭 1마리
        ]
    total_amount = (2 * 5000) + (1 * 8000) # 10000 + 8000 = 18000

    # WHEN: 로그인된 상태에서 /api/orders 에 POST 요청을 보낼 때
    response = logged_in_client.post('/api/orders', json={
        'items': order_items,
        'total_amount': total_amount,
        'customer_id': customer_id
    })

    # THEN: 응답 코드는 201 (Created) 여야 한다.
    assert response.status_code == 201
    assert response.json['message'] == 'Order created successfully'
    assert 'order_id' in response.json

    # 추가 검증: DB에 주문 및 주문 항목이 생성되었는지 확인
    from app import Order, OrderItem # Order, OrderItem 모델 임포트
    with app.app_context():
        order = Order.query.get(response.json['order_id'])
        assert order is not None
        assert order.total_amount == total_amount
        assert order.customer_id == customer_id
        assert len(order.items) == 2

        # 주문 항목 검증
        item1 = OrderItem.query.filter_by(order_id=order.id, product_id='P01').first()
        assert item1 is not None
        assert item1.quantity == 2
        assert item1.price_per_unit == 5000

        item2 = OrderItem.query.filter_by(order_id=order.id, product_id='P02').first()
        assert item2 is not None
        assert item2.quantity == 1
        assert item2.price_per_unit == 8000

        # 재고 감소 확인 (DB에서 다시 조회하여 정확한 값 확인)
        product_p01_after_order = Product.query.get('P01')
        product_p02_after_order = Product.query.get('P02')
        assert product_p01_after_order.stock_quantity == 98 # 초기 100개에서 2개 감소
        assert product_p02_after_order.stock_quantity == 99 # 초기 100개에서 1개 감소

def test_create_order_insufficient_stock(logged_in_client):
    """재고 부족 시 주문 생성 실패를 테스트합니다."""
    # GIVEN: 재고보다 많은 수량을 주문
    order_items = [{'id': 'P01', 'quantity': 101, 'price': 5000}] # P01 (재고 100개) 101개 주문
    total_amount = 10 * 5000

    # WHEN: 주문 생성 요청
    response = logged_in_client.post('/api/orders', json={
        'items': order_items,
        'total_amount': total_amount
    })

    # THEN: 400 에러 및 메시지 확인 (API에서 400으로 변경됨)
    assert response.status_code == 400
    assert 'Not enough stock' in response.json['error']


def test_create_order_missing_data(logged_in_client):
    """주문 생성 시 필수 데이터가 누락되었을 때 400 에러를 테스트합니다."""
    # WHEN: 'items' 필드가 누락된 주문 데이터를 보낼 때
    response = logged_in_client.post('/api/orders', json={
        'total_amount': 10000
    })

    # THEN: 응답 코드는 400 (Bad Request) 여야 한다.
    assert response.status_code == 400
    assert 'Missing order data' in response.json['error']

def test_order_api_unauthorized(client):
    """로그인하지 않은 상태에서 주문 API 접근 시 401 에러를 테스트합니다."""
    # POST
    response = client.post('/api/orders', json={
        'items': [],
        'total_amount': 0
    })
    assert response.status_code == 401

    # GET
    response = client.get('/api/orders')
    assert response.status_code == 401

    # DELETE /api/order/<id>
    response = client.delete('/api/order/1')
    assert response.status_code == 401

def test_get_orders_empty(logged_in_client):
    """주문 내역이 없을 때 빈 리스트를 반환하는지 테스트합니다."""
    # WHEN: 주문을 생성하지 않고 /api/orders 에 GET 요청을 보낼 때
    response = logged_in_client.get('/api/orders')

    # THEN: 응답 코드는 200 (OK) 이고, 결과는 빈 리스트여야 한다.
    assert response.status_code == 200
    assert response.json == []

def test_get_orders_success(logged_in_client):
    """로그인 후 주문 내역을 성공적으로 조회하는지 테스트합니다."""
    # GIVEN: 거래처 생성
    customer_res = logged_in_client.post('/api/customers', json={'name': '조회용거래처'})
    assert customer_res.status_code == 201
    customer_id = customer_res.json['id']

    # GIVEN: 사용자가 하나의 주문을 생성한 상태
    order_items = [
        {'id': 'P01', 'quantity': 2, 'price': 5000},
    ]
    total_amount = 10000
    logged_in_client.post('/api/orders', json={
        'items': order_items,
        'total_amount': total_amount,
        'customer_id': customer_id
    })

    # WHEN: /api/orders 에 GET 요청을 보낼 때
    response = logged_in_client.get('/api/orders')

    # THEN: 응답 코드는 200 (OK) 이고, 주문 내역이 정확해야 한다.
    assert response.status_code == 200
    orders = response.json
    assert len(orders) == 1

    order = orders[0]
    assert order['total_amount'] == total_amount
    assert order['customer_id'] == customer_id
    assert order['customer_name'] == '조회용거래처'
    assert order['status'] == 'completed'
    assert len(order['items']) == 1
    item = order['items'][0]
    assert item['product_id'] == 'P01'
    assert item['product_name'] == '근위'
    assert item['quantity'] == 2
    assert item['price_per_unit'] == 5000

def test_cancel_order_success(logged_in_client):
    """로그인 후 주문을 성공적으로 취소하는지 테스트합니다."""
    # GIVEN: 사용자가 P01 상품 1개를 주문하여 재고가 감소한 상태
    create_response = logged_in_client.post('/api/orders', json={
        'items': [{'id': 'P01', 'quantity': 1, 'price': 5000}],
        'total_amount': 5000
    })
    order_id = create_response.json['order_id']
    with app.app_context():
        product_before_cancel = Product.query.get('P01')
        assert product_before_cancel.stock_quantity == 99 # 100 - 1

    # WHEN: 생성된 주문에 대해 DELETE 요청을 보낼 때
    response = logged_in_client.delete(f'/api/order/{order_id}')

    # THEN: 응답 코드는 200 (OK) 이고, 주문 상태가 'cancelled'로 변경되어야 한다.
    assert response.status_code == 200
    assert response.json['status'] == 'cancelled'
    assert 'Order cancelled successfully' in response.json['message']

    # 추가 검증: DB에서 주문 상태가 'cancelled'로 변경되고 재고가 복구되었는지 확인
    with app.app_context():
        order = Order.query.get(order_id)
        assert order is not None
        assert order.status == 'cancelled'

        product_after_cancel = Product.query.get('P01')
        assert product_after_cancel.stock_quantity == 100 # 재고 복구

def test_cancel_order_not_found(logged_in_client):
    """존재하지 않는 주문 ID로 취소 시 404 에러를 테스트합니다."""
    response = logged_in_client.delete('/api/order/99999') # 존재하지 않을 ID
    assert response.status_code == 404

def test_cancel_already_cancelled_order_failure(logged_in_client):
    """이미 취소된 주문을 다시 취소하려고 할 때 실패하는지 테스트합니다."""
    # GIVEN: 주문이 생성된 후 즉시 취소됨
    create_response = logged_in_client.post('/api/orders', json={
        'items': [{'id': 'P01', 'quantity': 1, 'price': 5000}],
        'total_amount': 5000
    })
    order_id = create_response.json['order_id']
    logged_in_client.delete(f'/api/order/{order_id}') # 첫 번째 취소

    # WHEN: 동일한 주문을 다시 취소하려고 시도할 때
    response = logged_in_client.delete(f'/api/order/{order_id}')

    # THEN: 요청은 400 (Bad Request) 에러를 반환해야 한다.
    assert response.status_code == 400
    assert 'Order is already cancelled' in response.json['error']

def test_cancel_order_forbidden(client):
    """다른 사용자의 주문을 취소 시 404 에러를 테스트합니다."""
    # GIVEN: 사용자 A가 주문을 생성
    client.post('/api/auth/register', json={'username': 'user_a', 'password': 'password_a'})
    client.post('/api/auth/login', json={'username': 'user_a', 'password': 'password_a'})
    create_response = client.post('/api/orders', json={
        # P01 재고가 100개이므로 1개 주문은 성공
        'items': [{'id': 'P01', 'quantity': 1, 'price': 5000}],
        # 이 테스트는 별도의 클라이언트를 사용하므로 P01 재고는 100개로 초기화된 상태
        # 따라서 주문 생성은 성공할 것임
        'total_amount': 5000
    })
    order_id_a = create_response.json['order_id']
    client.post('/api/auth/logout') # 사용자 A 로그아웃

    # GIVEN: 사용자 B가 로그인
    client.post('/api/auth/register', json={'username': 'user_b', 'password': 'password_b'})
    client.post('/api/auth/login', json={'username': 'user_b', 'password': 'password_b'})

    # WHEN: 사용자 B가 사용자 A의 주문을 취소하려고 할 때
    response = client.delete(f'/api/order/{order_id_a}')

    # THEN: 응답 코드는 404 (Not Found) 여야 한다. (정보 노출 방지)
    assert response.status_code == 404

# --- Phase 4: 매출 집계 API 테스트 ---

def test_get_daily_sales_success(logged_in_client):
    """특정 날짜의 일일 매출을 성공적으로 조회하는지 테스트합니다."""
    # GIVEN: 특정 날짜에 주문을 생성
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        
        # 오늘 날짜의 주문 (P01, P02 재고 100개에서 사용)
        today = datetime.datetime.utcnow().date()
        # 주문 생성 시 OrderItem도 함께 생성되어야 재고 감소 로직이 작동하지만,
        # 이 테스트는 Order 모델만 직접 생성하므로 재고 감소는 일어나지 않음.
        # 매출 집계 테스트이므로 재고 감소는 부수 효과로 간주하고, OrderItem 생성은 생략.
        order1_today = Order(total_amount=1000, user_id=user.id, order_date=datetime.datetime.combine(today, datetime.time(10, 0, 0))) 
        order2_today = Order(total_amount=2500, user_id=user.id, order_date=datetime.datetime.combine(today, datetime.time(14, 30, 0))) 
        # 다른 날짜의 주문 (필터링되어야 함)
        yesterday = today - datetime.timedelta(days=1)
        order_yesterday = Order(total_amount=5000, user_id=user.id, order_date=datetime.datetime.combine(yesterday, datetime.time(11, 0, 0)))
        
        db.session.add_all([order1_today, order2_today, order_yesterday])
        db.session.commit()

    # WHEN: 오늘 날짜로 일일 매출 조회 요청
    response = logged_in_client.get(f'/api/sales/daily?date={today.isoformat()}')

    # THEN: 응답 코드는 200 (OK) 이고, 매출이 정확해야 한다.
    assert response.status_code == 200
    assert response.json['date'] == today.isoformat()
    assert response.json['total_sales'] == 3500 # 1000 + 2500

def test_get_daily_sales_no_sales(logged_in_client):
    """특정 날짜에 매출이 없을 때 0을 반환하는지 테스트합니다."""
    # GIVEN: 어떤 주문도 생성되지 않은 상태 (fixture가 초기화하므로)

    # WHEN: 매출이 없는 날짜로 일일 매출 조회 요청
    no_sales_date = (datetime.datetime.utcnow() + datetime.timedelta(days=10)).date() # 미래의 날짜
    response = logged_in_client.get(f'/api/sales/daily?date={no_sales_date.isoformat()}')

    # THEN: 응답 코드는 200 (OK) 이고, 매출은 0이어야 한다.
    assert response.status_code == 200
    assert response.json['date'] == no_sales_date.isoformat()
    assert response.json['total_sales'] == 0

def test_get_daily_sales_default_today(logged_in_client):
    """날짜 파라미터 없이 요청 시 오늘 날짜의 매출을 반환하는지 테스트합니다."""
    # GIVEN: 오늘 날짜에 주문을 생성
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        today = datetime.datetime.utcnow().date() # UTC 기준 오늘
        # 이 테스트도 OrderItem 생성 없이 Order만 생성하므로 재고 감소는 일어나지 않음.
        order_today = Order(total_amount=700, user_id=user.id, order_date=datetime.datetime.combine(today, datetime.time(12, 0, 0)))
        db.session.add(order_today)
        db.session.commit()

    # WHEN: 날짜 파라미터 없이 일일 매출 조회 요청
    response = logged_in_client.get('/api/sales/daily')

    # THEN: 응답 코드는 200 (OK) 이고, 오늘 날짜의 매출이 정확해야 한다.
    assert response.status_code == 200
    assert response.json['date'] == today.isoformat()
    assert response.json['total_sales'] == 700

def test_get_daily_sales_unauthorized(client):
    """로그인하지 않은 상태에서 일일 매출 조회 시 401 에러를 테스트합니다."""
    # WHEN: 로그인하지 않은 상태에서 /api/sales/daily 에 GET 요청을 보낼 때
    response = client.get('/api/sales/daily')

    # THEN: 응답 코드는 401 (Unauthorized) 여야 한다.
    assert response.status_code == 401

def test_get_daily_sales_invalid_date_format(logged_in_client):
    """잘못된 날짜 형식으로 요청 시 400 에러를 테스트합니다."""
    # WHEN: 잘못된 날짜 형식으로 일일 매출 조회 요청
    response = logged_in_client.get('/api/sales/daily?date=2023/10/26') # 잘못된 형식

    # THEN: 응답 코드는 400 (Bad Request) 여야 한다.
    assert response.status_code == 400
    assert 'Invalid date format' in response.json['error']

# --- Phase 5: 월별 매출 집계 API 테스트 ---

def test_get_monthly_sales_success(logged_in_client):
    """특정 월의 매출을 성공적으로 조회하는지 테스트합니다."""
    # GIVEN: 다른 월에 여러 주문을 생성
    with app.app_context(): # 이 테스트도 OrderItem 생성 없이 Order만 생성하므로 재고 감소는 일어나지 않음.
        user = User.query.filter_by(username='testuser').first()

        # 2023년 10월 주문
        order1_oct = Order(total_amount=1000, user_id=user.id, order_date=datetime.datetime(2023, 10, 15, 10, 0, 0))
        order2_oct = Order(total_amount=2500, user_id=user.id, order_date=datetime.datetime(2023, 10, 20, 14, 30, 0))

        # 2023년 11월 주문 (필터링되어야 함)
        order1_nov = Order(total_amount=5000, user_id=user.id, order_date=datetime.datetime(2023, 11, 5, 11, 0, 0))

        db.session.add_all([order1_oct, order2_oct, order1_nov])
        db.session.commit()

    # WHEN: 2023년 10월로 월별 매출 조회 요청
    response = logged_in_client.get('/api/sales/monthly?year=2023&month=10')

    # THEN: 응답 코드는 200 (OK) 이고, 매출이 정확해야 한다.
    assert response.status_code == 200
    assert response.json['year'] == 2023
    assert response.json['month'] == 10
    assert response.json['total_sales'] == 3500 # 1000 + 2500

def test_get_monthly_sales_no_sales(logged_in_client):
    """특정 월에 매출이 없을 때 0을 반환하는지 테스트합니다."""
    # GIVEN: 어떤 주문도 생성되지 않은 상태 (fixture가 초기화하므로)

    # WHEN: 매출이 없는 월로 월별 매출 조회 요청 (예: 2024년 1월)
    response = logged_in_client.get('/api/sales/monthly?year=2024&month=1')

    # THEN: 응답 코드는 200 (OK) 이고, 매출은 0이어야 한다.
    assert response.status_code == 200
    assert response.json['year'] == 2024
    assert response.json['month'] == 1
    assert response.json['total_sales'] == 0

def test_get_monthly_sales_unauthorized(client):
    """로그인하지 않은 상태에서 월별 매출 조회 시 401 에러를 테스트합니다."""
    # WHEN: 로그인하지 않은 상태에서 /api/sales/monthly 에 GET 요청을 보낼 때
    response = client.get('/api/sales/monthly?year=2023&month=10')

    # THEN: 응답 코드는 401 (Unauthorized) 여야 한다.
    assert response.status_code == 401

def test_get_monthly_sales_invalid_params(logged_in_client):
    """잘못된 파라미터로 요청 시 400 에러를 테스트합니다."""
    # WHEN: year 파라미터 누락
    response = logged_in_client.get('/api/sales/monthly?month=10')
    assert response.status_code == 400
    assert 'Year and month are required' in response.json['error']

    # WHEN: month 파라미터 누락
    response = logged_in_client.get('/api/sales/monthly?year=2023')
    assert response.status_code == 400
    assert 'Year and month are required' in response.json['error']

    # WHEN: 잘못된 year 형식
    response = logged_in_client.get('/api/sales/monthly?year=abc&month=10')
    assert response.status_code == 400
    assert 'Invalid year or month format' in response.json['error']

    # WHEN: 잘못된 month 형식
    response = logged_in_client.get('/api/sales/monthly?year=2023&month=xyz')
    assert response.status_code == 400
    assert 'Invalid year or month format' in response.json['error']

    # WHEN: 유효하지 않은 month 값 (범위 초과)
    response = logged_in_client.get('/api/sales/monthly?year=2023&month=13')
    assert response.status_code == 400
    assert 'Invalid year or month value' in response.json['error']

def test_get_orders_by_date_range(logged_in_client):
    """특정 기간의 주문 내역을 성공적으로 조회하는지 테스트합니다."""
    # GIVEN: 다른 날짜에 여러 주문을 생성
    from app import Order, User
    with app.app_context(): # 이 테스트도 OrderItem 생성 없이 Order만 생성하므로 재고 감소는 일어나지 않음.
        user = User.query.filter_by(username='testuser').first()

        # Order 1: 어제
        order1_date = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        order1 = Order(total_amount=1000, user_id=user.id, order_date=order1_date)

        # Order 2: 오늘
        order2_date = datetime.datetime.utcnow()
        order2 = Order(total_amount=2000, user_id=user.id, order_date=order2_date)

        # Order 3: 내일
        order3_date = datetime.datetime.utcnow() + datetime.timedelta(days=1)
        order3 = Order(total_amount=3000, user_id=user.id, order_date=order3_date)

        db.session.add_all([order1, order2, order3])
        db.session.commit()
        # 테스트에서 사용할 ID들을 변수에 저장
        order1_id, order2_id, order3_id = order1.id, order2.id, order3.id

    # WHEN: 어제부터 오늘까지의 기간으로 GET 요청
    start_str = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    end_str = datetime.datetime.utcnow().strftime('%Y-%m-%d')

    response = logged_in_client.get(f'/api/orders?start_date={start_str}&end_date={end_str}')

    # THEN: 2개의 주문(어제, 오늘)이 반환되어야 함
    assert response.status_code == 200
    data = response.json
    assert len(data) == 2
    returned_ids = {order['id'] for order in data}
    assert order1_id in returned_ids
    assert order2_id in returned_ids
    assert order3_id not in returned_ids

    # WHEN: 잘못된 날짜 형식으로 요청
    response_bad_format = logged_in_client.get('/api/orders?start_date=not-a-date')
    assert response_bad_format.status_code == 400
    assert 'Invalid date format' in response_bad_format.json['error']

# --- Phase 6: 거래처(Customer) API 테스트 ---

def test_customer_api_unauthorized(client):
    """로그인하지 않고 거래처 API 접근 시 401 에러를 테스트합니다."""
    response = client.get('/api/customers')
    assert response.status_code == 401
    response = client.post('/api/customers', json={'name': '새거래처'})
    assert response.status_code == 401
    response = client.put('/api/customer/1', json={'name': '수정된거래처'})
    assert response.status_code == 401
    response = client.delete('/api/customer/1')
    assert response.status_code == 401

def test_customer_crud_flow(logged_in_client):
    """거래처 생성, 전체 조회, 수정, 삭제의 전체 흐름을 테스트합니다."""
    # 1. Create a customer
    customer_data = {'name': '마켓봄', 'phone_number': '010-1234-5678', 'address': '서울시 강남구'}
    create_response = logged_in_client.post('/api/customers', json=customer_data)
    assert create_response.status_code == 201
    created_data = create_response.json
    assert created_data['name'] == '마켓봄'
    customer_id = created_data['id']

    # 2. Get all customers and verify the new one is there
    get_response = logged_in_client.get('/api/customers')
    assert get_response.status_code == 200
    customers = get_response.json
    assert len(customers) == 1
    assert customers[0]['name'] == '마켓봄'
    assert customers[0]['id'] == customer_id

    # 3. Update the customer
    update_data = {'name': '마켓봄(수정)', 'phone_number': '02-111-2222', 'address': '서울시 서초구'}
    update_response = logged_in_client.put(f'/api/customer/{customer_id}', json=update_data)
    assert update_response.status_code == 200
    assert update_response.json['message'] == 'Customer updated successfully'

    # Verify the update by checking the database
    with app.app_context():
        updated_customer = Customer.query.get(customer_id)
        assert updated_customer.name == '마켓봄(수정)'
        assert updated_customer.address == '서울시 서초구'

    # 4. Delete the customer
    delete_response = logged_in_client.delete(f'/api/customer/{customer_id}')
    assert delete_response.status_code == 204

    # Verify the deletion
    with app.app_context():
        deleted_customer = Customer.query.get(customer_id)
        assert deleted_customer is None

def test_create_customer_missing_name(logged_in_client):
    """이름 없이 거래처 생성 시 400 에러를 테스트합니다."""
    response = logged_in_client.post('/api/customers', json={'phone_number': '1234'})
    assert response.status_code == 400
    assert 'Customer name is required' in response.json['error']

def test_access_other_user_customer(client):
    """다른 사용자의 거래처에 접근할 수 없는지 테스트합니다."""
    # GIVEN: 사용자 A가 거래처 생성
    client.post('/api/auth/register', json={'username': 'user_a', 'password': 'password_a'})
    client.post('/api/auth/login', json={'username': 'user_a', 'password': 'password_a'})
    customer_res = client.post('/api/customers', json={'name': 'A의 거래처'})
    customer_id_a = customer_res.json['id']
    client.post('/api/auth/logout')

    # GIVEN: 사용자 B가 로그인
    client.post('/api/auth/register', json={'username': 'user_b', 'password': 'password_b'})
    client.post('/api/auth/login', json={'username': 'user_b', 'password': 'password_b'})

    # WHEN: 사용자 B가 사용자 A의 거래처에 접근 시도
    put_response = client.put(f'/api/customer/{customer_id_a}', json={'name': '해킹시도'})
    delete_response = client.delete(f'/api/customer/{customer_id_a}')

    # THEN: 404 Not Found 응답을 받아야 함
    assert put_response.status_code == 404
    assert delete_response.status_code == 404

# --- [신규 추가] Phase 7: 외상/미수금 관리 API 테스트 ---
def test_create_credit_order_updates_receivable(logged_in_client):
    """'외상' 주문 시 거래처의 외상 잔액이 정확히 증가하는지 테스트합니다."""
    # GIVEN: 외상 거래를 위한 거래처 생성
    customer_res = logged_in_client.post('/api/customers', json={'name': '외상거래처'})
    assert customer_res.status_code == 201
    customer_id = customer_res.json['id']

    # GIVEN: 주문 데이터
    order_data = {
        'items': [{'id': 'P01', 'quantity': 10, 'price': 5000}],
        'total_amount': 50000,
        'customer_id': customer_id,
        'payment_method': 'credit'  # 결제 방식을 '외상'으로 지정
    }
    
    # WHEN: 외상으로 주문 생성
    order_res = logged_in_client.post('/api/orders', json=order_data)
    
    # THEN: 주문은 성공적으로 생성되어야 함
    assert order_res.status_code == 201
    
    # 추가 검증: DB에서 거래처의 외상 잔액이 주문 금액만큼 증가했는지 확인
    with app.app_context():
        customer = Customer.query.get(customer_id)
        assert customer.receivable_balance == 50000

def test_create_credit_order_without_customer_fails(logged_in_client):
    """거래처 지정 없이 '외상' 주문 시 실패하는지 테스트합니다."""
    # GIVEN: 거래처 ID가 없는 외상 주문 데이터
    order_data = {
        'items': [{'id': 'P01', 'quantity': 1, 'price': 5000}],
        'total_amount': 5000,
        'payment_method': 'credit' # customer_id 누락
    }
    
    # WHEN: 주문 생성 요청
    response = logged_in_client.post('/api/orders', json=order_data)
    
    # THEN: 400 Bad Request 에러가 발생해야 함
    assert response.status_code == 400
    assert 'Customer must be selected' in response.json['error']

def test_record_payment_updates_receivable(logged_in_client):
    """입금 처리 시 외상 잔액이 정확히 감소하는지 테스트합니다."""
    # GIVEN: 외상 잔액이 50000원인 거래처
    customer_res = logged_in_client.post('/api/customers', json={'name': '입금테스트거래처'})
    customer_id = customer_res.json['id']
    logged_in_client.post('/api/orders', json={
        'items': [{'id': 'P01', 'quantity': 10, 'price': 5000}],
        'total_amount': 50000,
        'customer_id': customer_id,
        'payment_method': 'credit'
    })

    # WHEN: 해당 거래처에 대해 30000원을 입금 처리
    payment_res = logged_in_client.post(f'/api/customer/{customer_id}/payments', json={
        'amount': 30000,
        'payment_method': 'cash',
        'notes': '일부 입금'
    })
    
    # THEN: 입금 처리는 성공해야 함
    assert payment_res.status_code == 201
    assert payment_res.json['new_balance'] == 20000 # 50000 - 30000

    # 추가 검증: DB에서 거래처의 외상 잔액과 입금 내역 확인
    with app.app_context():
        customer = Customer.query.get(customer_id)
        assert customer.receivable_balance == 20000
        
        transactions = PaymentTransaction.query.filter_by(customer_id=customer_id).all()
        assert len(transactions) == 1
        assert transactions[0].amount == 30000
        assert transactions[0].notes == '일부 입금'

def test_cancel_credit_order_reverts_receivable(logged_in_client):
    """외상 주문 취소 시 외상 잔액이 원상 복구되는지 테스트합니다."""
    # GIVEN: 외상 잔액이 50000원인 거래처
    customer_res = logged_in_client.post('/api/customers', json={'name': '주문취소거래처'})
    customer_id = customer_res.json['id']
    order_res = logged_in_client.post('/api/orders', json={
        'items': [{'id': 'P01', 'quantity': 10, 'price': 5000}],
        'total_amount': 50000,
        'customer_id': customer_id,
        'payment_method': 'credit'
    })
    order_id = order_res.json['order_id']

    # WHEN: 해당 외상 주문을 취소
    cancel_res = logged_in_client.delete(f'/api/order/{order_id}')

    # THEN: 주문 취소는 성공해야 함
    assert cancel_res.status_code == 200
    
    # 추가 검증: DB에서 거래처의 외상 잔액이 0으로 복구되었는지 확인
    with app.app_context():
        customer = Customer.query.get(customer_id)
        assert customer.receivable_balance == 0

def test_get_customer_receivables_list(logged_in_client):
    """외상 잔액이 있는 거래처 목록만 정확히 조회되는지 테스트합니다."""
    # GIVEN: 거래처 3개 생성 (1개는 잔액 0, 2개는 잔액 > 0)
    c1_res = logged_in_client.post('/api/customers', json={'name': '무외상거래처'}) # 잔액 0
    c2_res = logged_in_client.post('/api/customers', json={'name': '소액외상거래처'}) # 잔액 > 0
    c3_res = logged_in_client.post('/api/customers', json={'name': '고액외상거래처'}) # 잔액 > 0
    
    logged_in_client.post('/api/orders', json={'items': [], 'total_amount': 10000, 'customer_id': c2_res.json['id'], 'payment_method': 'credit'})
    logged_in_client.post('/api/orders', json={'items': [], 'total_amount': 20000, 'customer_id': c3_res.json['id'], 'payment_method': 'credit'})

    # WHEN: 외상대금 거래처 목록 조회
    response = logged_in_client.get('/api/customers/receivables')
    
    # THEN: 외상 잔액이 있는 2개의 거래처만 반환되어야 함
    assert response.status_code == 200
    receivables = response.json
    assert len(receivables) == 2
    
    customer_names = {c['name'] for c in receivables}
    assert '소액외상거래처' in customer_names
    assert '고액외상거래처' in customer_names
    assert '무외상거래처' not in customer_names
        
# --- [신규 추가] Phase 8: 매입 관리 API 테스트 ---
def test_supplier_crud_flow(logged_in_client):
    """공급처 생성, 조회, 수정, 삭제의 전체 흐름을 테스트합니다."""
    # 1. Create
    supplier_data = {'name': '싱싱유통', 'contact_person': '김사장', 'phone_number': '010-8888-9999'}
    create_res = logged_in_client.post('/api/suppliers', json=supplier_data)
    assert create_res.status_code == 201
    supplier_id = create_res.json['id']

    # 2. Read
    get_res = logged_in_client.get('/api/suppliers')
    assert get_res.status_code == 200
    assert len(get_res.json) == 1
    assert get_res.json[0]['name'] == '싱싱유통'

    # 3. Update
    update_data = {'name': '싱싱유통(수정)', 'contact_person': '박사장'}
    update_res = logged_in_client.put(f'/api/supplier/{supplier_id}', json=update_data)
    assert update_res.status_code == 200

    # 4. Delete
    delete_res = logged_in_client.delete(f'/api/supplier/{supplier_id}')
    assert delete_res.status_code == 204
    assert Supplier.query.get(supplier_id) is None

def test_create_purchase_order_success_and_stock_increases(logged_in_client):
    """매입 기록 시 상품 재고가 정확히 증가하는지 테스트합니다."""
    # GIVEN: P01(근위) 상품의 초기 재고는 100개
    with app.app_context():
        product = Product.query.get('P01')
        assert product.stock_quantity == 100

    # GIVEN: 매입 데이터
    purchase_data = {
        'supplier_id': None,
        'items': [
            {'product_id': 'P01', 'quantity': 50, 'cost_per_unit': 4500}
        ]
    }

    # WHEN: 새로운 매입을 기록
    response = logged_in_client.post('/api/purchases', json=purchase_data)

    # THEN: 요청은 성공해야 함
    assert response.status_code == 201
    assert 'Purchase recorded successfully' in response.json['message']

    # 추가 검증: P01 상품의 재고가 150개로 증가했는지 확인
    with app.app_context():
        product_after = Product.query.get('P01')
        assert product_after.stock_quantity == 150 # 100 + 50

def test_delete_supplier_with_purchase_orders_fails(logged_in_client):
    """매입 기록이 있는 공급처는 삭제할 수 없는지 테스트합니다."""
    # GIVEN: 공급처 생성 및 해당 공급처로 매입 기록 생성
    supplier_res = logged_in_client.post('/api/suppliers', json={'name': '삭제테스트공급처'})
    supplier_id = supplier_res.json['id']
    logged_in_client.post('/api/purchases', json={'supplier_id': supplier_id, 'items': []})

    # WHEN: 해당 공급처를 삭제하려고 시도
    delete_res = logged_in_client.delete(f'/api/supplier/{supplier_id}')

    # THEN: 400 Bad Request 에러가 발생해야 함
    assert delete_res.status_code == 400
    assert 'Cannot delete supplier' in delete_res.json['error']