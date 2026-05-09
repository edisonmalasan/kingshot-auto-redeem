# Kingshot Auto Redeem CLI

## Local Setup

Follow these steps to set up and run the application:

1. **Clone the repository**

   ```bash
   git clone
   cd
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**
   - Windows:
     ```bash
     .venv\Scripts\activate
     ```
   - Mac/Linux:
     ```bash
     source .venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## How to Run

Start the application by running:

```bash
python main.py
```

## JSON State

Runtime JSON files live in `json/`:

- `json/config.json` stores app settings and API paths.
- `json/players.json` stores registered players and each player's redeemed codes.
- `json/known_codes.json` stores globally seen active codes so option 5 and auto-polling can detect new codes.
