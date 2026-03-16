# coins-ex

This project is designed to fetch cryptocurrency exchange balances from various platforms, including Binance, OKX, Bybit, and Bitget. 

## Project Structure

```
coins-ex
├── src
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── exchanges
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── binance.py
│   │   ├── okx.py
│   │   ├── bybit.py
│   │   └── bitget.py
│   └── utils
│       ├── __init__.py
│       └── helpers.py
├── tests
│   ├── __init__.py
│   ├── test_binance.py
│   ├── test_okx.py
│   ├── test_bybit.py
│   └── test_bitget.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   ```
2. Navigate to the project directory:
   ```
   cd coins-ex
   ```
3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Configuration

Create a `.env` file in the root directory and add your API keys and other configuration settings as specified in the `.env.example` file.

## Usage

Run the application using:
```
python src/main.py
```

This will initiate the process of fetching balances from the configured exchanges.

## Testing

To run the tests, use:
```
pytest
```

This will execute all unit tests defined in the `tests` directory.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.