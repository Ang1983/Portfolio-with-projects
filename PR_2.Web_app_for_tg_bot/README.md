# PR_2: Loyalty System (Telegram Mini App)

## The Problem
A coffee shop chain needs a loyalty system to increase customer retention and boost repeat sales.

## The Solution
Developed a comprehensive loyalty system based on a Telegram Mini App with the following functionality:
- Seamless customer registration via Telegram
- Bonus point accumulation for purchases
- Transaction and balance history tracking
- Admin panel for managing customers, promotions, and analytics

## Tech Stack
**Backend:**
- **Python 3.10+**
- **Django** - Web framework for building the REST API
- **PostgreSQL** - Relational database

**Frontend:**
- **JavaScript**
- **HTML5 / CSS3**
- **Telegram Web App API** - For seamless Telegram integration

**Tools:**
- **Git** - Version control
- **Postman** - API testing
- **Docker** - Containerization

## Project Structure

```markdown
PR_2.Web_app_for_tg_bot/
├── backend/
│   └── loyalty_backend/
│       ├── views.py          # API endpoints
│       ├── models.py         # Database models
│       ├── serializers.py    # Data serialization
│       ├── admin.py          # Django admin configuration
│       └── urls.py           # API routes
│   └── requirements.txt
├── frontend/
│   ├── index.html            # Main application page
│   └── js/
│       ├── profiles/         # Role-specific logic
│       │   ├── admin.js
│       │   ├── user.js
│       │   └── employee.js
│       ├── auth.js           # Authentication logic
│       ├── main.js           # Core methods (shared across profiles)
│       ├── coupon.js         # Coupon handling logic
│       └── qr_scanner.js     # QR code scanning functionality
└── README.md
```

## Development Status

In the final stages

Implemented:
- PostgreSQL database setup with migrations
- REST API for managing customers and transactions
- Frontend interface for the Telegram Mini App
- Integration with Telegram Bot API
- Server deployment
- Comprehensive testing

In progress:
- Debugging temporary synchronization gateways
- Integration with Telegram Wallet
