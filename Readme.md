# PBL Project

This project is a Problem-Based Learning (PBL) application featuring an AI-powered student agent discussion panel. It consists of a Vue.js frontend and a Python FastAPI backend using LangChain.

## Project Structure

```
PBL/
├── backend/      # FastAPI backend application
│   ├── agents.py
│   ├── server.py
│   ├── graph.py
│   └── requirements.txt
├── frontend/     # Vue.js frontend application
│   ├── src/
│   └── package.json
└── Readme.md
```

## Setup

### Backend

1.  Navigate to the backend directory:
    ```bash
    cd PBL/backend
    ```
2.  Create a Python virtual environment and activate it. For example, using Conda with Python 3.9:
    ```bash
    conda create --name pbl-env python=3.9 -y
    conda activate pbl-env
    ```
3.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Frontend

1.  Navigate to the frontend directory:
    ```bash
    cd PBL/frontend
    ```
2.  Install the required Node.js dependencies:
    ```bash
    npm install
    ```

## Running the Application

You will need two separate terminals to run the backend and frontend servers.

1.  **Run the Backend Server**
    *   From the `PBL/` root directory, run:
        ```bash
        uvicorn backend.server:app_fastapi --reload
        ```
    *   The backend will be available at `http://127.0.0.1:8000`.

2.  **Run the Frontend Development Server**
    *   From the `PBL/frontend/` directory, run:
        ```bash
        npm run dev
        ```
    *   The frontend will typically be available at `http://localhost:5173`.

## Testing

To run the backend agent tests, navigate to the `PBL/` root directory and run:
```bash
python -m unittest backend/test_agents.py
```

