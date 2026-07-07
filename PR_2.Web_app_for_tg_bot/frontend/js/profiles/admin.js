class Admin {
    constructor() {
        this.milkOrders = [];
        this.milkStats = {};
        this.cashierCache = {};
    }

    async loadMilkOrders(statuses = []) {
        try {
            const response = await api.getAllMilkOrders(statuses);

            if (response?.status === 'success') {
                this.milkOrders = response.data || [];
                this.milkStats = response.stats || {};

                return true;
            } else {
                app.showToast('Ошибка загрузки заказов: ' + (response.message || 'Неизвестная ошибка'));
                return false;
            }
        } catch (error) {
            console.error('Error loading milk orders:', error);
            app.showToast('Ошибка загрузки заказов: ' + error.message);
            return false;
        }
    }

    async showMilkOrders() {
        app.showScreen('admin-milk-orders-screen');

        const statuses = ['pending', 'confirmed'];
        
        const loaded = await this.loadMilkOrders(statuses);
        if (loaded) {
            this.renderMilkOrdersByAddress();
            this.renderMilkStats();
        }
    }

    groupOrdersByAddress(orders) {
        const grouped = {};

        if (!orders || orders.length === 0) {
            return [];
        }
    
        orders.forEach(order => {
            const address = order.cashier;
            const fullAddress = order.cashier_address;
            
            if (!grouped[address]) {
                grouped[address] = {
                    address: address,
                    fullAddress: fullAddress,
                    orders: [],
                    items: {},
                    totalAmount: 0
                };
            }
    
            grouped[address].orders.push(order);
    
            order.items.forEach(item => {
                const productName = item.milk?.name_product;
                const quantity = item.quantity;
                const price = item.milk?.count;
                
                if (!grouped[address].items[productName]) {
                    grouped[address].items[productName] = {
                        quantity: 0,
                        total: 0
                    };
                }
                
                grouped[address].items[productName].quantity += quantity;
                grouped[address].items[productName].total += price * quantity;
                grouped[address].totalAmount += price * quantity;
            });
        });

        return Object.values(grouped);
    }

    async groupOrdersByDateAndAddress() {
        const grouped = {};
    
        this.milkOrders.forEach(order => {
            const orderDate = new Date(order.created_at);
            const dateStr = orderDate.toLocaleDateString('ru-RU', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
            });

            const cashierShortName = order.cashier;
            const fullAddress = order.cashier_address;
            
            if (!grouped[dateStr]) {
                grouped[dateStr] = {};
            }
            
            if (!grouped[dateStr][cashierShortName]) {
                grouped[dateStr][cashierShortName] = {
                    shortName: cashierShortName,
                    fullAddress: fullAddress,
                    orders: [],
                    items: {},
                    totalAmount: 0
                };
            }
    
            grouped[dateStr][cashierShortName].orders.push(order);

            order.items.forEach(item => {
                const productName = item.milk?.name_product || 'Товар';
                const quantity = item.quantity;
                const price = item.milk?.count;
                
                if (!grouped[dateStr][cashierShortName].items[productName]) {
                    grouped[dateStr][cashierShortName].items[productName] = {
                        quantity: 0,
                        price: price,
                        total: 0
                    };
                }
                
                grouped[dateStr][cashierShortName].items[productName].quantity += quantity;
                grouped[dateStr][cashierShortName].items[productName].total += price * quantity;

                grouped[dateStr][cashierShortName].totalAmount += price * quantity;
            });
        });
    
        return grouped;
    }
    
    async renderMilkOrdersByAddress() {
        const container = document.getElementById('admin-milk-orders-list');
        if (!container) return;
    
        const groupedByDate = await this.groupOrdersByDateAndAddress();
        const dates = Object.keys(groupedByDate).sort((a, b) => {
            const [dayA, monthA, yearA] = a.split('.');
            const [dayB, monthB, yearB] = b.split('.');
            return new Date(yearB, monthB-1, dayB) - new Date(yearA, monthA-1, dayA);
        });
    
        if (dates.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>Нет активных заказов</p>
                </div>
            `;
            return;
        }
    
        let html = '';
        
        dates.forEach(dateStr => {
            const addresses = groupedByDate[dateStr];

            let pendingCount = 0;
            let pendingOrderIds = [];
            
            Object.values(addresses).forEach(group => {
                group.orders.forEach(order => {
                    if (order.status === 'pending') {
                        pendingCount++;
                        pendingOrderIds.push(order.id);
                    }
                });
            });
            
            html += `
                <div class="date-section">
                    <div class="date-header-wrapper">
                        <h3 class="date-header">Заказы за ${dateStr}</h3>
                        ${pendingCount > 0 ? `
                            <button class="btn-confirm-all" onclick="admin.confirmAllOrdersForDate('${dateStr}')">
                                Подтвердить все (${pendingCount})
                            </button>
                        ` : ''}
                    </div>
                    <h4 class="section-subheader">Заказы</h4>
            `;
            
            Object.values(addresses).forEach(group => {
                const itemsList = Object.entries(group.items)
                    .map(([name, data]) => `${name} — ${data.quantity} шт.`)
                    .join('<br>');
    
                const orderCount = group.orders.length;
                const totalAmount = group.totalAmount || 0;
    
                html += `
                    <div class="admin-order-group">
                        <div class="admin-order-address-full">
                            ${group.fullAddress}
                        </div>
                        <div class="admin-order-items">
                            ${itemsList}
                        </div>
                        <div class="admin-order-footer">
                            <span class="admin-order-total">${orderCount} заказ(ов)</span>
                            <span class="admin-order-amount"><strong>${totalAmount.toLocaleString('ru-RU')} ₽</strong></span>
                        </div>
                    </div>
                `;
            });
            
            html += `</div>`;
        });
    
        container.innerHTML = html;
    }

    async confirmAllOrdersForDate(dateStr) {
        try {
            const [day, month, year] = dateStr.split('.').map(Number);
            const targetDate = new Date(year, month - 1, day);
            targetDate.setHours(0, 0, 0, 0);
            
            const nextDay = new Date(targetDate);
            nextDay.setDate(nextDay.getDate() + 1);
            
            const ordersToConfirm = this.milkOrders.filter(order => {
                const orderDate = new Date(order.created_at);
                return order.status === 'pending' && 
                       orderDate >= targetDate && 
                       orderDate < nextDay;
            });
            
            console.log(`Found ${ordersToConfirm.length} pending orders to confirm`);
            
            if (ordersToConfirm.length === 0) {
                app.showToast('Нет заказов для подтверждения');
                return;
            }

            const confirmPromises = ordersToConfirm.map(order => 
                api.post(`admin/milk-orders/${order.id}/status`, {
                    status: 'confirmed'
                })
            );
            
            const results = await Promise.all(confirmPromises);

            const successCount = results.filter(r => r?.status === 'success').length;
            const errorCount = results.length - successCount;
            
            if (successCount > 0) {
                app.showToast(`Подтверждено ${successCount} заказ(ов)`);

                await this.loadMilkOrders(['pending', 'confirmed']);
                await this.renderMilkOrdersByAddress();
                this.renderMilkStats();
            }
            
            if (errorCount > 0) {
                app.showToast(`${errorCount} заказов не подтверждено`);
            }
            
        } catch (error) {
            console.error('Error confirming orders:', error);
            app.showToast('Ошибка подтверждения заказов: ' + error.message);
        }
    }

    renderMilkStats() {
        const statsContainer = document.getElementById('admin-milk-stats');
        if (!statsContainer) return;

        statsContainer.innerHTML = `
            <div class="admin-stat-card">
                <span class="admin-stat-value">${this.milkStats.pending || 0}</span>
                <span class="admin-stat-label">Ожидают</span>
            </div>
            <div class="admin-stat-card">
                <span class="admin-stat-value">${this.milkStats.confirmed || 0}</span>
                <span class="admin-stat-label">Подтверждено</span>
            </div>
            <div class="admin-stat-card">
                <span class="admin-stat-value">${this.milkStats.problem || 0}</span>
                <span class="admin-stat-label">Подтверждено</span>
            </div>
            <div class="admin-stat-card">
                <span class="admin-stat-value">${this.milkStats.completed || 0}</span>
                <span class="admin-stat-label">Выполнено</span>
            </div>
            <div class="admin-stat-card">
                <span class="admin-stat-value">${this.milkStats.total || 0}</span>
                <span class="admin-stat-label">Всего</span>
            </div>
        `;
    }

    async exportMilkOrders() {
        try {
            const today = new Date();
            today.setHours(0, 0, 0, 0);

            const tommorow = new Date(today);
            tommorow.setDate(tommorow.getDate() + 1);

            const lastDayOrders = this.milkOrders.filter(order => {
                const orderDate = new Date(order.created_at);
                return orderDate >= today && orderDate < tommorow;
            });

            if (lastDayOrders.length === 0) {
                app.showToast('Нет заказов за последний день');
                return;
            }

            const grouped = this.groupOrdersByAddress(lastDayOrders);

            let exportText = `Добрый день! Заказ на завтра, ИП Тетрадзе, кофейни Тейку\n`;

            grouped.forEach(group => {
                const displayAddress = group.fullAddress;
                exportText += `\n${displayAddress}\n`;

                Object.entries(group.items).forEach(([name, data]) => {
                    if (typeof data === 'object' && data !== null) {
                        exportText += `${name} — ${data.quantity} шт.\n`;
                    } else {
                        exportText += `${name} — ${data} шт.\n`;
                    }
                });
            });

            try {
                await navigator.clipboard.writeText(exportText);
                app.showToast('Заказы скопированы в буфер обмена');
            } catch (error) {
                const textarea = document.createElement('textarea');
                textarea.value = exportText;
                textarea.style.position = 'fixed';
                textarea.style.opacity = '0';
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                app.showToast('Не удалось скопировать в буфер обмена');
            }

        } catch (error) {
            app.showToast('Ошибка экспорта: ' + error.message);
        }
    }

    async updateOrderStatus(orderId, newStatus) {
        try {
            const response = await api.post(`admin/milk-orders/${orderId}/status/`, {
                status: newStatus
            });

            if (response?.status === 'success') {
                app.showToast(response.message || 'Статус обновлён');
                await this.loadMilkOrders(['pending', 'confirmed']);
                await this.renderMilkOrdersByAddress();
                this.renderMilkStats();
            } else {
                app.showToast(response?.message || 'Ошибка обновления');
            }
        } catch (error) {
            console.error('Error updating order status:', error);
            app.showToast('Ошибка обновления статуса: ' + error.message);
        }
    }

    async bulkUpdateStatus(orderIds, newStatus) {
        if (!orderIds.length) {
            app.showToast('Выберите заказы');
            return;
        }

        try {
            const response = await api.post('admin/milk-orders/bulk-status/', {
                order_ids: orderIds,
                status: newStatus
            });

            if (!response.error) {
                app.showToast(response.message);
                await this.loadMilkOrders();
                this.renderMilkOrdersByAddress();
                this.renderMilkStats();
            } else {
                app.showToast((response.message || 'Ошибка обновления'));
            }
        } catch (error) {
            console.error('Error bulk updating status:', error);
            app.showToast('Ошибка обновления статусов');
        }
    }

    showTemporaryScreen(title, content) {
        const tempDiv = document.createElement('div');
        tempDiv.className = 'screen';
        tempDiv.id = 'temp-admin-screen';
        tempDiv.innerHTML = `
            <div class="screen-header">
                <button class="back-btn" onclick="app.goBack()">Назад</button>
                <h2>${title}</h2>
            </div>
            <div class="screen-content">
                ${content}
            </div>
        `;
        
        document.body.appendChild(tempDiv);
        app.showScreen('temp-admin-screen');
    }

    manageSchedule() {
        app.showToast('Управление графиком будет доступно в следующей версии');
    }
    
    exportData() {
        app.showToast('Экспорт данных будет доступен в следующей версии');
    }
}

window.admin = new Admin();