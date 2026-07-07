class CoffeeApp { 
    constructor() {
        this.currentScreen = 'loading';
        this.profileType = null;
        this.history = [];
        this.selectedDrink = null;
        this.selectedSyrup = null;
        this.couponScanner = null;
        this.scannedFlyerData = null;
        
        console.log('КОНСТРУКТОР ЗАПУЩЕН');
        this.init();
    }
    
    init() {
        console.log('INIT ЗАПУЩЕН');

        const tgWebApp = window.Telegram?.WebApp;
        const maxWebApp = window.WebApp;

        console.log('1. Telegram WebApp exists:', !!tgWebApp);
        console.log('2. MAX WebApp exists:', !!maxWebApp);
        
        if (window.WebApp) {
            console.log('MAX WebApp detected');
            this.tg = window.WebApp;
            this.tg.ready?.();
            this.tg.expand?.();

            this.tgUser = this.tg.initDataUnsafe?.user || null;
            this.messanger = 'max';

            if (this.tgUser != null) {
                console.log('ЗАПУСК loadApp()');
                this.hideLoadingScreen()
                this.loadApp();
            } else{
                console.log('Telegram WebApp найден');
                this.tg = window.Telegram.WebApp;
                this.tg.ready();
                this.tg.expand();
    
                this.tg.setBackgroundColor('#FFD1DC');
                this.tg.setHeaderColor('#D8BFD8');
    
                this.tgUser = this.tg.initDataUnsafe?.user;
                this.messanger = 'telegram';
                console.log('tgUser:', this.tgUser);
                console.log('tg profile:', this.messanger);
            
                this.tg.initDataUnsafe.start_param = this.tg.initDataUnsafe?.start_param || '';
                console.log('ЗАПУСК loadApp()');
                this.hideLoadingScreen()
                this.loadApp();
            }

            console.log('MAX user:', this.tgUser);
            console.log('MAX profile:', this.messanger);

        }else{
            console.error('Telegram WebApp НЕ НАЙДЕН!');
        }
    }

    hideLoadingScreen() {
        const loadingScreen = document.getElementById('loading-screen');
        if (loadingScreen) {
            loadingScreen.classList.add('hidden');
            console.log('Экран загрузки скрыт');
        }
    }
    
    async loadApp() {
        try {
            console.log('loadApp() НАЧАЛО');
            
            const tgId = this.tgUser?.id || this.extractTgIdFromUrl() || this.tgUser;
            const messanger = this.messanger;
            console.log('tgId:', tgId);
            
            if (!tgId) {
                console.error('tgId не найден!');
                console.error('tgUser:', this.tgUser);
                console.error('URL params:', window.location.search);
                
                this.showToast('Ошибка: не удалось получить данные пользователя');
                this.showScreen('auth-screen');
                return;
            }
            
            console.log('Отправка запроса на аутентификацию...');
            console.log('tg_id:', tgId);
            
            const startTime = Date.now();
            const response = await api.authenticate(tgId, messanger);
            const endTime = Date.now();
            
            console.log('Ответ получен за ' + (endTime - startTime) + 'ms');
            console.log('Ответ от сервера:', response);
            
            if (!response) {
                console.error('Пустой ответ от сервера!');
                this.showToast('Ошибка: сервер не ответил');
                this.showScreen('auth-screen');
                return;
            }
            
            console.log('response.authenticated:', response.authenticated);
            console.log('response.profile_type:', response.profile_type);
            console.log('response.user_data:', response.user_data);
            
            if (response.authenticated) {
                console.log('Пользователь аутентифицирован!');
                
                this.profileType = response.profile_type;
                this.userData = response.user_data;
                
                console.log('profileType:', this.profileType);
                console.log('userData:', this.userData);
                
                const validTypes = ['admin', 'smm', 'employee', 'user'];
                if (!validTypes.includes(this.profileType)) {
                    console.error('Неверный тип профиля:', this.profileType);
                    this.showToast('Ошибка: неизвестный тип профиля');
                    this.showScreen('auth-screen');
                    return;
                }
                
                console.log('Вызов showProfile...');
                this.showProfile(this.profileType);
                console.log('=== loadApp() ЗАВЕРШЕН ===');
            } else {
                console.log('Пользователь не найден');
                this.showScreen('auth-screen');
            }
        } catch (error) {
            console.error('КРИТИЧЕСКАЯ ОШИБКА В loadApp():', error);
            console.error('Тип ошибки:', error.name);
            console.error('Сообщение:', error.message);
            console.error('Стек:', error.stack);
            
            this.showToast('Ошибка загрузки приложения: ' + error.message);
            this.showScreen('auth-screen');
        }
    }
    
    showProfile(profileType) {
        console.log('showProfile() вызван');
        console.log('profileType:', profileType);
        
        switch(profileType) {
            case 'admin':
                console.log('Переход на admin-profile-screen');
                this.showScreen('admin-profile-screen');
                
                const adminNameEl = document.getElementById('admin-name');
                console.log('admin-name element:', adminNameEl);
                
                if (adminNameEl && this.userData?.name) {
                    adminNameEl.textContent = this.userData.name;
                    console.log('admin-name установлен:', this.userData.name);
                } else {
                    console.error('admin-name element не найден или нет userData.name');
                }
                break;
                
            case 'smm':
            case 'employee':
                console.log('Переход на employee-profile-screen');
                this.showScreen('employee-profile-screen');
                
                const employeeNameEl = document.getElementById('employee-name');
                console.log('employee-name element:', employeeNameEl);
                
                if (employeeNameEl && this.userData?.name) {
                    employeeNameEl.textContent = this.userData.name;
                    console.log('employee-name установлен:', this.userData.name);
                } else {
                    console.error('employee-name element не найден или нет userData.name');
                }
                break;
                
            case 'user':
                console.log('Переход на user-profile-screen');
                this.showScreen('user-profile-screen');
                
                const userNameEl = document.getElementById('user-name');
                const bonusAmountEl = document.getElementById('bonus-amount');
                
                if (userNameEl && this.userData?.full_name) {
                    userNameEl.textContent = this.userData.full_name;
                }
                
                if (bonusAmountEl && this.userData?.bonuses !== undefined) {
                    bonusAmountEl.textContent = this.userData.bonuses;
                }
                break;
                
            default:
                console.error('Неизвестный тип профиля:', profileType);
                this.showScreen('auth-screen');
        }
        
        console.log('showProfile() ЗАВЕРШЕН');
    }
    
    showScreen(screenId) {
        console.log('showScreen() вызван');
        console.log('screenId:', screenId);
        
        const allScreens = document.querySelectorAll('.screen');
        console.log('Найдено экранов:', allScreens.length);
        
        allScreens.forEach(screen => {
            screen.classList.add('hidden');
        });
    
        const targetScreen = document.getElementById(screenId);
        console.log('Целевой экран:', targetScreen);
        
        if (targetScreen) {
            targetScreen.classList.remove('hidden');
            this.currentScreen = screenId;
            console.log('currentScreen установлен:', this.currentScreen);
    
            if (!this.history.includes(screenId)) {
                this.history.push(screenId);
                console.log('Добавлено в историю:', screenId);
            }

            if (screenId === 'coupon-screen') {
                this.loadDrinks();
                this.ensureNextButton('drink-next-btn', 'syrup-screen', '.coupon-container');
            }

            if (screenId === 'syrup-screen') {
                this.loadSyrups();
                this.ensureNextButton('syrup-next-btn', 'qr-screen', '.syrup-container');
            }

            if (screenId === 'discount-selection-screen') {
                this.loadDiscountDrinks();
                this.ensureNextButton('discount-next-btn', 'discount-qr', '.discount-container');
            }            
        } else {
            console.error('Экран с id="' + screenId + '" НЕ НАЙДЕН!');
            console.error('Доступные экраны:', Array.from(allScreens).map(s => s.id));
        }
        
        console.log('showScreen() ЗАВЕРШЕН');
    }
    
    
    async loadDrinks() {
        try {
            console.log('Загрузка списка напитков...');
            
            const drinks = await api.getDrinks();
            console.log('Получены напитки:', drinks);
            
            const drinkGrid = document.getElementById('drink-grid');
            if (!drinkGrid) {
                console.error('Элемент #drink-grid не найден');
                return;
            }

            drinkGrid.innerHTML = '';

            drinks.forEach(drink => {
                const drinkElement = this.createDrinkElement(drink);
                drinkGrid.appendChild(drinkElement);
            });
            
            console.log('Напитки отображены');
        } catch (error) {
            console.error('Ошибка загрузки напитков:', error);
            this.showToast('Ошибка загрузки списка напитков');
        }
    }
    
    createDrinkElement(drink) {
        const drinkElement = document.createElement('div');
        drinkElement.className = 'drink-card';
        drinkElement.dataset.drinkId = drink.id;

        const imageUrl = drink.url && drink.url.startsWith('http') 
            ? drink.url 
            : (drink.url ? `${api.API_BASE_URL}${drink.url}` : null);
        
        drinkElement.innerHTML = `
            <div class="drink-image-container">
                ${imageUrl 
                    ? `<img src="${imageUrl}" alt="${drink.name}" loading="lazy" onerror="this.parentElement.innerHTML='<div class=\\'no-image\\'></div>'">`
                    : `<div class="no-image">📷</div>`
                }
            </div>
            <div class="drink-info">
                <h3>${drink.name}</h3>
                <p class="drink-size">${drink.size}мл</p>
            </div>
            <div class="drink-checkmark">
                <svg class="checkmark" viewBox="0 0 24 24">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                </svg>
            </div>
        `;
    
        drinkElement.addEventListener('click', () => this.selectDrink(drinkElement, drink));
        
        return drinkElement;
    }
    
    selectDrink(drinkElement, drink) {
        console.log('Выбран напиток:', drink);

        document.querySelectorAll('.drink-card').forEach(card => {
            card.classList.remove('selected');
        });

        drinkElement.classList.add('selected');

        this.selectedDrink = drink;

        const nextBtn = document.getElementById('drink-next-btn');
        if (nextBtn) nextBtn.style.display = 'block';
    }

    
    async loadSyrups() {
        try {
            console.log('Загрузка списка сиропов...');
            
            const syrups = await api.getSyrups();
            console.log('Получены сиропы:', syrups);
            
            const syrupGrid = document.getElementById('syrup-grid');
            if (!syrupGrid) {
                console.error('Элемент #syrup-grid не найден');
                return;
            }

            syrupGrid.innerHTML = '';

            syrups.forEach(syrup => {
                const syrupElement = this.createSyrupElement(syrup);
                syrupGrid.appendChild(syrupElement);
            });
            
            console.log('Сиропы отображены');
        } catch (error) {
            console.error('Ошибка загрузки сиропов:', error);
            this.showToast('Ошибка загрузки списка сиропов');
        }
    }
    
    createSyrupElement(syrup) {
        const syrupElement = document.createElement('div');
        syrupElement.className = 'syrup-card';
        syrupElement.dataset.syrupId = syrup.id;

        const imageUrl = syrup.url && syrup.url.startsWith('http') 
            ? syrup.url 
            : (syrup.url ? `${api.API_BASE_URL}${syrup.url}` : null);
        
        syrupElement.innerHTML = `
            <div class="syrup-image-container">
                ${imageUrl 
                    ? `<img src="${imageUrl}" alt="${syrup.name}" loading="lazy" onerror="this.parentElement.innerHTML='<div class=\\'no-image\\'></div>'">`
                    : `<div class="no-image"></div>`
                }
            </div>
            <div class="syrup-info">
                <h3>${syrup.name}</h3>
            </div>
            <div class="syrup-checkmark">
                <svg class="checkmark" viewBox="0 0 24 24">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                </svg>
            </div>
        `;
    
        syrupElement.addEventListener('click', () => this.selectSyrup(syrupElement, syrup));

        return syrupElement;
    }
    
    selectSyrup(syrupElement, syrup) {
        console.log('Выбран сироп:', syrup);

        document.querySelectorAll('.syrup-card').forEach(card => {
            card.classList.remove('selected');
        });

        syrupElement.classList.add('selected');

        this.selectedSyrup = syrup;

        const nextBtn = document.getElementById('syrup-next-btn');
        if (nextBtn) nextBtn.style.display = 'block';
    }

    ensureNextButton(buttonId, nextScreen, containerSelector) {
        let nextBtn = document.getElementById(buttonId);
        if (nextBtn) return;
        
        const container = document.querySelector(containerSelector);
        if (!container) return;
        
        nextBtn = document.createElement('button');
        nextBtn.id = buttonId;
        nextBtn.className = 'btn-primary next-btn';
        nextBtn.textContent = 'Далее';
        nextBtn.style.display = 'none';
        
        const grid = container.querySelector('.drink-grid, .syrup-grid');
        if (grid) {
            grid.insertAdjacentElement('afterend', nextBtn);
        } else {
            container.appendChild(nextBtn);
        }
        
        nextBtn.addEventListener('click', () => {
            if (nextScreen === 'syrup-screen') this.goToSyrupScreen();
            else if (nextScreen === 'discount-qr') this.createDiscountCoupon();
            else if (nextScreen === 'qr-screen') this.createCoupon();
        });
    }
    
    goToSyrupScreen() {
        if (!this.selectedDrink) {
            this.showToast('Пожалуйста, выберите напиток');
            return;
        }
        
        console.log('Переход к выбору сиропа');
        this.showScreen('syrup-screen');
    }
    
    async createCoupon() {
        if (!this.selectedDrink) {
            this.showToast('Пожалуйста, выберите напиток');
            return;
        }
        
        try {
            
            const response = await api.createCoupon({
                type: 'coupon',
                tg_id: this.tgUser.id,
                messanger: this.messanger,
                drink_name: this.selectedDrink.name,
                syrup: this.selectedSyrup.name
            });
            
            console.log('Купон создан:', response);
            this.showToast('Купон успешно создан!');
 
            this.showQRCode(response.qr_code, response.coupon.id);
            
        } catch (error) {
            console.error('Ошибка создания купона:', error);
            this.showToast('Ошибка создания купона: ' + error.message);
        }
    }
    
    showQRCode(qrCodeData, couponId) {
        const qrScreen = document.getElementById('qr-screen');
        if (!qrScreen) {
            console.error('Элемент #qr-screen не найден');
            return;
        }
        
        const qrImage = document.getElementById('qr-image');
        const couponIdEl = document.getElementById('coupon-id');
        
        if (qrImage) {
            qrImage.src = qrCodeData;
        }
        
        if (couponIdEl) {
            couponIdEl.textContent = couponId;
        }
        
        this.showScreen('qr-screen');
    }
    
    goBack() {
        if (this.history.length > 1) {
            this.history.pop();
            const previousScreen = this.history[this.history.length - 1];
            this.showScreen(previousScreen);
        }
    }
    
    showToast(message) {
        const toast = document.getElementById('toast');
        if (!toast) return;
        
        toast.textContent = message;
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
    
    extractTgIdFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('tg_id');
    }

    async createFlyerCoupon() {
        if (!this.scannedFlyerData || !this.selectedDrink) {
            this.showToast('Ошибка: данные не найдены');
            return;
        }
        
        try {
            const response = await api.createCoupon({
                tg_id: this.tgUser.id,
                messanger: this.messanger,
                drink_name: this.selectedDrink.name,
                syrup: this.selectedSyrup?.name || 'no',
                source: 'flyer'
            });
            
            if (response.qr_code) {
                this.showToast('Купон создан!');
                this.showQRCode(response.qr_code, response.coupon.id);
                this.scannedFlyerData = null;
            } else {
                this.showToast('Ошибка: ' + response.error);
            }
        } catch (error) {
            console.error('Ошибка:', error);
            this.showToast('Ошибка: ' + error.message);
        }
    }

    async openCouponScanner() {
        console.log('Открытие сканера купона');
        
        this.showScreen('scan-coupon-screen');
        this.scannedFlyerData = null;
        
        setTimeout(() => this.initCouponScanner(), 300);
    }
    
    async initCouponScanner() {
        if (this.couponScanner) {
            try {
                await this.couponScanner.stop();
                this.couponScanner.clear();
            } catch(e) {}
            this.couponScanner = null;
        }
        
        const readerElement = document.getElementById('coupon-qr-reader');
        if (!readerElement) {
            console.error('Элемент #coupon-qr-reader не найден');
            return;
        }
        
        try {
            if (typeof Html5Qrcode === 'undefined') {
                console.error('Html5Qrcode не загружен!');
                this.showToast('Ошибка: сканер недоступен');
                return;
            }
            
            this.couponScanner = new Html5Qrcode('coupon-qr-reader');
            
            await this.couponScanner.start(
                { facingMode: "environment" },
                { fps: 10, qrbox: { width: 250, height: 250 } },
                (decodedText) => this.onFlyerCouponScanned(decodedText),
                (errorMessage) => {}
            );
            
        } catch (err) {
            console.error('Ошибка сканера:', err);
            this.showToast('Не удалось запустить камеру');
        }
    }
    
    async onFlyerCouponScanned(decodedText) {
        console.log('Сырой текст:', decodedText);

        if (this.couponScanner) {
            try {
                await this.couponScanner.stop();
                this.couponScanner.clear();
            } catch(e) {
                console.warn('Не удалось остановить сканер:', e);
            }
            this.couponScanner = null;
        }
    
        try {
            const qrData = JSON.parse(decodedText.trim());
            console.log('Тип:', qrData.type);
            
            const tgId = this.tgUser?.id;
            if (!tgId) {
                this.showToast('Ошибка: не удалось получить данные пользователя');
                return;
            }

            if (qrData.type === 'discount_30') {
                console.log('СКИДКА 30% - показываем форму');
                this.showDiscountRegistrationForm();
                return;
            }
            
            if (qrData.type === 'flyer_coupon') {
                console.log('КУПОН С ЛИСТОВКИ');
                await this.handleFlyerCoupon(qrData, tgId, this.messanger);
                return;
            }
            
            console.log('Неизвестный тип:', qrData.type);
            this.showToast('Это не купон с листовки');
            setTimeout(() => this.initCouponScanner(), 1500);
        
        } catch (err) {
            console.error('Ошибка:', err);
            this.showToast('Не удалось прочитать QR: ' + err.message);
            setTimeout(() => this.initCouponScanner(), 1500);
        }
    }    

    showDiscountRegistrationForm() {
        this.showScreen('loyalty-register-screen');
        
        setTimeout(() => {
            const howFindSelect = document.getElementById('how_find');
            if (howFindSelect) {
                let option = Array.from(howFindSelect.options).find(opt => 
                    opt.value === 'промоакция 2026' || opt.text === 'промоакция 2026'
                );
                
                if (!option) {
                    option = new Option('промоакция 2026', 'промоакция 2026');
                    howFindSelect.add(option);
                }
                
                howFindSelect.value = 'промоакция 2026';
                howFindSelect.style.backgroundColor = '#e9ecef';
                howFindSelect.readOnly = true;
                
                console.log('Автозаполнено: промоакция 2026');
            }
            
            if (window.user && window.user.initMasks) {
                window.user.initMasks();
            }
        }, 200);
    }
    
    async loadDiscountDrinks() {
        try {
            console.log('Загрузка напитков для скидки...');
            
            if (!window.user.menuLoaded) {
                await window.user.fetchMenuData();
            }
            
            const menuData = window.user.menuData;
            if (!menuData) {
                this.showToast('Меню недоступно');
                return;
            }
            
            const drinkGrid = document.getElementById('discount-drink-grid');
            if (!drinkGrid) {
                console.error('Элемент #discount-drink-grid не найден');
                return;
            }
            
            drinkGrid.innerHTML = '';
            
            const excludedCategories = ['сиропы', 'дополнения', 'десерты', 'еда'];
            
            Object.entries(menuData).forEach(([category, products]) => {
                if (excludedCategories.some(excluded => 
                    category.toLowerCase().includes(excluded)
                )) {
                    return;
                }
                
                const categoryHeader = document.createElement('div');
                categoryHeader.className = 'discount-category-header';
                categoryHeader.textContent = category;
                drinkGrid.appendChild(categoryHeader);
                
                Object.entries(products).forEach(([name, productData]) => {
                    const drinkElement = this.createDiscountDrinkElement(name, productData, category);
                    drinkGrid.appendChild(drinkElement);
                });
            });
            
            console.log('Напитки для скидки отображены');
            
        } catch (error) {
            console.error('Ошибка загрузки напитков для скидки:', error);
            this.showToast('Ошибка загрузки меню');
        }
    }

    createDiscountDrinkElement(name, productData, category) {
        const drinkElement = document.createElement('div');
        drinkElement.className = 'drink-card';
        drinkElement.dataset.drinkName = name;
        drinkElement.dataset.category = category;
        
        const photo = productData?.photo;
        const imageUrl = photo && photo.startsWith('http') 
            ? photo 
            : (photo ? `${api.API_BASE_URL}${photo}` : null);
        
        drinkElement.innerHTML = `
            <div class="drink-image-container">
                ${imageUrl 
                    ? `<img src="${imageUrl}" alt="${name}" loading="lazy">`
                    : `<div class="no-image"></div>`
                }
            </div>
            <div class="drink-info">
                <h3>${name}</h3>
            </div>
            <div class="drink-checkmark">
                <svg class="checkmark" viewBox="0 0 24 24">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                </svg>
            </div>
        `;
        
        drinkElement.addEventListener('click', () => this.selectDiscountDrink(drinkElement, name, productData, category));
        
        return drinkElement;
    }

    selectDiscountDrink(drinkElement, name, productData, category) {
        console.log('Выбран напиток для скидки:', name);
        
        document.querySelectorAll('#discount-drink-grid .drink-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        drinkElement.classList.add('selected');
        
        this.selectedDiscountDrink = {
            name: name,
            category: category,
            photo: productData?.photo
        };
        
        const nextBtn = document.getElementById('discount-next-btn');
        if (nextBtn) nextBtn.style.display = 'block';
    }

    async createDiscountCoupon() {
        if (!this.selectedDiscountDrink) {
            this.showToast('Пожалуйста, выберите напиток');
            return;
        }
        
        if (!this.discountRegistrationData) {
            this.showToast('Ошибка: данные регистрации не найдены');
            return;
        }
        
        try {
            const response = await api.generateDiscountQR({
                tg_id: this.tgUser.id,
                messanger: this.messanger,
                drink_name: this.selectedDiscountDrink.name,
                drink_category: this.selectedDiscountDrink.category,
            });
            
            if (response.success) {
                const qrImage = document.getElementById('discount-qr-image');
                const drinkName = document.getElementById('discount-drink-name');
                const lotteryNumber = document.getElementById('lottery-number');
                
                if (qrImage) qrImage.src = response.qr_code;
                if (drinkName) drinkName.textContent = response.drink_name;
                if (lotteryNumber) lotteryNumber.textContent = response.lottery_number;
                
                this.showScreen('discount-qr-screen');
                this.showToast('QR-код сгенерирован!');
                
                this.selectedDiscountDrink = null;
            } else {
                this.showToast(response.error || 'Ошибка генерации QR');
            }
            
        } catch (error) {
            console.error('Ошибка:', error);
            this.showToast('Ошибка генерации QR-кода');
        }
    }

    finishDiscountFlow() {
        this.selectedDiscountDrink = null;
        this.discountRegistrationData = null;
        this.showScreen('user-profile-screen');
    }

    async handleFlyerCoupon(qrData) {
        const self = this;
        const tgId = this.tgUser?.id;
        
        if (!tgId) {
            this.showToast('Ошибка: не удалось получить данные пользователя');
            return;
        }
    
        try {
            this.showScanResult('loading', 'Проверка купона...');
            
            const result = await api.checkFlyerCouponEligibility(tgId, this.messanger, qrData.flyer_id);
    
            if (result.success || result.has_pending) {
                this.scannedFlyerData = qrData;
                
                this.showScanResult('success', 'Купон доступен!', function() {
                    self.closeCouponScanner();
                    self.showScreen('coupon-screen');
                    if (window.user && window.user.loadDrinks) {
                        window.user.loadDrinks();
                    }
                });
            
            } else if (result.already_used) {
                const drink = result.used_drink || 'напиток';
                const date = result.used_at || 'ранее';
                
                this.showScanResult('error', 
                    `Вы уже использовали купон<br>${drink}<br>${date}`,
                    function() {
                        self.closeCouponScanner();
                        self.showScreen('auth-screen');
                    }
                );
            
            } else {
                this.showScanResult('error', 
                    `${result.error || 'Ошибка проверки'}`,
                    function() {
                        self.closeCouponScanner();
                        self.initCouponScanner();
                    }
                );
            }
        } catch (error) {
            console.error('Ошибка проверки купона:', error);
            this.showScanResult('error', 'Ошибка сервера', function() {
                self.closeCouponScanner();
                self.initCouponScanner();
            });
        }
    }
    
    showScanResult(type, message, onAction) {
        const resultDiv = document.getElementById('coupon-scan-result');
        if (!resultDiv) return;
        
        const icons = { 'success': '🥰', 'error': '🥺'};
        
        resultDiv.className = `scan-result ${type}`;
        resultDiv.innerHTML = `
            <div class="result-icon">${icons[type]}</div>
            <p>${message}</p>
            ${onAction ? `<div class="action-buttons">
                <button class="btn-primary" id="scan-result-action-btn">
                    ${type === 'error' ? 'Попробовать снова' : 'Продолжить'}
                </button>
            </div>` : ''}
        `;
        resultDiv.classList.remove('hidden');
    
        if (onAction) {
            const actionBtn = document.getElementById('scan-result-action-btn');
            if (actionBtn) {
                actionBtn.onclick = () => {
                    resultDiv.classList.add('hidden');
                    onAction();
                };
            }
        }
    }
    
    closeCouponScanner() {
        console.log('Закрытие сканера...');
    
        if (this.couponScanner) {
            try {
                this.couponScanner.stop().catch(err => {
                    console.warn('Предупреждение при остановке:', err);
                });
                this.couponScanner.clear();
            } catch (err) {
                console.warn('Ошибка при закрытии:', err);
            }
            this.couponScanner = null;
        }
    
        const resultDiv = document.getElementById('coupon-scan-result');
        if (resultDiv) resultDiv.classList.add('hidden');
    
        const scannerScreen = document.getElementById('scan-coupon-screen');
        if (scannerScreen) {
            scannerScreen.classList.add('hidden');
        }
    }
    
    
    
    async showPendingCouponQR(couponId, tgId, drinkName) {
        try {
            const qrData = {
                type: 'coupon',
                coupon_id: couponId,
                tg_id: tgId,
                drink_name: drinkName,
                syrup: 'no',
                source: 'flyer'
            };
            
            const qrContainer = document.createElement('div');
            const qr = new QRCode(qrContainer, {
                text: JSON.stringify(qrData),
                width: 240,
                height: 240,
                correctLevel: QRCode.CorrectLevel.H
            });
            
            const qrImage = document.getElementById('qr-image');
            const couponIdEl = document.getElementById('coupon-id');
            
            if (qrImage) {
                qrImage.src = qrContainer.querySelector('img')?.src || 
                             qrContainer.querySelector('canvas')?.toDataURL();
            }
            if (couponIdEl) {
                couponIdEl.textContent = `Купон #${couponId}`;
            }
            
            const qrScreen = document.getElementById('qr-screen');
            const qrInfo = qrScreen?.querySelector('.qr-info');
            if (qrInfo) {
                qrInfo.innerHTML = 'Этот купон ещё не активирован<br>Покажите код бариста';
            }
            
            this.showScreen('qr-screen');
            
        } catch (err) {
            console.error('Ошибка генерации QR:', err);
            this.showToast('Ошибка показа купона');
        }
    }
    
    async createFlyerCoupon() {
        if (!this.scannedFlyerData || !this.selectedDrink) {
            this.showToast('Ошибка: данные не найдены');
            return;
        }
        
        try {
            const response = await api.createCoupon({
                tg_id: this.tgUser.id,
                messanger: this.messanger,
                drink_name: this.selectedDrink.name,
                syrup: this.selectedSyrup?.name || 'no',
                source: 'flyer'
            });
            
            if (response.qr_code) {
                this.showToast('Купон создан!');
                this.showQRCode(response.qr_code, response.coupon.id);
                this.scannedFlyerData = null;
            } else {
                this.showToast('Ошибка: ' + response.error);
            }
        } catch (error) {
            console.error('Ошибка:', error);
            this.showToast('Ошибка: ' + error.message);
        }
    }
}

const app = new CoffeeApp();
window.app = app;