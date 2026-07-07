class Coupon {
    constructor() {
        this.selectedDrinkName = null;
        this.selectedSyrupName = null;
    }
    
    selectDrink(drinkName) {
        this.selectedDrinkName = drinkName;
        console.log('Выбран напиток:', drinkName);
        app.showScreen('syrup-screen');
    }
    
    selectSyrup(choice) {
        if (choice === 'yes') {
            app.showScreen('syrup-type-screen');
            this.loadSyrups();
        } else {
            this.createCoupon('no');
        }
    }
    
    async createCoupon(syrup) {
        try {
            if (!this.selectedDrinkName) {
                console.error('Напиток не выбран!');
                app.showToast('Ошибка: напиток не выбран');
                return;
            }
            
            console.log('Создание купона с именем напитка:', {
                tg_id: app.tgUser?.id,
                drink_name: this.selectedDrinkName,
                syrup: syrup || 'no'
            });
            
            const response = await api.createCoupon({
                tg_id: app.tgUser.id,
                messanger: app.messanger,
                drink_name: this.selectedDrinkName,
                syrup: syrup || 'no'
            });

            const qrImg = document.getElementById('qr-code-img');
            if (qrImg) {
                qrImg.src = response.qr_code;
            }
            
            app.showScreen('qr-result-screen');
            app.showToast('Купон успешно создан!');
            
        } catch (error) {
            console.error('Ошибка создания купона:', error);
            app.showToast('Ошибка создания купона: ' + (error.message || 'Неизвестная ошибка'));
        }
    }
}

window.coupon = new Coupon();