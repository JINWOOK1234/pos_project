// static/script.js
document.addEventListener('DOMContentLoaded', () => {
    // --- 전역 변수 및 상태 관리 ---
    let currentState = 'SELECT_CUSTOMER'; // 'SELECT_CUSTOMER', 'SELECT_PRODUCT', 'PAYMENT'
    let currentCustomer = null;
    let currentProduct = null;
    let cart = [];

    // --- DOM 요소 가져오기 ---
    const gridContainer = document.getElementById('main-grid');
    const selectedCustomerSpan = document.getElementById('selected-customer');
    const orderItemsTbody = document.getElementById('order-items');
    const totalQuantitySpan = document.getElementById('total-quantity');
    const totalAmountSpan = document.getElementById('total-amount');
    const paymentBtn = document.getElementById('payment-btn');
    const paymentControls = document.getElementById('payment-controls');
    const slipNumberSpan = document.getElementById('slip-number');

    // --- 모달 관련 DOM 요소 ---
    const modal = document.getElementById('quantity-modal');
    const modalProductName = document.getElementById('modal-product-name');
    const quantityInput = document.getElementById('quantity-input');
    const priceDisplay = document.getElementById('modal-price-display');
    const keypad = document.querySelector('.keypad');
    
    // --- 초기화 함수 ---
    async function initialize() {
        const response = await fetch('/api/customers');
        const customers = await response.json();
        displayCustomers(customers);
    }

    // --- 화면 표시(Display) 함수 ---
    function displayCustomers(customers) {
        gridContainer.innerHTML = '';
        customers.forEach(customer => {
            const button = document.createElement('button');
            button.innerText = customer.name;
            button.dataset.customerName = customer.name;
            button.addEventListener('click', handleCustomerSelect);
            gridContainer.appendChild(button);
        });
    }

    async function displayProducts() {
        gridContainer.innerHTML = '';
        const response = await fetch('/api/products');
        const products = await response.json();
        products.forEach(product => {
            const button = document.createElement('button');
            button.innerText = product.name;
            button.dataset.productId = product.id;
            button.dataset.productName = product.name;
            button.addEventListener('click', handleProductSelect);
            gridContainer.appendChild(button);
        });
    }

    // --- 이벤트 핸들러 함수 ---
    function handleCustomerSelect(event) {
        currentCustomer = event.target.dataset.customerName;
        selectedCustomerSpan.innerText = currentCustomer;
        currentState = 'SELECT_PRODUCT';
        displayProducts();
        paymentBtn.style.display = 'block';
    }

    function handleProductSelect(event) {
        currentProduct = {
            id: event.target.dataset.productId,
            name: event.target.dataset.productName
        };
        openModal();
    }
    
    // --- 장바구니(Cart) 렌더링 함수 ---
    function renderCart() {
        orderItemsTbody.innerHTML = '';
        let totalQuantity = 0;
        let totalAmount = 0;
        
        cart.forEach((item, index) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${index + 1}</td>
                <td>${item.name}</td>
                <td>${item.quantity}${item.unit}</td>
                <td>${item.price.toLocaleString()}</td>
                <td>${item.total.toLocaleString()}</td>
                <td></td>
            `;
            orderItemsTbody.appendChild(row);
            totalQuantity += parseFloat(item.quantity);
            totalAmount += item.total;
        });

        totalQuantitySpan.innerText = totalQuantity;
        totalAmountSpan.innerText = totalAmount.toLocaleString();
    }

    // --- 모달 관련 함수 ---
    function openModal() {
        modalProductName.innerText = currentProduct.name;
        quantityInput.value = '';
        priceDisplay.innerText = '';
        modal.style.display = 'flex';
    }

    function closeModal() {
        modal.style.display = 'none';
    }

    keypad.addEventListener('click', async (event) => {
        const button = event.target;
        const buttonValue = button.innerText;

        if (!isNaN(buttonValue) || buttonValue === '00') {
            quantityInput.value += buttonValue;
        } else if (button.classList.contains('unit-btn')) {
            const unit = button.dataset.unit;
            const quantity = quantityInput.value.replace(/[^0-9.]/g, '');
            if (!quantity) return;
            
            quantityInput.value = quantity + unit;
            
            // API로 가격 조회
            const response = await fetch(`/api/price?productId=${currentProduct.id}&unit=${unit}`);
            if(response.ok) {
                const data = await response.json();
                priceDisplay.innerText = `단가: ${data.price.toLocaleString()}원`;
                priceDisplay.dataset.price = data.price;
            } else {
                priceDisplay.innerText = '단가 정보 없음';
                priceDisplay.dataset.price = '0';
            }
        } else if (button.classList.contains('clear-btn')) {
            quantityInput.value = '';
            priceDisplay.innerText = '';
        } else if (button.classList.contains('back-btn')) {
            quantityInput.value = quantityInput.value.slice(0, -1);
        }
    });

    document.getElementById('modal-confirm-btn').addEventListener('click', () => {
        const quantity = parseFloat(quantityInput.value.replace(/[^0-9.]/g, ''));
        const unit = quantityInput.value.replace(/[0-9.]/g, '');
        const price = parseFloat(priceDisplay.dataset.price);

        if (quantity && unit && price) {
            cart.push({
                ...currentProduct,
                quantity: quantity,
                unit: unit,
                price: price,
                total: quantity * price
            });
            renderCart();
            closeModal();
        } else {
            alert('수량, 단위, 가격 정보가 올바르지 않습니다.');
        }
    });
    
    document.getElementById('modal-close-btn').addEventListener('click', closeModal);

    // --- 결제 관련 이벤트 핸들러 ---
    paymentBtn.addEventListener('click', () => {
        currentState = 'PAYMENT';
        gridContainer.style.display = 'none';
        paymentControls.style.display = 'block';
        paymentBtn.style.display = 'none';
    });
    
    document.getElementById('back-to-sell-btn').addEventListener('click', () => {
        currentState = 'SELECT_PRODUCT';
        gridContainer.style.display = 'grid';
        paymentControls.style.display = 'none';
        paymentBtn.style.display = 'block';
    });
    
    document.getElementById('complete-order-btn').addEventListener('click', async () => {
        if(cart.length === 0) {
            alert('주문 내역이 없습니다.');
            return;
        }

        const orderData = {
            customer: currentCustomer,
            items: cart,
            totalAmount: cart.reduce((sum, item) => sum + item.total, 0)
        };

        const response = await fetch('/api/order', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(orderData),
        });

        if(response.ok) {
            const result = await response.json();
            slipNumberSpan.innerText = result.slip_number;
            alert(`주문 완료! 전표번호: ${result.slip_number}\n영수증/작업서를 발행할 수 있습니다.`);
            // 초기화
            cart = [];
            renderCart();
            document.getElementById('back-to-sell-btn').click();
        } else {
            alert('주문 처리 중 오류가 발생했습니다.');
        }
    });

    // --- 애플리케이션 시작 ---
    initialize();
});