# League Review

A full-stack application with FastAPI backend and React frontend for reviewing League of Legends matches.

## Project Structure

```
league-review/
├── backend/           # FastAPI backend
│   ├── main.py       # Main FastAPI application
│   ├── app/          # Application modules
│   ├── alembic/      # Database migrations
│   └── requirements.txt
└── frontend/         # React frontend
    ├── package.json
    ├── public/
    └── src/
```

## Setup Instructions

### Backend Setup

1. Create and activate a virtual environment:

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables:

   - Copy `.env.example` to `.env` (if available) and update the values

4. Run database migrations:

```bash
alembic upgrade head
```

5. Run the backend server:

```bash
uvicorn main:app --reload
```

### Frontend Setup

1. Install dependencies:

```bash
cd frontend
npm install
```

2. Set up environment variables:

   - Copy `.env.example` to `.env` (if available) and update the values

3. Run the development server:

```bash
npm start
```

## Development

- Backend runs on http://localhost:8000
- Frontend runs on http://localhost:3000
- API documentation available at http://localhost:8000/docs

## GitHub Repository

This project is hosted on GitHub. To clone the repository:

```bash
git clone https://github.com/yourusername/league-review.git
cd league-review
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
