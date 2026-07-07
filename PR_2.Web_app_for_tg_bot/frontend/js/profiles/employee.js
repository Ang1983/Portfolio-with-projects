class Employee {
    constructor() {
        this.scheduleData = {};
        this.currentMonth = new Date();

        this.milkProducts = [];
        this.milkCart = {};
        this.milkOrders = [];

        this.currentEditingOrder = null;
        this.editCart = {}; 

        this.selectedRole = 'employee';
        this.pendingLocation = null;
        this.selectedCashierId = null;  

        this.scheduleData = {};
        this.currentMonth = new Date();
        this.prefMode = false;
        this.prefMonth = new Date();
        this.prefAvailability = {};
        this.prefPriority = [];
        this.prefBlocked = [];
        this.selectedShifts = new Set();
        this.allPoints = [];
    }

    async initPreferencesMode() {
        try {
            // Загружаем список точек
            const res = await fetch(`${API_BASE_URL}/cashiers/`);
            const data = await res.json();
            
            this.allPoints = data.map(c => ({ 
                id: c.id, 
                name: c.short_name_point 
            }));
            
            this.renderPointSelectors();
            this.prefMonth = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth() + 1, 1);
            this.renderCalendarGrid('calendar-grid', this.prefMonth);
            
        } catch (e) {
            console.error('Error loading cashiers:', e);
            app.showToast('Ошибка загрузки точек');
        }
    }
    
    setViewMode() {
        this.prefMode = false;
        
        // Скрываем панели заполнения
        document.getElementById('pref-mode-indicator').classList.add('hidden');
        document.getElementById('shift-toggles-panel').classList.add('hidden');
        document.getElementById('points-selector-panel').classList.add('hidden');
        document.getElementById('pref-actions').classList.add('hidden');

        // Показываем верхние кнопки переключения режимов
        const controls = document.querySelector('.schedule-controls');
        if (controls) controls.style.display = 'flex';
    
        // Рендерим обычный календарь
        this.renderCalendarGrid('calendar-grid', this.currentMonth);
    }

    // Переключение в режим заполнения
    setFillMode() {
        this.prefMode = true;
        
        // Сброс состояния
        this.selectedShifts = new Set();
        this.prefAvailability = {};
        this.prefPriority = [];
        this.prefBlocked = [];
    
        // Скрываем верхние кнопки переключения режимов
        const controls = document.querySelector('.schedule-controls');
        if (controls) controls.style.display = 'none';
    
        // Показываем всё, что нужно для заполнения
        document.getElementById('pref-mode-indicator').classList.remove('hidden');
        document.getElementById('shift-toggles-panel').classList.remove('hidden');
        document.getElementById('points-selector-panel').classList.remove('hidden');
        document.getElementById('pref-actions').classList.remove('hidden');
        document.getElementById('shift-details').classList.add('hidden');
        
        // Сброс тогглов смен
        document.querySelectorAll('.shift-toggles .tog').forEach(t => t.classList.remove('active'));
    
        // Переходим на следующий месяц
        this.prefMonth = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth() + 1, 1);
        this.initPreferencesMode();
    }

    // Переключение типа смены
    toggleShiftType(btn) {
        btn.classList.toggle('active');
        const shift = btn.dataset.shift;
    
        if (btn.classList.contains('active')) {
            this.selectedShifts.add(shift);
        } else {
            this.selectedShifts.delete(shift);
        }
    }

    // Рендер селекторов точек
    renderPointSelectors() {
        const pContainer = document.getElementById('pref-priority');
        const bContainer = document.getElementById('pref-blocked');
        if (!pContainer || !bContainer) return;

        const genBtns = (container, type) => {
            container.innerHTML = this.allPoints.map(p => {
                const isActive = (type === 'priority' ? this.prefPriority : this.prefBlocked).includes(p.name);
                return `<button class="point-btn ${type} ${isActive ? 'active' : ''}" 
                               onclick="employee.togglePoint('${type}', '${p.name}')">
                            ${p.name}
                        </button>`;
            }).join('');
        };
        genBtns(pContainer, 'priority');
        genBtns(bContainer, 'blocked');
    }

    togglePoint(type, name) {
        const arr = type === 'priority' ? this.prefPriority : this.prefBlocked;
        const idx = arr.indexOf(name);
        
        if (idx > -1) {
            arr.splice(idx, 1);
        } else {
            if (type === 'priority' && arr.length >= 3) {
                app.showToast('Можно выбрать не более 3 приоритетных точек');
                return;
            }
            arr.push(name);
        }
        this.renderPointSelectors();
    }
    
    async handleDayClick(dateStr) {
        if (!this.prefMode) return;
    
        if (this.selectedShifts.size === 0) {
            app.showToast('Сначала выберите тип смены (Утро/Вечер/Полная)');
            return;
        }

        // Открываем модалку выбора точки
        this.openDayPointPicker(dateStr);
        
        // Инициализируем массив смен для этой даты
        if (!this.prefAvailability[dateStr]) {
            this.prefAvailability[dateStr] = [];
        }
        
        const currentShifts = this.prefAvailability[dateStr];
        const allSelected = Array.from(this.selectedShifts).every(s => currentShifts.includes(s));
        
        if (allSelected && currentShifts.length === this.selectedShifts.size) {
            // Убираем все выбранные смены
            this.prefAvailability[dateStr] = currentShifts.filter(s => !this.selectedShifts.has(s));
            if (this.prefAvailability[dateStr].length === 0) {
                delete this.prefAvailability[dateStr];
            }
        } else {
            // Добавляем выбранные смены
            this.selectedShifts.forEach(s => {
                if (!this.prefAvailability[dateStr].includes(s)) {
                    this.prefAvailability[dateStr].push(s);
                }
            });
        }

        this.renderCalendarGrid('calendar-grid', this.prefMonth);
    }

    openDayPointPicker(dateStr) {
        this.tempSelectedDate = dateStr; 
        const modal = document.getElementById('day-point-picker-modal').classList.remove('hidden');
        const dateEl = document.getElementById('point-picker-date').classList.remove('hidden');
        const listEl = document.getElementById('point-picker-list').classList.remove('hidden');
        
        const dateObj = new Date(dateStr);
        dateEl.textContent = dateObj.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
        listEl.innerHTML = '';
    
        // Текущая привязка
        const currentData = this.prefAvailability[dateStr] || {};
        const currentFixedId = currentData.fixedPointId;
    
        this.allPoints.forEach(point => {
            const isSelected = currentFixedId === point.id;
            
            const btn = document.createElement('div');
            btn.className = `point-option ${isSelected ? 'selected' : ''}`;
            btn.innerHTML = `
                <span>${point.name}</span>
                ${isSelected ? '<span class="remove-fix">Сбросить</span>' : ''}
            `;
            
            btn.onclick = () => {
                this.assignPointToDate(dateStr, point.id);
                this.closeDayPointPicker();
                this.renderCalendarGrid('calendar-grid', this.prefMonth);
            };
            
            listEl.appendChild(btn);
        });
        
        modal.classList.remove('hidden');
    }

    assignPointToDate(dateStr, pointId) {
        if (!this.prefAvailability[dateStr]) {
            this.prefAvailability[dateStr] = { shifts: [], fixedPointId: null };
        }
        
        // Сохраняем смены
        this.prefAvailability[dateStr].shifts = Array.from(this.selectedShifts);
        
        // Если кликнули на уже выбранную точку — сбрасываем (null), иначе сохраняем ID
        if (this.prefAvailability[dateStr].fixedPointId === pointId) {
            this.prefAvailability[dateStr].fixedPointId = null;
            app.showToast('Привязка точки сброшена');
        } else {
            this.prefAvailability[dateStr].fixedPointId = pointId;
            app.showToast('Точка зафиксирована');
        }
    }
    
    closeDayPointPicker() {
        document.getElementById('day-point-picker-modal').classList.add('hidden');
    }

    enderCalendarGrid(containerId, month = null) {
        const container = document.getElementById(containerId);
        const headerContainer = document.getElementById('calendar-header');
        if (!container || !headerContainer) return;
        
        const targetMonth = month || this.currentMonth;
        const { daysInMonth, firstDayOfMonth } = this.getDaysInMonth(targetMonth);
        const monthName = targetMonth.toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' });
    
        const monthTitle = document.getElementById('schedule-month-title');
        if (monthTitle) monthTitle.textContent = monthName.charAt(0).toUpperCase() + monthName.slice(1);
    
        const weekDays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
        headerContainer.innerHTML = `
            <div class="calendar-header">
                <button type="button" class="cal-nav" onclick="employee.changeMonth(-1)">‹</button>
                <span>${monthName.charAt(0).toUpperCase() + monthName.slice(1)}</span>
                <button type="button" class="cal-nav" onclick="employee.changeMonth(1)">›</button>
            </div>`;
    
        let html = weekDays.map(day => `<div class="calendar-day-header">${day}</div>`).join('');
        const emptyCells = firstDayOfMonth === 0 ? 6 : firstDayOfMonth - 1;
        for (let i = 0; i < emptyCells; i++) html += `<div class="calendar-day empty"></div>`;
    
        const today = new Date();
        const isCurrentMonth = targetMonth.getMonth() === today.getMonth() && targetMonth.getFullYear() === today.getFullYear();
    
        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = `${targetMonth.getFullYear()}-${String(targetMonth.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const isToday = isCurrentMonth && day === today.getDate();
            let classes = 'calendar-day';
            let cellContent = day;
    
            if (this.prefMode) {
                classes += ' pref-selectable';
                const dayData = this.prefAvailability[dateStr];
                const prefShifts = dayData ? dayData.shifts : [];
    
                if (prefShifts.length > 0) {
                    if (prefShifts.length > 1) {
                        classes += ' has-pref-multiple';
                        cellContent = `${day}<small>×${prefShifts.length}</small>`;
                    } else {
                        const shiftClass = { 'morning': 'has-pref-morning', 'evening': 'has-pref-evening', 'full': 'has-pref-full' }[prefShifts[0]];
                        classes += ` ${shiftClass}`;
                    }
                    
                    if (dayData && dayData.fixedPointId) {
                        const point = this.allPoints.find(p => p.id === dayData.fixedPointId);
                        if (point) {
                            cellContent += `<br><span style="font-size:9px; opacity:0.9; font-weight:700;">${point.name}</span>`;
                        }
                    }
                }
                html += `<button class="${classes}" onclick="employee.handleDayClick('${dateStr}')">${cellContent}</button>`;
            } else {
                const shift = this.scheduleData[dateStr];
                if (shift) {
                    const shiftClass = { 'morning': 'has-shift-morning', 'evening': 'has-shift-evening', 'full': 'has-shift-full' }[shift.shift_type];
                    classes += ` has-shift ${shiftClass}`;
                    cellContent = shift.point_code.toUpperCase();
                    if (shift.day_part) cellContent += `<small>${shift.day_part}</small>`;
                }
                if (isToday) classes += ' is-today';
                html += `<button class="${classes}" ${shift ? `onclick="employee.showShiftDetails('${dateStr}')"` : ''}>${cellContent}</button>`;
            }
        }
        container.innerHTML = html;
    }

    async changeMonth(offset) {
        if (this.prefMode) {
            this.prefMonth = new Date(this.prefMonth.getFullYear(), this.prefMonth.getMonth() + offset, 1);
            this.renderCalendarGrid('calendar-grid', this.prefMonth);
        } else {
            const newDate = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth() + offset, 1);
            this.currentMonth = newDate;
            
            const loaded = await this.loadSchedule(this.currentMonth);
            if (loaded) {
                this.renderCalendarGrid('calendar-grid', this.currentMonth);
            }
        }
    }

    clearPreferences() {
        if (confirm('Очистить все выбранные дни и точки?')) {
            this.prefAvailability = {};
            this.prefPriority = [];
            this.prefBlocked = [];
            this.renderPointSelectors();
            this.renderCalendarGrid('calendar-grid', this.prefMonth);
            app.showToast('Все пожелания очищены');
        }
    }

    async savePreferences() {
        const year = this.prefMonth.getFullYear();
        const month = this.prefMonth.getMonth() + 1;
        
        if (Object.keys(this.prefAvailability).length === 0) {
            app.showToast('Выберите хотя бы один день для работы');
            return;
        }
        
        const payload = {
            tg_id: app.tgUser?.id,
            messanger: app.messanger,
            year, 
            month,
            availability: this.prefAvailability, 
            priority_points: this.prefPriority,
            blocked_points: this.prefBlocked
        };
    
        try {
            const response = await fetch(`${API_BASE_URL}/preferences/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const res = await response.json();
            if (res.status === 'success' || response.ok) {
                app.showToast('Пожелания сохранены!');
                this.setViewMode();
            } else {
                throw new Error(res.error || 'Ошибка сохранения');
            }
        } catch (error) {
            console.error('Save error:', error);
            app.showToast(error.message || 'Ошибка сети');
        }
    }

    async showSchedule() {
        const modal = document.getElementById('schedule-modal');
        if (!modal) {
            app.showToast('Ошибка: модальное окно не найдено');
            return;
        }
    
        if (Object.keys(this.scheduleData).length === 0) {
            const loaded = await this.loadSchedule();
            if (!loaded) return;
        }
    
        // Сбрасываем в режим просмотра при открытии
        this.prefMode = false;
        this.setViewMode();
        
        this.renderCalendarGrid('calendar-grid', this.currentMonth);
        modal.classList.remove('hidden');
    }
    


    async loadSchedule(month = null) {
        const tgId = app.tgUser?.id;
        if (!tgId) {
            app.showToast('Ошибка: пользователь не авторизован');
            return false;
        }

        try {
            const targetMonth = month || this.currentMonth;
            const monthStr = `${targetMonth.getFullYear()}-${String(targetMonth.getMonth() + 1).padStart(2, '0')}`;
            
            const data = await api.getShifts(app.tgUser.id, monthStr, app.messanger);
            
            if (data.error) {
                app.showToast(data.error);
                return false;
            }

            this.scheduleData = {};
            data.shifts.forEach(shift => {
                this.scheduleData[shift.date] = shift;
            });
            
            return true;
            
        } catch (error) {
            console.error('Error loading schedule:', error);
            app.showToast('Ошибка загрузки графика', error);
            return false;
        }
    }

    async changeMonth(offset) {
        const newDate = new Date(this.currentMonth.getFullYear(), this.currentMonth.getMonth() + offset, 1);
        this.currentMonth = newDate;
        
        const loaded = await this.loadSchedule(this.currentMonth);
        if (loaded) {
            this.renderCalendarGrid('calendar-grid', this.currentMonth);
        }
    }
    
    handleDayClick(dateStr) {
        if (!this.prefMode) return;
        
        if (this.selectedShifts.size === 0) {
            app.showToast('Сначала выберите тип смены (Утро/Вечер/Полная)');
            return;
        }
    
        if (!this.prefAvailability[dateStr]) {
            this.prefAvailability[dateStr] = [];
        }
    
        const currentShifts = this.prefAvailability[dateStr];
        const allSelected = Array.from(this.selectedShifts).every(s => currentShifts.includes(s));
        const sameCount = this.selectedShifts.size === currentShifts.length;
    
        if (allSelected && sameCount) {
            // Убираем все выбранные смены с этого дня
            delete this.prefAvailability[dateStr];
        } else {
            // Добавляем выбранные смены
            this.selectedShifts.forEach(s => {
                if (!this.prefAvailability[dateStr].includes(s)) {
                    this.prefAvailability[dateStr].push(s);
                }
            });
        }
        
        // Перерисовываем календарь с новыми отметками
        this.renderCalendarGrid('calendar-grid', this.prefMonth);
    }

    renderCalendarGrid(containerId, month = null) {
        const container = document.getElementById(containerId);
        const headerContainer = document.getElementById('calendar-header');
        if (!container || !headerContainer) return;
        
        const targetMonth = month || this.currentMonth;
        const { daysInMonth, firstDayOfMonth } = this.getDaysInMonth(targetMonth);
        const monthName = targetMonth.toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' });
    
        const monthTitle = document.getElementById('schedule-month-title');
        if (monthTitle) {
            monthTitle.textContent = monthName.charAt(0).toUpperCase() + monthName.slice(1);
        }
    
        const weekDays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    
        headerContainer.innerHTML = `
            <div class="calendar-header">
                <button type="button" class="cal-nav" onclick="employee.changeMonth(-1)">‹</button>
                <span>${monthName.charAt(0).toUpperCase() + monthName.slice(1)}</span>
                <button type="button" class="cal-nav" onclick="employee.changeMonth(1)">›</button>
            </div>
        `;
    
        let html = weekDays.map(day => 
            `<div class="calendar-day-header">${day}</div>`
        ).join('');
    
        const emptyCells = firstDayOfMonth === 0 ? 6 : firstDayOfMonth - 1;
        for (let i = 0; i < emptyCells; i++) {
            html += `<div class="calendar-day empty"></div>`;
        }

        const today = new Date();
        const isCurrentMonth = targetMonth.getMonth() === today.getMonth() && 
                              targetMonth.getFullYear() === today.getFullYear();
    
        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = `${targetMonth.getFullYear()}-${String(targetMonth.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const isToday = isCurrentMonth && day === today.getDate();
        
            let classes = 'calendar-day';
            let cellContent = day;
        
            if (this.prefMode) {
                // РЕЖИМ ЗАПОЛНЕНИЯ
                classes += ' pref-selectable';
                const prefShifts = this.prefAvailability[dateStr] || [];
            
                if (prefShifts.length > 0) {
                    // Определяем стиль на основе выбранных смен
                    if (prefShifts.includes('full') && prefShifts.length === 1) {
                        classes += ' has-pref-full';
                        cellContent = `<span class="shift-letter">П</span>`;
                    } else if (prefShifts.includes('morning') && !prefShifts.includes('evening')) {
                        classes += ' has-pref-morning';
                        cellContent = `<span class="shift-letter">У</span>`;
                    } else if (prefShifts.includes('evening') && !prefShifts.includes('morning')) {
                        classes += ' has-pref-evening';
                        cellContent = `<span class="shift-letter">В</span>`;
                    } else {
                        // Несколько смен или комбинации
                        classes += ' has-pref-mixed';
                        const letters = prefShifts.map(s => {
                            return s === 'morning' ? 'У' : s === 'evening' ? 'В' : 'П';
                        }).join('');
                        cellContent = `<span class="shift-letter">${letters}</span>`;
                    }
                }
            
                html += `
                    <button 
                        class="${classes}" 
                        data-date="${dateStr}"
                        onclick="employee.handleDayClick('${dateStr}')"
                    >
                        ${cellContent}
                    </button>
                `;
            
            } else {
                // РЕЖИМ ПРОСМОТРА
                const shift = this.scheduleData[dateStr];
            
                if (shift) {
                    const shiftClass = {
                        'morning': 'has-shift-morning',
                        'evening': 'has-shift-evening',
                        'full': 'has-shift-full'
                    }[shift.shift_type];
                
                    classes += ` has-shift ${shiftClass}`;
                    cellContent = shift.point_code.toUpperCase();
                    if (shift.day_part) {
                        cellContent += `<small>${shift.day_part}</small>`;
                    }
                }

                if (isToday) {
                    classes += ' is-today';
                }
                
                html += `
                    <button 
                        class="${classes}" 
                        data-date="${dateStr}"
                        ${shift ? `onclick="employee.showShiftDetails('${dateStr}')"` : ''}
                    >
                        ${cellContent}
                    </button>
                `;
            }
        }
        
        container.innerHTML = html;
    }

    
    showShiftDetails(dateStr) {
        const shift = this.scheduleData[dateStr];
        const details = document.getElementById('shift-details');
        if (!details || !shift) return;

        document.getElementById('pref-actions').classList.add('hidden');
        
        const date = new Date(dateStr + 'T00:00:00');
        const dayName = date.toLocaleDateString('ru-RU', { 
            weekday: 'long', 
            day: 'numeric', 
            month: 'long' 
        });
        
        const partText = {
            'morning': 'Утренняя смена',
            'evening': 'Вечерняя смена',
            'full': 'Полная смена'
        }[shift.shift_type] || '';
        
        details.innerHTML = `
            <h3 class="shift-details-title">
                ${partText}<br>
                <small>${dayName}</small>
            </h3>
            
            <div class="shift-detail-item">
                <span class="shift-detail-icon"></span>
                <div>
                    <p class="shift-detail-label">Адрес</p>
                    <p class="shift-detail-value">${shift.address}</p>
                </div>
            </div>
            
            <div class="shift-detail-item">
                <span class="shift-detail-icon"></span>
                <div>
                    <p class="shift-detail-label">Ваша смена</p>
                    <p class="shift-detail-value shift-time">
                        ${shift.shift_start} — ${shift.shift_end}
                    </p>
                </div>
            </div>
            
            <div class="shift-detail-item">
                <span class="shift-detail-icon"></span>
                <div>
                    <p class="shift-detail-label">Часы работы кофейни</p>
                    <p class="shift-detail-value">${shift.cafe_hours}</p>
                </div>
            </div>
            
            ${shift.day_part ? `
            <div class="shift-note">
                <span class="shift-note-icon"></span>
                <p>Вы работаете ${shift.day_part === 'у' ? 'первую половину' : 'вторую половину'} дня</p>
            </div>
            ` : ''}
        `;
        
        details.classList.remove('hidden');

        if (window.innerWidth < 768) {
            details.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    closeSchedule() {
        this.setViewMode();
        
        const modal = document.getElementById('schedule-modal');
        const details = document.getElementById('shift-details');
        if (modal) modal.classList.add('hidden');
        if (details) details.classList.add('hidden');
    }
    
    showSalary() {
        app.showToast('Зарплата за неделю: 0₽');
    }
    
    openQRScanner() {
        console.log('Открытие сканера сотрудника');

        const screen = document.getElementById('qr-scanner-screen');
        if (!screen) {
            console.error('Экран сканера не найден');
            app.showToast('Ошибка: сканер недоступен');
            return;
        }

        const resultModal = document.querySelector('.scanner-result');
        if (resultModal) {
            resultModal.classList.add('hidden');
            document.getElementById('scanner-result-text').textContent = '';
            document.getElementById('own-cup-container')?.classList.add('hidden');
        }

        app.showScreen('qr-scanner-screen');

        setTimeout(() => {
            if (window.scanner) {
                console.log('Запуск камеры...');
                window.scanner.start();
            } else {
                console.error('window.scanner не инициализирован');
                app.showToast('Ошибка загрузки сканера');
            }
        }, 300);
    }
    
    async showDailyStats() {
        try {
            const today = new Date().toISOString().split('T')[0];
            const stats = await api.getDailyStats(app.tgUser.id, today, app.messanger,);

            if (stats.shift_status === 'ok') {
                const statsHTML = `
                    <h3>Статистика за ${this.formatDate(today)}</h3>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <span class="stat-label">Выручка</span>
                            <span class="stat-value">${stats.total_for_day}₽</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Моя выручка</span>
                            <span class="stat-value">${stats.total_revenue}₽</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Наличные за день</span>
                            <span class="stat-value">${stats.cash}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Чеков</span>
                            <span class="stat-value">${stats.receipt_count}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Купонов</span>
                            <span class="stat-value">${stats.coupon_count}</span>
                        </div>
                    </div>
                `;
                
                this.showTemporaryScreen('Статистика дня', statsHTML);
    
            } else {
                const statsHTML = `
                    <h3>Статистика за ${this.formatDate(today)}</h3>
                    <div class="stats-grid">
                        <div class="stat-item">
                        </div>
                    </div>
                    <p style="text-align: center; color: #666; margin: 20px 0;">
                        Смена ещё не начата
                    </p>
                `;
                
                this.showTemporaryScreen('Статистика дня', statsHTML);
            }
            
        } catch (error) {
            console.error('Ошибка загрузки статистики:', error);
            app.showToast('Ошибка загрузки статистики');
        }
    }
    
    showTemporaryScreen(title, content) {
        const tempDiv = document.createElement('div');
        tempDiv.className = 'screen';
        tempDiv.id = 'temp-screen';
        tempDiv.innerHTML = `
            <button class="back-btn" onclick="app.goBack()">Назад</button>
            <h2>${title}</h2>
            <div class="temp-content">${content}</div>
        `;
        
        document.body.appendChild(tempDiv);
        app.showScreen('temp-screen');
    }
    
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('ru-RU', { 
            day: 'numeric', 
            month: 'long',
            weekday: 'short'
        });
    }
    
    getMonthName(monthIndex) {
        const months = ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
                       'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь'];
        return months[monthIndex];
    }

    getDaysInMonth(date) {
        const year = date.getFullYear();
        const month = date.getMonth();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const firstDayOfMonth = new Date(year, month, 1).getDay();
        return { daysInMonth, firstDayOfMonth };
    }

    async loadMilkData() {
        const tgId = app.tgUser?.id;
        if (!tgId) {
            app.showToast('Ошибка: пользователь не авторизован');
            return false;
        }
    
        try {
            const productsRes = await api.getMilk();
            const ordersRes = await api.getMilkOrders(tgId, app.messanger);
            
            if (productsRes.error) {
                app.showToast(productsRes.message || 'Ошибка загрузки товаров');
                return false;
            }
    
            if (ordersRes.error) {
                app.showToast(ordersRes.message || 'Ошибка загрузки заказов');
                return false;
            }
    
            this.milkProducts = [];
            productsRes.data.forEach(product => {
                this.milkProducts.push(product);
            });

            this.milkProducts.sort((a,b) => a.id - b.id)
    
            this.milkOrders = [];
            if (Array.isArray(ordersRes?.data)) {
                ordersRes.data.forEach(order => {
                    this.milkOrders.push(order);
                });
            } else {
                console.warn('ordersRes.data is not an array:', ordersRes?.data);
            }    
            
            return true;
            
        } catch (error) {
            console.error('Error loading milk data:', error);
            app.showToast('Ошибка загрузки данных', error);
            return false;
        }
    }

    renderMilkProducts() {
        const container = document.getElementById('milk-products-grid');
        if (!container) return;

        if (!this.milkProducts.length) {
            container.innerHTML = '<p class="empty-state">Товары не найдены</p>';
            return;
        }

        container.innerHTML = this.milkProducts.map(milk => {
            const qty = this.milkCart[milk.id] || 0;
            return `
                <div class="milk-product-card" data-milk-id="${milk.id}">
                    <div class="milk-product-info">
                        <h4 class="milk-product-name">${milk.name_product}</h4>
                        <p class="milk-product-unit">${milk.unit} шт.</p>
                    </div>
                    <div class="milk-qty-control">
                        <button type="button" class="qty-btn minus" 
                                onclick="employee.updateMilkQty(${milk.id}, -1)"
                                ${qty === 0 ? 'disabled' : ''}>
                            −
                        </button>
                        <span class="qty-value">${qty}</span>
                        <button type="button" class="qty-btn plus" 
                                onclick="employee.updateMilkQty(${milk.id}, 1)">
                            +
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    updateMilkQty(milkId, change) {
        const current = this.milkCart[milkId] || 0;
        const product = this.milkProducts.find(p => p.id === milkId);
        const unitQty = product?.unit || 1;
        
        let newVal;
        if (change > 0) {
            newVal = current + unitQty;
        } else {
            newVal = Math.max(0, current - unitQty);
        }
    
        if (newVal === 0) {
            delete this.milkCart[milkId];
        } else {
            this.milkCart[milkId] = newVal;
        }
    
        this.renderMilkProducts();
        this.updateCartBadge();
    }
    
    async submitMilkOrder() {
        const tgId = app.tgUser?.id;
        if (!tgId) {
            app.showToast('Ошибка: пользователь не авторизован');
            return;
        }
    
        const items = Object.entries(this.milkCart).map(([milk_id, quantity]) => ({
            milk_id: parseInt(milk_id),
            quantity
        }));
    
        const commentEl = document.getElementById('milk-order-comment-modal');
        const comment = commentEl ? commentEl.value.trim() : '';
    
        if (items.length === 0) {
            app.showToast('Добавьте хотя бы один товар');
            return;
        }
    
        const submitBtn = document.getElementById('milk-submit-btn-modal');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Оформление...';
        }
    
        try {
            const response = await api.postMilkOrder(tgId, app.messanger, items, comment);
    
            console.log('Order response:', response);
    
            if (response?.status === 'success') {
                app.showToast((response.message || 'Заказ оформлен'));
    
                this.milkCart = {};
                if (commentEl) commentEl.value = '';
    
                this.hideCartModal();
                this.updateCartBadge();
                await this.loadMilkData();
                this.renderMilkProducts();
                this.renderOrdersHistoryModal();
            } else {
                app.showToast((response?.message || 'Ошибка создания заказа'));
            }
        } catch (error) {
            console.error('Error submitting order:', error);
            app.showToast('Ошибка оформления заказа: ' + error.message);
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Оформить заказ';
            }
        }
    }
    
    async cancelMilkOrder(orderId) {
        if (!confirm('Вы уверены, что хотите отменить заказ?')) return;
    
        try {
            const response = await api.postCancelMilkOrder(orderId, app.tgId, app.messanger);
    
            if (!response.error) {
                app.showToast((response.message || 'Заказ отменён'));
                await this.loadMilkData();
                this.renderOrdersHistoryModal();
            } else {
                app.showToast((response.message || 'Ошибка отмены заказа'));
            }
        } catch (error) {
            console.error('Error canceling order:', error);
            app.showToast('Ошибка отмены заказа');
        }
    }

    async confirmMilkOrder(orderId) {
        console.log('=== confirmMilkOrder вызван ===');
        console.log('Order ID:', orderId);
        console.log('Все заказы:', this.milkOrders);
        
        const order = this.milkOrders.find(o => o.id === orderId);
        
        if (!order) {
            console.error('Заказ не найден! ID:', orderId);
            app.showToast('Заказ не найден');
            return;
        }
    
        console.log('Найден заказ:', order);
        console.log('Товары в заказе:', order.items);

        this.currentEditingOrder = order;

        this.editCart = {};
        
        if (order.items && order.items.length > 0) {
            order.items.forEach(item => {
                const milkId = item.milk?.id || item.milk_id;
                
                if (milkId) {
                    this.editCart[milkId] = {
                        ordered: item.quantity,
                        actual: item.quantity,
                        name: item.milk?.name_product,
                        unit: item.milk?.unit
                    };
                }
            });
        }
        
        console.log('editCart после заполнения:', this.editCart);
        console.log('Количество товаров:', Object.keys(this.editCart).length);
    
        const orderDate = new Date(order.created_at);
        const dateStr = orderDate.toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'long',
            year: 'numeric',
        });
    
        const modalTitle = document.getElementById('modalOrderId');
        if (modalTitle) {
            modalTitle.innerText = `${order.cashier} - ${dateStr}`;
        }
        
        this.openModal('modalConfirmDelivery');
    }
    
    async showMilkOrder() {
        app.showScreen('milk-order-screen');
        
        const loaded = await this.loadMilkData();
        if (loaded) {
            this.renderMilkProducts();
            this.updateCartBadge();
        }
    }

    showCartModal() {
        const modal = document.getElementById('cart-modal');
        if (modal) {
            this.renderCartModal();
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
        }
    }
    
    hideCartModal() {
        const modal = document.getElementById('cart-modal');
        if (modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = '';
        }
    }
    
    renderCartModal() {
        const container = document.getElementById('cart-items-modal');
        const totalEl = document.getElementById('cart-total-modal');
        const submitBtn = document.getElementById('milk-submit-btn-modal');
        
        if (!container) return;
    
        const items = Object.entries(this.milkCart);

        const totalAmount = items.reduce((sum, [milkId, qty]) => {
            const product = this.milkProducts.find(p => p.id == milkId);
            const price = product?.count;
            return sum + (price * qty);
        }, 0);

        const totalQty = items.reduce((sum, [, qty]) => sum + qty, 0);
    
        if (totalEl) {
            totalEl.textContent = `${totalAmount.toLocaleString('ru-RU')} ₽`;
        }
    
        if (items.length === 0) {
            container.innerHTML = '<p class="empty-cart">Корзина пуста</p>';
            if (submitBtn) submitBtn.disabled = true;
        } else {
            container.innerHTML = items.map(([id, qty]) => {
                const product = this.milkProducts.find(p => p.id == id);
                const name = product ? product.name_product : `Товар #${id}`;
                const unit = product ? product.unit : 1;
                const price = product?.count || 0;
                const itemTotal = price * qty;
                
                return `
                    <div class="cart-item-modal">
                        <div class="cart-item-info">
                            <div class="cart-item-name">${name}</div>
                            <div class="cart-item-qty">${price} × ${qty} = ${itemTotal.toLocaleString('ru-RU')} ₽</div>
                        </div>
                        <div class="cart-item-controls">
                            <span style="font-weight: 600; color: #9333ea;">${qty} шт.</span>
                            <button class="cart-item-remove" onclick="employee.removeFromCart(${id})">
                                ✕
                            </button>
                        </div>
                    </div>
                `;
            }).join('');
            if (submitBtn) submitBtn.disabled = false;
        }
    }
    
    removeFromCart(milkId) {
        delete this.milkCart[milkId];
        this.renderCartModal();
        this.renderMilkProducts();
        this.updateCartBadge();
    }
    
    updateCartBadge() {
        const badge = document.getElementById('cart-badge');
        const totalQty = Object.values(this.milkCart).reduce((sum, qty) => sum + qty, 0);
        
        if (badge) {
            if (totalQty > 0) {
                badge.textContent = totalQty;
                badge.classList.remove('hidden');
            } else {
                badge.classList.add('hidden');
            }
        }
    }

    showOrdersHistoryModal() {
        const modal = document.getElementById('orders-history-modal');
        if (modal) {
            this.renderOrdersHistoryModal();
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
        }
    }
    
    hideOrdersHistoryModal() {
        const modal = document.getElementById('orders-history-modal');
        if (modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = '';
        }
    }
    
    renderOrdersHistoryModal() {
        const container = document.getElementById('orders-history-modal-list');
        if (!container) return;
    
        if (!this.milkOrders.length) {
            container.innerHTML = '<p class="empty-state">У вас пока нет заказов</p>';
            return;
        }
    
        container.innerHTML = this.milkOrders.map(order => {
            const statusClass = `status-${order.status}`;
            const statusText = {
                'pending': 'Ожидает',
                'confirmed': 'Подтверждён',
                'completed': 'Выполнен',
                'cancelled': 'Отменён',
                'problem': 'Недовоз'
            }[order.status] || order.status;
    
            const itemsList = order.items.map(item => `
                <div class="order-item-row">
                    ${item.milk?.name_product || 'Товар'} — ${item.quantity} шт.
                </div>
            `).join('');
    
            const orderDate = new Date(order.created_at);
            const dateStr = orderDate.toLocaleDateString('ru-RU', {
                day: 'numeric',
                month: 'long',
                year: 'numeric',
            });
    
            return `
                <div class="order-card-modal">
                    <div class="order-header-modal">
                        <span class="order-id-modal">Заказ ${order.cashier}</span>
                        <span class="order-status-modal ${statusClass}">${statusText}</span>
                    </div>
                    <div class="order-date-modal">${dateStr}</div>
                    <div class="order-items-modal">
                        ${itemsList}
                    </div>
                    ${order.comment ? `<div class="order-comment-modal">${order.comment}</div>` : ''}
                    ${order.status === 'pending' ? `
                        <button class="order-cancel-btn" onclick="employee.cancelMilkOrder(${order.id})">
                            Отменить заказ
                        </button>
                    ` : ''}
                    ${order.status === 'confirmed' ? `
                        <button class="order-cancel-btn" onclick="employee.confirmMilkOrder(${order.id})">
                            Подтвердить заказ
                        </button>
                    ` : ''}
                </div>
            `;
        }).join('');
    }

    showProblemModal() {
        this.closeModal('modalConfirmDelivery');
        this.renderEditOrderItems();
        this.openModal('modalEditOrder');
    }

    renderEditOrderItems() {
        const container = document.getElementById('orderItemsList');
        if (!container) return;

        const items = Object.entries(this.editCart);

        if (items.length === 0) {
            container.innerHTML = '<div style="padding:10px; text-align:center; color:#777">Нет товаров</div>';
            return;
        }

        container.innerHTML = items.map(([id, data]) => {
            const isReduced = data.actual < data.ordered;
            return `
                <div class="order-item-row ${isReduced ? 'reduced' : ''}">
                    <div class="item-info">
                        <span class="item-name">${data.name}</span>
                        <div class="item-qty-display">
                            <span class="original">заказано: ${data.ordered}</span>
                        </div>
                    </div>
                    <div class="qty-controller">
                        <span class="qty-value">${data.actual} шт. </span>
                        <button class="btn-minus" 
                                onclick="employee.updateEditQty(${id})" 
                                ${data.actual <= 0 ? 'disabled' : ''}>
                            −
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    updateEditQty(milkId) {
        const item = this.editCart[milkId];
        const product = this.milkProducts.find(p => p.id === milkId);
        let unit
        if (milkId === 9) {
            unit = 1;
        } else {
            unit = product?.unit
        }
        if (!item) return;
        
        let newVal = item.actual - unit;

        if (newVal < 0) newVal = 0;

        item.actual = newVal;

        this.renderEditOrderItems();
    }


    async submitEditedOrder() {
        const tgId = app.tgUser?.id;
        if (!tgId) {
            app.showToast('Ошибка: пользователь не авторизован');
            return;
        }

        if (!this.currentEditingOrder) {
            app.showToast('Ошибка: нет текущего заказа');
            return;
        }

        const items = Object.entries(this.editCart).map(([milk_id, data]) => ({
            product_id: milk_id,
            ordered_quantity: data.ordered,
            actual_quantity: data.actual
        }));

        const commentEl = document.getElementById('editOrderComment');
        const comment = commentEl ? commentEl.value.trim() : '';

        if (items.length === 0) {
            app.showToast('Добавьте хотя бы один товар');
            return;
        }

        const submitBtn = document.querySelector('#modalEditOrder .btn-primary');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Сохранение...';
        }

        try {
            const response = await api.updatePartialMilkOrder(
                this.currentEditingOrder.id,
                items,
                comment
            );

            console.log('Response:', response);

            if (response?.status === 'success') {
                app.showToast(response.message || 'Изменения сохранены');

                this.editCart = {};
                if (commentEl) commentEl.value = '';

                this.closeModal('modalEditOrder');
                await this.loadMilkData();
                this.renderOrdersHistoryModal();
            } else {
                app.showToast(response?.message || 'Ошибка сохранения');
            }
        } catch (error) {
            console.error('Error updating order:', error);
            app.showToast('Ошибка сохранения: ' + error.message);
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Сохранить';
            }
        }
    }

    async handleAllArrived() {
        if (!this.currentEditingOrder) return;
        this.closeModal('modalConfirmDelivery');
        
        const response = await api.completeMilkOrder(this.currentEditingOrder.id, app.tgId, app.messanger);
        if (!response.error) {
            app.showToast('Заказ завершен');
            await this.loadMilkData();
            this.renderOrdersHistoryModal();
        } else {
            app.showToast(response.message || 'Ошибка');
        }
    }
    
    openModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.style.display = 'flex';
        setTimeout(() => modal.classList.add('active'), 10);
    }
    
    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.classList.remove('active');
        setTimeout(() => modal.style.display = 'none', 300);
    }

    async getCurrentLocation() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Геолокация не поддерживается вашим браузером'));
                return;
            }
    
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    resolve({
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude
                    });
                },
                (error) => {
                    switch(error.code) {
                        case 1:
                            reject(new Error('Доступ к геолокации запрещен'));
                            break;
                        case 2:
                            reject(new Error('Позиция недоступна'));
                            break;
                        case 3:
                            reject(new Error('Превышено время ожидания'));
                            break;
                        default:
                            reject(new Error('Ошибка получения местоположения'));
                    }
                },
                {
                    enableHighAccuracy: true,
                    timeout: 15000,
                    maximumAge: 0
                }
            );
        });
    }
    

    async detectPoint(latitude, longitude) {
        try {
            const response = await fetch(`${API_BASE_URL}/detect-point/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    latitude: latitude,
                    longitude: longitude
                })
            });
    
            const result = await response.json();
    
            if (result.status !== 'success') {
                throw new Error(result.message);
            }
    
            return result.data;
    
        } catch (error) {
            console.error('Detect point error:', error);
            throw error;
        }
    }


    async startShift(latitude, longitude, cashierId, role) {
        try {
            const response = await fetch(`${API_BASE_URL}/start-shift/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    tg_id: app.tgUser?.id,
                    messenger: app.messanger,
                    latitude: latitude,
                    longitude: longitude,
                    cashier_id: cashierId,
                    role: role
                })
            });
    
            const result = await response.json();
            return result;
    
        } catch (error) {
            console.error('Start shift error:', error);
            throw error;
        }
    }
    
    async startShiftFlow() {
        try {
            app.showToast('Определение местоположения...');

            const location = await this.getCurrentLocation();
            console.log('Location:', location);

            app.showToast('Поиск ближайшей точки...');
            const detectData = await this.detectPoint(location.latitude, location.longitude);
            console.log('Detect data:', detectData);
  
            this.pendingLocation = {
                latitude: location.latitude,
                longitude: location.longitude,
                allPoints: detectData.all_points
            };

            this.showPointConfirmation(detectData);
    
        } catch (error) {
            console.error('Start shift flow error:', error);
            app.showToast(`${error.message}`);
        }
    }
    

    showPointConfirmation(data) {
        const closest = data.closest_point;
        const isWithinRange = data.is_within_range;

        app.showScreen('point-confirmation-screen');

        const pointNameEl = document.getElementById('detected-point-name');
        const distanceEl = document.getElementById('detected-distance');
        const confirmBtn = document.getElementById('confirm-point-btn');
        const chooseOtherBtn = document.getElementById('choose-other-point-btn');
        const pointsListEl = document.getElementById('points-list');
    
        if (pointNameEl) {
            pointNameEl.textContent = closest.name;
        }
        if (distanceEl) {
            distanceEl.textContent = `${closest.distance}`;
        }

        if (isWithinRange) {
            if (confirmBtn) confirmBtn.style.display = 'block';
            if (chooseOtherBtn) chooseOtherBtn.style.display = 'block';
            if (pointsListEl) pointsListEl.classList.add('hidden');
        } else {
            if (confirmBtn) confirmBtn.style.display = 'none';
            if (chooseOtherBtn) chooseOtherBtn.style.display = 'none';
            if (pointsListEl) {
                pointsListEl.classList.remove('hidden');
                this.renderPointsList(data.all_points);
            }
        }
    }
    

    renderPointsList(points) {
        const container = document.getElementById('points-list');
        if (!container) return;
    
        container.innerHTML = '<h3>Все доступные точки:</h3>';
    
        points.forEach(point => {
            const card = document.createElement('div');
            card.className = 'point-card';
            card.innerHTML = `
                <h4>${point.name}</h4>
                <p>${point.distance_formatted}</p>
            `;
            card.onclick = () => this.selectPoint(point.id);
            container.appendChild(card);
        });
    }
    

    selectPoint(cashierId) {
        this.selectedCashierId = cashierId;
        this.confirmShift();
    }


    showPointsList() {
        const pointsListEl = document.getElementById('points-list');
        const confirmBtn = document.getElementById('confirm-point-btn');
        const chooseOtherBtn = document.getElementById('choose-other-point-btn');

        if (pointsListEl) {
            pointsListEl.classList.remove('hidden');

            if (this.pendingLocation?.allPoints) {
                this.renderPointsList(this.pendingLocation.allPoints);
            }
        }

        if (confirmBtn) confirmBtn.style.display = 'none';
        if (chooseOtherBtn) chooseOtherBtn.style.display = 'none';
    }
    
    async confirmShift() {
        try {
            app.showToast('Запуск смены...');
    
            const cashierId = this.selectedCashierId || this.pendingLocation.allPoints[0].id;
    
            const result = await this.startShift(
                this.pendingLocation.latitude,
                this.pendingLocation.longitude,
                cashierId,
                this.selectedRole
            );
    
            if (result.status === 'success') {
                app.showToast(`${result.message}\n${result.data.point}\n${result.data.time}`);

                setTimeout(() => {
                    app.loadApp();
                }, 1500);
            } else {
                app.showToast(`${result.message}`);
            }
    
        } catch (error) {
            console.error('Confirm shift error:', error);
            app.showToast(`${error.message}`);
        }
    }
    

    selectRole(role) {
        this.selectedRole = role;

        document.querySelectorAll('.role-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        const selectedCard = document.querySelector(`.role-card[data-role="${role}"]`);
        if (selectedCard) {
            selectedCard.classList.add('selected');
        }
    }

    showRoleSelection() {
        app.showScreen('role-selection-screen');
    }
}

window.employee = new Employee();