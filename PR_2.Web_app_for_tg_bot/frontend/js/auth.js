class Auth { 
    selectCoupon() {
        app.showScreen('coupon-screen');
        this.loadDrinks();
    }
    
    selectLoyaltyCard() {
        app.showScreen('loyalty-register-screen');
    }
    
    goBack() {
        app.goBack();
    }
    
    showUserMenu() {
        app.showScreen('user-profile-screen');
    }
}

window.auth = new Auth();