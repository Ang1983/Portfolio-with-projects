-- It was used in power_bi_homework.pbix --

-- 1. Топ-10 позиций по выручке + доля в общем обороте
SELECT 
    od.orderNumber,
    p.productName,
    od.quantityOrdered,
    od.priceEach,
    od.quantityOrdered * od.priceEach AS item_revenue,
    ROUND(
        (od.quantityOrdered * od.priceEach) * 100.0 / 
        SUM(od.quantityOrdered * od.priceEach) OVER (),
        2
    ) AS revenue_share_percent
FROM orderdetails od
JOIN products p ON od.productCode = p.productCode
ORDER BY item_revenue DESC
LIMIT 10;

-- 2. Заказы > 59 000 ₽ + сравнение с медианой всех заказов
SELECT 
    orderNumber,
    total,
    (SELECT MEDIAN(total) FROM (
        SELECT SUM(quantityOrdered * priceEach) AS total
        FROM orderdetails
        GROUP BY orderNumber
    )) AS median_order_value,
    CASE 
        WHEN total > 2.5 * (SELECT MEDIAN(total) FROM (
            SELECT SUM(quantityOrdered * priceEach) AS total
            FROM orderdetails
            GROUP BY orderNumber
        )) THEN 'very high'
        ELSE 'high'
    END AS tier
FROM (
    SELECT 
        orderNumber,
        SUM(quantityOrdered * priceEach) AS total
    FROM orderdetails
    GROUP BY orderNumber
) t
WHERE total > 59000
ORDER BY total DESC;

-- 3. Крупные заказы + статус и время выполнения (если shipped)
SELECT 
    o.orderNumber,
    o.orderDate,
    o.status,
    o.shippedDate,
    julianday(o.shippedDate) - julianday(o.orderDate) AS days_to_ship,
    t.total
FROM orders o
JOIN (
    SELECT 
        orderNumber,
        SUM(quantityOrdered * priceEach) AS total
    FROM orderdetails
    GROUP BY orderNumber
    HAVING total > 59000
) t ON o.orderNumber = t.orderNumber
ORDER BY t.total DESC;

-- 4. Клиенты с крупными заказами + частота заказов
SELECT 
    c.customerName,
    c.country,
    o.orderNumber,
    o.orderDate,
    o.status,
    t.total,
    customer_orders.order_count
FROM orders o
JOIN customers c ON o.customerNumber = c.customerNumber
JOIN (
    SELECT 
        orderNumber,
        SUM(quantityOrdered * priceEach) AS total
    FROM orderdetails
    GROUP BY orderNumber
    HAVING total > 59000
) t ON o.orderNumber = t.orderNumber
JOIN (
    SELECT 
        customerNumber,
        COUNT(*) AS order_count
    FROM orders
    GROUP BY customerNumber
) customer_orders ON c.customerNumber = customer_orders.customerNumber
ORDER BY t.total DESC;

-- 5. Топ-10 товаров по выручке + средняя цена и объём
SELECT 
    p.productName,
    p.productLine,
    SUM(od.quantityOrdered) AS total_quantity,
    AVG(od.priceEach) AS avg_price,
    SUM(od.quantityOrdered * od.priceEach) AS total_revenue
FROM orderdetails od
JOIN products p ON od.productCode = p.productCode
GROUP BY p.productCode, p.productName, p.productLine
ORDER BY total_revenue DESC
LIMIT 10;

-- 6. Менеджеры и их клиенты + кол-во клиентов на менеджера
SELECT 
    e.firstName,
    e.lastName,
    e.jobTitle,
    c.customerName,
    COUNT(c.customerNumber) OVER (PARTITION BY e.employeeNumber) AS clients_assigned
FROM employees e
LEFT JOIN customers c ON e.employeeNumber = c.salesRepEmployeeNumber
ORDER BY e.lastName, c.customerName;

-- 7. Руководители и их подчинённые + уровень должности
SELECT 
    boss.firstName || ' ' || boss.lastName AS manager,
    boss.jobTitle AS manager_role,
    emp.firstName || ' ' || emp.lastName AS report,
    emp.jobTitle AS report_role
FROM employees boss
LEFT JOIN employees emp ON boss.employeeNumber = emp.reportsTo
WHERE boss.jobTitle LIKE '%Manager%' OR boss.jobTitle LIKE '%VP%'
ORDER BY boss.lastName, emp.lastName;
