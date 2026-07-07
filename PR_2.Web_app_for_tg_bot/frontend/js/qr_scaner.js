class QRScanner {
    constructor() {
        this.video = document.getElementById('scanner-video');
        this.canvas = document.getElementById('scanner-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.scanning = false;
        this.qrCodeFound = false;
        this.scannedData = null;

        this.ownCupCount = 0;

        this.availableBonuses = 0;
    }

    updateBonusDisplay(bonuses) {
        this.availableBonuses = bonuses;
        
        const warningEl = document.getElementById('bonus-warning');
        const inputEl = document.getElementById('bonus-amount-input');
        
        if (inputEl) {
            inputEl.max = bonuses;
            inputEl.oninput = () => this.checkBonusInput();
        }
        
        if (warningEl && inputEl) {
            this.checkBonusInput();
        }
    }

    checkBonusInput() {
        const warningEl = document.getElementById('bonus-warning');
        const inputEl = document.getElementById('bonus-amount-input');
        
        if (warningEl && inputEl) {
            const entered = parseInt(inputEl.value) || 0;
            console.log('Введено бонусов:', entered, 'Доступно:', this.availableBonuses);
            
            if (entered > this.availableBonuses && entered > 0) {
                warningEl.classList.remove('hidden');
                inputEl.style.borderColor = '#d97706';
            } else {
                warningEl.classList.add('hidden');
                inputEl.style.borderColor = '#ddd';
            }
        }
    }

    incrementOwnCup() {
        if (this.ownCupCount < 10) {
            this.ownCupCount++;
            this.updateOwnCupDisplay();
            console.log('➕ Стаканы:', this.ownCupCount);
        }
    }

    decrementOwnCup() {
        if (this.ownCupCount > 0) {
            this.ownCupCount--;
            this.updateOwnCupDisplay();
            console.log('➖ Стаканы:', this.ownCupCount);
        }
    }

    updateOwnCupDisplay() {
        const countInput = document.getElementById('own-cup-count');
        const discountDisplay = document.getElementById('own-cup-discount-display');
        const discountAmount = document.getElementById('own-cup-discount-amount');
        
        if (countInput) {
            countInput.value = this.ownCupCount;
        }

        if (discountDisplay && discountAmount) {
            if (this.ownCupCount > 0) {
                discountDisplay.classList.remove('hidden');
                discountAmount.textContent = this.ownCupCount * 30;
            } else {
                discountDisplay.classList.add('hidden');
            }
        }
    }

    resetOwnCup() {
        this.ownCupCount = 0;
        this.updateOwnCupDisplay();
    }
    
    async start() {
        if (this.video.srcObject) {
            this.video.srcObject.getTracks().forEach(track => track.stop());
            this.video.srcObject = null;
        }
        
        const maxAttempts = 5;
        let attempt = 0;
        
        while (attempt < maxAttempts) {
            try {
                attempt++;
                console.log(`Попытка открыть камеру: ${attempt}/${maxAttempts}`);
                
                if (attempt > 1) {
                    await new Promise(resolve => setTimeout(resolve, 500));
                }
                
                const constraints = {
                    video: {
                        facingMode: { ideal: "environment" },
                        width: { ideal: 1280 },
                        height: { ideal: 720 }
                    },
                    audio: false
                };
                
                const stream = await navigator.mediaDevices.getUserMedia(constraints);
                
                this.video.srcObject = stream;
                
                await new Promise((resolve, reject) => {
                    const timeout = setTimeout(() => {
                        reject(new Error('Video timeout'));
                    }, 5000);
                    
                    this.video.onloadedmetadata = () => {
                        clearTimeout(timeout);
                        this.video.play().then(resolve).catch(reject);
                    };
                    
                    this.video.onerror = () => {
                        clearTimeout(timeout);
                        reject(new Error('Video error'));
                    };
                });
                
                this.scanning = true;
                this.qrCodeFound = false;
                
                console.log('Камера успешно открыта');
                requestAnimationFrame(() => this.scanFrame());
                return;
                
            } catch (error) {
                console.error(`Попытка ${attempt} не удалась:`, error);
                
                if (attempt === maxAttempts) {
                    console.error('Не удалось открыть камеру после всех попыток');
                    
                    let errorMessage = 'Не удалось получить доступ к камере';
                    if (error.name === 'NotAllowedError') {
                        errorMessage = 'Доступ к камере запрещен. Разрешите доступ в настройках.';
                    } else if (error.name === 'NotFoundError') {
                        errorMessage = 'Камера не найдена на устройстве';
                    } else if (error.name === 'NotReadableError') {
                        errorMessage = 'Камера используется другим приложением';
                    }
                    
                    app.showToast(errorMessage);
                    return;
                }
            }
        }
    }
    
    
    
    scanFrame() {
        if (!this.scanning) return;
        
        if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
            this.canvas.height = this.video.videoHeight;
            this.canvas.width = this.video.videoWidth;
            
            this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);

            if (typeof jsQR !== 'undefined') {
                try {
                    const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
                    const code = jsQR(imageData.data, imageData.width, imageData.height);
                    
                    if (code && code.data) {
                        this.handleQRCode(code.data);
                        return;
                    }
                } catch (e) {
                    console.error('Ошибка распознавания QR:', e);
                }
            } else {
                console.error('Библиотека jsQR не подключена!');
                app.showToast('Ошибка: библиотека jsQR не загружена');
            }
        }
        
        requestAnimationFrame(() => this.scanFrame());
    }
    
    handleQRCode(data) {
        this.qrCodeFound = true;
        this.scanning = false;

        if (this.video.srcObject) {
            this.video.srcObject.getTracks().forEach(track => track.stop());
        }

        this.resetOwnCup();
        this.resetBonusInput();
        
        const ownCupContainer = document.getElementById('own-cup-container');
        const BonusesSpend = document.getElementById('bonus-input-container');
        
        try {
            const parsed = JSON.parse(data);
            this.scannedData = parsed;
            
            let message = '';
            
            if (parsed.type === 'coupon') {
                if (ownCupContainer) ownCupContainer.classList.add('hidden');
                if (BonusesSpend) BonusesSpend.classList.add('hidden');
                
                message = `Купон на напиток\n`;
                if (parsed.drink_name) message += `Напиток: ${parsed.drink_name}\n`;
                if (parsed.syrup) message += `Сироп: ${this.decodeSyrup(parsed.syrup)}`;
                
            } else if (parsed.type === 'discount_30') {
                if (BonusesSpend) BonusesSpend.classList.remove('hidden');
                if (ownCupContainer) ownCupContainer.classList.remove('hidden');
                
                message = `Акция скидка 30%\n\n`;
                if (parsed.tg_id) message += `Номер карты владелец №${parsed.tg_id}\n`;
                if (parsed.lottery_number) message += `Номер лотереи №${parsed.lottery_number}\n`;
                if (parsed.drink_name) message += `Напиток: ${parsed.drink_name}\n`;
                 
            } else if (parsed.type === 'loyalty_card') {
                if (BonusesSpend) BonusesSpend.classList.remove('hidden');
                if (ownCupContainer) ownCupContainer.classList.remove('hidden');
                
                message = `Карта лояльности\n\n`;
                if (parsed.name) message += `Владелец карты №${parsed.tg_id}: ${parsed.name}\n`;
                if (parsed.bonus_avaliable) message += `Доступно бонусов для списания: ${parsed.bonus_avaliable}\n`;
                if (parsed.univercity_percent) message += `МЭИ/МТУСИ скидка: ${parsed.univercity_percent}\n`;

                this.updateBonusDisplay(parsed.bonus_avaliable);
                
            } else {
                if (ownCupContainer) ownCupContainer.classList.add('hidden');
                if (BonusesSpend) BonusesSpend.classList.add('hidden');
                message = 'Неизвестный тип QR-кода';
            }
            
            document.getElementById('scanner-result-text').textContent = message;
            document.querySelector('.scanner-result').classList.remove('hidden');
            
        } catch (error) {
            console.error('Ошибка парсинга QR:', error);
            if (ownCupContainer) ownCupContainer.classList.add('hidden');
            
            document.getElementById('scanner-result-text').textContent = 
                'Ошибка чтения QR-кода';
            document.querySelector('.scanner-result').classList.remove('hidden');
        }
    }

    decodeSyrup(syrupKey) {
        const SYRUP_MAP = {
            'vanilla': 'Ваниль',
            'caramel': 'Карамель',
            'chocolate': 'Шоколад',
            'salt_caramel': 'Солёная карамель',
            'strawberry': 'Клубника',
            'no': 'Без сиропа'
        };
        
        return SYRUP_MAP[syrupKey] || syrupKey;
    }
    
    async processResult() {
        if (!this.scannedData) {
            app.showToast('Нет данных для обработки');
            return;
        }

        const ownCupCount = this.ownCupCount;
        const bonusInput = document.getElementById('bonus-amount-input');
        const bonusAmount = bonusInput ? (parseInt(bonusInput.value)) : 0;
        
        try {
            this.scannedData.is_own_cup = ownCupCount;
            this.scannedData.bonus_amount = bonusAmount;

            const result = await api.scanQR( 
                JSON.stringify(this.scannedData),
                app.tgUser?.id,
            );
            
            if (result.success) {
                app.showToast('QR-код успешно обработан!');

                if (result.type === 'coupon') {
                    let message = `Напиток: ${result.drink_name}`;
                    if (result.syrup_name) {
                        message += `\nСироп: ${result.syrup_name}`;
                    }
                    app.showToast(message);

                } else if (result.type === 'discount_30') {
                    let message = `Промоакция применена`;
                    app.showToast(message);
                    
                } else if (result.type === 'loyalty_card') {
                    let message = `Карта лояльности применена. Списано ${bonusAmount} бонусов`;
                    if (ownCupCount) {
                        message += `\nСкидка за свой стакан применена`;
                    }
                    app.showToast(message);
                }

                setTimeout(() => {
                    this.close();
                    app.showProfile(app.profileType);
                }, 1500);
            } else {
                app.showToast(`${result.error || 'Ошибка обработки'}`);
            }
        } catch (error) {
            console.error('Ошибка обработки QR:', error);
            app.showToast('Ошибка обработки QR-кода');
        }
    }

    resetBonusInput() {
        this.availableBonuses = 0;
        const inputEl = document.getElementById('bonus-amount-input');
        if (inputEl) {
            inputEl.value = 0;
            inputEl.style.borderColor = '#ddd';
        }
        document.getElementById('bonus-warning')?.classList.add('hidden');
    }
    
    close() {
        this.scanning = false;
        this.qrCodeFound = false;
        this.scannedData = null;
        this.ownCupCount = 0;
        
        if (this.video.srcObject) {
            this.video.srcObject.getTracks().forEach(track => track.stop());
        }
        
        document.querySelector('.scanner-result').classList.add('hidden');
        app.goBack();
    }
}

window.scanner = new QRScanner();