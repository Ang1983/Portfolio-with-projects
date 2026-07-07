class User {
    constructor() {
        this.userData = null;
        this.currentLoyaltyTab = 'credit';
        this.studentQRScanner = null;
        this.pendingUniversityData = null;
        this.menuData = null;
        this.menuLoaded = false;
    }

    openStudentQRScanner() {
        console.log('Открытие сканера студенческой скидки');
        
        const modal = document.getElementById('student-qr-modal');
        const resultDiv = document.getElementById('student-scan-result');
        
        if (!modal) {
            console.error('Модальное окно студента не найдено');
            app.showToast('Ошибка: сканер недоступен');
            return;
        }

        if (resultDiv) resultDiv.classList.add('hidden');

        modal.classList.remove('hidden');

        setTimeout(() => this.initStudentQRScanner(), 300);
    }


    initStudentQRScanner() {
        const readerElement = document.getElementById('student-qr-reader');
        if (!readerElement) {
            console.error('Элемент #student-qr-reader не найден');
            return;
        }

        if (this.studentQRScanner) {
            try {
                this.studentQRScanner.stop();
                this.studentQRScanner.clear();
            } catch(e) {}
            this.studentQRScanner = null;
        }
        
        try {
            if (typeof Html5Qrcode === 'undefined') {
                console.error('Html5Qrcode не загружен!');
                app.showToast('Ошибка: сканер недоступен');
                return;
            }
            
            this.studentQRScanner = new Html5Qrcode('student-qr-reader');
            
            this.studentQRScanner.start(
                { facingMode: "environment" },
                { 
                    fps: 10, 
                    qrbox: { width: 250, height: 250 },
                    aspectRatio: 1.0
                },
                (decodedText) => this.onUniversityQRScanned(decodedText),
                (errorMessage) => {}
            ).catch(err => {
                console.error('Ошибка запуска сканера:', err);
                app.showToast('Не удалось запустить камеру');
                this.closeStudentQRScanner();
            });
            
        } catch (err) {
            console.error('Ошибка инициализации:', err);
            app.showToast('Ошибка сканера');
            this.closeStudentQRScanner();
        }
    }
    

    async onUniversityQRScanned(decodedText) {
        if (this.studentQRScanner) {
            try {
                await this.studentQRScanner.stop();
            } catch(e) {}
        }
        
        console.log('QR отсканирован:', decodedText);
        
        try {
            const qrData = JSON.parse(decodedText);

            if (qrData.type !== 'university_discount') {
                this.showStudentScanResult('error', 'Не тот QR', 'Попросите бариста отсканировать правильный код', () => {
                    this.initStudentQRScanner();
                });
                return;
            }
            
            const percent = qrData.university_percent;
            const self = this;
            
            if (percent === 15) {
                this.showStudentScanResult('success', 'Преподаватель!', 'Скидка 15%', () => {
                    self.pendingUniversityData = { university_percent: 15 };
                    self.confirmStudentDiscount();
                });
            } else if (percent === 10) {
                this.showStudentScanResult('success', 'Студент!', 'Скидка 10%', () => {
                    self.pendingUniversityData = { university_percent: 10 };
                    self.confirmStudentDiscount();
                });
            } else {
                this.showStudentScanResult('error', 'Ошибка', 'Неверный процент скидки', () => {
                    self.initStudentQRScanner();
                });
            }
            
        } catch (error) {
            console.error('Ошибка парсинга QR:', error);
            this.showStudentScanResult('error', 'Неверный формат', 'Попробуйте ещё раз', () => {
                this.initStudentQRScanner();
            });
        }
    }


    closeStudentQRScanner() {
        const modal = document.getElementById('student-qr-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
        
        if (this.studentQRScanner) {
            try {
                this.studentQRScanner.stop();
                this.studentQRScanner.clear();
            } catch (err) {
                console.warn('Предупреждение при остановке:', err);
            }
            this.studentQRScanner = null;
        }
        
        const resultDiv = document.getElementById('student-scan-result');
        if (resultDiv) resultDiv.classList.add('hidden');
        
        console.log('Студенческий сканер закрыт');
    }


    showStudentScanResult(type, title, message, onAction) {
        const resultDiv = document.getElementById('student-scan-result');
        const iconEl = document.getElementById('student-result-icon');
        const titleEl = document.getElementById('student-result-title');
        const messageEl = document.getElementById('student-result-message');
        const actionsDiv = document.getElementById('student-result-actions');
        
        if (!resultDiv) return;

        const classes = { 'success': 'success', 'error': 'error', 'loading': 'loading' };
        
        resultDiv.className = `scan-result ${classes[type] || ''}`;
        titleEl.textContent = title;
        messageEl.innerHTML = message;
        
        if (onAction && typeof onAction === 'function') {
            const btnText = type === 'error' ? 'Попробовать снова' : 'Продолжить';
            actionsDiv.innerHTML = `<button class="btn-primary" id="student-action-btn">${btnText}</button>`;
            
            setTimeout(() => {
                const btn = document.getElementById('student-action-btn');
                if (btn) {
                    btn.onclick = () => {
                        resultDiv.classList.add('hidden');
                        onAction();
                    };
                }
            }, 50);
        } else {
            actionsDiv.innerHTML = '';
        }
        
        resultDiv.classList.remove('hidden');
    }
    
 
    async confirmStudentDiscount() {
        const pendingData = JSON.parse(sessionStorage.getItem('pendingRegistration') || '{}');
        
        if (!pendingData.full_name) {
            app.showToast('Ошибка: данные регистрации не найдены');
            return;
        }
        
        const registrationData = {
            ...pendingData,
            university_percent: this.pendingUniversityData?.university_percent || 0
        };
        
        console.log('Завершение регистрации со скидкой:', registrationData);
        
        this.closeStudentQRScanner();

        if (loyalty?.completeRegistration) {
            await window.loyalty.completeRegistration(registrationData);
        } else {
            app.showToast('Ошибка: метод регистрации не найден');
        }
        
        sessionStorage.removeItem('pendingRegistration');
        this.pendingUniversityData = null;
    }

    async showHistory() {
        const modal = document.getElementById('purchase-history-modal');
        if (!modal) {
            console.error('Модальное окно истории не найдено');
            return;
        }
    
        modal.classList.remove('hidden');
        await this.loadHistory();
    }
    
    closeHistory() {
        const modal = document.getElementById('purchase-history-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
    }
    
    async loadHistory() {
        const historyList = document.getElementById('history-list');
        const historyEmpty = document.getElementById('history-empty');
        const historyLoading = document.getElementById('history-loading');
        
        if (!historyList) {
            console.error('Контейнер истории не найден');
            return;
        }

        historyList.classList.add('hidden');
        if (historyEmpty) historyEmpty.classList.add('hidden');
        if (historyLoading) historyLoading.classList.remove('hidden');
    
        try {
            const tgId = app?.tgUser?.id;
            
            if (!tgId) {
                if (historyLoading) historyLoading.classList.add('hidden');
                historyList.innerHTML = `
                    <div class="history-error">
                        <p>Ошибка авторизации</p>
                    </div>
                `;
                historyList.classList.remove('hidden');
                return;
            }
    
            const result = await api.getReceiptHistory(tgId, app.messanger);
            console.log('История заказов:', result);
    
            if (historyLoading) historyLoading.classList.add('hidden');
    
            if (!result.success || !result.receipts || result.receipts.length === 0) {
                historyList.classList.add('hidden');
                if (historyEmpty) {
                    historyEmpty.classList.remove('hidden');
                } else {
                    historyList.innerHTML = `
                        <div class="history-empty">
                            <div class="empty-icon">😔</div>
                            <p>У вас пока нет заказов</p>
                        </div>
                    `;
                    historyList.classList.remove('hidden');
                }
                return;
            }
    
            historyList.classList.remove('hidden');
            if (historyEmpty) historyEmpty.classList.add('hidden');
            
            historyList.innerHTML = '';
            
            result.receipts.forEach(receipt => {
                const item = this.createPurchaseItem(receipt);
                historyList.appendChild(item);
            });
    
        } catch (error) {
            console.error('Ошибка загрузки истории:', error);
            if (historyLoading) historyLoading.classList.add('hidden');
            historyList.innerHTML = `
                <div class="history-error">
                    <p>Ошибка загрузки данных</p>
                </div>
            `;
            historyList.classList.remove('hidden');
            app?.showToast?.('Не удалось загрузить историю заказов');
        }
    }
    
    createPurchaseItem(receipt) {
        const item = document.createElement('div');
        item.className = 'purchase-item';

        const productName = receipt.products && receipt.products.length > 0 
            ? receipt.products[0].name 
            : 'Заказ';

        const amount = parseFloat(receipt.amount) || 0;
        const type_operation = receipt.type;
        const bonus_percent = receipt.bonus_percent
        const amountFormatted = amount === 0 ? 'Бесплатно' : `${amount}`;

        const points = Math.floor(amount * bonus_percent/100);

        const dateFormatted = receipt.date_operation || '';
        

        if (type_operation === 'возврат'){
            item.innerHTML = `
            <div class="purchase-info">
                <h3 class="purchase-name">${productName}</h3>
                <p class="purchase-date">${dateFormatted}</p>
            </div>
            <div class="purchase-price">
                <span class="purchase-amount">${amountFormatted}</span>
                <span class="purchase-points">${points}</span>
            </div>
        `;}else if (type_operation === 'приход'){
            item.innerHTML = `
                <div class="purchase-info">
                    <h3 class="purchase-name">${productName}</h3>
                    <p class="purchase-date">${dateFormatted}</p>
                </div>
                <div class="purchase-price">
                    <span class="purchase-amount">${amountFormatted}</span>
                    <span class="purchase-points">${points}</span>
                </div>
        `;} else {
            item.innerHTML = `
                <div class="purchase-info">
                    <h3 class="purchase-name">${productName}</h3>
                    <p class="purchase-date">${dateFormatted}</p>
                </div>
                <div class="purchase-price">
                    <span class="purchase-amount">${amountFormatted}</span>
                </div>
        `;}
        
        return item;
    }

    async loadUserData() {
        try {
            const tgId = app?.tgUser?.id;
            const messanger = app?.messanger;
            if (!tgId) {
                console.warn('TG ID не найден, используем заглушку');
                return;
            }
    
            const response = await api.getUserProfile(tgId, app.messanger);
    
            if (response.success && response.data) {
                this.userData = response.data;
    
                this.updateAvatarUI(response.data.avatar);
    
                this.updateBalanceUI(response.data.bonuses);
    
                if (!document.getElementById('loyalty-qr-screen')?.classList.contains('hidden')) {
                    this.generateLoyaltyQR();
                }
    
                console.log('Данные пользователя загружены:', this.userData);
            }
        } catch (error) {
            console.error('Ошибка загрузки профиля:', error);
        }
    }

    updateAvatarUI(avatarBase64) {
        const avatarImg = document.getElementById('user-avatar');
        
        if (avatarImg) {
            if (avatarBase64 && (avatarBase64.startsWith('data:image/') || avatarBase64.startsWith('http'))) {
                avatarImg.src = avatarBase64;
                avatarImg.style.display = 'block';
                console.log('Аватар загружен:', avatarBase64.substring(0, 50) + '...');
            } else {
                avatarImg.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="40" r="30" fill="%23ccc"/><circle cx="50" cy="90" r="20" fill="%23ccc"/></svg>';
                avatarImg.style.display = 'block';
                console.log('Показана аватарка по умолчанию');
            }
        }
    }
    
    updateBalanceUI(newBalance) {
        const elements = [
            'bonus-amount',
            'loyalty-balance',
            'spend-current-balance'
        ];
        
        elements.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = newBalance;
        });

        if (app.userData) {
            app.userData.bonuses = newBalance;
        }
    }
    
    async showLoyaltyCard() {
        await this.loadUserData();
        
        const balanceEl = document.getElementById('loyalty-balance');
        const userNameEl = document.getElementById('loyalty-user-name');
        const userIdEl = document.getElementById('loyalty-user-id');
    
        const userData = this.userData || app.userData;
    
        if (balanceEl && userData?.bonuses !== undefined) {
            balanceEl.textContent = userData.bonuses;
        }
        
        if (userNameEl && userData?.full_name) {
            userNameEl.textContent = userData.full_name;
        }
        
        if (userIdEl && app.tgUser?.id) {
            userIdEl.textContent = this.generateUserId(app.tgUser.id);
        }

        this.currentLoyaltyTab = 'credit';

        const creditTab = document.getElementById('tab-credit');
        const debitTab = document.getElementById('tab-debit');
        const creditSection = document.getElementById('credit-section');
        const debitSection = document.getElementById('debit-section');
        
        if (creditTab) creditTab.classList.add('active');
        if (debitTab) debitTab.classList.remove('active');
        if (creditSection) creditSection.classList.remove('hidden');
        if (debitSection) debitSection.classList.add('hidden');

        await this.generateAccumulateQR();
        
        app.showScreen('loyalty-qr-screen');
    }
    
    async confirmSpendBonuses() {
        const inputEl = document.getElementById('spend-amount-input');
        const spendAmount = parseInt(inputEl?.value) || 0;
    
        const balanceEl = document.getElementById('loyalty-balance');
        const currentBalance = parseInt(balanceEl?.textContent) || 0;
        
        if (spendAmount <= 0) {
            app.showToast('Введите корректное количество бонусов');
            return;
        }
        
        if (spendAmount > currentBalance) {
            app.showToast('Недостаточно бонусов на балансе');
            return;
        }
        
        try {
            app.showToast('Списание бонусов...');
            
            const tgId = app.tgUser?.id;
            if (!tgId) {
                app.showToast('Ошибка: не удалось получить данные пользователя');
                return;
            }

            console.log('spendBonuses вызван:', {
                tg_id: tgId,
                messanger: app.messanger,
                amount: spendAmount
            });
            
            const response = await api.spendBonuses({
                tg_id: tgId,
                messanger: app.messanger,
                amount: spendAmount
            });
            
            console.log('Списание бонусов:', response);
            
            if (response.success) {
                const newBalance = response.new_balance !== undefined 
                    ? response.new_balance 
                    : currentBalance - spendAmount;
            
                this.updateBalanceUI(newBalance);
            
                if (this.userData) {
                    this.userData.bonuses = newBalance;
                }
                
                app.showToast(`Списано ${spendAmount} бонусов`);
                this.closeSpendModal();

                await this.generateSpendQR(spendAmount);
            } else {
                app.showToast(response.error || 'Ошибка при списании бонусов');
            }
            
        } catch (error) {
            console.error('Ошибка списания бонусов:', error);
            app.showToast('Ошибка: ' + (error.message || error));
        }
    }

    switchLoyaltyTab(tab) {
        this.currentLoyaltyTab = tab;
    
        const creditTab = document.getElementById('tab-credit');
        const debitTab = document.getElementById('tab-debit');
        const creditSection = document.getElementById('credit-section');
        const debitSection = document.getElementById('debit-section');

        const spendBtn = debitSection.querySelector('.spend-btn');
        const qrPlaceholder = debitSection.querySelector('.qr-placeholder');
    
        if (tab === 'credit') {
            creditTab.classList.add('active');
            debitTab.classList.remove('active');
            creditSection.classList.remove('hidden');
            debitSection.classList.add('hidden');
            
            this.generateAccumulateQR();
        } else {
            debitTab.classList.add('active');
            creditTab.classList.remove('active');
            debitSection.classList.remove('hidden');
            creditSection.classList.add('hidden');

            if (spendBtn) spendBtn.style.display = 'block';
            if (qrPlaceholder) qrPlaceholder.style.display = 'none';
        }
    }

    async generateAccumulateQR() {
        try {
            const response = await api.createLoyaltyQR({
                type: 'loyalty_card',
                tg_id: app.tgUser?.id,
                messanger: app.messanger,
                card_name: app.userData.card_name,
                university_percent: app.userData.university_percent
            });
            
            this.showLoyaltyQRCode(response.qr_code, 'accumulate', 0);
            
        } catch (error) {
            console.error('Ошибка генерации QR:', error);
            app.showToast('Ошибка: ' + error.message);
        }
    }
    
    async generateSpendQR(spendAmount = null) {
        if (spendAmount === null) {
            const bonusAmountInput = document.getElementById('spend-amount-input');
            spendAmount = parseInt(bonusAmountInput?.value) || 0;
        }
        
        const availableEl = document.getElementById('loyalty-balance');
        const available = parseInt(availableEl?.textContent || '0');
        
        if (isNaN(spendAmount) || spendAmount <= 0) {
            app.showToast('Введите корректное количество бонусов');
            return;
        }
        
        try {
            const response = await api.createLoyaltyQR({
                type: 'loyalty_card',
                card_name: app.userData.card_name,
                university_percent: app.userData.university_percent,
                tg_id: app.tgUser?.id,
                messanger: app.messanger
            });

            const debitSection = document.getElementById('debit-section');
            if (debitSection) {
                debitSection.innerHTML = '';
            }

            this.showLoyaltyQRCode(response.qr_code, 'spend', spendAmount);
            
        } catch (error) {
            console.error('Ошибка генерации QR:', error);
            app.showToast('Ошибка: ' + error.message);
        }
    }
    
    showLoyaltyQRCode(qrCodeData, mode, bonusAmount = 0) {
        const sectionId = mode === 'accumulate' ? 'credit-section' : 'debit-section';
        const section = document.getElementById(sectionId);
        let container = section.querySelector('.qr-placeholder');

        if (!container) {
            container = document.createElement('div');
            container.className = 'qr-placeholder';
            section.appendChild(container);
        }
        
        container.style.display = 'flex';
        container.innerHTML = '';
        
        const qrImage = document.createElement('img');
        qrImage.className = 'qr-code-image';
        qrImage.alt = 'Loyalty QR';
        qrImage.src = qrCodeData;
        
        qrImage.onerror = () => {
            container.innerHTML = `<p class="qr-error">⚠️ Не удалось загрузить QR</p>`;
            app.showToast('Ошибка загрузки QR-кода');
        };
        
        container.appendChild(qrImage);
    
        const label = document.createElement('p');
        label.className = 'qr-label';
        container.appendChild(label);
        
        const hint = document.createElement('p');
        hint.className = 'qr-hint';
        hint.textContent = mode === 'accumulate'
            ? 'Покажите этот QR-код бариста'
            : `Списать ${bonusAmount} бонусов`;
        container.appendChild(hint);

        document.getElementById('credit-section')?.classList.toggle('hidden', mode !== 'accumulate');
        document.getElementById('debit-section')?.classList.toggle('hidden', mode !== 'spend');
    }

    showSpendModal() {
        const modal = document.getElementById('spend-modal');
        const currentBalanceEl = document.getElementById('spend-current-balance');
        const balanceEl = document.getElementById('loyalty-balance');
        const inputEl = document.getElementById('spend-amount-input');
        const remainingContainer = document.getElementById('remaining-balance-container');
        
        if (currentBalanceEl && balanceEl) {
            currentBalanceEl.textContent = balanceEl.textContent;
        }
        
        if (inputEl) {
            inputEl.value = '';
        }
        
        if (remainingContainer) {
            remainingContainer.style.display = 'none';
        }
        
        if (modal) {
            modal.classList.remove('hidden');
        }
    }

    closeSpendModal() {
        const modal = document.getElementById('spend-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
    }

    calculateRemainingBalance() {
        const inputEl = document.getElementById('spend-amount-input');
        const currentBalanceEl = document.getElementById('spend-current-balance');
        const remainingEl = document.getElementById('spend-remaining-balance');
        const remainingContainer = document.getElementById('remaining-balance-container');
        
        if (!inputEl || !currentBalanceEl || !remainingEl) return;
        
        const currentBalance = parseInt(currentBalanceEl.textContent) || 0;
        const spendAmount = parseInt(inputEl.value) || 0;
        
        if (spendAmount > 0) {
            const remaining = currentBalance - spendAmount;
            remainingEl.textContent = remaining >= 0 ? remaining : 0;
            remainingContainer.style.display = 'block';
        } else {
            remainingContainer.style.display = 'none';
        }
    }

    async uploadAvatar(input) {
        const file = input.files[0];
        if (!file) return;
        
        if (!file.type.startsWith('image/')) {
            app.showToast('Пожалуйста, выберите изображение');
            return;
        }
        
        if (file.size > 5 * 1024 * 1024) {
            app.showToast('Размер файла не должен превышать 5MB');
            return;
        }
        
        try {
            app.showToast('Загрузка фото...');
            
            const reader = new FileReader();
            reader.onload = async (e) => {
                const base64Image = e.target.result;
                
                const avatarImg = document.getElementById('user-avatar');
                if (avatarImg) {
                    avatarImg.src = base64Image;
                }
                
                const tgId = app.tgUser?.id;
                if (tgId) {
                    try {
                        await api.uploadAvatar({
                            tg_id: tgId,
                            messanger: app.messanger,
                            employee: 'false',
                            avatar: base64Image
                        });
                        app.showToast('Аватар успешно загружен');
                    } catch (error) {
                        console.error('Ошибка сохранения аватара:', error);
                    }
                }
            };
            
            reader.readAsDataURL(file);
            
        } catch (error) {
            console.error('Ошибка загрузки аватара:', error);
            app.showToast('Ошибка загрузки фото');
        }
        
        input.value = '';
    }

    initMasks() {
        setTimeout(() => {
            const dateEl = document.getElementById('date_of_birth');
            if (dateEl && typeof IMask !== 'undefined') {
                if (dateEl._imask) {
                    dateEl._imask.destroy();
                    dateEl._imask = null;
                }

                const dateMask = IMask(dateEl, {
                    mask: '00.00.0000',
                    lazy: false,
                    placeholderChar: '_'
                });
                if (dateEl.value && dateEl.value.length === 10) {
                    dateMask.value = dateEl.value;
                }

                dateEl._imask = dateMask;
                console.log('Маска даты инициализирована');
            } else if (dateEl) {
                dateEl.placeholder = 'ДД.ММ.ГГГГ';
                console.warn('IMask не загружен, дата без маски');
            }
        }, 100);
    }

    getCleanDateOfBirth() {
        const dateEl = document.getElementById('date_of_birth');
        if (!dateEl) return null;

        const value = dateEl.value.trim();
        if (!value || value.length !== 10) return null;

        const parts = value.split('.');
        if (parts.length !== 3) return null;

        const [day, month, year] = parts;
        if (!day || !month || !year) return null;

        return `${year}-${month}-${day}`;
    }

    validateDateOfBirth(dateString) {
        if (!dateString || dateString.length !== 10) {
            return { valid: false, error: 'Некорректный формат даты' };
        }

        const parts = dateString.split('.');
        if (parts.length !== 3) {
            return { valid: false, error: 'Формат: ДД.ММ.ГГГГ' };
        }

        const day = parseInt(parts[0], 10);
        const month = parseInt(parts[1], 10);
        const year = parseInt(parts[2], 10);

        if (isNaN(day) || isNaN(month) || isNaN(year)) {
            return { valid: false, error: 'Дата должна содержать только цифры' };
        }

        if (month < 1 || month > 12) {
            return { valid: false, error: 'Месяц должен быть от 01 до 12' };
        }

        if (day < 1 || day > 31) {
            return { valid: false, error: 'День должен быть от 01 до 31' };
        }

        if (year < 1950 || year > 2050) {
            return { valid: false, error: 'Год должен быть от 1950 до 2050' };
        }

        return { valid: true, error: null };
    }

    async showMenu(forDiscount = false) {
        try {

            if (forDiscount) {
                app.showScreen('discount-selection-screen');
            } else {
                app.showScreen('menu-screen');
            }
            
            const menuContainer = document.getElementById('menu-container');
            const menuLoading = document.getElementById('menu-loading');
            
            if (!menuContainer) {
                console.error('Элементы меню не найдены');
                return;
            }
    
            if (menuLoading) menuLoading.classList.remove('hidden');
            menuContainer.classList.add('hidden');
    
            if (!this.menuLoaded) {
                await this.fetchMenuData();
            }
    
            this.renderMenu(forDiscount);
    
            if (menuLoading) menuLoading.classList.add('hidden');
            menuContainer.classList.remove('hidden');
    
            this.initCategoryScrollObserver();
            
        } catch (error) {
            console.error('Ошибка загрузки меню:', error);
            app.showToast('Не удалось загрузить меню');
        }
    }

    async fetchMenuData() {
        try {
            const response = await api.getMenu();
            
            if (response && Object.keys(response).length > 0) {
                this.menuData = response;
                this.menuLoaded = true;
                console.log('Меню загружено:', Object.keys(this.menuData).length, 'категорий');
            } else {
                console.warn('Меню пустое');
                app.showToast('Меню временно недоступно');
            }
        } catch (error) {
            console.error('Ошибка API меню:', error);
            throw error;
        }
    }

    renderMenu() {
        const categoriesWrapper = document.getElementById('menu-categories');
        const menuContent = document.getElementById('menu-content');
        
        if (!categoriesWrapper || !menuContent || !this.menuData) return;
    
        categoriesWrapper.innerHTML = '';
        menuContent.innerHTML = '';
    
        const categories = Object.keys(this.menuData);

        categories.forEach((category, index) => {
            const btn = document.createElement('button');
            btn.className = 'category-btn';

            if (index === 0) {
                btn.classList.add('active');
            }
            
            btn.textContent = category;
            btn.dataset.category = category;
            btn.addEventListener('click', () => this.scrollToCategory(category));
            categoriesWrapper.appendChild(btn);
        });

        categories.forEach(category => {
            const section = document.createElement('div');
            section.className = 'menu-section';
            section.id = `${category}`;
            section.dataset.category = category;
            
            const title = document.createElement('h2');
            title.className = 'category-title';
            title.textContent = category;
            section.appendChild(title);
            
            const grid = document.createElement('div');
            grid.className = 'products-grid';
            
            const products = this.menuData[category];
            Object.entries(products).forEach(([name, productData]) => {
                const card = this.createProductCard(name, productData, category);
                grid.appendChild(card);
            });
            
            section.appendChild(grid);
            menuContent.appendChild(section);
        });

        this.initCategoryScrollObserver();
    }

    createProductCard(name, productData, category) {
        const photo = productData?.photo;
        const description = productData?.description || '';
        
        const card = document.createElement('div');
        card.className = 'product-card';
        card.dataset.name = name;
        card.dataset.category = category;
        
        const imageUrl = photo && photo.startsWith('http') 
            ? photo 
            : (photo ? `${api.API_BASE_URL}${photo}` : null);
        
        card.innerHTML = `
            <div class="product-image">
                ${imageUrl 
                    ? `<img src="${imageUrl}" alt="${name}" loading="lazy" onerror="this.parentElement.innerHTML='<div class=\\'no-image\\'></div>'">`
                    : `<div class="no-image"></div>`
                }
            </div>
            <div class="product-info">
                <h3 class="product-name" title="${name}">${name}</h3>
            </div>
        `;
    
        card.onclick = (e) => {
            this.openProductModal(name, photo, description, category);
        };
        
        return card;
    }

    scrollToCategory(category) {
        console.log('Клик по категории:', category);

        document.querySelectorAll('.category-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.category === category) {
                btn.classList.add('active');
            }
        });

        if (category === 'all' || !category) {
            const menuContent = document.getElementById('menu-content');
            if (menuContent) {
                console.log('Скролл к началу');
                menuContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        } else {
            const slug = category;
            const sectionId = `${slug}`;
            console.log('Ищем секцию:', sectionId);
            
            const section = document.getElementById(sectionId);
            if (section) {
                console.log('Секция найдена:', section);
                section.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else {
                console.error('Секция не найдена:', sectionId);
                console.log('Все ID на странице:', 
                    Array.from(document.querySelectorAll('[id]')).map(el => el.id)
                );
            }
        }
    }

    initCategoryScrollObserver() {
        const sections = document.querySelectorAll('.menu-section');
        const buttons = document.querySelectorAll('.category-btn');
        
        if (!sections.length || !buttons.length) return;
        
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const category = entry.target.dataset.category;
                        buttons.forEach(btn => {
                            btn.classList.remove('active');
                            if (btn.dataset.category === category) {
                                btn.classList.add('active');
                            }
                        });
                    }
                });
            },
            { rootMargin: '-20% 0px -70% 0px', threshold: 0.1 }
        );
        
        sections.forEach(section => observer.observe(section));
    }

    openProductModal(name, photo, description, category) {
        const modal = document.getElementById('product-modal');
        const modalImage = document.getElementById('modal-product-image');
        const modalName = document.getElementById('modal-product-name');
        const modalCategory = document.getElementById('modal-product-category');
        const modalDescription = document.getElementById('modal-product-description');
        const modalAddBtn = document.getElementById('modal-add-to-cart');
        
        if (!modal) {
            console.error('Модальное окно товара не найдено');
            return;
        }

        if (modalImage) {
            modalImage.src = photo || 'https://via.placeholder.com/400x400/f5f5f5/999999?text=No+Photo';
            modalImage.alt = name;
        }
        if (modalName) modalName.textContent = name;
        if (modalCategory) modalCategory.textContent = category;
        if (modalDescription) {
            modalDescription.textContent = description || 'Описание отсутствует';
            modalDescription.classList.toggle('hidden', !description);
        }

        modal.dataset.productData = JSON.stringify({ name, photo, description, category });

        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }

    closeProductModal() {
        const modal = document.getElementById('product-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
        document.body.style.overflow = '';
    }
}

class Loyalty {
    async register(event) {
        event.preventDefault();
        
        const fullName = document.getElementById('full_name')?.value.trim();
        const howFind = document.getElementById('how_find')?.value;

        if (!fullName) {
            app.showToast('Пожалуйста, введите ваше имя');
            return;
        }

        const dateEl = document.getElementById('date_of_birth');
        const dateOfBirthRaw = dateEl?.value.trim();

        let dateOfBirthClean = null;
        if (dateOfBirthRaw && dateOfBirthRaw.length === 10) {
            const validation = window.user.validateDateOfBirth(dateOfBirthRaw);
            if (!validation.valid) {
                app.showToast(validation.error);
                return;
            }
            const [day, month, year] = dateOfBirthRaw.split('.');
            dateOfBirthClean = `${year}-${month}-${day}`;
        }

        if (howFind === 'mai' || howFind === 'mtusy') {
            sessionStorage.setItem('pendingRegistration', JSON.stringify({
                full_name: fullName,
                date_of_birth: this.getCleanDateOfBirth(),
                how_find: howFind
            }));

            window.user.openStudentQRScanner();
            return;
        }

        await this.completeRegistration({
            full_name: fullName,
            date_of_birth: this.getCleanDateOfBirth(),
            how_find: howFind,
            university_percent: 0
        });
    }

    async completeRegistration(data) {
        try {
            app.showToast('Регистрация...');
    
            console.log('Данные для отправки:', {
                tg_id: app.tgUser?.id,
                messanger: app.messanger,
                full_name: data.full_name,
                birthday: data.date_of_birth,
                how_find: data.how_find,
                status: 'active',
                university_percent: data.university_percent
            });
    
            const tgId = app.tgUser?.id;
            if (!tgId) {
                app.showToast('Ошибка: не удалось получить данные пользователя');
                return;
            }
    
            const response = await api.registerLoyaltyCard({
                tg_id: tgId,
                messanger: app.messanger,
                full_name: data.full_name,
                birthday: data.date_of_birth,
                how_find: data.how_find,
                status: 'active',
                university_percent: data.university_percent
            });
    
            console.log('Регистрация:', response);
    
            if (response?.error) {
                app.showToast(response.error);
                return;
            }

            if (data.how_find === 'промоакция 2026') {
                console.log('Переход к выбору напитка для скидки 30%');
            
                app.discountRegistrationData = {
                    full_name: data.full_name,
                    birthday: data.date_of_birth
                };
                
                setTimeout(() => {
                    app.showScreen('discount-selection-screen');
                }, 1000);
                
                return;
            }            

            app.showToast('Карта лояльности создана!');
            app.userData = response;
            app.profileType = 'user';

            setTimeout(() => {
                app.showProfile('user');
            }, 1000);
    
        } catch (error) {
            console.error('Ошибка регистрации:', error);
            app.showToast('Ошибка: ' + (error.message || error));
        }
    }    

    getCleanDateOfBirth() {
        const dateEl = document.getElementById('date_of_birth');
        if (!dateEl) return null;
        const value = dateEl.value.trim();
        if (!value || value.length !== 10) return null;
        const [day, month, year] = value.split('.');
        return `${year}-${month}-${day}`;
    }

    showSpendForm() {
        const spendForm = document.getElementById('spend-form');
        const qrImg = document.getElementById('loyalty-qr-img');

        if (spendForm) spendForm.classList.remove('hidden');
        if (qrImg) qrImg.src = '';
    }

    showAccumulate() {
        app.showToast('Бонусы будут начислены при следующей покупке');
    }

    async generateQR() {
        const bonusAmountInput = document.getElementById('bonus-amount-input');
        const bonusAmount = parseInt(bonusAmountInput?.value);
        const availableEl = document.getElementById('available-bonus');
        const available = parseInt(availableEl?.textContent || '0');

        if (!bonusAmountInput || isNaN(bonusAmount) || bonusAmount <= 0) {
            app.showToast('Введите корректное количество бонусов');
            return;
        }

        const spendForm = document.getElementById('spend-form');
        if (spendForm) spendForm.classList.add('hidden');

        const qrData = {
            type: 'loyalty_card',
            card_name: app.userData.card_name,
            university_percent: app.userData.university_percent,
            tg_id: app.tgUser?.id
        };

        try {
            const qrCodeImg = document.getElementById('loyalty-qr-img');
            if (qrCodeImg) {
                const qrString = JSON.stringify(qrData);
                const qrUrl = `https://chart.googleapis.com/chart?chs=240x240&cht=qr&chl=${encodeURIComponent(qrString)}&choe=UTF-8`;
                qrCodeImg.src = qrUrl;

                qrCodeImg.onerror = () => {
                    app.showToast('Ошибка загрузки QR-кода');
                    if (spendForm) spendForm.classList.remove('hidden');
                };
            }
            
        } catch (error) {
            console.error('Ошибка генерации QR:', error);
            app.showToast('Ошибка генерации QR-кода');
            if (spendForm) spendForm.classList.remove('hidden');
        }
    }
}



window.user = new User();
window.loyalty = new Loyalty();

document.addEventListener('DOMContentLoaded', function() {
    const observer = new MutationObserver(() => {
        const registerScreen = document.getElementById('loyalty-register-screen');
        if (registerScreen && !registerScreen.classList.contains('hidden')) {
            window.user.initMasks();
        }
    });
    
    observer.observe(document.body, { 
        attributes: true, 
        attributeFilter: ['class'],
        subtree: true 
    });

    const registerScreen = document.getElementById('loyalty-register-screen');
    if (registerScreen && !registerScreen.classList.contains('hidden')) {
        setTimeout(() => window.user.initMasks(), 100);
    }
});